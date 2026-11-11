"""Dispatcher:查找 → Schema 校验 → 权限 → 超时执行 → 结构化结果(Level 0)。

这是 Level 0 最关键的一段:任何非法调用在这里被明确拒绝并留下可追踪
Trace,任何工具异常都被转为结构化 ToolResult,绝不向调用方外泄堆栈。
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Mapping

from tools.protocol import (
    MAX_PAYLOAD_BYTES,
    ErrorCode,
    ToolCall,
    ToolCallRejected,
    ToolDefinition,
    ToolExecutionFailure,
    ToolResult,
    ok_result,
    parse_tool_call,
    rejected_result,
)
from tools.registry import ToolRegistry
from tools.schema import validate_arguments
from tools.trace import TraceRecorder

DEFAULT_TIMEOUT_SECONDS = 5.0


def _best_effort_call_id(raw) -> str:
    """信封解析失败时尽力保留 call_id,让拒绝结果仍可被关联追踪。"""
    envelope = None
    if isinstance(raw, Mapping):
        envelope = raw
    elif isinstance(raw, (str, bytes, bytearray)) and len(raw) <= MAX_PAYLOAD_BYTES:
        try:
            decoded = json.loads(raw)
            envelope = decoded if isinstance(decoded, Mapping) else None
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return ""
    if envelope is None:
        return ""
    value = envelope.get("call_id")
    return value if isinstance(value, str) else ""


@dataclass(frozen=True)
class PermissionPolicy:
    """权限白名单:required_permission 为 None 的工具总是放行。

    审批管"应不应该",隔离管"伤不伤得到"(原则 15);
    Level 0 只有这一层最小声明式白名单。
    """

    allowed: frozenset[str]

    def allows(self, required: str | None) -> bool:
        return required is None or required in self.allowed


class Dispatcher:
    def __init__(
        self,
        registry: ToolRegistry,
        permissions: PermissionPolicy | None = None,
        trace: TraceRecorder | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._registry = registry
        self._permissions = permissions
        self._trace = trace
        self._timeout_seconds = timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tool-exec")

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    @property
    def trace(self) -> TraceRecorder | None:
        return self._trace

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def __enter__(self) -> "Dispatcher":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def execute_envelope(self, raw) -> ToolResult:
        """解析原始信封(JSON 字符串或 Mapping)并执行;拒绝也是结构化结果。"""
        started = time.perf_counter()
        try:
            call = parse_tool_call(raw)
        except ToolCallRejected as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            self._emit("call_rejected", reason=exc.code, detail=exc.message,
                       call_id=_best_effort_call_id(raw))
            return rejected_result(call_id=_best_effort_call_id(raw), tool="",
                                   code=exc.code, message=exc.message,
                                   duration_ms=duration_ms)
        return self.execute(call)

    def execute(self, call: ToolCall) -> ToolResult:
        started = time.perf_counter()
        self._emit("tool_call_received", call_id=call.call_id, tool=call.name)

        tool = self._registry.get(call.name)
        if tool is None:
            return self._reject(call, ErrorCode.UNKNOWN_TOOL,
                                f"tool {call.name!r} is not registered", started)

        definition = tool.definition
        violations = validate_arguments(call.arguments, definition.parameters)
        if violations:
            first = violations[0]
            return self._reject(call, ErrorCode.SCHEMA_VIOLATION, first.message, started)

        if self._permissions is not None and not self._permissions.allows(definition.required_permission):
            return self._reject(
                call,
                ErrorCode.PERMISSION_DENIED,
                f"tool {call.name!r} requires permission "
                f"{definition.required_permission!r} which is not granted",
                started,
            )

        try:
            future = self._executor.submit(tool.execute, dict(call.arguments))
            output = future.result(timeout=self._timeout_seconds)
        except ToolExecutionFailure as exc:
            return self._reject(call, exc.code, exc.message, started)
        except TimeoutError:
            # Level 0 的超时只是放弃等待,不终止线程;真正的执行隔离在 Level 3。
            return self._reject(call, ErrorCode.TIMEOUT,
                                f"execution exceeded {self._timeout_seconds}s", started)
        except Exception as exc:
            return self._reject(call, ErrorCode.TOOL_ERROR,
                                f"{type(exc).__name__}: {exc}"[:300], started)

        duration_ms = int((time.perf_counter() - started) * 1000)
        self._emit("tool_executed", call_id=call.call_id, tool=call.name,
                   status="ok", duration_ms=duration_ms)
        return ok_result(call.call_id, call.name, output, duration_ms=duration_ms)

    def _reject(self, call: ToolCall, code: str, message: str, started: float) -> ToolResult:
        duration_ms = int((time.perf_counter() - started) * 1000)
        self._emit("tool_rejected", call_id=call.call_id, tool=call.name,
                   status="error", reason=code, duration_ms=duration_ms)
        return rejected_result(call.call_id, call.name, code, message,
                               duration_ms=duration_ms)

    def _emit(self, event: str, **fields) -> None:
        if self._trace is not None:
            self._trace.emit(event, **fields)

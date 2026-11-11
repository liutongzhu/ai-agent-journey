"""ToolCall 协议:结构化调用、统一结果格式与信封解析(Level 0)。

信封层是传输防御边界:无论调用来自模型 API 的结构化输出还是原始 JSON 载荷,
都必须先通过本模块解析与类型校验,才允许进入 Dispatcher。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

PROTOCOL_VERSION = 1

# 信封反序列化大小上限:超长输入的第一道防线(Boss 战第 5 类)。
MAX_PAYLOAD_BYTES = 64 * 1024

_ENVELOPE_KEYS = frozenset({"protocol_version", "call_id", "name", "arguments"})


class ErrorCode:
    INVALID_JSON = "invalid_json"
    INVALID_CALL = "invalid_call"
    UNSUPPORTED_VERSION = "unsupported_version"
    INPUT_TOO_LARGE = "input_too_large"
    UNKNOWN_TOOL = "unknown_tool"
    SCHEMA_VIOLATION = "schema_violation"
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    TOOL_ERROR = "tool_error"
    TOO_MANY_TOOL_CALLS = "too_many_tool_calls"
    FILE_NOT_FOUND = "file_not_found"


class ToolCallRejected(Exception):
    """信封解析或校验拒绝一次调用,携带稳定错误码。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ToolExecutionFailure(Exception):
    """工具执行中的预期失败,由工具主动抛出,Dispatcher 转为结构化结果。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ToolDefinition:
    """工具契约:白名单注册时的最小描述。

    required_permission 为 None 表示无权限要求;
    否则必须是 PermissionPolicy 允许集中声明的权限标识(如 "fs.read")。
    """

    name: str
    description: str
    parameters: dict
    required_permission: str | None = None


@dataclass(frozen=True)
class ToolCall:
    """一次工具调用(已通过信封解析,模型输出仍视为不可信输入)。"""

    call_id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class ToolError:
    code: str
    message: str


@dataclass(frozen=True)
class ToolResult:
    """统一结果格式:成功带 output,失败带 error;两者互斥。"""

    protocol_version: int
    call_id: str
    tool: str
    status: str  # "ok" | "error"
    output: str | None = None
    error: ToolError | None = None
    duration_ms: int | None = None

    def to_dict(self) -> dict:
        data: dict[str, Any] = {
            "protocol_version": self.protocol_version,
            "call_id": self.call_id,
            "tool": self.tool,
            "status": self.status,
        }
        if self.output is not None:
            data["output"] = self.output
        if self.error is not None:
            data["error"] = {"code": self.error.code, "message": self.error.message}
        if self.duration_ms is not None:
            data["duration_ms"] = self.duration_ms
        return data

    def feedback_text(self) -> str:
        """回传给 LLM 的单行文本:成功给输出,失败给错误码与原因。"""
        if self.status == "ok":
            return self.output or ""
        assert self.error is not None
        return f"error {self.error.code}: {self.error.message}"


def parse_tool_call(raw: str | bytes | Mapping) -> ToolCall:
    """解析信封为 ToolCall。

    raw 可以是已结构化的 Mapping,也可以是 JSON 字符串/字节(原始传输格式)。
    任何不符合协议的情况都抛 ToolCallRejected,绝不返回半可信对象。
    """
    if isinstance(raw, (str, bytes, bytearray)):
        if len(raw) > MAX_PAYLOAD_BYTES:
            raise ToolCallRejected(
                ErrorCode.INPUT_TOO_LARGE,
                f"payload exceeds {MAX_PAYLOAD_BYTES} bytes",
            )
        try:
            envelope = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ToolCallRejected(ErrorCode.INVALID_JSON, f"invalid JSON: {exc.msg}") from exc
    else:
        envelope = raw

    if not isinstance(envelope, Mapping):
        raise ToolCallRejected(ErrorCode.INVALID_CALL, "envelope must be a JSON object")

    unknown = set(envelope) - _ENVELOPE_KEYS
    if unknown:
        raise ToolCallRejected(
            ErrorCode.INVALID_CALL, f"unknown envelope fields: {sorted(unknown)}"
        )
    missing = _ENVELOPE_KEYS - set(envelope)
    if missing:
        raise ToolCallRejected(
            ErrorCode.INVALID_CALL, f"missing envelope fields: {sorted(missing)}"
        )

    if envelope["protocol_version"] != PROTOCOL_VERSION:
        raise ToolCallRejected(
            ErrorCode.UNSUPPORTED_VERSION,
            f"expected protocol_version={PROTOCOL_VERSION!r}, got {envelope['protocol_version']!r}",
        )

    call_id = envelope["call_id"]
    name = envelope["name"]
    arguments = envelope["arguments"]
    if not isinstance(call_id, str) or not call_id:
        raise ToolCallRejected(ErrorCode.INVALID_CALL, "call_id must be a non-empty string")
    if not isinstance(name, str) or not name:
        raise ToolCallRejected(ErrorCode.INVALID_CALL, "name must be a non-empty string")
    if not isinstance(arguments, dict):
        raise ToolCallRejected(ErrorCode.INVALID_CALL, "arguments must be a JSON object")

    return ToolCall(call_id=call_id, name=name, arguments=dict(arguments))


def from_tool_use(block: Mapping) -> ToolCall:
    """把模型 API 的结构化 tool_use block 转为 ToolCall(类型校验不可省略)。"""
    if not isinstance(block, Mapping):
        raise ToolCallRejected(ErrorCode.INVALID_CALL, "tool_use block must be an object")
    call_id = block.get("id")
    name = block.get("name")
    arguments = block.get("input")
    if not isinstance(call_id, str) or not call_id:
        raise ToolCallRejected(ErrorCode.INVALID_CALL, "tool_use.id must be a non-empty string")
    if not isinstance(name, str) or not name:
        raise ToolCallRejected(ErrorCode.INVALID_CALL, "tool_use.name must be a non-empty string")
    if not isinstance(arguments, Mapping):
        raise ToolCallRejected(ErrorCode.INVALID_CALL, "tool_use.input must be an object")
    return ToolCall(call_id=call_id, name=name, arguments=dict(arguments))


def rejected_result(call_id: str, tool: str, code: str, message: str,
                    duration_ms: int | None = None) -> ToolResult:
    """构造统一的拒绝结果。"""
    return ToolResult(
        protocol_version=PROTOCOL_VERSION,
        call_id=call_id,
        tool=tool,
        status="error",
        error=ToolError(code=code, message=message),
        duration_ms=duration_ms,
    )


def ok_result(call_id: str, tool: str, output: str,
              duration_ms: int | None = None) -> ToolResult:
    return ToolResult(
        protocol_version=PROTOCOL_VERSION,
        call_id=call_id,
        tool=tool,
        status="ok",
        output=output,
        duration_ms=duration_ms,
    )

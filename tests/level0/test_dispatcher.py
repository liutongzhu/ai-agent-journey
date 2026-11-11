"""Level 0: Dispatcher 查找 → 校验 → 权限 → 执行 → 结构化结果。"""

import json
import time
from pathlib import Path

import pytest

from tools.dispatcher import Dispatcher, PermissionPolicy
from tools.echo import EchoTool
from tools.protocol import (
    PROTOCOL_VERSION,
    ErrorCode,
    ToolCall,
    ToolDefinition,
    ToolExecutionFailure,
)
from tools.read_file import ReadFileTool
from tools.registry import ToolRegistry
from tools.trace import TraceRecorder


class SlowTool:
    @property
    def definition(self):
        return ToolDefinition(
            name="slow",
            description="always sleeps",
            parameters={
                "type": "object",
                "properties": {"seconds": {"type": "number"}},
                "required": ["seconds"],
                "additionalProperties": False,
            },
        )

    def execute(self, arguments):
        time.sleep(arguments["seconds"])
        return "done"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "sample.txt").write_text("hello", encoding="utf-8")
    return tmp_path


@pytest.fixture
def registry(workspace: Path) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(ReadFileTool(workspace))
    return registry


def make_dispatcher(registry, trace=None, permissions=None, timeout_seconds=5.0):
    return Dispatcher(registry, permissions=permissions, trace=trace,
                      timeout_seconds=timeout_seconds)


def test_echo_happy_path(registry):
    with make_dispatcher(registry) as dispatcher:
        result = dispatcher.execute(ToolCall("c1", "echo", {"text": "ping"}))
    assert result.status == "ok"
    assert result.output == "ping"
    assert result.protocol_version == PROTOCOL_VERSION
    assert isinstance(result.duration_ms, int) and result.duration_ms >= 0


def test_unknown_tool_rejected(registry):
    with make_dispatcher(registry) as dispatcher:
        result = dispatcher.execute(ToolCall("c2", "rm_rf", {}))
    assert result.status == "error"
    assert result.error.code == ErrorCode.UNKNOWN_TOOL
    assert "rm_rf" in result.error.message


def test_schema_violation_rejected(registry):
    with make_dispatcher(registry) as dispatcher:
        result = dispatcher.execute(ToolCall("c3", "echo", {"text": "hi", "extra": 1}))
    assert result.error.code == ErrorCode.SCHEMA_VIOLATION
    assert "unknown field 'extra'" in result.error.message


def test_permission_denied_when_not_granted(registry):
    with make_dispatcher(registry, permissions=PermissionPolicy(allowed=frozenset())) as dispatcher:
        denied = dispatcher.execute(ToolCall("c4", "read_file", {"path": "sample.txt"}))
        allowed = dispatcher.execute(ToolCall("c5", "echo", {"text": "hi"}))
    assert denied.error.code == ErrorCode.PERMISSION_DENIED
    assert denied.tool == "read_file"
    assert allowed.status == "ok"  # 无权限要求的工具不受影响


def test_permission_granted_allows_read(registry):
    policy = PermissionPolicy(allowed=frozenset({"fs.read"}))
    with make_dispatcher(registry, permissions=policy) as dispatcher:
        result = dispatcher.execute(ToolCall("c6", "read_file", {"path": "sample.txt"}))
    assert result.status == "ok"
    assert result.output == "hello"


def test_execute_envelope_with_json_string(registry):
    envelope = json.dumps({"protocol_version": PROTOCOL_VERSION, "call_id": "c7",
                           "name": "echo", "arguments": {"text": "raw"}})
    with make_dispatcher(registry) as dispatcher:
        result = dispatcher.execute_envelope(envelope)
    assert result.status == "ok"
    assert result.output == "raw"


def test_envelope_invalid_json_returns_structured_error(registry):
    with make_dispatcher(registry) as dispatcher:
        result = dispatcher.execute_envelope("{not json")
    assert result.status == "error"
    assert result.error.code == ErrorCode.INVALID_JSON
    assert result.call_id == ""


def test_tool_failure_code_preserved(registry):
    with make_dispatcher(registry) as dispatcher:
        result = dispatcher.execute(ToolCall("c8", "read_file", {"path": "missing.txt"}))
    assert result.error.code == ErrorCode.FILE_NOT_FOUND


def test_unexpected_exception_becomes_structured_error():
    class ExplodingTool:
        @property
        def definition(self):
            return ToolDefinition(
                name="explode",
                description="always raises",
                parameters={
                    "type": "object",
                    "properties": {"x": {"type": "string"}},
                    "required": ["x"],
                    "additionalProperties": False,
                },
            )

        def execute(self, arguments):
            raise ValueError("boom")

    registry = ToolRegistry()
    registry.register(ExplodingTool())
    with make_dispatcher(registry) as dispatcher:
        result = dispatcher.execute(ToolCall("c9", "explode", {"x": "y"}))
    assert result.error.code == ErrorCode.TOOL_ERROR
    assert "ValueError" in result.error.message
    assert "boom" in result.error.message


def test_timeout_returns_structured_error():
    registry = ToolRegistry()
    registry.register(SlowTool())
    with make_dispatcher(registry, timeout_seconds=0.1) as dispatcher:
        result = dispatcher.execute(ToolCall("c10", "slow", {"seconds": 0.6}))
    assert result.error.code == ErrorCode.TIMEOUT
    assert "0.1" in result.error.message


def test_trace_restores_full_call(registry):
    trace = TraceRecorder()
    with make_dispatcher(registry, trace=trace) as dispatcher:
        dispatcher.execute(ToolCall("c11", "echo", {"text": "hi"}))
        dispatcher.execute(ToolCall("c12", "nope", {}))
    events = trace.events
    assert [e["event"] for e in events] == [
        "tool_call_received", "tool_executed", "tool_call_received", "tool_rejected",
    ]
    assert events[0]["tool"] == "echo" and events[1]["call_id"] == "c11"
    assert events[3]["reason"] == ErrorCode.UNKNOWN_TOOL


def test_trace_does_not_record_argument_values(registry):
    secret = "super_secret_argument_value"
    trace = TraceRecorder()
    with make_dispatcher(registry, trace=trace) as dispatcher:
        dispatcher.execute(ToolCall("c13", "echo", {"text": secret}))
    rendered = json.dumps(trace.events)
    assert secret not in rendered

"""Boss 战(Level 0):五类非法调用全部被明确拒绝,且原因可追踪。

对应 docs/levels/level-0.md Boss Challenge:
1. 非法 JSON
2. 未注册工具名
3. 参数类型错误
4. 多余参数
5. 超长输入
"""

import json
from pathlib import Path

import pytest

from tools.dispatcher import Dispatcher, PermissionPolicy
from tools.echo import EchoTool
from tools.protocol import (
    PROTOCOL_VERSION,
    ErrorCode,
    ToolResult,
)
from tools.read_file import ReadFileTool
from tools.registry import ToolRegistry
from tools.trace import TraceRecorder

REPO_ROOT = Path(__file__).resolve().parents[2]


def envelope(name="echo", arguments=None, call_id="boss-1", version=PROTOCOL_VERSION):
    return json.dumps({
        "protocol_version": version,
        "call_id": call_id,
        "name": name,
        "arguments": arguments if arguments is not None else {"text": "hi"},
    })


@pytest.fixture
def boss_setup(tmp_path: Path):
    (tmp_path / "sample.txt").write_text("hello", encoding="utf-8")
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(ReadFileTool(tmp_path))
    trace = TraceRecorder()
    dispatcher = Dispatcher(
        registry,
        permissions=PermissionPolicy(allowed=frozenset({"fs.read"})),
        trace=trace,
    )
    return dispatcher, trace


def assert_rejected(result: ToolResult, code: str, call_id: str):
    assert result.status == "error", f"expected rejection, got ok: {result.to_dict()}"
    assert result.error is not None
    assert result.error.code == code
    assert result.error.message  # 拒绝必须带可读原因
    assert result.call_id == call_id
    assert result.duration_ms is not None


class TestBossFiveIllegalCalls:
    def test_1_invalid_json(self, boss_setup):
        dispatcher, trace = boss_setup
        result = dispatcher.execute_envelope('{"protocol_version": 1, "call_id": ')
        assert_rejected(result, ErrorCode.INVALID_JSON, call_id="")
        assert any(
            e["event"] == "call_rejected" and e["reason"] == ErrorCode.INVALID_JSON
            for e in trace.events
        )

    def test_2_unregistered_tool(self, boss_setup):
        dispatcher, trace = boss_setup
        result = dispatcher.execute_envelope(envelope(name="delete_everything"))
        assert_rejected(result, ErrorCode.UNKNOWN_TOOL, call_id="boss-1")
        assert "delete_everything" in result.error.message

    def test_3_wrong_parameter_type(self, boss_setup):
        dispatcher, trace = boss_setup
        result = dispatcher.execute_envelope(envelope(arguments={"text": 123}))
        assert_rejected(result, ErrorCode.SCHEMA_VIOLATION, call_id="boss-1")
        assert "type_mismatch" in result.error.message or "must be string" in result.error.message

    def test_4_extra_parameters(self, boss_setup):
        dispatcher, trace = boss_setup
        result = dispatcher.execute_envelope(
            envelope(arguments={"text": "hi", "mode": "dangerous"}))
        assert_rejected(result, ErrorCode.SCHEMA_VIOLATION, call_id="boss-1")
        assert "'mode'" in result.error.message

    def test_5_oversized_input(self, boss_setup):
        dispatcher, trace = boss_setup

        # 5a. 参数超过工具 Schema 的 maxLength
        result = dispatcher.execute_envelope(
            envelope(arguments={"text": "x" * 10_000}))
        assert_rejected(result, ErrorCode.SCHEMA_VIOLATION, call_id="boss-1")

        # 5b. 信封整体超过传输大小上限
        result = dispatcher.execute_envelope(envelope(arguments={"text": "x" * 100_000}))
        assert_rejected(result, ErrorCode.INPUT_TOO_LARGE, call_id="")

    def test_version_mismatch_rejected(self, boss_setup):
        dispatcher, _ = boss_setup
        result = dispatcher.execute_envelope(envelope(version=999))
        assert_rejected(result, ErrorCode.UNSUPPORTED_VERSION, call_id="boss-1")

    def test_every_rejection_is_traceable(self, boss_setup):
        dispatcher, trace = boss_setup
        dispatcher.execute_envelope('not json at all')
        dispatcher.execute_envelope(envelope(name="ghost_tool"))
        dispatcher.execute_envelope(envelope(arguments={"text": 1}))
        dispatcher.execute_envelope(envelope(arguments={"text": "hi", "x": 1}))
        dispatcher.execute_envelope(envelope(arguments={"text": "x" * 10_000}))

        reasons = [e.get("reason") for e in trace.events if e["event"] in ("call_rejected", "tool_rejected")]
        assert reasons == [
            ErrorCode.INVALID_JSON,
            ErrorCode.UNKNOWN_TOOL,
            ErrorCode.SCHEMA_VIOLATION,
            ErrorCode.SCHEMA_VIOLATION,
            ErrorCode.SCHEMA_VIOLATION,
        ]


class TestSecurityGuards:
    """胜利条件的静态守卫:源码层禁止 shell=True 与 os.system。"""

    SOURCE_DIRS = ["tools", "agent"]

    @pytest.mark.parametrize("pattern", ["shell=True", "os.system", "subprocess.Popen("])
    def test_no_shell_execution_in_sources(self, pattern):
        violations = []
        for dir_name in self.SOURCE_DIRS:
            for py_file in (REPO_ROOT / dir_name).rglob("*.py"):
                if "__pycache__" in py_file.parts:
                    continue
                if pattern in py_file.read_text(encoding="utf-8"):
                    violations.append(str(py_file))
        assert violations == [], f"forbidden pattern {pattern!r} found in: {violations}"

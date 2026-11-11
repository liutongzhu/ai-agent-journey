"""Level 0: 单轮 Harness 完整闭环(Mock LLM,确定性)。"""

from pathlib import Path

import pytest

from agent import AgentHarness, LLMResponse, MockLLMClient
from tools import (
    Dispatcher,
    EchoTool,
    PermissionPolicy,
    ReadFileTool,
    ToolCall,
    ToolRegistry,
    TraceRecorder,
)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "sample.txt").write_text("hello", encoding="utf-8")
    return tmp_path


@pytest.fixture
def dispatcher(workspace: Path):
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(ReadFileTool(workspace))
    trace = TraceRecorder()
    with Dispatcher(registry,
                    permissions=PermissionPolicy(allowed=frozenset({"fs.read"})),
                    trace=trace) as dispatcher:
        yield dispatcher, trace


def decision_with(*calls: ToolCall) -> LLMResponse:
    return LLMResponse(
        text=None,
        tool_calls=calls,
        raw_content=[
            {"type": "tool_use", "id": c.call_id, "name": c.name, "input": c.arguments}
            for c in calls
        ],
    )


def test_full_chain_tool_call_to_final_answer(dispatcher):
    dispatcher, trace = dispatcher
    client = MockLLMClient([
        decision_with(ToolCall("call_1", "echo", {"text": "ping"})),
        LLMResponse(text="echo 已执行,结果是 ping"),
    ])
    harness = AgentHarness(client, dispatcher, trace=trace)

    run = harness.run("请 echo 一下 ping")

    assert run.final_text == "echo 已执行,结果是 ping"
    assert run.all_tools_ok
    assert run.tool_results[0].output == "ping"

    # 第二次请求应包含 assistant tool_use 与 user tool_result 的完整回传
    followup = client.received_requests[1]
    roles = [m["role"] for m in followup["messages"]]
    assert roles == ["user", "assistant", "user"]
    tool_result_block = followup["messages"][2]["content"][0]
    assert tool_result_block == {
        "type": "tool_result",
        "tool_use_id": "call_1",
        "content": "ping",
    }

    event_names = [e["event"] for e in run.trace_events]
    assert event_names == [
        "run_started", "llm_decision",
        "tool_call_received", "tool_executed",
        "run_finished",
    ]


def test_multiple_tool_calls_all_dispatched(dispatcher, workspace):
    dispatcher, _ = dispatcher
    client = MockLLMClient([
        decision_with(
            ToolCall("call_1", "echo", {"text": "hi"}),
            ToolCall("call_2", "read_file", {"path": "sample.txt"}),
        ),
        LLMResponse(text="done"),
    ])
    run = AgentHarness(client, dispatcher).run("task")

    assert [r.tool for r in run.tool_results] == ["echo", "read_file"]
    assert run.tool_results[1].output == "hello"


def test_text_only_response_skips_dispatch(dispatcher):
    dispatcher, _ = dispatcher
    client = MockLLMClient([LLMResponse(text="直接回答")])
    run = AgentHarness(client, dispatcher).run("task")
    assert run.final_text == "直接回答"
    assert run.tool_results == []


def test_tool_call_cap_enforced(dispatcher):
    dispatcher, _ = dispatcher
    calls = tuple(ToolCall(f"c{i}", "echo", {"text": str(i)}) for i in range(5))
    client = MockLLMClient([decision_with(*calls), LLMResponse(text="done")])
    harness = AgentHarness(client, dispatcher, max_tool_calls_per_run=2)
    run = harness.run("task")

    assert len(run.tool_results) == 5
    assert run.tool_results[0].status == "ok"
    assert run.tool_results[1].status == "ok"
    assert run.tool_results[2].error.code == "too_many_tool_calls"


def test_mock_script_exhaustion_fails_honestly(dispatcher):
    dispatcher, _ = dispatcher
    client = MockLLMClient([])  # 没有任何响应脚本
    with pytest.raises(RuntimeError, match="exhausted"):
        AgentHarness(client, dispatcher).run("task")


def test_final_response_with_extra_tool_calls_is_recorded(dispatcher):
    dispatcher, trace = dispatcher
    client = MockLLMClient([
        decision_with(ToolCall("call_1", "echo", {"text": "hi"})),
        decision_with(ToolCall("call_2", "echo", {"text": "again"})),
    ])
    run = AgentHarness(client, dispatcher, trace=trace).run("task")

    assert run.final_text == ""
    events = [e["event"] for e in run.trace_events]
    assert "final_response_has_unexecuted_tool_calls" in events

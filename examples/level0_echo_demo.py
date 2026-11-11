"""Level 0 Demo:第一次工具调用。

默认 mock 模式(确定性脚本,不需要 API Key):
    python -m examples.level0_echo_demo

live 模式(真实 Anthropic API,需先 export ANTHROPIC_API_KEY):
    python -m examples.level0_echo_demo --live
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from agent import AgentHarness, AnthropicLLMClient, LLMResponse, MockLLMClient
from tools import (
    Dispatcher,
    EchoTool,
    PermissionPolicy,
    ReadFileTool,
    ToolCall,
    ToolRegistry,
    ToolResult,
    TraceRecorder,
)

SAMPLE_TEXT = "hello from level 0\n第一声 echo 来自主工具区。"


def build_workspace() -> Path:
    root = Path(tempfile.mkdtemp(prefix="level0-workspace-"))
    (root / "sample.txt").write_text(SAMPLE_TEXT, encoding="utf-8")
    (root / "notes").mkdir()
    (root / "notes" / "nested.txt").write_text("nested file ok", encoding="utf-8")
    return root


def build_harness(workspace: Path, live: bool) -> tuple[AgentHarness, TraceRecorder, object]:
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(ReadFileTool(workspace))

    trace = TraceRecorder()
    dispatcher = Dispatcher(
        registry,
        permissions=PermissionPolicy(allowed=frozenset({"fs.read"})),
        trace=trace,
    )

    if live:
        client = AnthropicLLMClient()
        task = (
            "请依次完成两件事:1) 用 echo 工具原样返回这句话;"
            "2) 用 read_file 读取 sample.txt。然后汇总两个结果给出最终回答。"
        )
    else:
        client = MockLLMClient([
            LLMResponse(
                text=None,
                tool_calls=(
                    ToolCall(call_id="call_1", name="echo",
                             arguments={"text": "hello from level 0"}),
                    ToolCall(call_id="call_2", name="read_file",
                             arguments={"path": "sample.txt"}),
                ),
                raw_content=[
                    {"type": "tool_use", "id": "call_1", "name": "echo",
                     "input": {"text": "hello from level 0"}},
                    {"type": "tool_use", "id": "call_2", "name": "read_file",
                     "input": {"path": "sample.txt"}},
                ],
            ),
            LLMResponse(text="echo 返回与输入一致;sample.txt 内容为 "
                             "'hello from level 0 / 第一声 echo 来自主工具区。'"),
        ])
        task = "复述一句话并读取 sample.txt"

    harness = AgentHarness(client, dispatcher, trace=trace)
    return harness, trace, task


def print_result(run) -> None:
    print("== trace ==")
    for line in trace_lines(run.trace_events):
        print(line)
    print("== tool results ==")
    for result in run.tool_results:
        print(json.dumps(result.to_dict(), ensure_ascii=False))
    print("== final answer ==")
    print(run.final_text)


def trace_lines(events) -> list[str]:
    recorder = TraceRecorder()
    recorder.events = list(events)
    return recorder.lines()


def main() -> int:
    parser = argparse.ArgumentParser(description="Level 0: 第一次工具调用")
    parser.add_argument("--live", action="store_true",
                        help="使用真实 Anthropic API(需 ANTHROPIC_API_KEY)")
    parser.add_argument("--task", default=None, help="自定义任务(live 模式)")
    args = parser.parse_args()

    try:
        workspace = build_workspace()
        harness, _trace, task = build_harness(workspace, args.live)
        if args.task:
            task = args.task
        print(f"workspace: {workspace}")
        print(f"mode: {'live(anthropic api)' if args.live else 'mock(确定性脚本,未调用真实模型)'}")
        print(f"task: {task}")
        run = harness.run(task)
    except RuntimeError as exc:
        print(f"demo failed: {exc}", file=sys.stderr)
        return 1
    print()
    print_result(run)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""最小 Harness(Level 0):单轮「决策 → 工具执行 → 结果回传 → 最终回答」。

这是工具调用的完整闭环,不是 Agent Loop——多步循环、预算与停止策略
属于 Level 1。本轮内工具调用数量有硬上限,防止失控模型拖垮运行。
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.llm import LLMClient, LLMResponse
from tools.dispatcher import Dispatcher
from tools.protocol import ErrorCode, ToolResult, rejected_result
from tools.trace import TraceRecorder

DEFAULT_MAX_TOOL_CALLS_PER_RUN = 8


@dataclass
class RunResult:
    task: str
    final_text: str
    tool_results: list[ToolResult]
    trace_events: list[dict]

    @property
    def all_tools_ok(self) -> bool:
        return bool(self.tool_results) and all(r.status == "ok" for r in self.tool_results)


class AgentHarness:
    def __init__(
        self,
        client: LLMClient,
        dispatcher: Dispatcher,
        trace: TraceRecorder | None = None,
        max_tool_calls_per_run: int = DEFAULT_MAX_TOOL_CALLS_PER_RUN,
    ) -> None:
        self._client = client
        self._dispatcher = dispatcher
        self._trace = trace if trace is not None else dispatcher.trace or TraceRecorder()
        self._max_tool_calls = max_tool_calls_per_run

    def run(self, task: str) -> RunResult:
        self._emit("run_started", mode="single_round")
        definitions = self._dispatcher.registry.definitions()
        messages: list[dict] = [{"role": "user", "content": task}]

        decision = self._client.complete(messages, definitions)
        self._emit("llm_decision", tool_calls=len(decision.tool_calls),
                   has_text=decision.text is not None)

        if not decision.tool_calls:
            self._emit("run_finished", tool_executed=False)
            return RunResult(task=task, final_text=decision.text or "",
                             tool_results=[], trace_events=self._trace.events)

        results = self._dispatch_all(decision)
        messages.append({
            "role": "assistant",
            "content": decision.raw_content
            or [_tool_use_block(c) for c in decision.tool_calls],
        })
        messages.append({"role": "user", "content": [_tool_result_block(r) for r in results]})

        final = self._client.complete(messages, definitions)
        if final.tool_calls:
            # Level 0 不再执行第二轮工具调用;如实记录而非静默吞掉。
            self._emit("final_response_has_unexecuted_tool_calls",
                       tool_calls=len(final.tool_calls))
        self._emit("run_finished", tool_executed=True)
        return RunResult(task=task, final_text=final.text or "",
                         tool_results=results, trace_events=self._trace.events)

    def _dispatch_all(self, decision: LLMResponse) -> list[ToolResult]:
        results: list[ToolResult] = []
        for index, call in enumerate(decision.tool_calls):
            if index >= self._max_tool_calls:
                results.append(rejected_result(
                    call.call_id, call.name, ErrorCode.TOO_MANY_TOOL_CALLS,
                    f"run accepts at most {self._max_tool_calls} tool calls",
                ))
                continue
            results.append(self._dispatcher.execute(call))
        return results

    def _emit(self, event: str, **fields) -> None:
        if self._trace is not None:
            self._trace.emit(event, **fields)


def _tool_use_block(call) -> dict:
    return {"type": "tool_use", "id": call.call_id, "name": call.name, "input": call.arguments}


def _tool_result_block(result: ToolResult) -> dict:
    return {
        "type": "tool_result",
        "tool_use_id": result.call_id,
        "content": result.feedback_text(),
    }

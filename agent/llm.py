"""LLM Adapter(Level 0 最小实现)。

两条铁律:
1. 结构化 Tool Calling——真实模型走 Anthropic Messages API 原生 tools/tool_use,
   参数以结构化 dict 到达;不要求模型在文本里输出 JSON 再解析执行。
2. 凭据只走环境变量——API Key 仅从 ANTHROPIC_API_KEY 读取,不进入
   请求体、日志、Trace 或异常消息。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol, Sequence

from tools.protocol import ToolCall, ToolCallRejected, ToolDefinition, from_tool_use

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TOKENS = 1024
API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"


class LLMError(RuntimeError):
    """LLM 调用失败;消息只含状态码与简短原因,不含凭据。"""


@dataclass(frozen=True)
class LLMResponse:
    """一次模型决策的统一视图。

    tool_calls 非空表示模型请求执行工具;
    raw_content 是原始 content blocks,供 Harness 回传 tool_result 时使用。
    """

    text: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    raw_content: list | None = field(default=None)


class LLMClient(Protocol):
    def complete(
        self, messages: list[dict], tool_definitions: Sequence[ToolDefinition]
    ) -> LLMResponse: ...


class MockLLMClient:
    """确定性脚本客户端:按序返回预置响应,不需要 API Key。

    脚本耗尽时抛 RuntimeError(诚实失败),绝不静默编造响应。
    """

    def __init__(self, responses: Sequence[LLMResponse]) -> None:
        self._responses = list(responses)
        self._index = 0
        self.received_requests: list[dict] = []

    def complete(
        self, messages: list[dict], tool_definitions: Sequence[ToolDefinition]
    ) -> LLMResponse:
        self.received_requests.append({
            "messages": json.loads(json.dumps(messages, default=str)),
            "tool_definitions": [d.name for d in tool_definitions],
        })
        if self._index >= len(self._responses):
            raise RuntimeError("MockLLMClient script exhausted")
        response = self._responses[self._index]
        self._index += 1
        return response


class AnthropicLLMClient:
    """Anthropic Messages API 客户端(标准库 urllib,原生结构化 Tool Calling)。"""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: float = 60.0,
        api_url: str = ANTHROPIC_API_URL,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._timeout_seconds = timeout_seconds
        self._api_url = api_url
        self._api_key = api_key if api_key is not None else os.environ.get(API_KEY_ENV_VAR)
        if not self._api_key:
            raise RuntimeError(
                f"{API_KEY_ENV_VAR} is not set; live mode refuses to start (fail closed)"
            )

    def complete(
        self, messages: list[dict], tool_definitions: Sequence[ToolDefinition]
    ) -> LLMResponse:
        body = self.build_request_body(messages, tool_definitions)
        request = urllib.request.Request(
            self._api_url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = self._error_detail(exc)
            raise LLMError(f"anthropic api http {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LLMError(f"anthropic api request failed: {type(exc).__name__}") from exc
        return self.parse_response(payload)

    def build_request_body(
        self, messages: list[dict], tool_definitions: Sequence[ToolDefinition]
    ) -> dict:
        """构造请求体(纯函数,便于确定性测试);绝不含任何凭据字段。"""
        return {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [self._encode_message(m) for m in messages],
            "tools": [
                {
                    "name": d.name,
                    "description": d.description,
                    "input_schema": d.parameters,
                }
                for d in tool_definitions
            ],
        }

    def parse_response(self, payload: dict) -> LLMResponse:
        """把 API 响应转为统一视图;tool_use block 经类型校验后成为 ToolCall。"""
        content = payload.get("content")
        if not isinstance(content, list):
            raise LLMError("anthropic api response missing content list")
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in content:
            block_type = block.get("type") if isinstance(block, dict) else None
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                try:
                    tool_calls.append(from_tool_use(block))
                except ToolCallRejected as exc:
                    raise LLMError(f"malformed tool_use block ({exc.code}): {exc.message}") from exc
        text = "".join(text_parts) if text_parts else None
        return LLMResponse(text=text, tool_calls=tuple(tool_calls), raw_content=content)

    @staticmethod
    def _encode_message(message: dict) -> dict:
        role = message.get("role")
        if role not in ("user", "assistant"):
            raise LLMError(f"unsupported message role: {role!r}")
        return {"role": role, "content": message["content"]}

    @staticmethod
    def _error_detail(exc: urllib.error.HTTPError) -> str:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            message = payload.get("error", {}).get("message", "")
        except Exception:
            message = ""
        return (message or "no detail")[:300]

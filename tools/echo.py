"""echo 工具:Mini Agent 与真实世界的第一次握手(Level 0)。"""

from __future__ import annotations

from tools.base import Tool
from tools.protocol import ToolDefinition

DEFAULT_MAX_LENGTH = 1000


class EchoTool(Tool):
    def __init__(self, max_length: int = DEFAULT_MAX_LENGTH) -> None:
        self._max_length = max_length
        self._definition = ToolDefinition(
            name="echo",
            description="原样返回输入的 text,用于验证工具调用链路。",
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "maxLength": max_length},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    def execute(self, arguments: dict) -> str:
        return arguments["text"]

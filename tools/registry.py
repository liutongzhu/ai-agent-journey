"""Tool Registry:白名单注册(Level 0)。

原则 3:只有显式注册的工具可被调用,没有隐式发现。
注册时校验命名与 Schema 子集,非法定义在注册阶段即失败(Fail Fast)。
"""

from __future__ import annotations

import re

from tools.base import Tool
from tools.protocol import ToolDefinition
from tools.schema import SchemaDefinitionError, validate_schema

_TOOL_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,63}")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        definition = tool.definition
        if not isinstance(definition, ToolDefinition):
            raise TypeError("tool.definition must be a ToolDefinition")
        if not _TOOL_NAME_PATTERN.fullmatch(definition.name):
            raise ValueError(
                f"invalid tool name {definition.name!r}: must match {_TOOL_NAME_PATTERN.pattern}"
            )
        if not definition.description:
            raise ValueError(f"tool {definition.name!r} must have a description")
        try:
            validate_schema(definition.parameters)
        except SchemaDefinitionError as exc:
            raise ValueError(f"tool {definition.name!r} has invalid schema: {exc}") from exc
        if definition.name in self._tools:
            raise ValueError(f"tool {definition.name!r} is already registered")
        self._tools[definition.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def definition_of(self, name: str) -> ToolDefinition | None:
        tool = self._tools.get(name)
        return tool.definition if tool is not None else None

    def definitions(self) -> list[ToolDefinition]:
        return [tool.definition for tool in self._tools.values()]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def __len__(self) -> int:
        return len(self._tools)

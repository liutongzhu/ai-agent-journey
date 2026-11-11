"""Level 0: Tool Registry 白名单。"""

import pytest

from tools.echo import EchoTool
from tools.protocol import ToolDefinition
from tools.registry import ToolRegistry


class StaticTool:
    """用给定定义注册的工具,便于构造非法定义。"""

    def __init__(self, definition):
        self._definition = definition

    @property
    def definition(self):
        return self._definition

    def execute(self, arguments):
        return ""


class ArrayTool:
    """Schema 超出支持子集的工具,注册时应被拒绝。"""

    @property
    def definition(self):
        return ToolDefinition(
            name="bad_tool",
            description="schema uses unsupported array type",
            parameters={
                "type": "object",
                "properties": {"items": {"type": "array"}},
                "required": ["items"],
                "additionalProperties": False,
            },
        )

    def execute(self, arguments):
        return ""


def echo_definition_with(name: str, description: str = "echo variant"):
    return ToolDefinition(
        name=name,
        description=description,
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
    )


def test_register_and_lookup():
    registry = ToolRegistry()
    tool = EchoTool()
    registry.register(tool)
    assert registry.get("echo") is tool
    assert registry.get("nope") is None
    assert registry.names() == ["echo"]
    assert len(registry) == 1
    assert registry.definitions()[0].name == "echo"


def test_duplicate_registration_rejected():
    registry = ToolRegistry()
    registry.register(EchoTool())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(EchoTool())


@pytest.mark.parametrize("name", ["Echo", "rm -rf", "1echo", "echo!", "a" * 65])
def test_invalid_tool_name_rejected(name):
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="invalid tool name"):
        registry.register(StaticTool(echo_definition_with(name)))


def test_missing_description_rejected():
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="description"):
        registry.register(StaticTool(echo_definition_with("mute", description="")))


def test_unsupported_schema_rejected_at_registration():
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="invalid schema"):
        registry.register(ArrayTool())

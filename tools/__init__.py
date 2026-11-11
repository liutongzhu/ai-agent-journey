"""tools: Tool 协议、Schema 校验、Registry 与 Dispatcher(Level 0 起实现)。"""

from tools.base import Tool
from tools.dispatcher import Dispatcher, PermissionPolicy
from tools.echo import EchoTool
from tools.protocol import (
    PROTOCOL_VERSION,
    ErrorCode,
    ToolCall,
    ToolCallRejected,
    ToolDefinition,
    ToolError,
    ToolExecutionFailure,
    ToolResult,
    from_tool_use,
    ok_result,
    parse_tool_call,
    rejected_result,
)
from tools.read_file import ReadFileTool
from tools.registry import ToolRegistry
from tools.schema import SchemaDefinitionError, SchemaViolation, validate_arguments, validate_schema
from tools.trace import TraceRecorder, redact

__all__ = [
    "PROTOCOL_VERSION",
    "Dispatcher",
    "EchoTool",
    "ErrorCode",
    "PermissionPolicy",
    "ReadFileTool",
    "SchemaDefinitionError",
    "SchemaViolation",
    "Tool",
    "ToolCall",
    "ToolCallRejected",
    "ToolDefinition",
    "ToolError",
    "ToolExecutionFailure",
    "ToolRegistry",
    "ToolResult",
    "TraceRecorder",
    "from_tool_use",
    "ok_result",
    "parse_tool_call",
    "redact",
    "rejected_result",
    "validate_arguments",
    "validate_schema",
]

"""read_file 工具:限定在工作区内只读文件(Level 0)。

边界策略:先 resolve(展开 .. 与符号链接),再 is_relative_to 判断是否仍
落在工作区内,边界检查先于存在性检查(不泄露工作区外文件的存在性)。
路径校验是约束而非隔离(原则 10):真正的执行隔离由 Level 3 Sandbox 提供。
"""

from __future__ import annotations

from pathlib import Path

from tools.base import Tool
from tools.protocol import ErrorCode, ToolDefinition, ToolExecutionFailure

DEFAULT_MAX_BYTES = 64 * 1024
_MAX_PATH_LENGTH = 1024


class ReadFileTool(Tool):
    def __init__(self, workspace_root: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        self._root = Path(workspace_root).resolve()
        self._max_bytes = max_bytes
        self._definition = ToolDefinition(
            name="read_file",
            description="读取工作区内一个 UTF-8 文本文件,返回其内容。只接受工作区相对路径。",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "maxLength": _MAX_PATH_LENGTH},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            required_permission="fs.read",
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    @property
    def workspace_root(self) -> Path:
        return self._root

    def execute(self, arguments: dict) -> str:
        raw = arguments["path"]
        resolved = self._resolve_in_workspace(raw)
        try:
            data = resolved.read_bytes()
        except OSError as exc:
            raise ToolExecutionFailure(ErrorCode.TOOL_ERROR, f"cannot read file: {exc}") from exc
        if len(data) > self._max_bytes:
            raise ToolExecutionFailure(
                "content_too_large",
                f"file exceeds {self._max_bytes} bytes (got {len(data)})",
            )
        return data.decode("utf-8", errors="replace")

    def _resolve_in_workspace(self, raw: str) -> Path:
        candidate = Path(raw)
        if candidate.is_absolute():
            raise ToolExecutionFailure(
                "path_outside_workspace",
                "absolute paths are not allowed; use a workspace-relative path",
            )
        resolved = (self._root / candidate).resolve()
        if not resolved.is_relative_to(self._root):
            raise ToolExecutionFailure(
                "path_outside_workspace",
                f"resolved path escapes the workspace: {raw!r}",
            )
        if not resolved.exists():
            raise ToolExecutionFailure(ErrorCode.FILE_NOT_FOUND, f"file not found: {raw!r}")
        if resolved.is_dir():
            raise ToolExecutionFailure("is_a_directory", f"path is a directory: {raw!r}")
        return resolved

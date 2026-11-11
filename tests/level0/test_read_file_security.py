"""Level 0: read_file 路径边界 — 目录穿越与符号链接越界必须被拒绝。"""

import os
from pathlib import Path

import pytest

from tools.echo import EchoTool
from tools.protocol import ToolCall, ToolExecutionFailure
from tools.read_file import ReadFileTool
from tools.registry import ToolRegistry
from tools.dispatcher import Dispatcher, PermissionPolicy


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "sample.txt").write_text("hello from workspace", encoding="utf-8")
    (root / "notes").mkdir()
    (root / "notes" / "nested.txt").write_text("nested 中文内容", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("top secret", encoding="utf-8")
    (tmp_path.parent / "outside-secret.txt").write_text("outside", encoding="utf-8")
    return root


def make_tool(workspace: Path, max_bytes=64 * 1024) -> ReadFileTool:
    return ReadFileTool(workspace, max_bytes=max_bytes)


def test_reads_file_inside_workspace(workspace):
    tool = make_tool(workspace)
    assert tool.execute({"path": "sample.txt"}) == "hello from workspace"


def test_reads_nested_file_with_unicode(workspace):
    tool = make_tool(workspace)
    assert tool.execute({"path": "notes/nested.txt"}) == "nested 中文内容"


def test_traversal_to_parent_rejected(workspace):
    tool = make_tool(workspace)
    with pytest.raises(ToolExecutionFailure) as excinfo:
        tool.execute({"path": "../secret.txt"})
    assert excinfo.value.code == "path_outside_workspace"


def test_deep_traversal_rejected(workspace):
    tool = make_tool(workspace)
    with pytest.raises(ToolExecutionFailure) as excinfo:
        tool.execute({"path": "../../../../outside-secret.txt"})
    assert excinfo.value.code == "path_outside_workspace"


def test_absolute_path_rejected(workspace):
    tool = make_tool(workspace)
    with pytest.raises(ToolExecutionFailure) as excinfo:
        tool.execute({"path": "/etc/hosts"})
    assert excinfo.value.code == "path_outside_workspace"


def test_dotdot_only_rejected(workspace):
    tool = make_tool(workspace)
    with pytest.raises(ToolExecutionFailure) as excinfo:
        tool.execute({"path": ".."})
    assert excinfo.value.code == "path_outside_workspace"


def test_symlink_pointing_outside_rejected(workspace):
    target = workspace.parent / "secret.txt"
    link = workspace / "innocent.txt"
    os.symlink(target, link)
    tool = make_tool(workspace)
    with pytest.raises(ToolExecutionFailure) as excinfo:
        tool.execute({"path": "innocent.txt"})
    assert excinfo.value.code == "path_outside_workspace"


def test_symlinked_directory_escape_rejected(workspace):
    outside_dir = workspace.parent / "outside-notes"
    outside_dir.mkdir(exist_ok=True)
    (outside_dir / "leak.txt").write_text("leak", encoding="utf-8")
    os.symlink(outside_dir, workspace / "links")
    tool = make_tool(workspace)
    with pytest.raises(ToolExecutionFailure) as excinfo:
        tool.execute({"path": "links/leak.txt"})
    assert excinfo.value.code == "path_outside_workspace"


def test_symlink_inside_workspace_is_fine(workspace):
    os.symlink(workspace / "sample.txt", workspace / "alias.txt")
    tool = make_tool(workspace)
    assert tool.execute({"path": "alias.txt"}) == "hello from workspace"


def test_workspace_root_via_symlink_is_resolved(workspace):
    link_root = workspace.parent / "ws-link"
    os.symlink(workspace, link_root)
    tool = make_tool(link_root)
    assert tool.execute({"path": "sample.txt"}) == "hello from workspace"
    assert tool.workspace_root == workspace.resolve()


def test_missing_file_reports_not_found(workspace):
    tool = make_tool(workspace)
    with pytest.raises(ToolExecutionFailure) as excinfo:
        tool.execute({"path": "nope.txt"})
    assert excinfo.value.code == "file_not_found"


def test_directory_rejected(workspace):
    tool = make_tool(workspace)
    with pytest.raises(ToolExecutionFailure) as excinfo:
        tool.execute({"path": "notes"})
    assert excinfo.value.code == "is_a_directory"


def test_workspace_dot_rejected(workspace):
    tool = make_tool(workspace)
    with pytest.raises(ToolExecutionFailure) as excinfo:
        tool.execute({"path": "."})
    assert excinfo.value.code == "is_a_directory"


def test_oversized_file_rejected(workspace):
    big = workspace / "big.txt"
    big.write_bytes(b"x" * 64)
    tool = make_tool(workspace, max_bytes=16)
    with pytest.raises(ToolExecutionFailure) as excinfo:
        tool.execute({"path": "big.txt"})
    assert excinfo.value.code == "content_too_large"


def test_boundary_checked_before_existence(workspace):
    """越界路径即使不存在也统一拒绝,不泄露存在性信息。"""
    tool = make_tool(workspace)
    with pytest.raises(ToolExecutionFailure) as excinfo:
        tool.execute({"path": "../maybe-exists.txt"})
    assert excinfo.value.code == "path_outside_workspace"


def test_full_chain_via_dispatcher(workspace):
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(make_tool(workspace))
    dispatcher = Dispatcher(registry,
                            permissions=PermissionPolicy(allowed=frozenset({"fs.read"})))
    with dispatcher:
        ok = dispatcher.execute(ToolCall("c1", "read_file", {"path": "sample.txt"}))
        bad = dispatcher.execute(ToolCall("c2", "read_file", {"path": "../secret.txt"}))
    assert ok.status == "ok"
    assert bad.error.code == "path_outside_workspace"

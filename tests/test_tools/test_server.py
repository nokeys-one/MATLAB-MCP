import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


def test_create_server_returns_fastmcp():
    from matlab_mcp_server.server import create_server
    from matlab_mcp_server.config import Settings

    settings = Settings(sandbox_dir=Path("/tmp/test_sandbox"))
    mcp = create_server(settings)
    assert mcp is not None
    assert hasattr(mcp, "tool")


def test_create_server_registers_task_manager_tools():
    from matlab_mcp_server.server import create_server
    from matlab_mcp_server.config import Settings

    settings = Settings(sandbox_dir=Path("/tmp/test_sandbox"))
    mcp = create_server(settings)

    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "check_task_status" in tool_names
    assert "cancel_task" in tool_names
    assert "approve_operation" in tool_names
    assert "reject_operation" in tool_names
    assert "list_pending_approvals" in tool_names
    assert "reset_workspace" in tool_names


def test_create_server_initializes_all_components():
    from matlab_mcp_server.server import create_server
    from matlab_mcp_server.config import Settings

    settings = Settings(sandbox_dir=Path("/tmp/test_sandbox"))
    mcp = create_server(settings)
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert len(tool_names) >= 6

import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from matlab_mcp_server.config import Settings
from matlab_mcp_server.tools.registry import registry
from matlab_mcp_server.security.approval_queue import ApprovalQueue


def test_all_tools_registered():
    import matlab_mcp_server.tools.task_manager
    import matlab_mcp_server.tools.computation
    import matlab_mcp_server.tools.simulink
    import matlab_mcp_server.tools.visualization
    import matlab_mcp_server.tools.toolbox
    import matlab_mcp_server.tools.file_ops

    names = set(registry.list_names())
    expected = {
        "check_task_status", "cancel_task", "reset_workspace",
        "approve_operation", "reject_operation", "list_pending_approvals",
        "run_matlab_function", "execute_matlab_script", "evaluate_expression",
        "get_workspace_variable", "list_workspace_variables",
        "load_simulink_model", "modify_block_parameters", "list_block_parameters",
        "create_simple_model", "configure_simulation", "run_simulation",
        "get_simulation_results", "open_simulink_gui",
        "create_plot", "create_3d_plot", "export_figure", "subplot_layout", "verify_plot_data",
        "signal_processing", "control_system", "optimization", "machine_learning", "data_analysis",
        "load_data", "save_data", "list_sandbox_files", "verify_checksum", "delete_data",
    }
    missing = expected - names
    assert not missing, f"Missing tools: {missing}"


def test_all_tool_schemas_valid():
    import matlab_mcp_server.tools.task_manager
    import matlab_mcp_server.tools.computation
    import matlab_mcp_server.tools.simulink
    import matlab_mcp_server.tools.visualization
    import matlab_mcp_server.tools.toolbox
    import matlab_mcp_server.tools.file_ops

    for name, tool_def in registry.get_all().items():
        schema = tool_def["input_schema"]
        assert "type" in schema, f"Tool '{name}' missing 'type' in schema"
        assert schema["type"] == "object", f"Tool '{name}' schema type is not 'object'"
        assert "handler" in tool_def, f"Tool '{name}' missing handler"
        assert callable(tool_def["handler"]), f"Tool '{name}' handler not callable"


def test_workspace_manager_creates_sandbox(tmp_path):
    from matlab_mcp_server.sandbox.workspace_manager import WorkspaceManager

    mgr = WorkspaceManager(tmp_path / "test_sandbox")
    result = mgr.ensure_sandbox_exists()
    assert (tmp_path / "test_sandbox").exists()
    assert (tmp_path / "test_sandbox" / "figures").exists()
    assert (tmp_path / "test_sandbox" / "data").exists()


def test_workspace_manager_reset(tmp_path):
    from matlab_mcp_server.sandbox.workspace_manager import WorkspaceManager

    mgr = WorkspaceManager(tmp_path / "sandbox")
    mgr.ensure_sandbox_exists()
    junk = mgr.sandbox_dir / "figures" / "test.png"
    junk.write_bytes(b"fake")
    assert junk.exists()
    result = mgr.reset_workspace()
    assert result["status"] == "reset"
    assert not junk.exists()


def test_settings_loads_defaults():
    s = Settings()
    assert s.transport in ("stdio", "http")
    assert s.matlab_timeout > 0
    assert s.payload_max_mb > 0
    assert s.max_concurrent_tasks > 0
    assert s.orphan_ttl_seconds > 0
    assert s.steady_state_window_size > 0


def test_settings_env_prefix():
    import os
    os.environ["MATLAB_MCP_TRANSPORT"] = "http"
    try:
        s = Settings()
        assert s.transport == "http"
    finally:
        del os.environ["MATLAB_MCP_TRANSPORT"]


@pytest.mark.asyncio
async def test_approval_queue_flow():
    queue = ApprovalQueue(timeout=5.0)
    req = queue.create_request(
        operation="system('dir')",
        description="Execute system command",
        risk_level="high",
        params={"command": "dir"},
    )
    assert req.approval_id.startswith("approval_")
    assert req.future is not None

    pending = queue.get_pending()
    assert len(pending) == 1
    assert pending[0]["risk_level"] == "high"

    queue.approve(req.approval_id)
    assert req.approved is True
    assert req.resolved is True
    assert len(queue.get_pending()) == 0


@pytest.mark.asyncio
async def test_approval_queue_reject():
    queue = ApprovalQueue(timeout=5.0)
    req = queue.create_request(
        operation="eval('x')",
        description="Eval test",
        risk_level="critical",
        params={},
    )
    queue.reject(req.approval_id)
    assert req.approved is False
    assert req.resolved is True


@pytest.mark.asyncio
async def test_approval_queue_wait_timeout():
    queue = ApprovalQueue(timeout=0.1)
    req = queue.create_request(
        operation="test",
        description="test timeout",
        risk_level="low",
        params={},
    )
    result = await queue.wait_for_approval(req.approval_id)
    assert result is False
    assert req.resolved is True


@pytest.mark.asyncio
async def test_approval_queue_approve_resolves_wait():
    queue = ApprovalQueue(timeout=5.0)
    req = queue.create_request(
        operation="test",
        description="test approve",
        risk_level="medium",
        params={},
    )

    async def approve_after_delay():
        await asyncio.sleep(0.1)
        queue.approve(req.approval_id)

    asyncio.create_task(approve_after_delay())
    result = await queue.wait_for_approval(req.approval_id)
    assert result is True


def test_lock_manager_acquires_and_releases():
    from matlab_mcp_server.engine.lock_manager import EngineLockManager, EngineState

    mgr = EngineLockManager()
    assert mgr.state == EngineState.IDLE
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        acquired = loop.run_until_complete(mgr.acquire("run_matlab_function"))
        assert acquired is True
        assert mgr.state == EngineState.RUNNING
        loop.run_until_complete(mgr.release())
        assert mgr.state == EngineState.IDLE
    finally:
        loop.close()


def test_lock_manager_query_tools_bypass():
    from matlab_mcp_server.engine.lock_manager import EngineLockManager, QUERY_TOOLS

    mgr = EngineLockManager()
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        for tool in QUERY_TOOLS:
            result = loop.run_until_complete(mgr.acquire(tool))
            assert result is True, f"QUERY_TOOLS tool '{tool}' should bypass lock"
    finally:
        loop.close()


def test_injection_guard_blocks_dangerous_code():
    from matlab_mcp_server.engine.injection_guard import pre_execute_check, InjectionBlockedError

    pre_execute_check("x = sin(0);")
    pre_execute_check("plot(x, y);")

    with pytest.raises(InjectionBlockedError):
        pre_execute_check("eval('x=1')")

    with pytest.raises(InjectionBlockedError):
        pre_execute_check("evalc('x=1')")

    with pytest.raises(InjectionBlockedError):
        pre_execute_check("feval('system', 'ls')")


def test_path_sanitizer_blocks_traversal():
    from matlab_mcp_server.security.path_sanitizer import sanitize_path, PathTraversalError

    result = sanitize_path("data/test.csv", "/sandbox")
    assert "data" in result

    with pytest.raises(PathTraversalError):
        sanitize_path("../../../etc/passwd", "/sandbox")

    with pytest.raises(PathTraversalError):
        sanitize_path("../../windows/system32", "/sandbox")


def test_whitelist_security_levels():
    from matlab_mcp_server.security.whitelist import check_security_level, SecurityLevel

    level = check_security_level("sin")
    assert level == SecurityLevel.L0_AUTO

    level = check_security_level("eval")
    assert level == SecurityLevel.L3_BLOCKED

    level = check_security_level("system")
    assert level == SecurityLevel.L2_APPROVAL


def test_error_formatter_handles_exceptions():
    from matlab_mcp_server.output.error_formatter import format_error

    result = format_error(ValueError("test error"))
    assert "success" in result
    assert result["success"] is False
    assert "error" in result


def test_client_adapter_image_response():
    from matlab_mcp_server.output.client_adapter import ClientAdapter

    adapter = ClientAdapter(client_vision=True)
    result = adapter.adapt_image_response({"success": True}, "/fake/path.png")
    assert isinstance(result, dict)


def test_data_serializer():
    from matlab_mcp_server.output.data_serializer import serialize_variable
    import numpy as np

    data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = serialize_variable(data)
    assert isinstance(result, dict)
    assert "data" in result
    assert "metadata" in result


def test_integrity_checksum():
    from matlab_mcp_server.output.integrity import compute_checksum, verify_checksum

    data = b"test data"
    checksum = compute_checksum(data, "sha256")
    assert len(checksum) == 64
    assert verify_checksum(data, checksum, "sha256") is True
    assert verify_checksum(data, "wrong", "sha256") is False


def test_server_creation():
    from matlab_mcp_server.server import create_server

    settings = Settings()
    server = create_server(settings)
    assert server is not None

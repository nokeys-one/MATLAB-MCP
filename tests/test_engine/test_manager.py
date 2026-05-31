import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from matlab_mcp_server.engine.manager import MatlabEngineManager


@pytest.fixture
def temp_sandbox(tmp_path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    shadow = tmp_path / "shadows"
    shadow.mkdir()
    return sandbox, shadow


@pytest.fixture
def manager(temp_sandbox):
    sandbox, shadow = temp_sandbox
    return MatlabEngineManager(sandbox_dir=sandbox, shadow_dir=shadow)


@pytest.fixture
def mock_matlab_engine():
    mock_engine = MagicMock()
    mock_engine.addpath = MagicMock()
    mock_engine.cd = MagicMock()
    mock_engine.eval = MagicMock(return_value="")
    mock_engine.quit = MagicMock()
    mock_engine.workspace = MagicMock()

    mock_matlab_engine = MagicMock()
    mock_matlab_engine.start_matlab.return_value = mock_engine

    mock_matlab = MagicMock()
    mock_matlab.engine = mock_matlab_engine

    return mock_matlab, mock_engine


def test_initialization(temp_sandbox):
    sandbox, shadow = temp_sandbox
    mgr = MatlabEngineManager(sandbox_dir=sandbox, shadow_dir=shadow)
    assert mgr.sandbox_dir == sandbox
    assert mgr.shadow_dir == shadow
    assert mgr.is_running is False


def test_initialization_with_injection_disabled(temp_sandbox):
    sandbox, shadow = temp_sandbox
    mgr = MatlabEngineManager(
        sandbox_dir=sandbox, shadow_dir=shadow,
        enable_injection_check=False,
    )
    assert mgr._enable_injection_check is False


@pytest.mark.asyncio
async def test_execute_raises_when_not_started(manager):
    with pytest.raises(RuntimeError, match="MATLAB Engine not started"):
        await manager.execute("1 + 1")


@pytest.mark.asyncio
async def test_get_variable_info_raises_when_not_started(manager):
    with pytest.raises(RuntimeError, match="MATLAB Engine not started"):
        await manager.get_variable_info("x")


@pytest.mark.asyncio
async def test_list_workspace_raises_when_not_started(manager):
    with pytest.raises(RuntimeError, match="MATLAB Engine not started"):
        await manager.list_workspace()


@pytest.mark.asyncio
async def test_start_success(temp_sandbox, mock_matlab_engine):
    sandbox, shadow = temp_sandbox
    mgr = MatlabEngineManager(sandbox_dir=sandbox, shadow_dir=shadow)
    mock_matlab, mock_engine = mock_matlab_engine

    with patch.dict(sys.modules, {"matlab": mock_matlab, "matlab.engine": mock_matlab.engine}):
        result = await mgr.start()

    assert result is True
    assert mgr.is_running is True
    mock_engine.addpath.assert_called_once()
    mock_engine.cd.assert_called_once_with(str(sandbox), nargout=0)


@pytest.mark.asyncio
async def test_start_failure(temp_sandbox):
    sandbox, shadow = temp_sandbox
    mgr = MatlabEngineManager(sandbox_dir=sandbox, shadow_dir=shadow)

    mock_matlab = MagicMock()
    mock_matlab.engine.start_matlab.side_effect = Exception("MATLAB not found")

    with patch.dict(sys.modules, {"matlab": mock_matlab, "matlab.engine": mock_matlab.engine}):
        result = await mgr.start()

    assert result is False
    assert mgr.is_running is False


@pytest.mark.asyncio
async def test_stop(manager):
    manager._engine = MagicMock()
    manager._engine_started = True
    await manager.stop()
    assert manager.is_running is False
    assert manager._engine is None


@pytest.mark.asyncio
async def test_stop_no_error_on_quit_failure(manager):
    mock_engine = MagicMock()
    mock_engine.quit.side_effect = Exception("quit failed")
    manager._engine = mock_engine
    manager._engine_started = True
    await manager.stop()
    assert manager.is_running is False
    assert manager._engine is None


@pytest.mark.asyncio
async def test_restart(temp_sandbox, mock_matlab_engine):
    sandbox, shadow = temp_sandbox
    mgr = MatlabEngineManager(sandbox_dir=sandbox, shadow_dir=shadow)
    mock_matlab, mock_engine = mock_matlab_engine

    with patch.dict(sys.modules, {"matlab": mock_matlab, "matlab.engine": mock_matlab.engine}):
        result = await mgr.restart()

    assert result is True
    assert mgr.is_running is True


@pytest.mark.asyncio
async def test_execute_with_mock_engine(manager):
    manager._engine = MagicMock()
    manager._engine_started = True
    manager._engine.eval.return_value = "ans = 4"

    result = await manager.execute("2 + 2", skip_injection_check=True)
    assert "4" in result


@pytest.mark.asyncio
async def test_execute_injection_check_called(manager):
    manager._engine = MagicMock()
    manager._engine_started = True
    manager._engine.eval.return_value = ""

    with patch("matlab_mcp_server.engine.injection_guard.pre_execute_check") as mock_check:
        await manager.execute("sin(0)", skip_injection_check=False)
        mock_check.assert_called_once_with("sin(0)")


@pytest.mark.asyncio
async def test_execute_skip_injection_check(manager):
    manager._engine = MagicMock()
    manager._engine_started = True
    manager._engine.eval.return_value = ""

    with patch("matlab_mcp_server.engine.injection_guard.pre_execute_check") as mock_check:
        await manager.execute("sin(0)", skip_injection_check=True)
        mock_check.assert_not_called()


@pytest.mark.asyncio
async def test_execute_injection_blocked(manager):
    manager._engine = MagicMock()
    manager._engine_started = True

    from matlab_mcp_server.engine.injection_guard import InjectionBlockedError

    with patch("matlab_mcp_server.engine.injection_guard.pre_execute_check") as mock_check:
        mock_check.side_effect = InjectionBlockedError([])
        with pytest.raises(InjectionBlockedError):
            await manager.execute("eval('dangerous')", skip_injection_check=False)


@pytest.mark.asyncio
async def test_execute_returns_empty_string_for_none(manager):
    manager._engine = MagicMock()
    manager._engine_started = True
    manager._engine.eval.return_value = None

    result = await manager.execute("x;", skip_injection_check=True)
    assert result == ""


@pytest.mark.asyncio
async def test_get_variable_info_success(manager):
    manager._engine = MagicMock()
    manager._engine_started = True
    manager._engine.workspace.__getitem__ = MagicMock(return_value=42.0)
    manager._engine.eval.return_value = "  Name      Size    Bytes  Class Attributes\n  x         1x1       8  double"

    result = await manager.get_variable_info("x")
    assert result["name"] == "x"
    assert "42" in result["value_preview"]


@pytest.mark.asyncio
async def test_get_variable_info_not_found(manager):
    manager._engine = MagicMock()
    manager._engine_started = True
    manager._engine.workspace.__getitem__ = MagicMock(side_effect=Exception("Variable not found"))

    result = await manager.get_variable_info("nonexistent")
    assert result["name"] == "nonexistent"
    assert "error" in result


@pytest.mark.asyncio
async def test_list_workspace_success(manager):
    manager._engine = MagicMock()
    manager._engine_started = True
    manager._engine.eval.return_value = "  Name      Size    Bytes  Class\n  x         1x1       8  double"

    result = await manager.list_workspace()
    assert "x" in str(result)


@pytest.mark.asyncio
async def test_list_workspace_error_raises(manager):
    manager._engine = MagicMock()
    manager._engine_started = True
    manager._engine.eval.side_effect = Exception("Engine crashed")

    with pytest.raises(Exception, match="Engine crashed"):
        await manager.list_workspace()


@pytest.mark.asyncio
async def test_clear_workspace(manager):
    manager._engine = MagicMock()
    manager._engine_started = True

    await manager.clear_workspace()
    manager._engine.eval.assert_called_once_with(
        "clear; clc; close all;", nargout=0
    )


@pytest.mark.asyncio
async def test_clear_workspace_skips_if_not_started(manager):
    manager._engine_started = False
    await manager.clear_workspace()


@pytest.mark.asyncio
async def test_close_shuts_down_executor(manager):
    manager._engine = MagicMock()
    manager._engine_started = True

    await manager.close()
    assert manager.is_running is False
    assert manager._engine is None


def test_pid_is_none_after_init(manager):
    assert manager._pid is None


@pytest.mark.asyncio
async def test_pid_is_captured_on_matlab_engine_start():
    sandbox = MagicMock()
    shadow = MagicMock()

    mock_engine = MagicMock()
    mock_engine.pid = 99999
    mock_engine.addpath = MagicMock()
    mock_engine.cd = MagicMock()

    mgr = MatlabEngineManager(sandbox_dir=sandbox, shadow_dir=shadow)

    mock_matlab = MagicMock()
    mock_matlab.engine.start_matlab.return_value = mock_engine

    with patch.dict(sys.modules, {"matlab": mock_matlab, "matlab.engine": mock_matlab.engine}):
        await mgr.start()

    assert mgr._pid == 99999
    await mgr.stop()


@pytest.mark.asyncio
async def test_pid_is_reset_after_stop(temp_sandbox, mock_matlab_engine):
    sandbox, shadow = temp_sandbox
    mgr = MatlabEngineManager(sandbox_dir=sandbox, shadow_dir=shadow)
    mock_matlab, mock_engine = mock_matlab_engine

    mock_engine.pid = 12345

    with patch.dict(sys.modules, {"matlab": mock_matlab, "matlab.engine": mock_matlab.engine}):
        await mgr.start()
        assert mgr._pid == 12345
        await mgr.stop()

    assert mgr._pid is None

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path


def test_simulink_tools_registered():
    from matlab_mcp_server.tools.registry import registry
    import matlab_mcp_server.tools.simulink

    names = registry.list_names()
    expected = [
        "load_simulink_model", "modify_block_parameters", "list_block_parameters",
        "create_simple_model", "configure_simulation", "run_simulation",
        "get_simulation_results", "open_simulink_gui",
    ]
    for name in expected:
        assert name in names, f"Missing tool: {name}"


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.execute = AsyncMock(return_value="")
    engine._execute_sync = MagicMock(return_value="")
    return engine


@pytest.fixture
def mock_task_executor():
    executor = MagicMock()
    executor.submit = MagicMock(return_value="task_abc123")
    task_mock = MagicMock()
    task_mock.status.value = "completed"
    task_mock.result = {"time": [0, 1, 2], "data": [0, 0.5, 1.0]}
    executor.get_task = MagicMock(return_value=task_mock)
    return executor


@pytest.mark.asyncio
async def test_load_simulink_model_path_traversal(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_load_simulink_model

    result = await handle_load_simulink_model(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_path": "../../../etc/passwd"},
    )
    assert result["success"] is False
    assert "traversal" in result["error"].lower() or "outside" in result["error"].lower()


@pytest.mark.asyncio
async def test_modify_block_parameters(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_modify_block_parameters

    result = await handle_modify_block_parameters(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "model_name": "test_model",
            "block_path": "Subsystem/Gain",
            "params": {"Gain": "5"},
        },
    )
    assert result["success"] is True
    assert result["model"] == "test_model"
    assert result["block"] == "Subsystem/Gain"
    assert "Gain" in result["modified_params"]
    mock_engine.execute.assert_called_once()
    called_script = mock_engine.execute.call_args[0][0]
    assert "set_param('test_model/Subsystem/Gain', 'Gain', '5')" in called_script


@pytest.mark.asyncio
async def test_modify_block_parameters_numeric(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_modify_block_parameters

    result = await handle_modify_block_parameters(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "model_name": "test_model",
            "block_path": "PID/Kp",
            "params": {"Kp": 2.5, "Ki": 0.1},
        },
    )
    assert result["success"] is True
    assert set(result["modified_params"]) == {"Kp", "Ki"}


@pytest.mark.asyncio
async def test_modify_block_parameters_engine_error(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_modify_block_parameters

    mock_engine.execute = AsyncMock(side_effect=Exception("Block not found"))
    result = await handle_modify_block_parameters(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "model_name": "test_model",
            "block_path": "NonExistent",
            "params": {"Gain": "1"},
        },
    )
    assert result["success"] is False
    assert "Block not found" in result["error"]


@pytest.mark.asyncio
async def test_list_block_parameters(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_list_block_parameters

    mock_engine.execute = AsyncMock(return_value="struct('Gain', struct(...))")
    result = await handle_list_block_parameters(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_name": "test_model", "block_path": "Gain"},
    )
    assert result["success"] is True
    assert result["model"] == "test_model"
    assert result["block"] == "Gain"
    assert "parameters" in result


@pytest.mark.asyncio
async def test_create_simple_model(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_create_simple_model

    result = await handle_create_simple_model(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_name": "my_model", "blocks": ["Step", "Gain", "Scope"]},
    )
    assert result["success"] is True
    assert result["model_name"] == "my_model"
    assert result["blocks"] == ["Step", "Gain", "Scope"]
    mock_engine.execute.assert_called_once()
    called_script = mock_engine.execute.call_args[0][0]
    assert "new_system('my_model')" in called_script
    assert "add_block('simulink/Sources/Step'" in called_script
    assert "add_block('simulink/Math Operations/Gain'" in called_script
    assert "add_block('simulink/Sinks/Scope'" in called_script
    assert "add_line('my_model', 'Block_0/1', 'Block_1/1')" in called_script
    assert "add_line('my_model', 'Block_1/1', 'Block_2/1')" in called_script


@pytest.mark.asyncio
async def test_create_simple_model_custom_lib_path(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_create_simple_model

    result = await handle_create_simple_model(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "model_name": "custom_model",
            "blocks": ["simulink/Sources/Step", "simulink/Sinks/Scope"],
        },
    )
    assert result["success"] is True
    called_script = mock_engine.execute.call_args[0][0]
    assert "add_block('simulink/Sources/Step'" in called_script
    assert "add_block('simulink/Sinks/Scope'" in called_script


@pytest.mark.asyncio
async def test_configure_simulation(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_configure_simulation

    result = await handle_configure_simulation(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_name": "my_model", "solver": "ode45", "stop_time": 10.0, "step_size": 0.01},
    )
    assert result["success"] is True
    assert result["model"] == "my_model"
    assert result["solver"] == "ode45"
    assert result["stop_time"] == 10.0
    mock_engine.execute.assert_called_once()
    called_script = mock_engine.execute.call_args[0][0]
    assert "set_param('my_model', 'Solver', 'ode45')" in called_script
    assert "set_param('my_model', 'StopTime', '10.0')" in called_script


@pytest.mark.asyncio
async def test_configure_simulation_defaults(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_configure_simulation

    result = await handle_configure_simulation(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_name": "my_model"},
    )
    assert result["success"] is True
    assert result["solver"] == "ode45"
    assert result["stop_time"] == 10.0


@pytest.mark.asyncio
async def test_run_simulation(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_run_simulation

    result = await handle_run_simulation(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_name": "my_model", "mode": "code"},
    )
    assert result["success"] is True
    assert result["task_id"] == "task_abc123"
    assert result["model_name"] == "my_model"
    assert result["mode"] == "code"
    mock_task_executor.submit.assert_called_once()


@pytest.mark.asyncio
async def test_run_simulation_gui_mode(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_run_simulation

    result = await handle_run_simulation(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_name": "my_model", "mode": "gui"},
    )
    assert result["success"] is True
    assert result["mode"] == "gui"


@pytest.mark.asyncio
async def test_get_simulation_results_completed(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_get_simulation_results

    result = await handle_get_simulation_results(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"task_id": "task_abc123"},
    )
    assert result["success"] is True
    assert result["task_id"] == "task_abc123"
    assert result["result"] == {"time": [0, 1, 2], "data": [0, 0.5, 1.0]}


@pytest.mark.asyncio
async def test_get_simulation_results_not_found(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_get_simulation_results

    mock_task_executor.get_task = MagicMock(return_value=None)
    result = await handle_get_simulation_results(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"task_id": "nonexistent"},
    )
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_get_simulation_results_not_completed(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_get_simulation_results

    task_mock = MagicMock()
    task_mock.status.value = "running"
    mock_task_executor.get_task = MagicMock(return_value=task_mock)
    result = await handle_get_simulation_results(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"task_id": "task_abc123"},
    )
    assert result["success"] is False
    assert "not completed" in result["error"].lower()


@pytest.mark.asyncio
async def test_open_simulink_gui(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_open_simulink_gui

    result = await handle_open_simulink_gui(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_name": "my_model"},
    )
    assert result["success"] is True
    assert result["model_name"] == "my_model"
    mock_engine.execute.assert_called_once_with("open_system('my_model')")


@pytest.mark.asyncio
async def test_open_simulink_gui_error(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_open_simulink_gui

    mock_engine.execute = AsyncMock(side_effect=Exception("Model not found"))
    result = await handle_open_simulink_gui(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_name": "nonexistent"},
    )
    assert result["success"] is False
    assert "Model not found" in result["error"]


def test_esc_helper():
    from matlab_mcp_server.tools.simulink import _esc

    assert _esc("normal") == "normal"
    assert _esc("it's") == "it''s"
    assert _esc("a'b'c") == "a''b''c"
    assert _esc("") == ""


@pytest.mark.asyncio
async def test_modify_block_parameters_escapes_quotes(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_modify_block_parameters

    result = await handle_modify_block_parameters(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "model_name": "my'model",
            "block_path": "sub/block",
            "params": {"Gain": "it's a value"},
        },
    )
    assert result["success"] is True
    called_script = mock_engine.execute.call_args[0][0]
    assert "my''model" in called_script
    assert "it''s a value" in called_script
    assert "'my'model" not in called_script
    assert "'it's a value'" not in called_script


@pytest.mark.asyncio
async def test_list_block_parameters_escapes_quotes(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_list_block_parameters

    mock_engine.execute = AsyncMock(return_value="struct()")
    result = await handle_list_block_parameters(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_name": "my'model", "block_path": "sub'block"},
    )
    assert result["success"] is True
    called_script = mock_engine.execute.call_args[0][0]
    assert "my''model" in called_script
    assert "sub''block" in called_script


@pytest.mark.asyncio
async def test_create_simple_model_escapes_quotes(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_create_simple_model

    result = await handle_create_simple_model(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_name": "my'model", "blocks": ["Step", "Scope"]},
    )
    assert result["success"] is True
    called_script = mock_engine.execute.call_args[0][0]
    assert "my''model" in called_script
    assert "'my'model'" not in called_script


@pytest.mark.asyncio
async def test_configure_simulation_escapes_quotes(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_configure_simulation

    result = await handle_configure_simulation(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_name": "my'model", "solver": "ode'45"},
    )
    assert result["success"] is True
    called_script = mock_engine.execute.call_args[0][0]
    assert "my''model" in called_script
    assert "ode''45" in called_script
    assert "'my'model'" not in called_script
    assert "'ode'45'" not in called_script


@pytest.mark.asyncio
async def test_open_simulink_gui_escapes_quotes(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.simulink import handle_open_simulink_gui

    result = await handle_open_simulink_gui(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"model_name": "my'model"},
    )
    assert result["success"] is True
    called_script = mock_engine.execute.call_args[0][0]
    assert "my''model" in called_script
    assert "'my'model'" not in called_script

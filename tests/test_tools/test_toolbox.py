import pytest
from unittest.mock import MagicMock, AsyncMock


def test_toolbox_tools_registered():
    from matlab_mcp_server.tools.registry import registry
    import matlab_mcp_server.tools.toolbox
    names = registry.list_names()
    expected = ["signal_processing", "control_system", "optimization", "machine_learning", "data_analysis"]
    for name in expected:
        assert name in names, f"Missing toolbox tool: {name}"


def test_signal_processing_tool_schema():
    from matlab_mcp_server.tools.registry import registry
    import matlab_mcp_server.tools.toolbox
    tool = registry.get_all()["signal_processing"]
    assert "fft" in tool["input_schema"]["properties"]["operation"]["enum"]
    assert "lowpass" in tool["input_schema"]["properties"]["operation"]["enum"]


def test_control_system_tool_schema():
    from matlab_mcp_server.tools.registry import registry
    import matlab_mcp_server.tools.toolbox
    tool = registry.get_all()["control_system"]
    assert "tf" in tool["input_schema"]["properties"]["operation"]["enum"]
    assert "bode" in tool["input_schema"]["properties"]["operation"]["enum"]


def test_machine_learning_requires_label_for_classification():
    from matlab_mcp_server.tools.registry import registry
    import matlab_mcp_server.tools.toolbox
    tool = registry.get_all()["machine_learning"]
    assert "data_variable" in tool["input_schema"]["required"]


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.execute = AsyncMock(return_value="")
    return engine


@pytest.fixture
def mock_task_executor():
    return MagicMock()


@pytest.mark.asyncio
async def test_signal_processing_fft(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_signal_processing
    result = await handle_signal_processing(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "fft", "input_variable": "x", "output_variable": "X"},
    )
    assert result["success"] is True
    assert result["operation"] == "fft"
    assert "fft(x)" in mock_engine.execute.call_args[0][0]


@pytest.mark.asyncio
async def test_signal_processing_lowpass(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_signal_processing
    result = await handle_signal_processing(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "lowpass", "input_variable": "sig", "params": {"cutoff": 200, "fs": 1000}},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "butter" in script
    assert "filter" in script


@pytest.mark.asyncio
async def test_signal_processing_unknown_op(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_signal_processing
    result = await handle_signal_processing(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "unknown", "input_variable": "x"},
    )
    assert result["success"] is False
    assert "Unknown operation" in result["error"]


@pytest.mark.asyncio
async def test_control_system_tf(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_control_system
    result = await handle_control_system(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "tf", "num": [1, 2], "den": [1, 3, 2]},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "tf([1, 2], [1, 3, 2])" in script


@pytest.mark.asyncio
async def test_control_system_tf_missing_num_den(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_control_system
    result = await handle_control_system(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "tf"},
    )
    assert result["success"] is False
    assert "requires 'num' and 'den'" in result["error"]


@pytest.mark.asyncio
async def test_control_system_bode(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_control_system
    result = await handle_control_system(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "bode", "output_variable": "sys"},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "bode(sys)" in script


@pytest.mark.asyncio
async def test_optimization_fminsearch(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_optimization
    result = await handle_optimization(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "fminsearch", "objective_variable": "@(x) x.^2", "x0_variable": "[1]"},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "fminsearch" in script


@pytest.mark.asyncio
async def test_optimization_linprog(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_optimization
    result = await handle_optimization(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "linprog", "params": {"c": "[1; 2]", "A": "[1, 1]", "b": "[10]"}},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "linprog" in script


@pytest.mark.asyncio
async def test_machine_learning_fitcsvm(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_machine_learning
    result = await handle_machine_learning(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "fitcsvm", "data_variable": "X", "label_variable": "Y"},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "fitcsvm(X, Y)" in script


@pytest.mark.asyncio
async def test_machine_learning_fitcsvm_missing_label(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_machine_learning
    result = await handle_machine_learning(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "fitcsvm", "data_variable": "X"},
    )
    assert result["success"] is False
    assert "label_variable" in result["error"]


@pytest.mark.asyncio
async def test_machine_learning_pca(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_machine_learning
    result = await handle_machine_learning(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "pca", "data_variable": "X"},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "pca(X)" in script


@pytest.mark.asyncio
async def test_data_analysis_describe(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_data_analysis
    result = await handle_data_analysis(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "describe", "data_variable": "data"},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "mean(data)" in script
    assert "median(data)" in script
    assert "std(data)" in script


@pytest.mark.asyncio
async def test_data_analysis_corrcoef(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_data_analysis
    result = await handle_data_analysis(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "corrcoef", "data_variable": "M"},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "corrcoef(M)" in script


@pytest.mark.asyncio
async def test_data_analysis_engine_error(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_data_analysis
    mock_engine.execute = AsyncMock(side_effect=Exception("Undefined function"))
    result = await handle_data_analysis(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "describe", "data_variable": "data"},
    )
    assert result["success"] is False
    assert "Undefined function" in result["error"]


@pytest.mark.asyncio
async def test_machine_learning_method_escaping(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.toolbox import handle_machine_learning
    result = await handle_machine_learning(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"operation": "fitcensemble", "data_variable": "X", "label_variable": "Y", "params": {"method": "it's"}},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "it''s" in script

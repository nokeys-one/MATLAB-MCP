import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path


def test_computation_tools_registered():
    from matlab_mcp_server.tools.registry import registry
    import matlab_mcp_server.tools.computation  # noqa: F401

    names = registry.list_names()
    assert "run_matlab_function" in names
    assert "execute_matlab_script" in names
    assert "evaluate_expression" in names
    assert "get_workspace_variable" in names
    assert "list_workspace_variables" in names


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.execute = AsyncMock(return_value="4")
    engine.get_variable_info = AsyncMock(return_value={"name": "x", "value_preview": "42"})
    engine.list_workspace = AsyncMock(return_value="x  1x1  8  double")
    return engine


@pytest.fixture
def mock_task_executor():
    return MagicMock()


@pytest.mark.asyncio
async def test_run_matlab_function_l0_success(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_run_matlab_function

    result = await handle_run_matlab_function(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"function_name": "fft", "args": [[1, 2, 3, 4]], "output_variable": "result"},
    )
    assert result["success"] is True
    assert result["function"] == "fft"
    mock_engine.execute.assert_called_once()
    called_script = mock_engine.execute.call_args[0][0]
    assert "result = fft(" in called_script


@pytest.mark.asyncio
async def test_run_matlab_function_l3_blocked(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_run_matlab_function

    result = await handle_run_matlab_function(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"function_name": "eval", "args": ["disp('hello')"]},
    )
    assert result["success"] is False
    assert result["security_level"] == "L3_BLOCKED"
    mock_engine.execute.assert_not_called()


@pytest.mark.asyncio
async def test_run_matlab_function_l2_no_approval_queue(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_run_matlab_function

    result = await handle_run_matlab_function(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"function_name": "system", "args": ["ls"]},
    )
    assert result["success"] is False
    assert result["pending_approval"] is True
    assert result["security_level"] == "L2_APPROVAL"


@pytest.mark.asyncio
async def test_run_matlab_function_l2_approved(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_run_matlab_function
    from matlab_mcp_server.security.approval_queue import ApprovalQueue

    aq = ApprovalQueue(timeout=5.0)

    async def auto_approve(aq_ref):
        import asyncio
        await asyncio.sleep(0.1)
        for req in aq_ref.get_pending():
            aq_ref.approve(req["approval_id"])

    import asyncio
    task = asyncio.create_task(auto_approve(aq))

    result = await handle_run_matlab_function(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"function_name": "system", "args": ["ls"]},
        approval_queue=aq,
    )
    assert result["success"] is True
    await task


@pytest.mark.asyncio
async def test_run_matlab_function_l2_rejected(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_run_matlab_function
    from matlab_mcp_server.security.approval_queue import ApprovalQueue

    aq = ApprovalQueue(timeout=0.5)

    async def auto_reject(aq_ref):
        import asyncio
        await asyncio.sleep(0.1)
        for req in aq_ref.get_pending():
            aq_ref.reject(req["approval_id"])

    import asyncio
    task = asyncio.create_task(auto_reject(aq))

    result = await handle_run_matlab_function(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"function_name": "system", "args": ["rm -rf /"]},
        approval_queue=aq,
    )
    assert result["success"] is False
    assert result["rejected"] is True
    await task


@pytest.mark.asyncio
async def test_run_matlab_function_engine_error(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_run_matlab_function

    mock_engine.execute = AsyncMock(side_effect=Exception("MATLAB crashed"))
    result = await handle_run_matlab_function(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"function_name": "sin", "args": [3.14]},
    )
    assert result["success"] is False
    assert "MATLAB crashed" in result["error"]


@pytest.mark.asyncio
async def test_evaluate_expression_safe(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_evaluate_expression

    result = await handle_evaluate_expression(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"expression": "sin(pi) + cos(0)"},
    )
    assert result["success"] is True
    assert result["expression"] == "sin(pi) + cos(0)"
    mock_engine.execute.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_expression_blocked(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_evaluate_expression

    result = await handle_evaluate_expression(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"expression": "eval('disp(hello)')"},
    )
    assert result["success"] is False
    assert result["security_level"] == "L3_BLOCKED"
    assert len(result["risks"]) > 0


@pytest.mark.asyncio
async def test_evaluate_expression_warn_no_approval_queue(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_evaluate_expression

    result = await handle_evaluate_expression(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"expression": "system('ls')"},
    )
    assert result["success"] is False
    assert result["pending_approval"] is True


@pytest.mark.asyncio
async def test_get_workspace_variable_success(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_get_workspace_variable

    result = await handle_get_workspace_variable(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"variable_name": "x"},
    )
    assert result["success"] is True
    assert result["name"] == "x"


@pytest.mark.asyncio
async def test_get_workspace_variable_not_found(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_get_workspace_variable

    mock_engine.get_variable_info = AsyncMock(return_value={"name": "missing", "error": "not found"})
    result = await handle_get_workspace_variable(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"variable_name": "missing"},
    )
    assert result["success"] is False
    assert result["error"] == "not found"
    assert result["name"] == "missing"


@pytest.mark.asyncio
async def test_list_workspace_variables_success(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_list_workspace_variables

    result = await handle_list_workspace_variables(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={},
    )
    assert result["success"] is True
    assert "variables" in result


@pytest.mark.asyncio
async def test_execute_matlab_script_path_traversal(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_execute_matlab_script

    result = await handle_execute_matlab_script(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"script_path": "../../../etc/passwd"},
    )
    assert result["success"] is False
    mock_engine.execute.assert_not_called()


def test_to_matlab_literal_string_escaping():
    from matlab_mcp_server.tools.computation import _to_matlab_literal

    assert _to_matlab_literal("hello") == "'hello'"
    assert _to_matlab_literal("it's") == "'it''s'"
    assert _to_matlab_literal("a'b'c") == "'a''b''c'"


def test_to_matlab_literal_types():
    from matlab_mcp_server.tools.computation import _to_matlab_literal

    assert _to_matlab_literal(42) == "42"
    assert _to_matlab_literal(3.14) == "3.14"
    assert _to_matlab_literal(True) == "true"
    assert _to_matlab_literal(False) == "false"
    assert _to_matlab_literal(None) == "[]"
    assert _to_matlab_literal([1, 2, 3]) == "[1, 2, 3]"


def test_to_matlab_literal_nested_list():
    from matlab_mcp_server.tools.computation import _to_matlab_literal

    assert _to_matlab_literal([[1, 2], [3, 4]]) == "[[1, 2], [3, 4]]"


def test_to_matlab_literal_string_in_list():
    from matlab_mcp_server.tools.computation import _to_matlab_literal

    assert _to_matlab_literal(["a", "b"]) == "['a', 'b']"


def test_to_matlab_literal_unsupported_type():
    from matlab_mcp_server.tools.computation import _to_matlab_literal

    with pytest.raises(ValueError, match="Unsupported"):
        _to_matlab_literal(object())


@pytest.mark.asyncio
async def test_run_matlab_function_string_arg_quotes_escaped(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_run_matlab_function

    result = await handle_run_matlab_function(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"function_name": "disp", "args": ["it's a test"]},
    )
    assert result["success"] is True
    called_script = mock_engine.execute.call_args[0][0]
    assert called_script == "disp('it''s a test');"


@pytest.mark.asyncio
async def test_run_matlab_function_kwarg_name_value_syntax(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_run_matlab_function

    result = await handle_run_matlab_function(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"function_name": "plot", "args": [[1, 2]], "kwargs": {"Color": "red"}},
    )
    assert result["success"] is True
    called_script = mock_engine.execute.call_args[0][0]
    assert "Color='red'" in called_script


@pytest.mark.asyncio
async def test_run_matlab_function_kwarg_string_value_escaped(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_run_matlab_function

    result = await handle_run_matlab_function(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"function_name": "plot", "args": [[1, 2]], "kwargs": {"Title": "it's a test"}},
    )
    assert result["success"] is True
    called_script = mock_engine.execute.call_args[0][0]
    assert "Title='it''s a test'" in called_script


@pytest.mark.asyncio
async def test_execute_matlab_script_path_quote_escaped(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.computation import handle_execute_matlab_script

    with patch("matlab_mcp_server.security.path_sanitizer.sanitize_path", return_value=r"C:\sandbox\my file.m"):
        with patch("matlab_mcp_server.config.Settings") as MockCls:
            MockCls.return_value = MagicMock(sandbox_dir=Path("/sandbox"))
            result = await handle_execute_matlab_script(
                engine=mock_engine,
                task_executor=mock_task_executor,
                params={"script_path": "my file.m"},
            )

    assert result["success"] is True
    called_cmd = mock_engine.execute.call_args[0][0]
    assert "my file.m" in called_cmd
    assert called_cmd == "run('C:\\sandbox\\my file.m')"

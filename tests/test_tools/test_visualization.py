import pytest
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path


def test_visualization_tools_registered():
    from matlab_mcp_server.tools.registry import registry
    import matlab_mcp_server.tools.visualization

    names = registry.list_names()
    expected = ["create_plot", "create_3d_plot", "export_figure", "subplot_layout", "verify_plot_data"]
    for name in expected:
        assert name in names, f"Missing tool: {name}"


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.execute = AsyncMock(return_value="")
    engine.sandbox_dir = Path("/tmp/sandbox")
    return engine


@pytest.fixture
def mock_task_executor():
    return MagicMock()


@pytest.fixture
def mock_client_adapter():
    adapter = MagicMock()
    adapter.adapt_image_response = MagicMock(side_effect=lambda r, p: r)
    return adapter


@pytest.mark.asyncio
async def test_create_plot_line(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_create_plot

    result = await handle_create_plot(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "plot_type": "line",
            "x_variable_name": "x",
            "y_variable_name": "y",
            "title": "Test Plot",
            "xlabel": "X",
            "ylabel": "Y",
        },
    )
    assert result["success"] is True
    assert "figure_path" in result
    assert mock_engine.execute.call_count == 2
    plot_script = mock_engine.execute.call_args_list[0][0][0]
    assert "plot(x, y)" in plot_script
    assert "title('Test Plot')" in plot_script
    assert "xlabel('X')" in plot_script
    assert "ylabel('Y')" in plot_script


@pytest.mark.asyncio
async def test_create_plot_bar(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_create_plot

    result = await handle_create_plot(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "plot_type": "bar",
            "x_variable_name": "categories",
            "y_variable_name": "values",
        },
    )
    assert result["success"] is True
    plot_script = mock_engine.execute.call_args_list[0][0][0]
    assert "bar(categories, values)" in plot_script


@pytest.mark.asyncio
async def test_create_plot_scatter(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_create_plot

    result = await handle_create_plot(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "plot_type": "scatter",
            "x_variable_name": "a",
            "y_variable_name": "b",
        },
    )
    assert result["success"] is True
    plot_script = mock_engine.execute.call_args_list[0][0][0]
    assert "scatter(a, b)" in plot_script


@pytest.mark.asyncio
async def test_create_plot_with_client_adapter(mock_engine, mock_task_executor, mock_client_adapter):
    from matlab_mcp_server.tools.visualization import handle_create_plot

    result = await handle_create_plot(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "plot_type": "line",
            "x_variable_name": "x",
            "y_variable_name": "y",
        },
        client_adapter=mock_client_adapter,
    )
    assert result["success"] is True
    mock_client_adapter.adapt_image_response.assert_called_once()


@pytest.mark.asyncio
async def test_create_plot_engine_error(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_create_plot

    mock_engine.execute = AsyncMock(side_effect=Exception("Plot failed"))
    result = await handle_create_plot(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "plot_type": "line",
            "x_variable_name": "x",
            "y_variable_name": "y",
        },
    )
    assert result["success"] is False
    assert "Plot failed" in result["error"]


@pytest.mark.asyncio
async def test_create_plot_escapes_quotes(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_create_plot

    result = await handle_create_plot(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "plot_type": "line",
            "x_variable_name": "x",
            "y_variable_name": "y",
            "title": "it's a test",
            "xlabel": "x'axis",
        },
    )
    assert result["success"] is True
    plot_script = mock_engine.execute.call_args_list[0][0][0]
    assert "it''s a test" in plot_script
    assert "x''axis" in plot_script
    assert "'it's a test'" not in plot_script
    assert "'x'axis'" not in plot_script


@pytest.mark.asyncio
async def test_create_3d_plot_surf(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_create_3d_plot

    result = await handle_create_3d_plot(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "plot_type": "surf",
            "x_variable_name": "X",
            "y_variable_name": "Y",
            "z_variable_name": "Z",
        },
    )
    assert result["success"] is True
    assert "figure_path" in result
    plot_script = mock_engine.execute.call_args_list[0][0][0]
    assert "surf(X,Y,Z)" in plot_script


@pytest.mark.asyncio
async def test_create_3d_plot_mesh(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_create_3d_plot

    result = await handle_create_3d_plot(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "plot_type": "mesh",
            "x_variable_name": "X",
            "y_variable_name": "Y",
            "z_variable_name": "Z",
        },
    )
    assert result["success"] is True
    plot_script = mock_engine.execute.call_args_list[0][0][0]
    assert "mesh(X,Y,Z)" in plot_script


@pytest.mark.asyncio
async def test_create_3d_plot_with_adapter(mock_engine, mock_task_executor, mock_client_adapter):
    from matlab_mcp_server.tools.visualization import handle_create_3d_plot

    result = await handle_create_3d_plot(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "plot_type": "contour",
            "x_variable_name": "X",
            "y_variable_name": "Y",
            "z_variable_name": "Z",
        },
        client_adapter=mock_client_adapter,
    )
    assert result["success"] is True
    mock_client_adapter.adapt_image_response.assert_called_once()


@pytest.mark.asyncio
async def test_create_3d_plot_escapes_path(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_create_3d_plot

    result = await handle_create_3d_plot(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "plot_type": "surf",
            "x_variable_name": "X",
            "y_variable_name": "Y",
            "z_variable_name": "Z",
        },
    )
    assert result["success"] is True
    save_script = mock_engine.execute.call_args_list[1][0][0]
    assert "''" not in save_script or "saveas" in save_script


@pytest.mark.asyncio
async def test_export_figure(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_export_figure

    result = await handle_export_figure(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"filename": "my_figure.png", "format": "png", "dpi": 300},
    )
    assert result["success"] is True
    assert "figure_path" in result
    save_script = mock_engine.execute.call_args[0][0]
    assert "saveas" in save_script


@pytest.mark.asyncio
async def test_export_figure_with_adapter(mock_engine, mock_task_executor, mock_client_adapter):
    from matlab_mcp_server.tools.visualization import handle_export_figure

    result = await handle_export_figure(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"filename": "output.svg"},
        client_adapter=mock_client_adapter,
    )
    assert result["success"] is True
    mock_client_adapter.adapt_image_response.assert_called_once()


@pytest.mark.asyncio
async def test_export_figure_error(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_export_figure

    mock_engine.execute = AsyncMock(side_effect=Exception("Export failed"))
    result = await handle_export_figure(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"filename": "fail.png"},
    )
    assert result["success"] is False
    assert "Export failed" in result["error"]


@pytest.mark.asyncio
async def test_subplot_layout(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_subplot_layout

    result = await handle_subplot_layout(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "rows": 2,
            "cols": 2,
            "plots": [
                {"plot_type": "plot", "x_variable_name": "x1", "y_variable_name": "y1", "title": "Plot 1"},
                {"plot_type": "bar", "x_variable_name": "x2", "y_variable_name": "y2", "title": "Plot 2"},
            ],
        },
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args_list[0][0][0]
    assert "subplot(2,2,1)" in script
    assert "subplot(2,2,2)" in script
    assert "plot(x1,y1)" in script
    assert "bar(x2,y2)" in script


@pytest.mark.asyncio
async def test_subplot_layout_escapes_quotes(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_subplot_layout

    result = await handle_subplot_layout(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "rows": 1,
            "cols": 2,
            "plots": [
                {"plot_type": "plot", "x_variable_name": "x", "y_variable_name": "y", "title": "it's"},
            ],
        },
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args_list[0][0][0]
    assert "it''s" in script


@pytest.mark.asyncio
async def test_subplot_layout_with_adapter(mock_engine, mock_task_executor, mock_client_adapter):
    from matlab_mcp_server.tools.visualization import handle_subplot_layout

    result = await handle_subplot_layout(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={
            "rows": 1,
            "cols": 1,
            "plots": [{"plot_type": "plot", "x_variable_name": "x", "y_variable_name": "y"}],
        },
        client_adapter=mock_client_adapter,
    )
    assert result["success"] is True
    mock_client_adapter.adapt_image_response.assert_called_once()


@pytest.mark.asyncio
async def test_verify_plot_data(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_verify_plot_data

    mock_engine.execute = AsyncMock(return_value="struct with axes info")
    result = await handle_verify_plot_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"figure_path": "/path/to/fig.png"},
    )
    assert result["success"] is True
    assert result["chart_info"] == "struct with axes info"
    script = mock_engine.execute.call_args[0][0]
    assert "openfig" in script
    assert "findobj" in script


@pytest.mark.asyncio
async def test_verify_plot_data_escapes_quotes(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_verify_plot_data

    mock_engine.execute = AsyncMock(return_value="info")
    result = await handle_verify_plot_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"figure_path": "C:\\my'path\\fig.png"},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "my''path" in script


@pytest.mark.asyncio
async def test_verify_plot_data_error(mock_engine, mock_task_executor):
    from matlab_mcp_server.tools.visualization import handle_verify_plot_data

    mock_engine.execute = AsyncMock(side_effect=Exception("File not found"))
    result = await handle_verify_plot_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"figure_path": "/missing.png"},
    )
    assert result["success"] is False
    assert "File not found" in result["error"]

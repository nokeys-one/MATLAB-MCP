import json
import pytest  # type: ignore
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from mcp.server.fastmcp import FastMCP

from matlab_mcp_server.resources.matlab_resources import register_resources
from matlab_mcp_server.resources.prompts import (
    register_prompts,
    SIMULATION_GUIDE,
    PLOT_STYLING,
    DATA_ANALYSIS_WORKFLOW,
    SIGNAL_PROCESSING_GUIDE,
    TROUBLESHOOTING,
)


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.list_workspace = AsyncMock(return_value="whos output")
    engine.get_variable_info = AsyncMock(return_value={"name": "x", "value_preview": "[1 2 3]"})
    engine.execute = AsyncMock(return_value="model_info_raw")
    return engine


@pytest.fixture
def mock_task_executor():
    executor = MagicMock()
    executor.get_status = MagicMock(return_value={
        "task_id": "task_abc",
        "tool_name": "run_simulation",
        "status": "completed",
        "progress": 1.0,
        "elapsed_seconds": 5.2,
        "created_at": time.time(),
        "started_at": time.time() - 5,
        "completed_at": time.time(),
    })
    task = MagicMock()
    task.result = {"data": [1, 2, 3]}
    task.error = None
    executor.get_task = MagicMock(return_value=task)
    return executor


@pytest.fixture
def mock_workspace(tmp_path):
    ws = MagicMock()
    ws.sandbox_dir = tmp_path
    return ws


@pytest.fixture
def mock_settings(tmp_path):
    settings = MagicMock()
    settings.sandbox_dir = tmp_path
    return settings


@pytest.fixture
def mcp_with_resources(mock_engine, mock_task_executor, mock_workspace, mock_settings):
    mcp = FastMCP(name="test-resources")
    register_resources(mcp, mock_engine, mock_task_executor, mock_workspace, mock_settings)
    register_prompts(mcp)
    return mcp


async def read_resource_content(mcp, uri: str) -> str:
    resource = await mcp._resource_manager.get_resource(uri)
    assert resource is not None, f"Resource not found: {uri}"
    return await resource.read()


def parse_json_resource(content: str | bytes) -> dict:
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    return json.loads(content)


class TestWorkspaceVariablesResource:
    @pytest.mark.asyncio
    async def test_success(self, mcp_with_resources, mock_engine):
        content = await read_resource_content(mcp_with_resources, "matlab://workspace/variables")
        data = parse_json_resource(content)
        assert data["success"] is True
        assert "variables" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_engine_error(self, mcp_with_resources, mock_engine):
        mock_engine.list_workspace = AsyncMock(side_effect=RuntimeError("Engine not started"))
        content = await read_resource_content(mcp_with_resources, "matlab://workspace/variables")
        data = parse_json_resource(content)
        assert data["success"] is False
        assert "Engine not started" in data["error"]


class TestWorkspaceVariableDetailResource:
    @pytest.mark.asyncio
    async def test_success(self, mcp_with_resources, mock_engine):
        content = await read_resource_content(mcp_with_resources, "matlab://workspace/variable/x")
        data = parse_json_resource(content)
        assert data["success"] is True
        assert "variable" in data
        assert data["variable"]["name"] == "x"

    @pytest.mark.asyncio
    async def test_engine_error(self, mcp_with_resources, mock_engine):
        mock_engine.get_variable_info = AsyncMock(side_effect=Exception("fail"))
        content = await read_resource_content(mcp_with_resources, "matlab://workspace/variable/y")
        data = parse_json_resource(content)
        assert data["success"] is False
        assert data["variable_name"] == "y"


class TestSandboxFilesResource:
    @pytest.mark.asyncio
    async def test_empty_sandbox(self, mcp_with_resources):
        content = await read_resource_content(mcp_with_resources, "matlab://sandbox/files")
        data = parse_json_resource(content)
        assert data["success"] is True
        assert data["count"] >= 0
        assert "sandbox_dir" in data

    @pytest.mark.asyncio
    async def test_with_files(self, mcp_with_resources, mock_settings):
        (mock_settings.sandbox_dir / "data").mkdir(exist_ok=True)
        (mock_settings.sandbox_dir / "data" / "test.csv").write_text("a,b\n1,2")
        content = await read_resource_content(mcp_with_resources, "matlab://sandbox/files")
        data = parse_json_resource(content)
        assert data["success"] is True
        assert data["count"] >= 1
        found = any("test.csv" in f["path"] for f in data["files"])
        assert found


class TestSandboxFileContentResource:
    @pytest.mark.asyncio
    async def test_text_file(self, mcp_with_resources, mock_settings):
        (mock_settings.sandbox_dir / "hello.txt").write_text("hello world")
        content = await read_resource_content(mcp_with_resources, "matlab://sandbox/file/hello.txt")
        data = parse_json_resource(content)
        assert data["success"] is True
        assert data["format"] == "text"
        assert data["content"] == "hello world"

    @pytest.mark.asyncio
    async def test_not_found(self, mcp_with_resources):
        content = await read_resource_content(mcp_with_resources, "matlab://sandbox/file/nonexistent.txt")
        data = parse_json_resource(content)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_traversal_blocked_via_function(self, mock_engine, mock_task_executor, mock_workspace, mock_settings):
        from matlab_mcp_server.security.path_sanitizer import sanitize_path, PathTraversalError
        mcp = FastMCP(name="test-traversal")
        register_resources(mcp, mock_engine, mock_task_executor, mock_workspace, mock_settings)
        resource = await mcp._resource_manager.get_resource("matlab://sandbox/file/hello.txt")
        assert resource is not None
        with pytest.raises(PathTraversalError):
            sanitize_path("../../etc/passwd", str(mock_settings.sandbox_dir))

    @pytest.mark.asyncio
    async def test_template_rejects_invalid_uri(self, mcp_with_resources):
        with pytest.raises((ValueError, Exception)):
            await mcp_with_resources._resource_manager.get_resource(
                "matlab://sandbox/file/../../etc/passwd"
            )

    @pytest.mark.asyncio
    async def test_binary_file(self, mcp_with_resources, mock_settings):
        (mock_settings.sandbox_dir / "data.mat").write_bytes(b"\x00\x01\x02\x03")
        content = await read_resource_content(mcp_with_resources, "matlab://sandbox/file/data.mat")
        data = parse_json_resource(content)
        assert data["success"] is True
        assert data["format"] == "binary"
        assert "content_base64" in data


class TestTaskStatusResource:
    @pytest.mark.asyncio
    async def test_success(self, mcp_with_resources):
        content = await read_resource_content(mcp_with_resources, "matlab://tasks/task_abc")
        data = parse_json_resource(content)
        assert data["success"] is True
        assert data["status"] == "completed"
        assert data["result"] == {"data": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_not_found(self, mcp_with_resources, mock_task_executor):
        mock_task_executor.get_status = MagicMock(return_value=None)
        content = await read_resource_content(mcp_with_resources, "matlab://tasks/nonexistent")
        data = parse_json_resource(content)
        assert data["success"] is False


class TestSimulinkModelInfoResource:
    @pytest.mark.asyncio
    async def test_success(self, mcp_with_resources, mock_engine):
        content = await read_resource_content(mcp_with_resources, "matlab://sandbox/simulink/mymodel")
        data = parse_json_resource(content)
        assert data["success"] is True
        assert data["model_name"] == "mymodel"
        mock_engine.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_engine_error(self, mcp_with_resources, mock_engine):
        mock_engine.execute = AsyncMock(side_effect=Exception("model not found"))
        content = await read_resource_content(mcp_with_resources, "matlab://sandbox/simulink/badmodel")
        data = parse_json_resource(content)
        assert data["success"] is False
        assert data["model_name"] == "badmodel"


class TestPrompts:
    def test_simulation_guide_content(self):
        assert "Simulink" in SIMULATION_GUIDE
        assert "load_simulink_model" in SIMULATION_GUIDE
        assert "run_simulation" in SIMULATION_GUIDE

    def test_plot_styling_content(self):
        assert "plot_type" in PLOT_STYLING
        assert "line" in PLOT_STYLING
        assert "scatter" in PLOT_STYLING

    def test_data_analysis_workflow_content(self):
        assert "load_data" in DATA_ANALYSIS_WORKFLOW
        assert "describe" in DATA_ANALYSIS_WORKFLOW
        assert "corrcoef" in DATA_ANALYSIS_WORKFLOW

    def test_signal_processing_guide_content(self):
        assert "fft" in SIGNAL_PROCESSING_GUIDE
        assert "lowpass" in SIGNAL_PROCESSING_GUIDE
        assert "fs" in SIGNAL_PROCESSING_GUIDE

    def test_troubleshooting_content(self):
        assert "Undefined function" in TROUBLESHOOTING
        assert "L2_APPROVAL" in TROUBLESHOOTING
        assert "reset_workspace" in TROUBLESHOOTING

    def test_all_prompts_registered(self, mcp_with_resources):
        prompts = mcp_with_resources._prompt_manager.list_prompts()
        names = [p.name for p in prompts]
        assert "simulation_guide" in names
        assert "plot_styling" in names
        assert "data_analysis_workflow" in names
        assert "signal_processing_guide" in names
        assert "troubleshooting" in names

    def test_prompt_retrievable(self, mcp_with_resources):
        prompt = mcp_with_resources._prompt_manager.get_prompt("simulation_guide")
        assert prompt is not None
        assert prompt.name == "simulation_guide"

    @pytest.mark.asyncio
    async def test_prompt_renderable(self, mcp_with_resources):
        messages = await mcp_with_resources._prompt_manager.render_prompt("simulation_guide")
        assert len(messages) > 0
        content = messages[0].content
        text = content.text if hasattr(content, "text") else str(content)
        assert "Simulink" in text

    @pytest.mark.asyncio
    async def test_all_prompts_renderable(self, mcp_with_resources):
        for name in ["simulation_guide", "plot_styling", "data_analysis_workflow",
                      "signal_processing_guide", "troubleshooting"]:
            messages = await mcp_with_resources._prompt_manager.render_prompt(name)
            assert len(messages) > 0, f"Prompt '{name}' returned no messages"


class TestResourcesRegistered:
    def test_all_resources_exist(self, mcp_with_resources):
        rm = mcp_with_resources._resource_manager
        concrete = list(rm._resources.keys())
        templates = list(rm._templates.keys())
        all_uris = concrete + templates
        assert any("workspace/variables" in u for u in all_uris)
        assert any("sandbox/files" in u for u in all_uris)
        assert any("sandbox/file" in u for u in all_uris)
        assert any("tasks" in u for u in all_uris)
        assert any("simulink" in u for u in all_uris)

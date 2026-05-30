import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import Settings
from .engine.manager import MatlabEngineManager
from .engine.async_executor import AsyncTaskExecutor
from .engine.lock_manager import EngineLockManager, EngineBusyError, QUERY_TOOLS
from .sandbox.workspace_manager import WorkspaceManager
from .output.client_adapter import ClientAdapter
from .output.error_formatter import format_error
from .security.approval_queue import ApprovalQueue

logger = logging.getLogger(__name__)


def create_server(settings: Settings) -> FastMCP:
    mcp = FastMCP(
        name="matlab-mcp-server",
        instructions="MATLAB MCP Server: 提供 MATLAB 仿真、建模、画图、数据分析等工具",
    )

    workspace = WorkspaceManager(settings.sandbox_dir)
    workspace.ensure_sandbox_exists()
    shadow_dir = workspace.get_shadow_dir_path()

    engine_mgr = MatlabEngineManager(
        sandbox_dir=settings.sandbox_dir,
        shadow_dir=Path(shadow_dir),
    )
    task_executor = AsyncTaskExecutor(max_workers=settings.max_concurrent_tasks)
    lock_manager = EngineLockManager()
    approval_queue = ApprovalQueue()
    client_adapter = ClientAdapter(
        client_vision=settings.client_vision,
        context_limit=settings.context_limit,
    )

    from .tools.registry import registry

    import matlab_mcp_server.tools.task_manager  # noqa: F401
    import matlab_mcp_server.tools.computation  # noqa: F401
    import matlab_mcp_server.tools.simulink  # noqa: F401
    import matlab_mcp_server.tools.visualization  # noqa: F401

    for name, tool_def in registry.get_all().items():
        handler = tool_def["handler"]

        def make_handler(h, tool_name=name):
            async def tool_handler(params: dict) -> Any:
                needs_lock = tool_name not in QUERY_TOOLS

                if needs_lock:
                    try:
                        acquired = await lock_manager.acquire(tool_name)
                        if not acquired:
                            return {
                                "success": False,
                                "error": "Engine is busy, please wait or call check_task_status",
                                "engine_state": lock_manager.state.value,
                            }
                    except EngineBusyError as e:
                        return format_error(e)

                try:
                    result = await h(
                        engine=engine_mgr,
                        task_executor=task_executor,
                        params=params,
                        client_adapter=client_adapter,
                        workspace=workspace,
                        approval_queue=approval_queue,
                    )
                    return result
                except Exception as e:
                    return format_error(e)
                finally:
                    if needs_lock:
                        await lock_manager.release()
            return tool_handler

        mcp.tool(
            name=name,
            description=tool_def["description"],
        )(make_handler(handler))

    return mcp

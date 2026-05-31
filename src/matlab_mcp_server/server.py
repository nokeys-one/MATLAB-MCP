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
    logger.info("[INIT] Creating MATLAB MCP Server...")
    mcp = FastMCP(
        name="matlab-mcp-server",
        instructions="MATLAB MCP Server: 提供 MATLAB 仿真、建模、画图、数据分析等工具",
    )

    workspace = WorkspaceManager(settings.sandbox_dir)
    workspace.ensure_sandbox_exists()
    shadow_dir = workspace.get_shadow_dir_path()
    logger.info("[INIT] sandbox=%s  shadow=%s", settings.sandbox_dir, shadow_dir)

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
    logger.info("[INIT] max_concurrent_tasks=%s  client_vision=%s  context_limit=%s",
                settings.max_concurrent_tasks, settings.client_vision, settings.context_limit)

    from .tools.registry import registry

    import matlab_mcp_server.tools.task_manager  # noqa: F401
    import matlab_mcp_server.tools.computation  # noqa: F401
    import matlab_mcp_server.tools.simulink  # noqa: F401
    import matlab_mcp_server.tools.visualization  # noqa: F401
    import matlab_mcp_server.tools.toolbox  # noqa: F401
    import matlab_mcp_server.tools.file_ops  # noqa: F401

    def make_handler(h, tool_name):
        async def tool_handler(params: dict) -> Any:
            import time as _time
            param_preview = {k: str(v)[:80] for k, v in params.items()}
            logger.info("[DISPATCH] >>> tool=%s  params=%s", tool_name, param_preview)
            t0 = _time.monotonic()

            needs_lock = tool_name not in QUERY_TOOLS

            if needs_lock:
                try:
                    logger.debug("[LOCK] requesting engine lock for tool=%s", tool_name)
                    acquired = await lock_manager.acquire(tool_name)
                    if not acquired:
                        logger.warning("[LOCK] engine busy, rejecting tool=%s, state=%s",
                                       tool_name, lock_manager.state.value)
                        return {
                            "success": False,
                            "error": "Engine is busy, please wait or call check_task_status",
                            "engine_state": lock_manager.state.value,
                        }
                    logger.debug("[LOCK] acquired engine lock for tool=%s", tool_name)
                except EngineBusyError as e:
                    logger.warning("[LOCK] EngineBusyError for tool=%s: %s", tool_name, e)
                    return format_error(e)

            try:
                result = await h(
                    engine=engine_mgr,
                    task_executor=task_executor,
                    params=params,
                    client_adapter=client_adapter,
                    workspace=workspace,
                    approval_queue=approval_queue,
                    settings=settings,
                )
                elapsed_ms = (_time.monotonic() - t0) * 1000
                success = result.get("success", True) if isinstance(result, dict) else True
                logger.info("[DISPATCH] <<< tool=%s  success=%s  elapsed=%.1fms",
                            tool_name, success, elapsed_ms)
                return result
            except Exception as e:
                elapsed_ms = (_time.monotonic() - t0) * 1000
                logger.error("[DISPATCH] !!! tool=%s  error=%s(%s)  elapsed=%.1fms",
                             tool_name, type(e).__name__, e, elapsed_ms, exc_info=True)
                return format_error(e)
            finally:
                if needs_lock:
                    logger.debug("[LOCK] releasing engine lock for tool=%s", tool_name)
                    await lock_manager.release()
        return tool_handler

    for name, tool_def in registry.get_all().items():
        mcp.tool(
            name=name,
            description=tool_def["description"],
        )(make_handler(tool_def["handler"], name))

    registered = registry.list_names()
    logger.info("[INIT] Registered %d tools: %s", len(registered), sorted(registered))

    from .resources.matlab_resources import register_resources
    register_resources(mcp, engine_mgr, task_executor, workspace, settings)

    from .resources.prompts import register_prompts
    register_prompts(mcp)

    return mcp

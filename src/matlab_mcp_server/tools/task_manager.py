from .registry import registry


@registry.register(
    name="check_task_status",
    description="查询异步任务的状态和进度。返回任务状态、已用时间、结果或错误。",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务 ID"},
        },
        "required": ["task_id"],
    },
)
async def handle_check_task_status(engine, task_executor, params, **kwargs):
    task_id = params["task_id"]
    status = task_executor.get_status(task_id)
    if status is None:
        return {"success": False, "error": f"Task {task_id} not found"}
    task = task_executor.get_task(task_id)
    result = {"success": True, **status}
    if task and task.result is not None:
        result["result"] = task.result
    if task and task.error is not None:
        result["error"] = task.error
    return result


@registry.register(
    name="cancel_task",
    description="取消正在运行的异步任务。",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务 ID"},
        },
        "required": ["task_id"],
    },
)
async def handle_cancel_task(engine, task_executor, params, **kwargs):
    task_id = params["task_id"]
    cancelled = task_executor.cancel(task_id)
    if cancelled:
        return {"success": True, "message": f"Task {task_id} cancellation requested"}
    return {"success": False, "error": f"Task {task_id} not found or not running"}


@registry.register(
    name="approve_operation",
    description="批准一个等待审批的 L2 安全操作。当返回 pending_approval 时使用此工具批准执行。",
    input_schema={
        "type": "object",
        "properties": {
            "approval_id": {"type": "string", "description": "审批请求 ID（从 pending_approval 响应中获取）"},
        },
        "required": ["approval_id"],
    },
)
async def handle_approve_operation(engine, task_executor, params, approval_queue=None, **kwargs):
    if approval_queue is None:
        return {"success": False, "error": "Approval queue not available"}
    approval_id = params["approval_id"]
    result = approval_queue.approve(approval_id)
    if result:
        return {"success": True, "approval_id": approval_id, "message": "Operation approved"}
    return {"success": False, "error": f"Approval request '{approval_id}' not found or already processed"}


@registry.register(
    name="reject_operation",
    description="拒绝一个等待审批的 L2 安全操作。",
    input_schema={
        "type": "object",
        "properties": {
            "approval_id": {"type": "string", "description": "审批请求 ID"},
        },
        "required": ["approval_id"],
    },
)
async def handle_reject_operation(engine, task_executor, params, approval_queue=None, **kwargs):
    if approval_queue is None:
        return {"success": False, "error": "Approval queue not available"}
    approval_id = params["approval_id"]
    result = approval_queue.reject(approval_id)
    if result:
        return {"success": True, "approval_id": approval_id, "message": "Operation rejected"}
    return {"success": False, "error": f"Approval request '{approval_id}' not found or already processed"}


@registry.register(
    name="list_pending_approvals",
    description="列出所有等待审批的 L2 操作。",
    input_schema={"type": "object", "properties": {}},
)
async def handle_list_pending_approvals(engine, task_executor, params, approval_queue=None, **kwargs):
    if approval_queue is None:
        return {"success": True, "pending": []}
    return {"success": True, "pending": approval_queue.get_pending()}


@registry.register(
    name="reset_workspace",
    description="重置 MATLAB 工作区到沙盒状态。清除所有变量、关闭图形、重置工作目录。",
    input_schema={"type": "object", "properties": {}},
)
async def handle_reset_workspace(engine, task_executor, params, workspace=None, **kwargs):
    try:
        await engine.clear_workspace()
        if workspace is not None:
            cleanup_report = workspace.cleanup_residual_files()
            return {
                "success": True,
                "message": "Workspace reset to sandbox state",
                "cleanup": cleanup_report,
            }
        return {"success": True, "message": "Workspace reset to sandbox state"}
    except Exception as e:
        return {"success": False, "error": str(e)}

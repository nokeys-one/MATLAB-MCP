import logging
from .registry import registry

logger = logging.getLogger(__name__)


def _to_matlab_literal(value):
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return repr(value)
    elif isinstance(value, list):
        elements = ", ".join(_to_matlab_literal(v) for v in value)
        return f"[{elements}]"
    elif value is None:
        return "[]"
    else:
        raise ValueError(f"Unsupported MATLAB literal type: {type(value)}")


@registry.register(
    name="run_matlab_function",
    description="调用预定义的 MATLAB 安全函数执行计算。函数必须在白名单中。参数通过小数组或标量传递。",
    input_schema={
        "type": "object",
        "properties": {
            "function_name": {"type": "string", "description": "MATLAB 函数名（必须在安全白名单中）"},
            "args": {"type": "array", "description": "位置参数列表（仅支持标量或小数组，<100元素）", "default": []},
            "kwargs": {"type": "object", "description": "关键字参数", "default": {}},
            "output_variable": {"type": "string", "description": "结果保存到的变量名（可选）", "default": ""},
        },
        "required": ["function_name"],
    },
)
async def handle_run_matlab_function(engine, task_executor, params, **kwargs):
    from ..security.whitelist import check_security_level, SecurityLevel
    from ..security.injection_detector import analyze_matlab_code

    func_name = params["function_name"]
    args = params.get("args", [])
    kw = params.get("kwargs", {})
    out_var = params.get("output_variable", "")

    logger.info(
        "[run_matlab_function] 收到调用请求: func=%s, args=%s, kwargs=%s, out_var=%s",
        func_name, args, kw, out_var or "(无)",
    )

    security_level = check_security_level(func_name)
    logger.debug("[run_matlab_function] 安全检查结果: func=%s -> %s", func_name, security_level.value)

    if security_level == SecurityLevel.L3_BLOCKED:
        logger.warning(
            "[run_matlab_function] 函数被 L3 安全策略阻止: func=%s, security_level=L3_BLOCKED",
            func_name,
        )
        return {
            "success": False,
            "error": f"Function '{func_name}' is blocked for security reasons",
            "security_level": "L3_BLOCKED",
        }

    arg_str = ", ".join(_to_matlab_literal(a) for a in args)
    kw_str = ", ".join(f"{k}={_to_matlab_literal(v)}" for k, v in kw.items())
    all_args = ", ".join(filter(None, [arg_str, kw_str]))

    if out_var:
        script = f"{out_var} = {func_name}({all_args});"
    else:
        script = f"{func_name}({all_args});"

    logger.info("[run_matlab_function] 生成脚本: %s", script)

    if security_level == SecurityLevel.L2_APPROVAL:
        logger.info("[run_matlab_function] L2 级别，需要用户审批: func=%s", func_name)
        aq = kwargs.get("approval_queue")
        if aq is None:
            logger.error("[run_matlab_function] 审批队列不可用，无法处理 L2 请求: func=%s", func_name)
            return {
                "success": False,
                "pending_approval": True,
                "operation": func_name,
                "script": script,
                "error": f"Function '{func_name}' requires user approval before execution",
                "security_level": "L2_APPROVAL",
            }
        req = aq.create_request(
            operation=func_name,
            description=f"Execute MATLAB function '{func_name}' with args: {all_args}",
            risk_level="L2",
            params={"script": script, "function_name": func_name, "args": args, "kwargs": kw},
        )
        logger.info("[run_matlab_function] 审批请求已创建: approval_id=%s, 等待用户响应...", req.approval_id)
        approved = await aq.wait_for_approval(req.approval_id)
        if not approved:
            logger.warning("[run_matlab_function] 审批被拒绝或超时: approval_id=%s", req.approval_id)
            return {
                "success": False,
                "rejected": True,
                "approval_id": req.approval_id,
                "error": f"Operation '{func_name}' was rejected or timed out",
            }
        logger.info("[run_matlab_function] 审批通过: approval_id=%s", req.approval_id)

    try:
        logger.debug("[run_matlab_function] 开始执行脚本: %s", script)
        result = await engine.execute(script)
        logger.info(
            "[run_matlab_function] 执行成功: func=%s, result_len=%d, result_preview=%s",
            func_name, len(result), result[:200] if result else "(空)",
        )
        return {"success": True, "function": func_name, "result": result}
    except Exception as e:
        logger.error(
            "[run_matlab_function] 执行失败: func=%s, error_type=%s, error=%s",
            func_name, type(e).__name__, e, exc_info=True,
        )
        return {"success": False, "error": str(e), "function": func_name}


@registry.register(
    name="execute_matlab_script",
    description="执行预审阅的 MATLAB 脚本文件。脚本路径必须在沙盒目录内。",
    input_schema={
        "type": "object",
        "properties": {
            "script_path": {"type": "string", "description": "脚本文件路径（相对于沙盒目录）"},
            "params": {"type": "object", "description": "传递给脚本的参数", "default": {}},
        },
        "required": ["script_path"],
    },
)
async def handle_execute_matlab_script(engine, task_executor, params, **kwargs):
    from ..security.path_sanitizer import sanitize_path, PathTraversalError
    from ..config import Settings

    script_rel = params["script_path"]
    script_params = params.get("params", {})
    logger.info("[execute_matlab_script] 收到请求: script_path=%s, params=%s", script_rel, script_params)

    settings = Settings()
    try:
        full_path = sanitize_path(script_rel, str(settings.sandbox_dir))
        logger.info("[execute_matlab_script] 路径校验通过: %s -> %s", script_rel, full_path)
    except PathTraversalError as e:
        logger.warning("[execute_matlab_script] 路径穿越攻击被阻止: %s, error=%s", script_rel, e)
        return {"success": False, "error": str(e)}

    try:
        full_path_escaped = full_path.replace("'", "''")
        matlab_cmd = f"run('{full_path_escaped}')"
        logger.debug("[execute_matlab_script] 执行: %s", matlab_cmd)
        result = await engine.execute(matlab_cmd)
        logger.info(
            "[execute_matlab_script] 执行成功: script=%s, result_len=%d",
            script_rel, len(result),
        )
        return {"success": True, "script": script_rel, "result": result}
    except Exception as e:
        logger.error(
            "[execute_matlab_script] 执行失败: script=%s, error_type=%s, error=%s",
            script_rel, type(e).__name__, e, exc_info=True,
        )
        return {"success": False, "error": str(e)}


@registry.register(
    name="evaluate_expression",
    description="计算 MATLAB 表达式（受限，需用户审批）。⚠️ 此操作需要用户批准。",
    input_schema={
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "MATLAB 表达式"},
        },
        "required": ["expression"],
    },
)
async def handle_evaluate_expression(engine, task_executor, params, **kwargs):
    from ..security.injection_detector import is_code_safe

    expr = params["expression"]
    logger.info("[evaluate_expression] 收到请求: expression=%s", expr[:200])

    safe, risks = is_code_safe(expr)
    blocked = [r for r in risks if r.severity == "block"]
    warnings = [r for r in risks if r.severity == "warn"]

    if blocked:
        logger.warning(
            "[evaluate_expression] 表达式被注入检测阻止: blocked_keywords=%s",
            [r.keyword for r in blocked],
        )
        return {
            "success": False,
            "error": "Expression contains blocked code patterns",
            "security_level": "L3_BLOCKED",
            "risks": [
                {"keyword": r.keyword, "line": r.line, "reason": r.reason}
                for r in blocked
            ],
        }

    if warnings:
        logger.info(
            "[evaluate_expression] 检测到警告级风险: warning_keywords=%s, 进入审批流程",
            [r.keyword for r in warnings],
        )
        aq = kwargs.get("approval_queue")
        if aq is None:
            logger.error("[evaluate_expression] 审批队列不可用，无法处理带警告的表达式")
            return {
                "success": False,
                "pending_approval": True,
                "operation": "evaluate_expression",
                "expression": expr,
                "security_level": "L2_APPROVAL",
                "risks": [
                    {"keyword": r.keyword, "line": r.line, "reason": r.reason}
                    for r in warnings
                ],
                "error": "Expression contains patterns requiring user approval",
            }
        req = aq.create_request(
            operation="evaluate_expression",
            description=f"Evaluate MATLAB expression with {len(warnings)} warning(s)",
            risk_level="L2",
            params={"expression": expr, "risks": [r.keyword for r in warnings]},
        )
        logger.info("[evaluate_expression] 审批请求已创建: approval_id=%s", req.approval_id)
        approved = await aq.wait_for_approval(req.approval_id)
        if not approved:
            logger.warning("[evaluate_expression] 审批被拒绝或超时: approval_id=%s", req.approval_id)
            return {
                "success": False,
                "rejected": True,
                "approval_id": req.approval_id,
                "error": "Expression evaluation was rejected or timed out",
            }
        logger.info("[evaluate_expression] 审批通过: approval_id=%s", req.approval_id)

    try:
        logger.debug("[evaluate_expression] 开始执行: %s", expr)
        result = await engine.execute(expr)
        logger.info(
            "[evaluate_expression] 执行成功: result_len=%d, result_preview=%s",
            len(result), result[:200] if result else "(空)",
        )
        return {"success": True, "expression": expr, "result": result}
    except Exception as e:
        logger.error(
            "[evaluate_expression] 执行失败: error_type=%s, error=%s",
            type(e).__name__, e, exc_info=True,
        )
        return {"success": False, "error": str(e)}


@registry.register(
    name="get_workspace_variable",
    description="获取工作区变量的值和元数据。大数据自动降采样或返回统计摘要。",
    input_schema={
        "type": "object",
        "properties": {
            "variable_name": {"type": "string", "description": "变量名"},
            "max_rows": {"type": "integer", "description": "最大返回行数", "default": 100},
        },
        "required": ["variable_name"],
    },
)
async def handle_get_workspace_variable(engine, task_executor, params, **kwargs):
    var_name = params["variable_name"]
    max_rows = params.get("max_rows", 100)
    logger.info("[get_workspace_variable] 查询变量: name=%s, max_rows=%d", var_name, max_rows)
    try:
        info = await engine.get_variable_info(var_name, max_rows)
        if "error" in info:
            logger.warning("[get_workspace_variable] 变量不存在或查询出错: name=%s, error=%s", var_name, info["error"])
            return {"success": False, "name": var_name, "error": info["error"]}
        logger.debug("[get_workspace_variable] 查询成功: name=%s, info_keys=%s", var_name, list(info.keys()))
        return {"success": True, **info}
    except Exception as e:
        logger.error(
            "[get_workspace_variable] 查询失败: name=%s, error_type=%s, error=%s",
            var_name, type(e).__name__, e, exc_info=True,
        )
        return {"success": False, "error": str(e)}


@registry.register(
    name="list_workspace_variables",
    description="列出当前 MATLAB 工作区所有变量的元数据（名称、维度、类型）。",
    input_schema={"type": "object", "properties": {}},
)
async def handle_list_workspace_variables(engine, task_executor, params, **kwargs):
    logger.info("[list_workspace_variables] 列出工作区变量")
    try:
        result = await engine.list_workspace()
        logger.debug("[list_workspace_variables] 查询成功, result_len=%d", len(result) if result else 0)
        return {"success": True, "variables": result}
    except Exception as e:
        logger.error(
            "[list_workspace_variables] 查询失败: error_type=%s, error=%s",
            type(e).__name__, e, exc_info=True,
        )
        return {"success": False, "error": str(e)}

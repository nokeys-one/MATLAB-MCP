import logging
from .registry import registry

logger = logging.getLogger(__name__)


def _esc(s: str) -> str:
    return s.replace("'", "''")


SIMULINK_BLOCK_LIBRARIES = {
    "Sine Wave": "simulink/Sources/Sine Wave",
    "Step": "simulink/Sources/Step",
    "Constant": "simulink/Sources/Constant",
    "Ramp": "simulink/Sources/Ramp",
    "Clock": "simulink/Sources/Clock",
    "Pulse Generator": "simulink/Sources/Pulse Generator",
    "Signal Generator": "simulink/Sources/Signal Generator",
    "From Workspace": "simulink/Sources/From Workspace",
    "In1": "simulink/Sources/In1",
    "Gain": "simulink/Math Operations/Gain",
    "Sum": "simulink/Math Operations/Sum",
    "Product": "simulink/Math Operations/Product",
    "Math Function": "simulink/Math Operations/Math Function",
    "Trigonometric Function": "simulink/Math Operations/Trigonometric Function",
    "Abs": "simulink/Math Operations/Abs",
    "Sign": "simulink/Math Operations/Sign",
    "Rounding": "simulink/Math Operations/Rounding",
    "MinMax": "simulink/Math Operations/MinMax",
    "Logic": "simulink/Logic and Bit Operations/Logical Operator",
    "Compare To Zero": "simulink/Logic and Bit Operations/Compare To Zero",
    "Compare To Constant": "simulink/Logic and Bit Operations/Compare To Constant",
    "Integrator": "simulink/Continuous/Integrator",
    "Derivative": "simulink/Continuous/Derivative",
    "Transfer Fcn": "simulink/Continuous/Transfer Fcn",
    "State-Space": "simulink/Continuous/State-Space",
    "Zero-Pole": "simulink/Continuous/Zero-Pole",
    "Transport Delay": "simulink/Continuous/Transport Delay",
    "Scope": "simulink/Sinks/Scope",
    "Display": "simulink/Sinks/Display",
    "To Workspace": "simulink/Sinks/To Workspace",
    "To File": "simulink/Sinks/To File",
    "Terminator": "simulink/Sinks/Terminator",
    "Out1": "simulink/Sinks/Out1",
    "SubSystem": "simulink/Ports & Subsystems/Subsystem",
    "Unit Delay": "simulink/Discrete/Unit Delay",
    "Discrete Transfer Fcn": "simulink/Discrete/Discrete Transfer Fcn",
    "Discrete State-Space": "simulink/Discrete/Discrete State-Space",
    "Saturation": "simulink/Discontinuities/Saturation",
    "Dead Zone": "simulink/Discontinuities/Dead Zone",
    "Relay": "simulink/Discontinuities/Relay",
    "Mux": "simulink/Signal Routing/Mux",
    "Demux": "simulink/Signal Routing/Demux",
    "Bus Creator": "simulink/Signal Routing/Bus Creator",
    "Bus Selector": "simulink/Signal Routing/Bus Selector",
    "Switch": "simulink/Signal Routing/Switch",
    "Manual Switch": "simulink/Signal Routing/Manual Switch",
}


@registry.register(
    name="load_simulink_model",
    description="加载已有的 Simulink .slx 模型模板。加载前自动清理回调函数（防止恶意代码注入）。",
    input_schema={
        "type": "object",
        "properties": {
            "model_path": {"type": "string", "description": "模型文件路径（相对于沙盒目录）"},
        },
        "required": ["model_path"],
    },
)
async def handle_load_simulink_model(engine, task_executor, params, **kwargs):
    model_path = params["model_path"]
    from ..security.path_sanitizer import sanitize_path, PathTraversalError
    from ..config import Settings

    settings = Settings()
    try:
        full_path = sanitize_path(model_path, str(settings.sandbox_dir))
    except PathTraversalError as e:
        return {"success": False, "error": str(e)}

    try:
        await engine.execute(f"load_system('{_esc(full_path)}')")
        from pathlib import Path
        model_name = Path(model_path).stem

        if settings.simulink_cleanup_callbacks:
            from ..security.callback_cleaner import build_sanitization_script
            cleanup_script = build_sanitization_script(model_name)
            await engine.execute(cleanup_script)

        return {"success": True, "model_name": model_name, "model_path": full_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="modify_block_parameters",
    description="修改 Simulink 模型中指定模块的参数。用于在预建模板上调参。",
    input_schema={
        "type": "object",
        "properties": {
            "model_name": {"type": "string", "description": "模型名称"},
            "block_path": {"type": "string", "description": "模块路径（如 'motor/PID Controller'）"},
            "params": {"type": "object", "description": "要修改的参数字典"},
        },
        "required": ["model_name", "block_path", "params"],
    },
)
async def handle_modify_block_parameters(engine, task_executor, params, **kwargs):
    model = params["model_name"]
    block = params["block_path"]
    param_dict = params["params"]

    scripts = []
    safe_model = _esc(model)
    safe_block = _esc(block)
    for key, value in param_dict.items():
        safe_key = _esc(key)
        if isinstance(value, str):
            scripts.append(f"set_param('{safe_model}/{safe_block}', '{safe_key}', '{_esc(value)}')")
        else:
            scripts.append(f"set_param('{safe_model}/{safe_block}', '{safe_key}', {value})")

    try:
        await engine.execute(";\n".join(scripts))
        return {"success": True, "model": model, "block": block, "modified_params": list(param_dict.keys())}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="list_block_parameters",
    description="列出 Simulink 模型中指定模块的所有可调参数及其当前值。",
    input_schema={
        "type": "object",
        "properties": {
            "model_name": {"type": "string"},
            "block_path": {"type": "string"},
        },
        "required": ["model_name", "block_path"],
    },
)
async def handle_list_block_parameters(engine, task_executor, params, **kwargs):
    model = params["model_name"]
    block = params["block_path"]
    try:
        result = await engine.execute(f"get_param('{_esc(model)}/{_esc(block)}', 'DialogParameters')")
        return {"success": True, "model": model, "block": block, "parameters": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="create_simple_model",
    description="创建简单的线性链式 Simulink 模型（模块按顺序自动连接）。支持常用 Simulink 模块名称（如 'Gain', 'Integrator', 'Scope'）自动映射到正确的库路径，也支持传入完整库路径（如 'simulink/Math Operations/Gain'）。",
    input_schema={
        "type": "object",
        "properties": {
            "model_name": {"type": "string"},
            "blocks": {"type": "array", "items": {"type": "string"}, "description": "模块类型列表，按顺序连接"},
        },
        "required": ["model_name", "blocks"],
    },
)
async def handle_create_simple_model(engine, task_executor, params, **kwargs):
    model = params["model_name"]
    blocks = params["blocks"]
    safe_model = _esc(model)

    script_lines = [f"new_system('{safe_model}')"]
    for i, block_type in enumerate(blocks):
        block_name = f"Block_{i}"
        if "/" in block_type:
            lib_path = block_type
        elif block_type in SIMULINK_BLOCK_LIBRARIES:
            lib_path = SIMULINK_BLOCK_LIBRARIES[block_type]
        else:
            lib_path = f"simulink/Sources/{block_type}"
        script_lines.append(f"add_block('{_esc(lib_path)}', '{safe_model}/{block_name}')")
    for i in range(len(blocks) - 1):
        src = f"Block_{i}/1"
        dst = f"Block_{i+1}/1"
        script_lines.append(f"add_line('{safe_model}', '{src}', '{dst}')")

    try:
        await engine.execute(";\n".join(script_lines))
        return {"success": True, "model_name": model, "blocks": blocks}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="configure_simulation",
    description="配置 Simulink 仿真参数（求解器、仿真时长、步长等）。",
    input_schema={
        "type": "object",
        "properties": {
            "model_name": {"type": "string"},
            "solver": {"type": "string", "default": "ode45"},
            "stop_time": {"type": "number", "default": 10.0},
            "step_size": {"type": "number", "default": 0.01},
        },
        "required": ["model_name"],
    },
)
async def handle_configure_simulation(engine, task_executor, params, **kwargs):
    model = params["model_name"]
    solver = params.get("solver", "ode45")
    stop_time = params.get("stop_time", 10.0)
    step_size = params.get("step_size", 0.01)

    safe_model = _esc(model)
    safe_solver = _esc(solver)
    script = (
        f"set_param('{safe_model}', 'Solver', '{safe_solver}');\n"
        f"set_param('{safe_model}', 'StopTime', '{stop_time}');\n"
        f"set_param('{safe_model}', 'FixedStep', '{step_size}');"
    )
    try:
        await engine.execute(script)
        return {"success": True, "model": model, "solver": solver, "stop_time": stop_time}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="run_simulation",
    description="运行 Simulink 仿真（异步执行，立即返回 Task_ID）。三种模式：code(纯后台)、gui(打开GUI)、hybrid(后台+GUI可查看)。",
    input_schema={
        "type": "object",
        "properties": {
            "model_name": {"type": "string"},
            "mode": {"type": "string", "enum": ["code", "gui", "hybrid"], "default": "code"},
        },
        "required": ["model_name"],
    },
)
async def handle_run_simulation(engine, task_executor, params, **kwargs):
    model = params["model_name"]
    mode = params.get("mode", "code")
    safe_model = _esc(model)

    def run_sim():
        if mode in ("gui", "hybrid"):
            engine._execute_sync(f"open_system('{safe_model}')")
        result = engine._execute_sync(f"sim('{safe_model}')")
        return result

    task_id = task_executor.submit("run_simulation", run_sim)
    return {
        "success": True,
        "task_id": task_id,
        "model_name": model,
        "mode": mode,
        "message": "Simulation started. Use check_task_status(task_id) to monitor progress.",
    }


@registry.register(
    name="get_simulation_results",
    description="获取已完成仿真的结果数据。大数据自动降采样。",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
            "signals": {"type": "array", "items": {"type": "string"}, "description": "要获取的信号名列表"},
        },
        "required": ["task_id"],
    },
)
async def handle_get_simulation_results(engine, task_executor, params, **kwargs):
    task_id = params["task_id"]
    task = task_executor.get_task(task_id)
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}
    if task.status.value != "completed":
        return {"success": False, "error": f"Task not completed. Current status: {task.status.value}"}
    return {"success": True, "task_id": task_id, "result": task.result}


@registry.register(
    name="open_simulink_gui",
    description="打开 Simulink GUI 让用户查看/编辑模型。",
    input_schema={
        "type": "object",
        "properties": {"model_name": {"type": "string"}},
        "required": ["model_name"],
    },
)
async def handle_open_simulink_gui(engine, task_executor, params, **kwargs):
    model = params["model_name"]
    try:
        await engine.execute(f"open_system('{_esc(model)}')")
        return {"success": True, "model_name": model, "message": "Simulink GUI opened"}
    except Exception as e:
        return {"success": False, "error": str(e)}

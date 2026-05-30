import re
import traceback
from typing import Optional


def format_error(error: Exception, task_id: Optional[str] = None,
                 workspace_info: Optional[dict] = None,
                 client_vision: bool = True) -> dict:
    error_str = str(error)
    matlab_stack = re.findall(r"Error in .*? \(line \d+\)", error_str)

    code = "MATLAB_RUNTIME_ERROR"
    if "Out of memory" in error_str:
        code = "RESOURCE_EXHAUSTED"
    elif "Undefined function" in error_str:
        code = "UNDEFINED_FUNCTION"
    elif "Index exceeds" in error_str:
        code = "INDEX_ERROR"

    suggestions = {
        "RESOURCE_EXHAUSTED": "减小数据规模或重启引擎",
        "UNDEFINED_FUNCTION": "检查函数名拼写，或确认所需工具箱已加载",
        "INDEX_ERROR": "检查数组索引是否从 1 开始（MATLAB 使用 1-based 索引）",
    }

    result = {
        "success": False,
        "error_type": type(error).__name__,
        "error": {
            "code": code,
            "message": error_str[:1000],
            "matlab_stack": matlab_stack[:10],
            "suggestion": suggestions.get(code, "请检查输入参数是否正确"),
            "recoverable": code != "RESOURCE_EXHAUSTED",
            "traceback": traceback.format_exc(),
        },
    }
    if task_id:
        result["error"]["task_id"] = task_id
    if workspace_info and not client_vision:
        result["error"]["workspace_context"] = workspace_info
    return result


def format_divergence_error(task_id: str, divergence_time: float,
                             signal_name: str, pre_div_plot: Optional[str] = None,
                             client_vision: bool = True) -> dict:
    result = {
        "success": False,
        "error": {
            "code": "SIMULATION_DIVERGENCE",
            "message": f"Simulation diverged at t={divergence_time:.2f}s. NaN detected in '{signal_name}'.",
            "divergence_point": {"time": divergence_time, "signal": signal_name},
            "suggestion": "减小步长或切换为 stiff solver (如 ode15s)",
            "recoverable": True,
            "task_id": task_id,
        },
    }
    if client_vision and pre_div_plot:
        result["error"]["visualization"] = {
            "pre_divergence_plot": pre_div_plot,
            "description": "发散前的有效数据缩略图",
        }
    return result

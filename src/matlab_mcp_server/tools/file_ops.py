import os
import re
import logging
from .registry import registry

logger = logging.getLogger(__name__)

_VAR_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _esc(s: str) -> str:
    return s.replace("'", "''")


def _validate_var_name(var_name: str) -> str | None:
    if not _VAR_RE.match(var_name):
        return f"Invalid MATLAB variable name: '{var_name}'. Must match [a-zA-Z_][a-zA-Z0-9_]*"
    return None


@registry.register(
    name="load_data",
    description=(
        "加载数据文件到 MATLAB 工作区。文件路径必须在沙盒目录内。"
        "⚠️ .mat 文件风险提示：MATLAB load() 会自动执行 .mat 中嵌入的 "
        "classdef 构造函数和自定义序列化回调，可能执行任意代码。"
        "建议仅加载可信来源的 .mat 文件。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "文件路径（相对于沙盒目录）"},
            "format": {"type": "string", "enum": ["csv", "xlsx", "mat", "json"], "default": "csv"},
            "variable_name": {"type": "string", "description": "加载到的变量名", "default": "loaded_data"},
        },
        "required": ["file_path"],
    },
)
async def handle_load_data(engine, task_executor, params, **kwargs):
    from ..security.path_sanitizer import sanitize_path, PathTraversalError
    from ..security.injection_detector import is_code_safe
    from ..config import Settings as _Settings

    settings = kwargs.get("settings") or _Settings()
    file_path = params["file_path"]
    fmt = params.get("format", "csv")
    var_name = params.get("variable_name", "loaded_data")

    err = _validate_var_name(var_name)
    if err:
        return {"success": False, "error": err}

    try:
        full_path = sanitize_path(file_path, str(settings.sandbox_dir))
    except PathTraversalError as e:
        return {"success": False, "error": str(e)}

    fp = _esc(full_path)

    load_scripts = {
        "csv": f"{var_name} = readtable('{fp}');",
        "xlsx": f"{var_name} = readtable('{fp}');",
        "mat": (
            f"loaded = load('-mat', '{fp}');\n"
            f"{var_name} = loaded;"
        ),
        "json": f"{var_name} = jsondecode(fileread('{fp}'));",
    }

    script = load_scripts.get(fmt, load_scripts["csv"])

    if fmt == "mat":
        safe, risks = is_code_safe(script)
        if not safe:
            return {
                "success": False,
                "error": "MAT file load script blocked by injection guard",
                "risks": [{"keyword": r.keyword, "reason": r.reason} for r in risks if r.severity == "block"],
            }

    try:
        await engine.execute(script)
        info = await engine.get_variable_info(var_name)
        return {"success": True, "variable_name": var_name, "file_path": file_path, "info": info}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="save_data",
    description="保存工作区变量到文件。文件保存在沙盒目录内。",
    input_schema={
        "type": "object",
        "properties": {
            "variable_name": {"type": "string", "description": "要保存的变量名"},
            "file_path": {"type": "string", "description": "保存路径（相对于沙盒目录）"},
            "format": {"type": "string", "enum": ["csv", "mat", "json"], "default": "csv"},
        },
        "required": ["variable_name", "file_path"],
    },
)
async def handle_save_data(engine, task_executor, params, **kwargs):
    from ..security.path_sanitizer import sanitize_path, PathTraversalError
    from ..config import Settings as _Settings

    settings = kwargs.get("settings") or _Settings()
    var_name = params["variable_name"]
    file_path = params["file_path"]
    fmt = params.get("format", "csv")

    err = _validate_var_name(var_name)
    if err:
        return {"success": False, "error": err}

    try:
        full_path = sanitize_path(file_path, str(settings.sandbox_dir))
    except PathTraversalError as e:
        return {"success": False, "error": str(e)}

    fp = _esc(full_path)
    vn = _esc(var_name)

    save_scripts = {
        "csv": f"writetable({var_name}, '{fp}');",
        "mat": f"save('{fp}', '{vn}');",
        "json": f"fid = fopen('{fp}', 'w');\nfwrite(fid, jsonencode({var_name}));\nfclose(fid);",
    }

    script = save_scripts.get(fmt, save_scripts["csv"])
    try:
        await engine.execute(script)
        return {"success": True, "variable_name": var_name, "file_path": file_path, "format": fmt}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="list_sandbox_files",
    description="列出沙盒目录中的所有文件。",
    input_schema={"type": "object", "properties": {}},
)
async def handle_list_sandbox_files(engine, task_executor, params, **kwargs):
    from ..config import Settings as _Settings

    settings = kwargs.get("settings") or _Settings()
    sandbox = str(settings.sandbox_dir)
    files = []
    for root, dirs, filenames in os.walk(sandbox):
        for f in filenames:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, sandbox)
            size = os.path.getsize(full)
            files.append({"path": rel, "size_bytes": size})
    return {"success": True, "files": files, "count": len(files)}


@registry.register(
    name="verify_checksum",
    description="验证文件或数据的校验和完整性。",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "文件路径（相对于沙盒目录）"},
            "expected_hash": {"type": "string", "description": "期望的校验和值"},
            "algorithm": {"type": "string", "enum": ["sha256", "crc32"], "default": "sha256"},
        },
        "required": ["file_path", "expected_hash"],
    },
)
async def handle_verify_checksum(engine, task_executor, params, **kwargs):
    from ..security.path_sanitizer import sanitize_path, PathTraversalError
    from ..output.integrity import verify_checksum
    from ..config import Settings as _Settings

    settings = kwargs.get("settings") or _Settings()
    file_path = params["file_path"]
    expected = params["expected_hash"]
    algo = params.get("algorithm", "sha256")

    try:
        full_path = sanitize_path(file_path, str(settings.sandbox_dir))
    except PathTraversalError as e:
        return {"success": False, "error": str(e)}

    try:
        with open(full_path, "rb") as f:
            data = f.read()
        valid = verify_checksum(data, expected, algo)
        return {"success": True, "valid": valid, "file_path": file_path, "algorithm": algo}
    except FileNotFoundError:
        return {"success": False, "error": f"File not found: {file_path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="delete_data",
    description="删除沙盒目录中的文件。必须提供删除原因以供审计。文件路径必须在沙盒目录内。",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "要删除的文件路径（相对于沙盒目录）"},
            "reason": {"type": "string", "description": "删除原因（用于审计记录）"},
        },
        "required": ["file_path", "reason"],
    },
)
async def handle_delete_data(engine, task_executor, params, audit_logger=None, **kwargs):
    from ..security.path_sanitizer import sanitize_path, PathTraversalError
    from ..config import Settings as _Settings

    settings = kwargs.get("settings") or _Settings()
    file_path = params["file_path"]
    reason = params.get("reason", "unspecified")

    try:
        full_path = sanitize_path(file_path, str(settings.sandbox_dir))
    except PathTraversalError as e:
        return {"success": False, "error": str(e)}

    if not os.path.isfile(full_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    try:
        file_size = os.path.getsize(full_path)
        os.remove(full_path)
        if audit_logger is not None:
            audit_logger.log(
                session_id=kwargs.get("session_id", "unknown"),
                task_id=kwargs.get("task_id"),
                client=kwargs.get("client", "unknown"),
                tool="delete_data",
                params={"file_path": file_path, "reason": reason},
                security_level="L1",
                result="deleted",
            )
        return {
            "success": True,
            "file_path": file_path,
            "size_bytes": file_size,
            "reason": reason,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

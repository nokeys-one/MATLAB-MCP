import json
import os
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_resources(mcp, engine_mgr, task_executor, workspace, settings):
    @mcp.resource(
        uri="matlab://workspace/variables",
        name="workspace_variables",
        description="当前 MATLAB 工作区所有变量列表（JSON），包含名称、维度、类型信息",
        mime_type="application/json",
    )
    async def workspace_variables() -> str:
        try:
            result = await engine_mgr.list_workspace()
            return json.dumps({
                "success": True,
                "variables": result,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, ensure_ascii=False)

    @mcp.resource(
        uri="matlab://workspace/variable/{name}",
        name="workspace_variable_detail",
        description="某个工作区变量的详细信息（元数据、预览值、统计摘要）",
        mime_type="application/json",
    )
    async def workspace_variable_detail(name: str) -> str:
        try:
            info = await engine_mgr.get_variable_info(name, max_rows=100)
            return json.dumps({
                "success": True,
                "variable": info,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({
                "success": False,
                "variable_name": name,
                "error": str(e),
            }, ensure_ascii=False)

    @mcp.resource(
        uri="matlab://sandbox/files",
        name="sandbox_files",
        description="沙盒目录中的文件列表（JSON），包含相对路径和文件大小",
        mime_type="application/json",
    )
    async def sandbox_files() -> str:
        sandbox = str(settings.sandbox_dir)
        files = []
        try:
            for root, dirs, filenames in os.walk(sandbox):
                for f in filenames:
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, sandbox)
                    try:
                        size = os.path.getsize(full)
                    except OSError:
                        size = 0
                    files.append({"path": rel.replace("\\", "/"), "size_bytes": size})
            return json.dumps({
                "success": True,
                "files": files,
                "count": len(files),
                "sandbox_dir": sandbox,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
            }, ensure_ascii=False)

    @mcp.resource(
        uri="matlab://sandbox/file/{path}",
        name="sandbox_file_content",
        description="沙盒内某个文件的内容（文本文件返回原文，二进制返回 base64）",
        mime_type="text/plain",
    )
    async def sandbox_file_content(path: str) -> str:
        from ..security.path_sanitizer import sanitize_path, PathTraversalError

        try:
            full_path = sanitize_path(path, str(settings.sandbox_dir))
        except PathTraversalError as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

        if not os.path.isfile(full_path):
            return json.dumps({
                "success": False,
                "error": f"File not found: {path}",
            }, ensure_ascii=False)

        try:
            size = os.path.getsize(full_path)
            if size > 5 * 1024 * 1024:
                return json.dumps({
                    "success": False,
                    "error": f"File too large ({size} bytes, max 5MB)",
                }, ensure_ascii=False)

            binary_exts = {".mat", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".pdf", ".fig", ".slx", ".mexw64", ".mexa64"}
            ext = os.path.splitext(full_path)[1].lower()

            if ext in binary_exts:
                import base64
                with open(full_path, "rb") as f:
                    data = f.read()
                return json.dumps({
                    "success": True,
                    "path": path,
                    "format": "binary",
                    "size_bytes": len(data),
                    "content_base64": base64.b64encode(data).decode("utf-8"),
                    "mime_hint": ext.lstrip("."),
                })
            else:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                return json.dumps({
                    "success": True,
                    "path": path,
                    "format": "text",
                    "size_bytes": size,
                    "content": content,
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
            }, ensure_ascii=False)

    @mcp.resource(
        uri="matlab://tasks/{task_id}",
        name="task_status",
        description="异步任务状态详情，包含进度、耗时、结果或错误",
        mime_type="application/json",
    )
    async def task_status(task_id: str) -> str:
        status = task_executor.get_status(task_id)
        if status is None:
            return json.dumps({
                "success": False,
                "error": f"Task {task_id} not found",
            }, ensure_ascii=False)

        task = task_executor.get_task(task_id)
        result = {"success": True, **status}
        if task:
            if task.result is not None:
                result["result"] = task.result
            if task.error is not None:
                result["error"] = task.error
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.resource(
        uri="matlab://sandbox/simulink/{name}",
        name="simulink_model_info",
        description="Simulink 模型信息（方块图结构、参数、加载状态）",
        mime_type="application/json",
    )
    async def simulink_model_info(name: str) -> str:
        try:
            model_info_script = f"""
info = struct();
info.name = '{name.replace("'", "''")}';
try
    info.loaded = bdIsLoaded('{name.replace("'", "''")}');
    if info.loaded
        info.block_count = numel(find_system('{name.replace("'", "''")}', 'Type', 'block'));
        info.line_count = numel(find_system('{name.replace("'", "''")}', 'Type', 'line'));
        info.solver = get_param('{name.replace("'", "''")}', 'Solver');
        info.stop_time = get_param('{name.replace("'", "''")}', 'StopTime');
        info.sample_time = get_param('{name.replace("'", "''")}', 'FixedStep');
        blocks = find_system('{name.replace("'", "''")}', 'Type', 'block');
        info.block_list = {{}};
        for i = 1:min(numel(blocks), 50)
            b = blocks{{i}};
            binfo = struct();
            binfo.name = b;
            binfo.block_type = get_param(b, 'BlockType');
            info.block_list{{end+1}} = binfo;
        end
    end
catch e
    info.error = e.message;
end
result = info;
"""
            raw = await engine_mgr.execute(model_info_script.strip())
            return json.dumps({
                "success": True,
                "model_name": name,
                "info_raw": raw,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({
                "success": False,
                "model_name": name,
                "error": str(e),
            }, ensure_ascii=False)

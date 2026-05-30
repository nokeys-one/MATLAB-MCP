import logging
from .registry import registry

logger = logging.getLogger(__name__)


def _esc(s: str) -> str:
    return s.replace("'", "''")


PLOT_DESCRIPTION = (
    "创建标准 MATLAB 图表。"
    "⚠️ 重要：若生成了图表且你不具备视觉能力，"
    "绝对不要尝试直接解析图片内容。"
    "请改用 verify_plot_data 工具获取图表的文本描述，"
    "或调用 execute_matlab_script 编写 imread 代码，利用 MATLAB 后台提取特征返回。"
)


@registry.register(
    name="create_plot",
    description=PLOT_DESCRIPTION,
    input_schema={
        "type": "object",
        "properties": {
            "plot_type": {"type": "string", "enum": ["line", "bar", "scatter", "histogram", "stairs", "stem"]},
            "x_variable_name": {"type": "string"},
            "y_variable_name": {"type": "string"},
            "title": {"type": "string", "default": ""},
            "xlabel": {"type": "string", "default": ""},
            "ylabel": {"type": "string", "default": ""},
            "style": {"type": "object", "default": {}},
        },
        "required": ["plot_type", "x_variable_name", "y_variable_name"],
    },
)
async def handle_create_plot(engine, task_executor, params, client_adapter=None, **kwargs):
    plot_type = params["plot_type"]
    x_var = params["x_variable_name"]
    y_var = params["y_variable_name"]
    title = params.get("title", "")
    xlabel = params.get("xlabel", "")
    ylabel = params.get("ylabel", "")

    plot_funcs = {"line": "plot", "bar": "bar", "scatter": "scatter",
                  "histogram": "histogram", "stairs": "stairs", "stem": "stem"}
    func = plot_funcs.get(plot_type, "plot")

    script = (
        f"figure('Visible', 'off');\n"
        f"{func}({x_var}, {y_var});\n"
        f"title('{_esc(title)}');\n"
        f"xlabel('{_esc(xlabel)}');\n"
        f"ylabel('{_esc(ylabel)}');\n"
        f"grid on;\n"
    )
    try:
        await engine.execute(script)
        fig_path = str(engine.sandbox_dir / "figures" / "latest_plot.png")
        await engine.execute(f"saveas(gcf, '{_esc(fig_path)}')")
        result = {"success": True, "figure_path": fig_path}
        if client_adapter:
            result = client_adapter.adapt_image_response(result, fig_path)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="create_3d_plot",
    description=PLOT_DESCRIPTION,
    input_schema={
        "type": "object",
        "properties": {
            "plot_type": {"type": "string", "enum": ["surf", "mesh", "contour", "scatter3"]},
            "x_variable_name": {"type": "string"},
            "y_variable_name": {"type": "string"},
            "z_variable_name": {"type": "string"},
        },
        "required": ["plot_type", "x_variable_name", "y_variable_name", "z_variable_name"],
    },
)
async def handle_create_3d_plot(engine, task_executor, params, client_adapter=None, **kwargs):
    plot_type = params["plot_type"]
    x_var = params["x_variable_name"]
    y_var = params["y_variable_name"]
    z_var = params["z_variable_name"]
    func = {"surf": "surf", "mesh": "mesh", "contour": "contour", "scatter3": "scatter3"}.get(plot_type, "surf")
    script = f"figure('Visible','off');\n{func}({x_var},{y_var},{z_var});\ngrid on;"
    try:
        await engine.execute(script)
        fig_path = str(engine.sandbox_dir / "figures" / "latest_3d_plot.png")
        await engine.execute(f"saveas(gcf, '{_esc(fig_path)}')")
        result = {"success": True, "figure_path": fig_path}
        if client_adapter:
            result = client_adapter.adapt_image_response(result, fig_path)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="export_figure",
    description="导出当前 MATLAB 图形为文件。返回路径或 Base64（取决于客户端视觉能力）。",
    input_schema={
        "type": "object",
        "properties": {
            "filename": {"type": "string"},
            "format": {"type": "string", "enum": ["png", "svg", "pdf"], "default": "png"},
            "dpi": {"type": "integer", "default": 300},
        },
        "required": ["filename"],
    },
)
async def handle_export_figure(engine, task_executor, params, client_adapter=None, **kwargs):
    filename = params["filename"]
    try:
        fig_path = str(engine.sandbox_dir / "figures" / filename)
        await engine.execute(f"saveas(gcf, '{_esc(fig_path)}')")
        result = {"success": True, "figure_path": fig_path}
        if client_adapter:
            result = client_adapter.adapt_image_response(result, fig_path)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="subplot_layout",
    description=PLOT_DESCRIPTION,
    input_schema={
        "type": "object",
        "properties": {
            "rows": {"type": "integer"},
            "cols": {"type": "integer"},
            "plots": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["rows", "cols", "plots"],
    },
)
async def handle_subplot_layout(engine, task_executor, params, client_adapter=None, **kwargs):
    rows = params["rows"]
    cols = params["cols"]
    plots = params["plots"]
    script = "figure('Visible','off');\n"
    for i, p in enumerate(plots):
        script += f"subplot({rows},{cols},{i+1});\n"
        func = p.get("plot_type", "plot")
        x_var = p.get("x_variable_name", "[]")
        y_var = p.get("y_variable_name", "[]")
        title = p.get("title", "")
        script += f"{func}({x_var},{y_var});\ntitle('{_esc(title)}');\ngrid on;\n"
    try:
        await engine.execute(script)
        fig_path = str(engine.sandbox_dir / "figures" / "subplot.png")
        await engine.execute(f"saveas(gcf, '{_esc(fig_path)}')")
        result = {"success": True, "figure_path": fig_path}
        if client_adapter:
            result = client_adapter.adapt_image_response(result, fig_path)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="verify_plot_data",
    description="纯文本 AI 的'代码眼'：读取图表文件，提取坐标轴、曲线、图例等关键信息为 JSON 文本。",
    input_schema={
        "type": "object",
        "properties": {"figure_path": {"type": "string"}},
        "required": ["figure_path"],
    },
)
async def handle_verify_plot_data(engine, task_executor, params, client_adapter=None, **kwargs):
    fig_path = params["figure_path"]
    script = f"""
fig = openfig('{_esc(fig_path)}', 'invisible');
ax = findobj(fig, 'Type', 'axes');
result = struct('axes_info', {{}}, 'curves', {{}});
for i = 1:length(ax)
    info = struct();
    info.xlabel = get(ax(i), 'XLabel').String;
    info.ylabel = get(ax(i), 'YLabel').String;
    info.title = get(ax(i), 'Title').String;
    info.xlim = get(ax(i), 'XLim');
    info.ylim = get(ax(i), 'YLim');
    result.axes_info{{end+1}} = info;
    lines = findobj(ax(i), 'Type', 'line');
    for j = 1:length(lines)
        curve = struct();
        curve.name = get(lines(j), 'DisplayName');
        xdata = get(lines(j), 'XData');
        ydata = get(lines(j), 'YData');
        curve.x_range = [min(xdata), max(xdata)];
        curve.y_range = [min(ydata), max(ydata)];
        curve.data_points = length(xdata);
        curve.mean_val = mean(ydata);
        curve.std_val = std(ydata);
        result.curves{{end+1}} = curve;
    end
end
close(fig);
"""
    try:
        result = await engine.execute(script)
        return {"success": True, "figure_path": fig_path, "chart_info": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

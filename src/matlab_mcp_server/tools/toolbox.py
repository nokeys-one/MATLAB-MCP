import logging
from .registry import registry

logger = logging.getLogger(__name__)


def _esc(s: str) -> str:
    return s.replace("'", "''")


@registry.register(
    name="signal_processing",
    description="信号处理工具箱。支持滤波器设计、频谱分析、FFT、功率谱估计等。",
    input_schema={
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["fft", "ifft", "lowpass", "highpass", "bandpass", "psd", "spectrogram", "filter_design"],
            },
            "input_variable": {"type": "string", "description": "输入信号的变量名"},
            "output_variable": {"type": "string", "description": "输出结果保存到的变量名", "default": "signal_result"},
            "params": {"type": "object", "description": "操作参数（如截止频率、采样率等）", "default": {}},
        },
        "required": ["operation", "input_variable"],
    },
)
async def handle_signal_processing(engine, task_executor, params, **kwargs):
    op = params["operation"]
    input_var = params["input_variable"]
    output_var = params.get("output_variable", "signal_result")
    p = params.get("params", {})
    fs = p.get("fs", 1000)
    cutoff = p.get("cutoff", 100)

    scripts = {
        "fft": f"{output_var} = fft({input_var});",
        "ifft": f"{output_var} = ifft({input_var});",
        "lowpass": (
            f"[b, a] = butter(4, {cutoff}/({fs}/2), 'low');\n"
            f"{output_var} = filter(b, a, {input_var});"
        ),
        "highpass": (
            f"[b, a] = butter(4, {cutoff}/({fs}/2), 'high');\n"
            f"{output_var} = filter(b, a, {input_var});"
        ),
        "bandpass": (
            f"low = {p.get('low_cutoff', 50)} / ({fs}/2);\n"
            f"high = {p.get('high_cutoff', 200)} / ({fs}/2);\n"
            f"[b, a] = butter(4, [low, high], 'bandpass');\n"
            f"{output_var} = filter(b, a, {input_var});"
        ),
        "psd": (
            f"nfft = {p.get('nfft', 1024)};\n"
            f"[{output_var}, f_vec] = pwelch({input_var}, hanning(nfft), nfft/2, nfft, {fs});"
        ),
        "spectrogram": (
            f"nfft = {p.get('nfft', 256)};\n"
            f"[S, F, T] = spectrogram({input_var}, hanning(nfft), nfft/4, nfft, {fs});\n"
            f"{output_var} = struct('S', S, 'F', F, 'T', T);"
        ),
        "filter_design": (
            f"order = {p.get('order', 4)};\n"
            f"fc = {cutoff} / ({fs}/2);\n"
            f"[b, a] = butter(order, fc, 'low');\n"
            f"{output_var} = struct('b', b, 'a', a);"
        ),
    }

    script = scripts.get(op)
    if not script:
        return {"success": False, "error": f"Unknown operation: {op}. Supported: {list(scripts.keys())}"}
    try:
        result = await engine.execute(script.strip())
        return {"success": True, "operation": op, "output_variable": output_var, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="control_system",
    description="控制系统工具箱。支持传递函数、状态空间、Bode 图、根轨迹、阶跃响应等。",
    input_schema={
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["tf", "ss", "bode", "rlocus", "step", "impulse", "nyquist", "pid_tune"],
            },
            "num": {"type": "array", "items": {"type": "number"}, "description": "传递函数分子系数"},
            "den": {"type": "array", "items": {"type": "number"}, "description": "传递函数分母系数"},
            "output_variable": {"type": "string", "default": "sys"},
            "params": {"type": "object", "default": {}},
        },
        "required": ["operation"],
    },
)
async def handle_control_system(engine, task_executor, params, **kwargs):
    op = params["operation"]
    output_var = params.get("output_variable", "sys")
    p = params.get("params", {})
    num = params.get("num", [])
    den = params.get("den", [])

    num_str = ", ".join(str(n) for n in num)
    den_str = ", ".join(str(d) for d in den)

    if op in ("tf",) and (not num or not den):
        return {"success": False, "error": f"Operation '{op}' requires 'num' and 'den' arrays"}

    scripts = {
        "tf": f"{output_var} = tf([{num_str}], [{den_str}]);",
        "ss": (
            f"A = {p.get('A', '[]')}; B = {p.get('B', '[]')}; "
            f"C = {p.get('C', '[]')}; D = {p.get('D', '0')};\n"
            f"{output_var} = ss(A, B, C, D);"
        ),
        "bode": f"bode({output_var});\ngrid on;",
        "rlocus": f"rlocus({output_var});",
        "step": f"step({output_var});\ngrid on;",
        "impulse": f"impulse({output_var});\ngrid on;",
        "nyquist": f"nyquist({output_var});",
        "pid_tune": (
            f"Kp = {p.get('Kp', 1)}; Ki = {p.get('Ki', 0)}; Kd = {p.get('Kd', 0)};\n"
            f"{output_var} = pid(Kp, Ki, Kd);"
        ),
    }

    script = scripts.get(op)
    if not script:
        return {"success": False, "error": f"Unknown operation: {op}. Supported: {list(scripts.keys())}"}

    try:
        result = await engine.execute(script.strip())
        return {"success": True, "operation": op, "output_variable": output_var, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="optimization",
    description="优化工具箱。支持线性规划、非线性优化、最小二乘拟合等。",
    input_schema={
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["fmincon", "fminsearch", "linprog", "lsqcurvefit", "fminunc"],
            },
            "objective_variable": {"type": "string", "description": "目标函数的变量名（或函数句柄表达式）"},
            "x0_variable": {"type": "string", "description": "初始猜测的变量名"},
            "output_variable": {"type": "string", "default": "opt_result"},
            "params": {"type": "object", "default": {}},
        },
        "required": ["operation"],
    },
)
async def handle_optimization(engine, task_executor, params, **kwargs):
    op = params["operation"]
    obj = params.get("objective_variable", "@(x) x.^2")
    x0 = params.get("x0_variable", "[0]")
    output_var = params.get("output_variable", "opt_result")
    p = params.get("params", {})

    scripts = {
        "fminsearch": f"[{output_var}, fval] = fminsearch({obj}, {x0});",
        "fminunc": (
            f"options = optimoptions('fminunc', 'Display', 'off');\n"
            f"[{output_var}, fval] = fminunc({obj}, {x0}, options);"
        ),
        "fmincon": (
            f"A_ineq = {p.get('A', '[]')}; b_ineq = {p.get('b', '[]')};\n"
            f"Aeq = {p.get('Aeq', '[]')}; beq = {p.get('beq', '[]')};\n"
            f"lb = {p.get('lb', '[]')}; ub = {p.get('ub', '[]')};\n"
            f"options = optimoptions('fmincon', 'Display', 'off');\n"
            f"[{output_var}, fval] = fmincon({obj}, {x0}, A_ineq, b_ineq, Aeq, beq, lb, ub, [], options);"
        ),
        "linprog": (
            f"c = {p.get('c', '[]')};\n"
            f"A_ineq = {p.get('A', '[]')}; b_ineq = {p.get('b', '[]')};\n"
            f"Aeq = {p.get('Aeq', '[]')}; beq = {p.get('beq', '[]')};\n"
            f"lb = {p.get('lb', '[]')}; ub = {p.get('ub', '[]')};\n"
            f"[{output_var}, fval] = linprog(c, A_ineq, b_ineq, Aeq, beq, lb, ub);"
        ),
        "lsqcurvefit": (
            f"fun = {obj};\n"
            f"xdata = {p.get('xdata', '[]')}; ydata = {p.get('ydata', '[]')};\n"
            f"lb = {p.get('lb', '[]')}; ub = {p.get('ub', '[]')};\n"
            f"options = optimoptions('lsqcurvefit', 'Display', 'off');\n"
            f"[{output_var}, resnorm] = lsqcurvefit(fun, {x0}, xdata, ydata, lb, ub, options);"
        ),
    }

    script = scripts.get(op)
    if not script:
        return {"success": False, "error": f"Unknown operation: {op}. Supported: {list(scripts.keys())}"}
    try:
        result = await engine.execute(script.strip())
        return {"success": True, "operation": op, "output_variable": output_var, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="machine_learning",
    description="机器学习工具箱。支持分类、回归、聚类、降维等。",
    input_schema={
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["fitcsvm", "fitctree", "fitcensemble", "fitlm", "kmeans", "pca", "tsne"],
            },
            "data_variable": {"type": "string", "description": "训练数据变量名"},
            "label_variable": {"type": "string", "description": "标签变量名（分类/回归需要）", "default": ""},
            "output_variable": {"type": "string", "default": "ml_model"},
            "params": {"type": "object", "default": {}},
        },
        "required": ["operation", "data_variable"],
    },
)
async def handle_machine_learning(engine, task_executor, params, **kwargs):
    op = params["operation"]
    data_var = params["data_variable"]
    label_var = params.get("label_variable", "")
    output_var = params.get("output_variable", "ml_model")
    p = params.get("params", {})

    if op in ("fitcsvm", "fitctree", "fitcensemble") and not label_var:
        return {"success": False, "error": f"Operation '{op}' requires 'label_variable'"}

    scripts = {
        "fitcsvm": f"{output_var} = fitcsvm({data_var}, {label_var});",
        "fitctree": f"{output_var} = fitctree({data_var}, {label_var});",
        "fitcensemble": f"{output_var} = fitcensemble({data_var}, {label_var}, 'Method', '{_esc(p.get('method', 'AdaBoostM1'))}');",
        "fitlm": f"{output_var} = fitlm({data_var}, {label_var});" if label_var else f"{output_var} = fitlm({data_var});",
        "kmeans": (
            f"k = {p.get('k', 3)};\n"
            f"[{output_var}_idx, {output_var}_centroids] = kmeans({data_var}, k);"
        ),
        "pca": f"[{output_var}_coeff, {output_var}_score, {output_var}_latent] = pca({data_var});",
        "tsne": (
            f"{output_var} = tsne({data_var}, 'NumDimensions', {p.get('num_dims', 2)}, "
            f"'Perplexity', {p.get('perplexity', 30)});"
        ),
    }

    script = scripts.get(op)
    if not script:
        return {"success": False, "error": f"Unknown operation: {op}. Supported: {list(scripts.keys())}"}
    try:
        result = await engine.execute(script.strip())
        return {"success": True, "operation": op, "output_variable": output_var, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="data_analysis",
    description="数据分析工具箱。支持统计分析、相关性、回归、假设检验、插值等。",
    input_schema={
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["describe", "corrcoef", "regress", "ttest", "anova", "interp1", "smooth", "histogram_stats"],
            },
            "data_variable": {"type": "string", "description": "输入数据变量名"},
            "output_variable": {"type": "string", "default": "analysis_result"},
            "params": {"type": "object", "default": {}},
        },
        "required": ["operation", "data_variable"],
    },
)
async def handle_data_analysis(engine, task_executor, params, **kwargs):
    op = params["operation"]
    data_var = params["data_variable"]
    output_var = params.get("output_variable", "analysis_result")
    p = params.get("params", {})

    scripts = {
        "describe": (
            f"{output_var} = struct();\n"
            f"{output_var}.mean = mean({data_var});\n"
            f"{output_var}.median = median({data_var});\n"
            f"{output_var}.std = std({data_var});\n"
            f"{output_var}.min = min({data_var});\n"
            f"{output_var}.max = max({data_var});\n"
            f"{output_var}.size = size({data_var});"
        ),
        "corrcoef": f"{output_var} = corrcoef({data_var});",
        "regress": (
            f"y = {data_var};\n"
            f"X = {p.get('X', 'ones(size(y))')};\n"
            f"[b, bint, r, rint, stats] = regress(y, X);\n"
            f"{output_var} = struct('coefficients', b, 'ci', bint, 'residuals', r, 'stats', stats);"
        ),
        "ttest": (
            f"[h, p_val, ci, stats] = ttest({data_var});\n"
            f"{output_var} = struct('reject', h, 'p_value', p_val, 'ci', ci, 'tstat', stats.tstat);"
        ),
        "anova": (
            f"groups = {p.get('groups', '[]')};\n"
            f"[p_val, tbl, stats] = anova1({data_var}, groups);\n"
            f"{output_var} = struct('p_value', p_val, 'table', {{tbl}});"
        ),
        "interp1": (
            f"x = {p.get('x', '[]')};\n"
            f"xq = {p.get('xq', '[]')};\n"
            f"method = '{_esc(p.get('method', 'linear'))}';\n"
            f"{output_var} = interp1(x, {data_var}, xq, method);"
        ),
        "smooth": (
            f"span = {p.get('span', 5)};\n"
            f"{output_var} = smooth({data_var}, span);"
        ),
        "histogram_stats": (
            f"[N, edges] = histcounts({data_var});\n"
            f"{output_var} = struct('counts', N, 'edges', edges, 'mean', mean({data_var}), 'std', std({data_var}));"
        ),
    }

    script = scripts.get(op)
    if not script:
        return {"success": False, "error": f"Unknown operation: {op}. Supported: {list(scripts.keys())}"}
    try:
        result = await engine.execute(script.strip())
        return {"success": True, "operation": op, "output_variable": output_var, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

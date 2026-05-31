# MATLAB MCP Server 使用文档

## 目录

- [项目简介](#项目简介)
- [环境要求](#环境要求)
- [安装与启动](#安装与启动)
- [传输模式](#传输模式)
- [配置参数](#配置参数)
- [安全机制](#安全机制)
- [工具列表（34 个）](#工具列表)
- [资源列表（6 个）](#资源列表)
- [提示词列表（5 个）](#提示词列表)
- [典型使用场景](#典型使用场景)
- [常见问题](#常见问题)

---

## 项目简介

MATLAB MCP Server 是一个基于 MCP（Model Context Protocol）协议的服务器，允许 AI 助手（如 Trae、Claude、Cursor 等）直接调用 MATLAB 进行仿真、建模、画图和数据分析。

它将 MATLAB 的能力封装为标准 MCP 工具（Tools）、资源（Resources）和提示词（Prompts），AI 助手通过 MCP 协议即可无缝使用 MATLAB。

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | >= 3.11 |
| MATLAB | R2025a 或更高版本 |
| MATLAB Engine | matlabengine >= 25.1.0（Python 包） |
| 操作系统 | Windows / macOS / Linux |

---

## 安装与启动

### 1. 安装

```bash
# 克隆项目
git clone <repository_url>
cd MatlabMcp

# 安装基础依赖
pip install -e .

# 安装 MATLAB Engine（需要先安装 MATLAB R2025a）
pip install matlabengine>=25.1.0

# 或一步到位安装所有可选依赖
pip install -e ".[matlab]"
```

### 2. 配置

复制环境变量模板并按需修改：

```bash
cp .env.example .env
```

核心配置项（`.env` 文件）：

```env
# MATLAB 引擎
MATLAB_MCP_MATLAB_TIMEOUT=3600            # 执行超时（秒）
MATLAB_MCP_MATLAB_MAX_MEMORY_MB=8192      # 最大内存（MB）

# 沙盒目录（所有文件操作限制在此目录内）
MATLAB_MCP_SANDBOX_DIR=C:\Users\user\matlab_mcp_sandbox

# 传输模式
MATLAB_MCP_TRANSPORT=stdio                # stdio 或 http

# HTTP 模式专用
MATLAB_MCP_HTTP_PORT=3000
MATLAB_MCP_HTTP_BIND=127.0.0.1
MATLAB_MCP_HTTP_TOKEN=                    # 鉴权令牌（留空则无鉴权）

# AI 客户端能力
MATLAB_MCP_CLIENT_VISION=true             # 客户端是否支持图片
MATLAB_MCP_CONTEXT_LIMIT=200000           # 上下文长度限制

# 并发任务
MATLAB_MCP_MAX_CONCURRENT_TASKS=1         # 最大并发 MATLAB 任务数

# 安全
MATLAB_MCP_ENABLE_REGEX_INJECTION_ANALYSIS=true   # 代码注入检测
MATLAB_MCP_ENABLE_SHADOW_FUNCTIONS=true           # 沙盒影子函数
```

### 3. 启动

```bash
# stdio 模式（默认，供 AI 客户端直接调用）
matlab-mcp

# 或通过模块启动
python -m matlab_mcp_server

# 指定传输模式
matlab-mcp --transport stdio
matlab-mcp --transport http --port 3000 --bind 127.0.0.1

# 带鉴权令牌
matlab-mcp --transport http --port 3000 --token my-secret-token
```

### 4. 在 AI 客户端中配置

**Trae / Cursor / VS Code（MCP 插件）**

在 MCP 配置文件（如 `mcp.json` 或 `settings.json`）中添加：

```json
{
  "mcpServers": {
    "matlab": {
      "command": "matlab-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "MATLAB_MCP_SANDBOX_DIR": "C:\\Users\\user\\matlab_mcp_sandbox"
      }
    }
  }
}
```

**HTTP 模式（远程/跨进程）**

```json
{
  "mcpServers": {
    "matlab": {
      "url": "http://127.0.0.1:3000/mcp",
      "headers": {
        "Authorization": "Bearer my-secret-token"
      }
    }
  }
}
```

---

## 传输模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `stdio` | 通过标准输入/输出通信 | 本地 AI 客户端直接启动进程（默认，推荐） |
| `http` | Streamable HTTP 协议 | 远程访问、多客户端共享、Web 集成 |

---

## 配置参数

所有参数均支持环境变量（前缀 `MATLAB_MCP_`）、`.env` 文件和命令行参数三种方式配置。

### 引擎配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `matlab_timeout` | 3600 | MATLAB 执行超时（秒） |
| `matlab_max_memory_mb` | 8192 | MATLAB 最大内存（MB） |
| `matlab_cpu_threshold` | 0.95 | CPU 使用率告警阈值 |
| `matlab_heartbeat_interval` | 10 | 资源监控心跳间隔（秒） |

### 沙盒配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `sandbox_dir` | ~/matlab_mcp_sandbox | 沙盒目录路径 |
| `auto_cleanup` | true | 自动清理过期文件 |

### 数据降采样阈值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `full_data_threshold` | 100 | 数据量 <= 此值时返回完整数据 |
| `downsample_threshold` | 1000 | 数据量 <= 此值时降采样返回 |
| `metadata_only_threshold` | 1000000 | 超过此值仅返回元数据 |

### 仿真稳态检测

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `steady_state_enabled` | true | 启用稳态检测 |
| `steady_state_window_size` | 10 | 检测窗口大小 |
| `steady_state_mean_tolerance` | 1e-3 | 均值容差 |
| `steady_state_std_tolerance` | 1e-3 | 标准差容差 |

### 数据完整性校验

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `integrity_check_enabled` | true | 启用数据完整性校验 |
| `integrity_algorithm` | sha256 | 校验算法（sha256 / crc32） |
| `integrity_auto_retry` | 2 | 校验失败自动重试次数 |

### Simulink 配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `simulink_cleanup_callbacks` | true | 加载模型时自动清理回调函数 |
| `simulink_max_sim_time` | 86400.0 | 最大仿真时长（秒） |

---

## 安全机制

MATLAB MCP Server 内置多层安全防护：

### 1. 路径沙盒

所有文件操作严格限制在 `sandbox_dir` 目录内，路径穿越攻击（如 `../`）会被自动拦截。

### 2. 代码注入检测

启用 `enable_regex_injection_analysis` 后，所有传入 MATLAB 的代码会经过正则分析，检测常见的注入模式（如 `eval`、`system`、`feval` 等）。

### 3. 影子函数（Shadow Functions）

沙盒目录下预置了 20 个 MATLAB 影子函数，覆盖危险内置函数（如 `eval`、`system`、`delete`、`dos` 等），在沙盒环境中自动替换为安全版本。

影子函数列表：

| 函数 | 说明 |
|------|------|
| `eval.m` / `evalc.m` / `evalin.m` | 拦截动态代码执行 |
| `system.m` / `dos.m` | 拦截系统命令调用 |
| `delete.m` / `rmdir.m` | 限制文件删除操作 |
| `feval.m` / `str2func.m` | 限制函数动态调用 |
| `webread.m` / `webwrite.m` / `urlread.m` / `urlwrite.m` | 拦截网络请求 |
| `input.m` / `keyboard.m` | 阻止交互式输入 |
| `javaaddpath.m` / `addpath.m` / `rmpath.m` | 限制路径修改 |
| `builtin.m` | 拦截内置函数直接调用 |

### 4. 审批队列

高风险操作（如 `evaluate_expression`）需要用户手动批准后才能执行。通过 `approve_operation` / `reject_operation` 工具管理。

### 5. 审计日志

所有安全事件记录到 `audit_log_path` 指定的日志文件中。

---

## 工具列表

共 **34 个工具**，分为 7 个类别。

### 计算工具（Computation）

| 工具名 | 说明 | 关键参数 |
|--------|------|----------|
| `run_matlab_function` | 调用预定义的 MATLAB 安全函数 | `function`, `args` |
| `execute_matlab_script` | 执行沙盒内的 MATLAB 脚本文件 | `script_path`, `args` |
| `evaluate_expression` | 计算 MATLAB 表达式（⚠️ 需用户审批） | `expression` |
| `get_workspace_variable` | 获取工作区变量的值和元数据 | `variable_name`, `max_rows` |
| `list_workspace_variables` | 列出工作区所有变量 | — |

### 可视化工具（Visualization）

| 工具名 | 说明 | 关键参数 |
|--------|------|----------|
| `create_plot` | 创建图表（支持 line/bar/scatter/3D 等） | `plot_type`, `data`, `title`, `style` |
| `export_figure` | 导出图形为文件（PNG/SVG/PDF）或 Base64 | `format`, `dpi`, `filename` |
| `subplot_layout` | 多子图布局 | `layout`, `plots` |
| `verify_plot_data` | 以纯文本方式提取图表信息（AI 的"代码眼"） | `filepath` |

### Simulink 仿真工具

| 工具名 | 说明 | 关键参数 |
|--------|------|----------|
| `load_simulink_model` | 加载 .slx 模型（自动清理回调） | `model_path` |
| `modify_block_parameters` | 修改模块参数 | `model_name`, `block_path`, `params` |
| `list_block_parameters` | 列出模块可调参数 | `model_name`, `block_path` |
| `create_simple_model` | 创建线性链式模型（自动连接） | `model_name`, `blocks` |
| `configure_simulation` | 配置仿真参数 | `model_name`, `solver`, `stop_time`, `step_size` |
| `run_simulation` | 运行仿真（异步，返回 Task ID） | `model_name`, `mode` |
| `get_simulation_results` | 获取仿真结果数据 | `task_id`, `signals` |
| `open_simulink_gui` | 打开 Simulink GUI | `model_name` |

### 文件操作工具（File Ops）

| 工具名 | 说明 | 关键参数 |
|--------|------|----------|
| `load_data` | 加载数据文件（CSV/XLSX/MAT/JSON） | `filename`, `variable_name` |
| `save_data` | 保存工作区变量到文件 | `variable_name`, `filename`, `format` |
| `list_sandbox_files` | 列出沙盒目录中的文件 | — |
| `verify_checksum` | 验证文件校验和 | `filepath`, `expected_hash`, `algorithm` |
| `delete_data` | 删除沙盒文件（需提供原因审计） | `filepath`, `reason` |

### 工具箱工具（Toolbox）

| 工具名 | 说明 | 关键参数 |
|--------|------|----------|
| `signal_processing` | 信号处理（FFT、滤波器设计、频谱分析等） | `operation`, `input_variable`, `params` |
| `control_system` | 控制系统（传递函数、Bode 图、根轨迹等） | `operation`, `params` |
| `optimization` | 优化（线性规划、非线性优化等） | `operation`, `params` |
| `machine_learning` | 机器学习（分类、回归、聚类、降维等） | `operation`, `params` |
| `data_analysis` | 数据分析（统计、相关性、回归、假设检验等） | `operation`, `input_variable`, `params` |

### 任务管理工具（Task Manager）

| 工具名 | 说明 | 关键参数 |
|--------|------|----------|
| `check_task_status` | 查询异步任务状态和进度 | `task_id` |
| `cancel_task` | 取消正在运行的异步任务 | `task_id` |
| `approve_operation` | 批准等待审批的 L2 操作 | `operation_id` |
| `reject_operation` | 拒绝等待审批的 L2 操作 | `operation_id` |
| `list_pending_approvals` | 列出所有待审批操作 | — |
| `reset_workspace` | 重置 MATLAB 工作区 | — |

---

## 资源列表

共 **6 个资源**，通过 URI 访问。

| 资源名 | URI | 说明 |
|--------|-----|------|
| `workspace_variables` | `matlab://workspace/variables` | 工作区所有变量列表（JSON） |
| `workspace_variable_detail` | `matlab://workspace/variable/{name}` | 某个变量的详细信息 |
| `sandbox_files` | `matlab://sandbox/files` | 沙盒目录文件列表 |
| `sandbox_file_content` | `matlab://sandbox/file/{path}` | 沙盒内文件内容（文本或 Base64） |
| `task_status` | `matlab://tasks/{task_id}` | 异步任务状态详情 |
| `simulink_model_info` | `matlab://sandbox/simulink/{name}` | Simulink 模型结构信息 |

---

## 提示词列表

共 **5 个提示词**，为 AI 助手提供参考指南。

| 提示词名 | 说明 |
|----------|------|
| `simulation_guide` | Simulink 仿真指南（含三种模式选择流程） |
| `plot_styling` | MATLAB 画图样式配置指南 |
| `data_analysis_workflow` | 数据分析标准工作流 |
| `signal_processing_guide` | 信号处理工具使用指南 |
| `troubleshooting` | 常见错误与解决方案 |

---

## 典型使用场景

### 场景 1：MATLAB 数值计算

```
用户：帮我计算矩阵 A = [1 2; 3 4] 的特征值

AI 调用：
1. evaluate_expression("A = [1 2; 3 4]; eig(A)")  → 需用户审批
2. 或 run_matlab_function("eig", args=[[1,2,3,4]])  → 白名单函数，自动执行
```

### 场景 2：数据加载与分析

```
用户：分析 data.csv 中数据的统计特征

AI 调用：
1. load_data(filename="data.csv")           → 加载到工作区
2. data_analysis(operation="describe", ...)  → 描述性统计
3. data_analysis(operation="corrcoef", ...)  → 相关系数
4. create_plot(plot_type="histogram", ...)   → 可视化分布
```

### 场景 3：Simulink 仿真

```
用户：帮我仿真一个 PID 控制系统

AI 调用：
1. load_simulink_model(model_path="pid_template.slx")
2. modify_block_parameters(model_name="pid", block_path="PID", params={...})
3. configure_simulation(model_name="pid", solver="ode45", stop_time=10)
4. run_simulation(model_name="pid", mode="code")  → 返回 task_id
5. check_task_status(task_id="task_xxx")           → 轮询进度
6. get_simulation_results(task_id="task_xxx")      → 获取结果
7. create_plot(plot_type="line", data={...})       → 可视化
```

### 场景 4：信号处理

```
用户：对信号做 FFT 频谱分析

AI 调用：
1. evaluate_expression("t = 0:0.001:1; x = sin(2*pi*50*t) + sin(2*pi*120*t)")
2. signal_processing(operation="fft", input_variable="x", params={"fs": 1000})
3. create_plot(plot_type="line", data={...})
```

### 场景 5：控制系统设计

```
用户：画一个传递函数 G(s) = 1/(s^2 + 2s + 1) 的 Bode 图

AI 调用：
1. control_system(operation="tf", params={"num": [1], "den": [1, 2, 1]})
2. control_system(operation="bode", params={})
3. export_figure(format="png")
```

---

## 常见问题

### Q: MATLAB 引擎启动失败？

确认已安装 MATLAB R2025a 并执行 `pip install matlabengine>=25.1.0`。Windows 上需以管理员权限运行一次 MATLAB 完成注册。

### Q: "Engine is busy" 错误？

`max_concurrent_tasks` 默认为 1，同一时间只允许一个写操作。用 `check_task_status` 等待当前任务完成，或调大并发数。

### Q: 路径被拒绝？

所有文件操作限制在 `sandbox_dir` 内。使用相对路径（如 `"data/test.csv"`），不要使用 `../` 或绝对路径。

### Q: `evaluate_expression` 无法自动执行？

这是安全设计。`evaluate_expression` 属于 L2 级操作，需要用户手动审批。使用 `run_matlab_function`（白名单函数）可自动执行。

### Q: 大数据返回不完整？

当数据量超过 `downsample_threshold`（默认 1000 行）时会自动降采样。超过 `metadata_only_threshold`（默认 1000000）仅返回元数据。可通过 `get_workspace_variable` 的 `max_rows` 参数控制。

### Q: 如何查看沙盒中的文件？

- 工具：`list_sandbox_files`
- 资源：`matlab://sandbox/files`（返回完整文件列表 JSON）

### Q: 如何重置 MATLAB 工作区？

调用 `reset_workspace` 工具，会清除所有变量、关闭图形窗口、重置工作目录到沙盒。

---

## 项目结构

```
MatlabMcp/
├── src/matlab_mcp_server/
│   ├── __init__.py
│   ├── __main__.py          # CLI 入口
│   ├── config.py             # Pydantic Settings 配置
│   ├── server.py             # FastMCP 服务器组装
│   ├── engine/
│   │   ├── manager.py        # MATLAB Engine 管理器
│   │   ├── async_executor.py # 异步任务执行器
│   │   ├── lock_manager.py   # 引擎锁管理
│   │   ├── resource_monitor.py # 资源监控（CPU/内存）
│   │   ├── injection_guard.py  # 注入检测
│   │   └── checkpoint.py     # 仿真检查点
│   ├── tools/
│   │   ├── registry.py       # 工具注册表
│   │   ├── computation.py    # 计算工具（5 个）
│   │   ├── visualization.py  # 可视化工具（4 个）
│   │   ├── simulink.py       # Simulink 工具（8 个）
│   │   ├── file_ops.py       # 文件操作工具（5 个）
│   │   ├── toolbox.py        # 工具箱工具（5 个）
│   │   └── task_manager.py   # 任务管理工具（6 个）
│   ├── resources/
│   │   ├── matlab_resources.py # MCP 资源（6 个）
│   │   └── prompts.py        # MCP 提示词（5 个）
│   ├── security/
│   │   ├── path_sanitizer.py   # 路径穿越防护
│   │   ├── injection_detector.py # 代码注入检测
│   │   ├── whitelist.py        # 函数白名单
│   │   ├── approval_queue.py   # 审批队列
│   │   ├── callback_cleaner.py # Simulink 回调清理
│   │   └── audit_logger.py     # 审计日志
│   ├── sandbox/
│   │   ├── workspace_manager.py # 沙盒管理
│   │   └── matlab_shadows/      # 20 个影子函数
│   ├── output/
│   │   ├── error_formatter.py   # 错误格式化
│   │   ├── client_adapter.py    # 客户端适配器
│   │   ├── payload_breaker.py   # 大载荷分片
│   │   ├── data_serializer.py   # 数据序列化/降采样
│   │   └── integrity.py         # 数据完整性校验
│   └── transport/
│       ├── stdio.py             # stdio 传输
│       └── http.py              # HTTP 传输
├── tests/                        # 312 个测试
├── .env.example                  # 环境变量模板
└── pyproject.toml                # 项目配置
```

---

## 测试

```bash
# 运行全部测试（312 个）
python -m pytest tests/ -v

# 运行特定模块测试
python -m pytest tests/test_tools/ -v
python -m pytest tests/test_engine/ -v
python -m pytest tests/test_security/ -v
```

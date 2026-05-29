# MATLAB MCP Server 设计文档

> **项目名称**：matlab-mcp-server
> **创建日期**：2026-05-27
> **状态**：设计完成，待实现

---

## 1. 项目概述

### 1.1 目标

构建一个基于 MCP（Model Context Protocol）协议的服务器，使 AI 助手（Claude Desktop、Trae IDE、Claude Code CLI 等）能够直接调用 MATLAB R2025a 完成仿真、建模、画图、数据分析等任务。

### 1.2 核心需求

- AI 通过 MCP 协议调用 MATLAB，无需手动编写代码
- 支持 MATLAB 全功能模块：基础计算、Simulink 仿真、数据可视化、工具箱
- 完善的错误处理与超时机制（仿真可能崩溃）
- 严格的安全限制，防止危险操作（白名单 + 用户审批）
- 支持多种 AI 客户端（stdio + HTTP/SSE 双传输）

### 1.3 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| MCP 服务器 | Python + `mcp` SDK | 官方 Python SDK，社区成熟 |
| MATLAB 集成 | MATLAB Engine API for Python | MathWorks 官方推荐，最稳定 |
| MATLAB 版本 | R2025a | 最新版本，API 支持最好 |
| HTTP 框架 | Starlette + uvicorn | 轻量级 ASGI，支持 SSE |
| 进程监控 | psutil | CPU/内存监控 + 进程管理 |
| 配置管理 | pydantic-settings | 环境变量 & 配置文件验证 |
| 日志 | structlog | 结构化审计日志 |

---

## 2. 系统架构

### 2.1 总体架构图

```
┌─────────────────────────────────────────────────────────┐
│                    AI 客户端层                            │
│   Claude Desktop │ Trae IDE │ Claude Code CLI │ 其他     │
└────────────────────────┬────────────────────────────────┘
                         │  MCP 协议 (JSON-RPC 2.0)
                         │  stdio / HTTP+SSE
┌────────────────────────┴────────────────────────────────┐
│              MCP Server (Python)                         │
│                                                         │
│  ┌──────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ 传输层    │  │ 工具注册 & 分发   │  │ 资源 & 提示词│  │
│  │ stdio    │  │ (装饰器模式注册)  │  │ 管理         │  │
│  │ HTTP/SSE │  │                  │  │              │  │
│  └────┬─────┘  └────────┬─────────┘  └──────┬───────┘  │
│       │                 │                   │          │
│  ┌────┴─────────────────┴───────────────────┴───────┐   │
│  │              安全层 (Safety Layer)                 │   │
│  │  ┌────────────────┐  ┌──────────┐  ┌───────────┐│   │
│  │  │ 预定义接口调用   │  │ 参数校验  │  │ 审计日志  ││   │
│  │  │ (非 eval 执行)  │  │ & 白名单  │  │           ││   │
│  │  └────────────────┘  └──────────┘  └───────────┘│   │
│  │  ┌────────────────────────────────────────────┐  │   │
│  │  │ 用户审批队列 (白名单外操作 → 阻塞等待确认)  │  │   │
│  │  └────────────────────────────────────────────┘  │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                               │
│  ┌──────────────────────┴───────────────────────────┐   │
│  │         异步任务管理器 (TaskManager)              │   │
│  │  ┌────────────┐ ┌──────────────┐ ┌────────────┐ │   │
│  │  │ 任务提交    │ │ 状态轮询      │ │ SSE 进度推送│ │   │
│  │  │ → Task_ID  │ │ check_status │ │ 实时进度条  │ │   │
│  │  └────────────┘ └──────────────┘ └────────────┘ │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                               │
│  ┌──────────────────────┴───────────────────────────┐   │
│  │           MATLAB Engine Manager                   │   │
│  │  ┌──────────────┐  ┌──────────────────────────┐  │   │
│  │  │ 沙盒会话管理  │  │ 超时控制 & 硬中断        │  │   │
│  │  │              │  │                          │  │   │
│  │  │ - 新任务:    │  │ - 任务级超时              │  │   │
│  │  │   clear/clc  │  │ - 进程 CPU/内存监控       │  │   │
│  │  │   close all  │  │ - 强杀 & 自动重启引擎     │  │   │
│  │  │   重置沙盒路径│  │                          │  │   │
│  │  │ - 连续任务:  │  │                          │  │   │
│  │  │   维持状态    │  │                          │  │   │
│  │  │ - 手动清理:  │  │                          │  │   │
│  │  │   reset 工具  │  │                          │  │   │
│  │  └──────────────┘  └──────────────────────────┘  │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                               │
│  ┌──────────────────────┴───────────────────────────┐   │
│  │           输出处理层 (Output Processor)            │   │
│  │  ┌──────────┐  ┌────────────────┐  ┌──────────┐ │   │
│  │  │ 图表导出  │  │ 数据降采样 &    │  │ 错误格式化│ │   │
│  │  │ PNG/SVG  │  │ 统计特征提取    │  │          │ │   │
│  │  └──────────┘  │ - >1000 点:    │  └──────────┘ │   │
│  │                │   降采样/统计   │               │   │
│  │                │ - 大矩阵:      │               │   │
│  │                │   仅返回图像    │               │   │
│  │                └────────────────┘               │   │
│  │  ┌────────────────────────────────────────────┐ │   │
│  │  │         负载熔断器 (Payload Breaker)        │ │   │
│  │  │  Payload > 5MB → 持久化到文件 → 返回路径    │ │   │
│  │  └────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────┘
                           │  MATLAB Engine API
┌──────────────────────────┴──────────────────────────────┐
│                  MATLAB R2025a                           │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────────┐│
│  │ 工作区    │  │ Simulink │  │ 工具箱 (信号处理/      ││
│  │ 计算引擎  │  │ 引擎     │  │ 控制/优化/ML等)        ││
│  └──────────┘  └──────────┘  └────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## 3. MCP 工具（Tools）设计

### 3.1 设计原则

- **预定义接口，非任意代码执行**：AI 只能调用预定义的类型化接口，不能发送任意 MATLAB 代码
- **传引用而非传值**：大数据通过变量名引用（`data_variable_name: str`），不通过 JSON 传输原始数组
- **装饰器模式注册**：各功能域文件通过装饰器将 Tool 注册到统一的 Registry

### 3.2 工具注册机制（装饰器模式）

```python
# src/matlab_mcp_server/tools/registry.py

from mcp.server import Server
from mcp.types import Tool
from typing import Callable, Any

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, description: str, input_schema: dict):
        """装饰器：将函数注册为 MCP Tool"""
        def decorator(func: Callable):
            self._tools[name] = {
                "name": name,
                "description": description,
                "input_schema": input_schema,
                "handler": func,
            }
            return func
        return decorator

    def bind_to_server(self, server: Server):
        """将所有注册的 Tools 绑定到 MCP Server 实例"""
        for name, tool_def in self._tools.items():
            server.add_tool(
                Tool(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    inputSchema=tool_def["input_schema"],
                ),
                handler=tool_def["handler"],
            )

registry = ToolRegistry()
```

```python
# src/matlab_mcp_server/tools/computation.py（使用示例）

from .registry import registry

@registry.register(
    name="run_matlab_function",
    description="调用预定义的 MATLAB 安全函数执行计算",
    input_schema={
        "type": "object",
        "properties": {
            "function_name": {"type": "string", "description": "MATLAB 函数名"},
            "args": {"type": "array", "description": "位置参数列表（仅支持标量/小数组）"},
            "kwargs": {"type": "object", "description": "关键字参数"},
            "output_variable": {"type": "string", "description": "结果保存到的变量名"},
        },
        "required": ["function_name"],
    },
)
async def handle_run_matlab_function(engine, params):
    # 实现逻辑
    pass
```

### 3.3 工具清单

#### MATLAB 计算与脚本工具

| Tool | 描述 | 参数 | 安全等级 |
|------|------|------|----------|
| `run_matlab_function` | 调用预定义的 MATLAB 函数 | `function_name`, `args`, `kwargs`, `output_variable` | L0 白名单 |
| `execute_matlab_script` | 执行预审阅的 MATLAB 脚本文件 | `script_path`, `params` | L0 白名单 |
| `evaluate_expression` | 计算 MATLAB 表达式（受限） | `expression` | L2 需审批 |
| `get_workspace_variable` | 获取工作区变量的信息 | `variable_name`, `max_rows` (默认 100) | L0 白名单 |
| `list_workspace_variables` | 列出当前工作区所有变量元数据 | 无 | L0 白名单 |

#### Simulink 仿真工具

| Tool | 描述 | 参数 | 安全等级 |
|------|------|------|----------|
| `load_simulink_model` | 加载已有的 .slx 模板 | `model_path` | L0 白名单 |
| `modify_block_parameters` | 修改指定模块的参数 | `model_name`, `block_path`, `params` | L0 白名单 |
| `list_block_parameters` | 列出某模块所有可调参数 | `model_name`, `block_path` | L0 白名单 |
| `create_simple_model` | 创建简单的线性链式模型 | `model_name`, `blocks` (按顺序连接) | L0 白名单 |
| `configure_simulation` | 配置仿真参数 | `model_name`, `solver`, `stop_time`, `step_size` | L0 白名单 |
| `run_simulation` | 运行 Simulink 仿真（异步） | `model_name`, `mode` (code/gui/hybrid) | L0 白名单 |
| `get_simulation_results` | 获取仿真结果数据 | `task_id`, `signals` | L0 白名单 |
| `open_simulink_gui` | 打开 GUI 让用户查看/编辑 | `model_name` | L0 白名单 |

#### 数据可视化工具

| Tool | 描述 | 参数 | 安全等级 |
|------|------|------|----------|
| `create_plot` | 创建标准图表 | `plot_type`, `x_variable_name`, `y_variable_name`, `title`, `xlabel`, `ylabel`, `style` | L0 白名单 |
| `create_3d_plot` | 创建 3D 图表 | `plot_type`, `x/y/z_variable_name`, `style` | L0 白名单 |
| `export_figure` | 导出当前图形 | `filename`, `format` (png/svg/pdf), `dpi`, `size` | L0 白名单 |
| `subplot_layout` | 创建子图布局 | `rows`, `cols`, `plots` | L0 白名单 |
| `verify_plot_data` | 读取 .fig 文件，提取图表关键信息为文本（纯文本 AI 的"代码眼"） | `figure_path` | L0 白名单 |

#### 工具箱专用工具

| Tool | 描述 | 参数 | 安全等级 |
|------|------|------|----------|
| `signal_processing` | 信号处理操作 | `operation` (fft/filter/spectrogram/wavelet), `data_variable_name`, `params` | L0 |
| `control_system` | 控制系统分析 | `operation` (bode/nyquist/step/rlocus/pid_tune), `system_variable_name`, `params` | L0 |
| `optimization` | 优化求解 | `solver` (fmincon/linprog/ga/particleswarm), `objective`, `constraints`, `bounds` | L0 |
| `machine_learning` | 机器学习/深度学习 | `operation` (train/predict/evaluate/visualize), `model_type`, `data_variable_name`, `params` | L2（训练需审批） |
| `data_analysis` | 数据分析 | `operation` (statistics/regression/clustering/pca), `data_variable_name`, `params` | L0 |

#### 异步任务管理工具

| Tool | 描述 | 参数 | 安全等级 |
|------|------|------|----------|
| `check_task_status` | 查询异步任务状态 | `task_id` | L0 白名单 |
| `cancel_task` | 取消正在运行的任务 | `task_id` | L0 白名单 |
| `reset_workspace` | 重置 MATLAB 工作区到沙盒状态 | 无 | L0 白名单 |

#### 文件与数据工具

| Tool | 描述 | 参数 | 安全等级 |
|------|------|------|----------|
| `load_data` | 加载数据文件到工作区 | `file_path`, `format` (csv/xlsx/mat/json), `variable_name` | L0（限沙盒） |
| `save_data` | 保存工作区数据到文件 | `variable_name`, `file_path`, `format` | L0（限沙盒） |
| `list_sandbox_files` | 列出沙盒目录中的文件 | 无 | L0 白名单 |
| `verify_checksum` | 验证文件或数据的校验和完整性 | `file_path`, `expected_hash` | L0 白名单 |

### 3.4 MCP 资源（Resources）

| 资源 URI | 描述 |
|----------|------|
| `matlab://workspace/variables` | 当前工作区变量列表（JSON） |
| `matlab://workspace/variable/{name}` | 某个变量的详细信息（元数据） |
| `matlab://sandbox/files` | 沙盒目录文件列表 |
| `matlab://sandbox/file/{path}` | 沙盒内文件内容 |
| `matlab://tasks/{task_id}` | 异步任务状态 |
| `matlab://sandbox/simulink/{name}` | Simulink 模型信息 |

### 3.5 MCP 提示词模板（Prompts）

| 提示词名称 | 描述 |
|-----------|------|
| `simulation_guide` | Simulink 仿真指南（含三种模式选择流程） |
| `plot_styling` | MATLAB 画图样式配置指南 |
| `data_analysis_workflow` | 数据分析标准工作流 |
| `signal_processing_guide` | 信号处理工具使用指南 |
| `troubleshooting` | 常见错误与解决方案 |

---

## 4. 异步任务与状态轮询机制

### 4.1 异步任务流程

```
AI 提交长耗时任务 (如 run_simulation)
    │
    ▼
MCP Server 立即返回 Task_ID
    │
    ├── 后台线程池中启动 MATLAB 执行
    │
    └── AI 通过 check_task_status(task_id) 轮询进度
        或通过 SSE 接收实时进度推送
```

### 4.2 任务状态机

```
                    ┌──────────┐
                    │  PENDING │  任务已提交，等待执行
                    └────┬─────┘
                         │ 开始执行
                         ▼
                    ┌──────────┐
              ┌─────│ RUNNING  │─────┐
              │     └────┬─────┘     │
              │          │           │
         超时/取消    正常完成     发生错误
              │          │           │
              ▼          ▼           ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │CANCELLING│ │COMPLETED │ │  FAILED  │
        └────┬─────┘ └──────────┘ └──────────┘
             │
             ▼
        ┌──────────┐
        │ CANCELLED│
        └──────────┘
```

### 4.3 客户端断连 TTL 机制

```
客户端断连
    │
    ▼
任务标记为 ORPHANED
    │
    ├── TTL 计时器启动（默认 2 小时，可配置）
    │
    ├── TTL 内客户端重连 → 恢复为 RUNNING
    │
    └── TTL 到期未重连
         ├── 普通任务 → 自动 CANCELLED，清理资源
         └── critical 任务 → 完成当前迭代 → 保存 checkpoint → CANCELLED_WITH_CHECKPOINT
```

---

## 5. 错误处理与超时机制

### 5.1 三层超时防护架构

#### 第 1 层：任务级超时

- AI 提交任务后立即返回 Task_ID，后台启动计时器
- 超时阈值可配置：普通任务 60s，仿真任务 3600s，训练任务无限制
- 超时后触发"温和停止"（调用 MATLAB `break` 或 `set_param(..., 'SimulationCommand', 'stop')`）

#### 第 2 层：进程级监控 + 稳态检测

**进程健康监控：**
- psutil 持续监控 MATLAB 进程的 CPU 和内存
- CPU > 95% 持续 5 分钟 → 警告
- 内存 > 80% 系统内存 → 警告
- 每 10 秒发送心跳 ping 检测进程响应性
- 进程无响应 → 触发"强制停止"

**仿真稳态检测（Steady-State Detection）：**
- 每个采样周期检查输出信号的统计特征
- 连续 N 个周期（可配置，默认 10）的均值波动 < 阈值且标准差 < 阈值 → 判定收敛
- 收敛后自动停止仿真，节省计算资源
- 返回结果中包含 `steady_state` 标记和收敛时间点

#### 第 3 层：进程级强杀与重启

- `process.terminate()` (psutil, 跨平台) → 等待 5 秒
- `process.kill()` (psutil, 跨平台，等效 SIGKILL/TerminateProcess) → 强制杀死
- 清理残留资源：
  - 扫描并删除 `.lck`（Simulink 模型锁）
  - 删除 `.slxc`（Simulink 编译缓存）
  - 删除 `.autosave`（自动保存临时文件）
  - 删除 `matlab_crash_dump_*`
  - 检查并清理共享内存段残留
- 自动启动新的 MATLAB Engine 实例
- 验证：尝试加载测试模型确认引擎正常
- 记录崩溃日志到审计系统

### 5.2 错误分类与处理策略

| 错误类型 | 检测方式 | 处理策略 |
|---------|----------|----------|
| 语法错误 | Engine API 抛出 `MatlabExecutionError` | 捕获 → 返回详细错误信息给 AI |
| 运行时错误 | Engine API 抛出 `MatlabExecutionError` | 捕获 → 返回堆栈 → 轻量化快照 |
| 资源耗尽 | 捕获异常 + psutil 监控 | 终止任务 → 建议减小数据规模 → 重启引擎 |
| Simulink 编译错误 | Simulink 编译阶段报错 | 返回编译错误详情 → 建议检查模块参数 |
| 仿真发散 | 检测输出中的 NaN/Inf | 终止仿真 → 返回已采集数据 → 建议调整求解器 |
| 引擎崩溃 | 进程消失 + psutil 检测 | 第 3 层强杀 → 自动重启 → 通知任务失败 |
| 超时 | 计时器触发 | 三层超时防护 |
| 连接断开 | stdio EOF / HTTP 连接关闭 | 后台继续 → 标记 ORPHANED → TTL 机制 |

### 5.3 轻量化快照机制

| 级别 | 触发条件 | 内容 | 性能影响 |
|------|----------|------|----------|
| Level 0 (默认) | 每次错误 | 仅保存变量元数据（名称、维度、类型），不写磁盘 | 零延迟 |
| Level 1 | 断点续跑需求 | 仅保存标记为 critical 的变量到 `.mat` 文件 | 通常 < 100 MB |
| Level 2 | 用户显式请求 | 全量工作区保存 | 需用户批准 + 磁盘空间检查 |

### 5.4 仿真稳态检测（Steady-State Detection）

#### 检测算法

对每个监测信号 s：

1. 按 `steady_state_check_interval` 采样，维护一个长度为 `steady_state_window_size` 的滑动窗口
2. 每次新采样加入窗口，计算：
   - 窗口内均值的变化率：`Δmean = |mean_current - mean_previous|`
   - 窗口内标准差：`std_current`
3. 若连续 `steady_state_window_size` 次：
   - `Δmean < mean_tolerance`
   - `std_current < std_tolerance`
   → 判定该信号已收敛
4. 所有监测信号均收敛 → 整个仿真判定为稳态，自动停止

#### 稳态检测配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `steady_state_enabled` | `true` | 是否启用稳态检测 |
| `steady_state_window_size` | `10` | 连续多少个周期满足条件才判定收敛 |
| `steady_state_mean_tolerance` | `1e-3` | 均值波动阈值（绝对误差） |
| `steady_state_std_tolerance` | `1e-3` | 标准差波动阈值 |
| `steady_state_check_interval` | `1.0` | 检查间隔（仿真时间单位） |
| `steady_state_signals` | `["all"]` | 需要监测的信号列表（默认全部） |

#### 稳态检测返回结果

```json
{
  "success": true,
  "task_id": "task_abc123",
  "steady_state": {
    "detected": true,
    "convergence_time": 45.6,
    "converged_signals": ["voltage_out", "current_in"],
    "final_values": {
      "voltage_out": {"mean": 3.3001, "std": 0.0002},
      "current_in": {"mean": 0.5000, "std": 0.0001}
    },
    "total_sim_time": 45.6,
    "original_stop_time": 100.0,
    "time_saved_percent": 54.4
  },
  "results": { "..." }
}
```

### 5.5 输出数据完整性校验

所有通过 MCP 通道返回的数据都附带校验和，防止结果被篡改或传输错误。

#### 校验和计算策略

| 数据大小 | 算法 | 理由 |
|----------|------|------|
| < 1 MB | SHA-256 | 强安全性，碰撞概率极低 |
| ≥ 1 MB | CRC32 | 速度快，大数据场景碰撞率可接受 |

#### 响应中的校验和字段

```json
{
  "success": true,
  "data": { "..." },
  "integrity": {
    "checksum": "a1b2c3d4e5f6...",
    "algorithm": "sha256",
    "data_size_bytes": 1024000,
    "timestamp": "2026-05-28T10:30:00Z"
  }
}
```

#### 校验失败处理

```
校验和不匹配
    │
    ▼
    返回错误码 INTEGRITY_CHECK_FAILED
    │
    ├── 自动重试（最多 integrity_auto_retry 次，默认 2）
    │
    ├── 重试成功 → 返回结果
    │
    └── 重试仍失败 → 记录审计日志 → 通知用户
```

#### 文件级校验（大数据持久化场景）

当负载熔断器将大数据保存到文件时，同时写入 `.checksum` 校验文件：

```
sandbox/
├── result_task123.mat              # 数据文件
├── result_task123.mat.sha256       # 校验和文件
├── result_task123.json
└── result_task123.json.sha256
```

AI 可调用 `verify_checksum(file_path, expected_hash)` 工具验证文件完整性。

### 5.6 错误信息返回格式

```json
{
  "success": false,
  "error": {
    "code": "MATLAB_RUNTIME_ERROR",
    "message": "Array indices must be positive integers or logical values.",
    "matlab_stack": ["Error in my_simulation (line 42)"],
    "suggestion": "检查数组索引是否从 1 开始（MATLAB 使用 1-based 索引）",
    "recoverable": true,
    "task_id": "task_abc123",
    "workspace_snapshot": {
      "level": 0,
      "variables": [
        {"name": "X", "size": [1000000, 1], "class": "double", "bytes": 8000000}
      ],
      "total_memory_mb": 512.3
    },
    "cleanup_status": {
      "lock_files_cleaned": 2,
      "cache_files_cleaned": 5,
      "cleanup_success": true
    }
  }
}
```

---

## 6. 安全层设计

### 6.1 五关防护架构

```
AI 请求进入
    │
    ▼
┌───────────────────────────────────────────────┐
│  第 1 关：接口层校验                           │
│  - AI 只能调用预定义 Tool，不能发任意代码       │
│  - Tool 参数类型校验（Pydantic schema）        │
│  - 参数范围检查（如 stop_time > 0 且 < 86400） │
└───────────────────┬───────────────────────────┘
                    ▼
┌───────────────────────────────────────────────┐
│  第 2 关：白名单过滤                           │
│  - 操作类型匹配白名单列表                      │
│  - 白名单内 → 直接放行                         │
│  - 白名单外 → 进入审批流程                     │
└───────────────────┬───────────────────────────┘
                    ▼
┌───────────────────────────────────────────────┐
│  第 3 关：参数安全净化                         │
│  - 路径穿越检测（os.path.realpath）            │
│  - 变量名合法性检查（^[a-zA-Z_]\w*$）          │
│  - MATLAB AST 注入分析（mtree）                │
│  - 数值范围强制裁剪                           │
└───────────────────┬───────────────────────────┘
                    ▼
┌───────────────────────────────────────────────┐
│  第 4 关：沙盒执行                             │
│  - MATLAB 工作目录锁定到沙盒                   │
│  - 文件 I/O 仅限沙盒目录                      │
│  - 危险函数遮蔽（sandbox/*.m 优先级最高）       │
│  - Simulink 回调自动清理                      │
└───────────────────┬───────────────────────────┘
                    ▼
┌───────────────────────────────────────────────┐
│  第 5 关：审计日志                             │
│  - 每次操作完整记录（时间、操作、参数、结果）   │
│  - 异常操作告警                               │
│  - 日志不可篡改（append-only）                 │
└───────────────────────────────────────────────┘
```

### 6.2 白名单分级

| 等级 | 分类 | 操作示例 | 处理方式 |
|------|------|---------|----------|
| L0 自动放行 | 基础计算 | `fft`, `conv`, `polyfit`, `linspace` 等 | 无副作用，直接执行 |
| L0 自动放行 | 可视化 | `plot`, `bar`, `scatter`, `surf` 等 | 仅生成图形 |
| L0 自动放行 | 工作区查询 | `whos`, `size`, `class`, `exist` | 只读 |
| L0 自动放行 | 沙盒文件IO | `load`, `save`, `readtable` (限沙盒) | 文件操作 |
| L0 自动放行 | Simulink API | `load_system`, `set_param`, `sim` | Simulink 操作 |
| L1 日志标记 | 工具箱函数 | 各工具箱特定函数 | 合法但需记录 |
| L2 需审批 | 系统调用 | `system`, `dos`, `unix` | 用户批准后执行 |
| L2 需审批 | 网络访问 | `urlread`, `webread`, `webwrite` | 可能泄露数据 |
| L2 需审批 | 危险文件IO | `delete`, `rmdir` (沙盒外) | 文件破坏风险 |
| L2 需审批 | ML 训练 | `trainNetwork` 等 | 耗资源 |
| L3 禁止 | 代码注入 | `eval`, `evalc`, `evalin`, `builtin` (沙盒外) | 绝对禁止 |
| L3 禁止 | 环境污染 | `addpath`, `rmpath`, `javaaddpath` | 绝对禁止 |

### 6.3 MATLAB AST 代码安全分析

使用 MATLAB 内置 `mtree` 函数解析代码为抽象语法树，替代正则表达式：

- 遍历所有函数调用节点
- 黑名单函数（`system`, `eval`, `feval`, `builtin`, `str2func` 等）→ 拒绝
- 白名单外的未知函数 → 拒绝
- 能检测正则无法拦截的绕过方式：`feval(strrev('lave'), ...)`, `builtin('system', ...)`, `str2func('system')(...)` 等

### 6.4 Simulink 回调函数防护

```python
def sanitize_simulink_model(model_name: str) -> CleanupReport:
    """在任何 sim() 调用前强制执行"""
    # 1. 剥离所有生命周期回调
    #    PreLoadFcn, PostLoadFcn, PreSaveFcn, StopFcn, InitFcn 等 15 个
    # 2. 遍历所有模块，剥离模块级回调
    #    ClickFcn, DeleteFcn, OpenFcn 等 12 个
    # 3. 返回清理报告（包含被剥离的回调名称和原始值）
    # 4. 记录到审计日志
```

**策略层级：**

| 场景 | 处理方式 |
|------|----------|
| AI 创建的新模型 | 完全禁止设置回调（Tool 接口不提供回调参数） |
| 加载用户 .slx 模型 | 自动剥离所有回调 → 返回清理报告 |
| 用户要求保留回调 | 需 L2 审批 → 展示回调内容 → 用户确认 |

### 6.5 沙盒函数遮蔽（Shadowing）

在 MATLAB 搜索路径最前端放置遮蔽函数文件，使危险函数被拦截：

```
sandbox/matlab_shadows/
├── system.m        → error('MATLABMCP:SecurityViolation', 'blocked')
├── dos.m           → error(...)
├── eval.m          → error(...)
├── evalc.m         → error(...)
├── evalin.m        → error(...)
├── feval.m         → error(...)
├── builtin.m       → error(...)
├── str2func.m      → error(...)
├── delete.m        → error(...)
├── rmdir.m         → error(...)
├── addpath.m       → error(...)
├── rmpath.m        → error(...)
├── javaaddpath.m   → error(...)
├── urlread.m       → error(...)
├── urlwrite.m      → error(...)
├── webread.m       → error(...)
├── webwrite.m      → error(...)
├── keyboard.m      → error(...)
├── input.m         → error(...)
└── __init_sandbox__.m  → addpath(sandbox_dir, '-begin')
```

**三层安全协同**：即使 AST 分析（第 3 关）被绕过，MATLAB 端的函数遮蔽（第 4 关）仍能拦截；即使遮蔽也被绕过，psutil 进程监控（第 5 关）能检测异常子进程并强杀。

### 6.6 路径安全净化

```python
def sanitize_path(file_path: str, sandbox_dir: str) -> str:
    normalized = os.path.normpath(file_path)
    full_path = os.path.realpath(os.path.join(sandbox_dir, normalized))
    if not full_path.startswith(os.path.realpath(sandbox_dir)):
        raise SecurityError(f"Path traversal detected: {file_path}")
    return full_path
```

- 使用 `os.path.realpath()` 解析所有符号链接后再比较
- 所有文件操作在 Python 层校验后才传递给 MATLAB
- 沙盒目录默认为 `~/matlab_mcp_sandbox/`

### 6.7 用户审批流程

白名单外操作返回 MCP 响应：
```json
{
  "requires_approval": true,
  "operation": "system('dir')",
  "risk_level": "high",
  "description": "执行系统命令",
  "approval_id": "approval_xyz"
}
```
AI 向用户展示审批请求，用户批准后执行或拒绝后返回拒绝信息。

### 6.8 审计日志格式

```json
{
  "timestamp": "2026-05-27T10:30:45.123Z",
  "session_id": "sess_abc123",
  "task_id": "task_def456",
  "client": "trae_ide",
  "tool": "run_simulation",
  "params": {"model_name": "motor_control", "mode": "code"},
  "security_level": "L0",
  "result": "success",
  "duration_ms": 45230,
  "matlab_memory_mb": 256.7,
  "matlab_cpu_percent": 87.3
}
```

---

## 7. 传输层设计

### 7.1 双传输模式

#### stdio 模式

- 适用：Claude Code CLI、Trae IDE
- 通信：stdin/stdout JSON-RPC 2.0
- 特点：零配置、进程级隔离、即开即用
- 启动：`python -m matlab_mcp_server --transport stdio`

#### HTTP + SSE 模式

- 适用：Claude Desktop、其他 Web 客户端
- 端口：默认 3000（可配置）
- 协议：`POST /mcp/message` → 客户端发请求；`GET /mcp/sse` → SSE 长连接推送
- 特点：支持服务端主动推送（进度条、审批通知）
- 启动：`python -m matlab_mcp_server --transport http --port 3000 --token <token>`

### 7.2 负载熔断机制

当通过通道返回的 Payload 超过阈值时，强制拦截：

| 传输通道 | 熔断阈值 | 理由 |
|----------|---------|------|
| stdio | 5 MB | stdout 管道缓冲区有限 |
| HTTP/SSE | 50 MB | HTTP 更耐受但仍需限制 |
| 图片 | 单张 10 MB | 超过则返回文件路径而非 base64 |

超过阈值时：
1. 数据持久化到沙盒文件（.mat / .json / .csv）
2. 仅返回文件路径 + 数据摘要信息

### 7.3 全局引擎互斥锁

MATLAB Engine 严格单线程，必须实现互斥锁：

```python
class EngineLockManager:
    """全局引擎锁管理器"""
    QUERY_TOOLS = {"check_task_status", "list_sandbox_files", "cancel_task", "get_server_info"}

    async def acquire(self, tool_name: str):
        if tool_name in self.QUERY_TOOLS:
            return True  # 查询类操作不需锁
        if self._state == EngineState.RUNNING:
            raise EngineBusyError(...)  # 返回 429
        # 获取锁

    async def release(self):
        # 释放锁
```

**并发请求处理策略：**

| 请求类型 | 引擎 IDLE 时 | 引擎 RUNNING 时 |
|---------|-------------|-----------------|
| 计算类 Tool | 获取锁 → 执行 | 立即返回 EngineBusyError (429) |
| 查询类 Tool | 直接执行 | 直接执行（不需锁） |
| `check_task_status` | 直接执行 | 直接执行 |
| `cancel_task` | 直接执行 | 直接执行（最高优先级） |
| `resources/read` | 直接执行 | 直接执行（只读） |

### 7.4 HTTP 模式 Token 认证

- 默认仅允许 `127.0.0.1` 访问
- 启动时必须指定 `--token` 参数（或 `MATLAB_MCP_TOKEN` 环境变量）
- 请求头需携带 `Authorization: Bearer <token>`
- 使用 `secrets.compare_digest()` 防止时序攻击
- 局域网访问需显式 `--bind 0.0.0.0`

### 7.5 客户端配置示例

**Claude Desktop (stdio):**
```json
{
  "mcpServers": {
    "matlab": {
      "command": "python",
      "args": ["-m", "matlab_mcp_server"],
      "env": {
        "MATLAB_MCP_MATLAB_TIMEOUT": "3600",
        "MATLAB_MCP_SANDBOX_DIR": "C:\\Users\\user\\matlab_sandbox"
      }
    }
  }
}
```

**Claude Desktop (HTTP):**
```json
{
  "mcpServers": {
    "matlab": {
      "url": "http://localhost:3000/mcp",
      "headers": {
        "Authorization": "Bearer my-secret-token"
      }
    }
  }
}
```

**Trae IDE / Claude Code CLI (stdio):**
```json
{
  "mcpServers": {
    "matlab": {
      "command": "python",
      "args": ["-m", "matlab_mcp_server", "--transport", "stdio"]
    }
  }
}
```

---

## 8. 项目结构

```
matlab-mcp-server/
├── pyproject.toml
├── README.md
├── .env.example
│
├── src/
│   └── matlab_mcp_server/
│       ├── __init__.py
│       ├── __main__.py                   # 入口：python -m matlab_mcp_server
│       ├── config.py                     # 配置管理
│       ├── server.py                     # MCP Server 核心
│       │
│       ├── transport/
│       │   ├── __init__.py
│       │   ├── stdio.py                  # stdio 传输模式
│       │   └── http.py                   # HTTP+SSE 传输 + Token 认证
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── registry.py               # 装饰器模式工具注册 & 分发器
│       │   ├── computation.py            # MATLAB 计算 & 脚本工具
│       │   ├── simulink.py               # Simulink 仿真工具
│       │   ├── visualization.py          # 数据可视化工具
│       │   ├── toolbox.py                # 工具箱专用工具
│       │   ├── task_manager.py           # 异步任务管理工具
│       │   └── file_ops.py               # 文件与数据工具
│       │
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── manager.py                # MATLAB Engine Manager
│       │   ├── async_executor.py         # 异步任务执行器
│       │   ├── lock_manager.py           # 全局引擎互斥锁
│       │   └── resource_monitor.py       # CPU/内存监控 + 硬中断
│       │
│       ├── security/
│       │   ├── __init__.py
│       │   ├── whitelist.py              # 白名单定义 & 过滤
│       │   ├── path_sanitizer.py         # 路径穿越净化
│       │   ├── injection_detector.py     # AST 注入检测
│       │   ├── callback_cleaner.py       # Simulink 回调清理
│       │   ├── approval_queue.py         # 用户审批队列
│       │   └── audit_logger.py           # 审计日志记录
│       │
│       ├── output/
│       │   ├── __init__.py
│       │   ├── figure_export.py          # 图表导出
│       │   ├── data_serializer.py        # 数据序列化 & 降采样
│       │   ├── payload_breaker.py        # 负载熔断器
│       │   ├── error_formatter.py        # 错误信息格式化（含差异化错误恢复）
│       │   └── client_adapter.py         # 客户端能力适配器（图像降级/数据路由）
│       │
│       └── sandbox/
│           ├── __init__.py
│           ├── matlab_shadows/           # MATLAB 危险函数遮蔽文件
│           │   ├── system.m
│           │   ├── dos.m
│           │   ├── eval.m
│           │   ├── feval.m
│           │   ├── builtin.m
│           │   ├── delete.m
│           │   ├── rmdir.m
│           │   ├── addpath.m
│           │   ├── urlread.m
│           │   ├── keyboard.m
│           │   ├── input.m
│           │   └── __init_sandbox__.m
│           └── workspace_manager.py      # 工作区清理 & 沙盒管理
│
├── tests/
│   ├── conftest.py                       # Mock MATLAB Engine fixtures
│   ├── test_security/
│   │   ├── test_path_sanitizer.py
│   │   ├── test_injection_detector.py
│   │   ├── test_callback_cleaner.py
│   │   └── test_whitelist.py
│   ├── test_engine/
│   │   ├── test_manager.py
│   │   ├── test_async_executor.py
│   │   └── test_resource_monitor.py
│   ├── test_output/
│   │   ├── test_payload_breaker.py
│   │   └── test_data_serializer.py
│   └── integration/
│       ├── test_end_to_end.py
│       └── test_client_compatibility.py
│
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-05-27-matlab-mcp-design.md
```

---

## 9. 配置管理

```python
class Settings(BaseSettings):
    # MATLAB 引擎
    matlab_timeout: int = 3600
    matlab_max_memory_mb: int = 8192
    matlab_cpu_threshold: float = 0.95
    matlab_heartbeat_interval: int = 10

    # 沙盒
    sandbox_dir: Path = Path.home() / "matlab_mcp_sandbox"
    auto_cleanup: bool = True

    # 传输层
    transport: str = "stdio"              # stdio | http
    http_port: int = 3000
    http_bind: str = "127.0.0.1"
    http_token: str | None = None

    # 负载限制
    payload_max_mb: int = 5
    image_max_mb: int = 10

    # AI 客户端能力
    client_vision: bool = True
    context_limit: int = 200000

    # 数据降级阈值
    full_data_threshold: int = 100
    downsample_threshold: int = 1000
    metadata_only_threshold: int = 1000000

    # 异步任务
    orphan_ttl_seconds: int = 7200
    checkpoint_enabled: bool = True
    max_concurrent_tasks: int = 1

    # 安全
    enable_ast_analysis: bool = True
    enable_shadow_functions: bool = True
    audit_log_path: Path = Path.home() / "matlab_mcp_sandbox" / "audit.log"

    # Simulink
    simulink_cleanup_callbacks: bool = True
    simulink_max_sim_time: float = 86400.0

    # 稳态检测
    steady_state_enabled: bool = True
    steady_state_window_size: int = 10
    steady_state_mean_tolerance: float = 1e-3
    steady_state_std_tolerance: float = 1e-3
    steady_state_check_interval: float = 1.0

    # 数据完整性
    integrity_check_enabled: bool = True
    integrity_algorithm: str = "sha256"   # sha256 (< 1MB) / crc32 (>= 1MB)
    integrity_auto_retry: int = 2         # 校验失败自动重试次数

    class Config:
        env_prefix = "MATLAB_MCP_"
        env_file = ".env"
```

---

## 10. AI 客户端异构能力适配

不同 AI 客户端的能力差异巨大（如 Claude 支持视觉，DeepSeek R1 仅纯文本）。MCP Server 必须根据客户端能力动态调整输出策略，防止不兼容数据导致幻觉或崩溃。

### 10.1 客户端能力标识

通过启动参数注入 AI 能力配置，`ToolDispatcher` 在发送响应前根据标识动态重塑 Payload 结构。

**配置参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--client-vision` | bool | `true` | AI 是否具备视觉能力（能解析图片） |
| `--context-limit` | int | `200000` | AI 上下文窗口大小（token 数），影响数据裁剪策略 |

```bash
# Claude Desktop (支持视觉)
python -m matlab_mcp_server --client-vision true --context-limit 200000

# DeepSeek R1 (纯文本)
python -m matlab_mcp_server --client-vision false --context-limit 65536
```

### 10.2 自适应降级路由

#### 图像输出降级

| AI 能力 | 图像处理策略 | 返回格式 |
|---------|-------------|----------|
| Vision=True (如 Claude) | 直接渲染 | `.png` 的 Base64 编码嵌入 MCP 响应 |
| Vision=False (如 DeepSeek) | 仅返回路径 + 元数据 | 文件路径 + `imfinfo` 元数据（分辨率、通道数、文件大小） |

```json
// Vision=True 响应
{
  "image": "base64_encoded_png_data...",
  "format": "png",
  "width": 1920,
  "height": 1080
}

// Vision=False 响应
{
  "image_path": "sandbox/figures/simulation_result.png",
  "metadata": {
    "format": "png",
    "width": 1920,
    "height": 1080,
    "color_channels": 3,
    "file_size_kb": 245,
    "bit_depth": 8
  },
  "instruction": "请调用 execute_matlab_script 编写 imread 代码，利用 MATLAB 后台提取特征"
}
```

#### 高维数据拦截

`get_workspace_variable` 对大规模矩阵强制返回降采样数据或统计摘要，避免上下文溢出：

```
数据大小 vs 返回策略：
  < 100 个元素     → 返回完整数据
  100 ~ 1000 元素  → 返回完整数据 + 统计摘要
  > 1000 个元素    → 强制返回降采样 + 统计摘要（极值、均值、方差）
  > 100 万元素     → 仅返回元数据（维度、类型、统计摘要）+ 建议绘图查看
```

### 10.3 防御性 Schema 描述

在 Tool 注册时，通过 `description` 字段向纯文本模型注入操作规范，防止 AI 猜测图片内容：

```python
@registry.register(
    name="create_plot",
    description=(
        "创建标准 MATLAB 图表。"
        "⚠️ 重要：若生成了图表且你不具备视觉能力，"
        "绝对不要尝试直接解析图片内容。"
        "请改用 verify_plot_data 工具获取图表的文本描述，"
        "或调用 execute_matlab_script 编写 imread 代码，"
        "利用 MATLAB 后台提取特征返回。"
    ),
    input_schema={...},
)
```

所有产出图表的 Tool（`create_plot`、`create_3d_plot`、`export_figure`、`subplot_layout`）都必须在 description 中包含上述防猜图 Prompt。

### 10.4 纯文本专属"代码眼"：verify_plot_data

新增一个专门为纯文本模型设计的验证工具：

| Tool | 描述 | 参数 | 安全等级 |
|------|------|------|----------|
| `verify_plot_data` | 读取 .fig 文件，提取图表关键信息为文本 | `figure_path: str` | L0 白名单 |

**返回内容：**
```json
{
  "axes_info": [
    {
      "xlabel": "Time (s)",
      "ylabel": "Voltage (V)",
      "xlim": [0, 10],
      "ylim": [-5, 5],
      "title": "Simulation Result"
    }
  ],
  "curves": [
    {
      "name": "V_out",
      "x_range": [0, 9.99],
      "y_range": [-4.8, 4.9],
      "data_points": 10000,
      "mean": 0.12,
      "std": 3.45,
      "peaks": [{"x": 2.5, "y": 4.9}, {"x": 7.5, "y": -4.8}]
    }
  ],
  "legends": ["V_in", "V_out"],
  "grid": true,
  "figure_size": [800, 600],
  "colormap": null
}
```

纯文本 AI 绘图后可调用此工具进行"闭眼 Debug"，验证数据呈现是否准确。

### 10.5 差异化错误恢复上下文

针对不同 AI 的出错特点，提供差异化的抢救信息：

#### 纯文本模型（逻辑强，易忘状态）

报错时在 JSON 中强制附加当前工作区的 `whos` 列表：

```json
{
  "success": false,
  "error": {
    "code": "MATLAB_RUNTIME_ERROR",
    "message": "Undefined function 'sim' for input arguments of type 'char'.",
    "suggestion": "Simulink 未加载。请先调用 load_simulink_model。",
    "workspace_context": {
      "variables": [
        {"name": "model_name", "class": "char", "size": [1, 12]},
        {"name": "params", "class": "struct", "size": [1, 1]}
      ],
      "loaded_toolboxes": ["Signal Processing Toolbox"],
      "current_path": "C:/Users/user/matlab_mcp_sandbox"
    }
  }
}
```

#### 多模态模型（视觉强）

仿真因数值问题发散时，将发散点前段的有效数据绘制成缩略图回传：

```json
{
  "success": false,
  "error": {
    "code": "SIMULATION_DIVERGENCE",
    "message": "Simulation diverged at t=2.34s. NaN detected in output signal.",
    "divergence_point": {"time": 2.34, "signal": "y_out"},
    "visualization": {
      "pre_divergence_plot": "base64_encoded_thumbnail...",
      "description": "发散前的有效数据缩略图，红色标记为发散起始点"
    },
    "suggestion": "减小步长或切换为 stiff solver (如 ode15s)"
  }
}
```

### 10.6 config.py 新增配置

```python
class Settings(BaseSettings):
    # ... 原有配置 ...

    # AI 客户端能力
    client_vision: bool = True          # AI 是否支持视觉
    context_limit: int = 200000         # AI 上下文窗口大小（token）

    # 数据降级阈值
    full_data_threshold: int = 100      # < 100 元素返回完整数据
    downsample_threshold: int = 1000    # > 1000 元素强制降采样
    metadata_only_threshold: int = 1000000  # > 100 万仅返回元数据
```

---

## 11. 技术栈与依赖

| 组件 | 选型 | 版本 |
|------|------|------|
| Python | 语言 | ≥ 3.11 |
| `mcp` | MCP SDK | ≥ 1.0 |
| `matlab.engine` | MATLAB API | R2025a |
| Starlette + uvicorn | HTTP 框架 | latest |
| `psutil` | 进程监控 | ≥ 5.9 |
| `numpy` | 数值计算 | latest |
| `pydantic-settings` | 配置管理 | latest |
| `structlog` | 结构化日志 | latest |
| `pytest` + `pytest-asyncio` | 测试框架 | latest |

---

## 12. 启动流程

```
python -m matlab_mcp_server [options]

启动序列：
  1. 加载配置（.env → 环境变量 → 命令行参数）
  2. 创建沙盒目录（如不存在）
  3. 部署 MATLAB 危险函数遮蔽文件到沙盒
  4. 启动 MATLAB Engine
  5. 初始化沙盒路径优先级（addpath sandbox -begin）
  6. 启动资源监控线程
  7. 启动审计日志
  8. 解析客户端能力标识（--client-vision, --context-limit）→ 注册到 ToolDispatcher
  9. 根据 transport 参数选择传输模式
  10. 通过装饰器注册所有 MCP Tools & Resources（含防御性 Schema 描述）
  11. 就绪，等待客户端连接
```

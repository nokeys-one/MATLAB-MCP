import json
from mcp.types import PromptMessage, TextContent


SIMULATION_GUIDE = """# Simulink 仿真指南

## 仿真工作流程

1. **加载或创建模型**
   - `load_simulink_model` — 加载已有的 .slx 模板
   - `create_simple_model` — 创建线性链式模型（自动连接模块）

2. **配置仿真参数**
   - `configure_simulation` — 设置求解器、仿真时长、步长
   - 推荐求解器：ode45（非刚性）、ode15s（刚性）、ode23（低精度快速）

3. **修改模块参数**
   - `modify_block_parameters` — 修改增益、频率、阈值等
   - `list_block_parameters` — 查看模块可调参数

4. **运行仿真**
   - `run_simulation` — 三种模式：
     - `code`：纯后台运行（默认）
     - `gui`：打开 Simulink GUI
     - `hybrid`：后台运行 + 可查看 GUI

5. **获取结果**
   - `check_task_status` — 轮询任务进度
   - `get_simulation_results` — 仿真完成后获取数据
   - `verify_plot_data` — 文本方式查看图表信息

## 故障排除

| 问题 | 建议 |
|------|------|
| 仿真发散 | 减小步长，切换 ode15s |
| 内存溢出 | 减少信号记录，缩短仿真时间 |
| 模块未找到 | 检查 Simulink 工具箱是否加载 |
"""


PLOT_STYLING = """# MATLAB 画图样式配置指南

## 常用图表类型

| 类型 | plot_type 值 | 适用场景 |
|------|-------------|----------|
| 折线图 | line | 连续数据趋势 |
| 柱状图 | bar | 分类数据对比 |
| 散点图 | scatter | 相关性分析 |
| 直方图 | histogram | 分布分析 |
| 阶梯图 | stairs | 离散信号 |
| 茎图 | stem | 采样信号 |

## 样式参数

通过 `style` 对象传入：
- `Color` — 颜色（如 'r', 'b', '#FF5733'）
- `LineWidth` — 线宽（默认 1.5）
- `Marker` — 标记样式（'o', 's', '^', 'd'）
- `MarkerSize` — 标记大小
- `LineStyle` — 线型（'-'实线, '--'虚线, ':'点线）

## 3D 图表

- surf — 表面图（彩色填充）
- mesh — 网格图（透明线框）
- contour — 等高线图
- scatter3 — 3D 散点图

## 导出

- `export_figure` — 导出为 PNG/SVG/PDF
- 推荐 DPI：300（打印质量）
"""


DATA_ANALYSIS_WORKFLOW = """# 数据分析标准工作流

## 1. 数据加载
- `load_data` — 支持 CSV/XLSX/MAT/JSON
- 文件必须在沙盒目录内

## 2. 数据探索
- `list_workspace_variables` — 查看所有变量
- `get_workspace_variable` — 查看变量详情
- `data_analysis` (describe) — 统计摘要（均值/中位数/标准差/极值）

## 3. 数据分析操作

| 操作 | 说明 |
|------|------|
| describe | 描述性统计 |
| corrcoef | 相关系数矩阵 |
| regress | 线性回归 |
| ttest | t 检验 |
| anova | 方差分析 |
| interp1 | 一维插值 |
| smooth | 平滑处理 |
| histogram_stats | 直方图统计 |

## 4. 可视化
- `create_plot` — 创建图表
- `subplot_layout` — 多子图布局

## 5. 保存结果
- `save_data` — 保存到 CSV/MAT/JSON
"""


SIGNAL_PROCESSING_GUIDE = """# 信号处理工具使用指南

## 支持的操作

| 操作 | 说明 | 关键参数 |
|------|------|----------|
| fft | 快速傅里叶变换 | — |
| ifft | 逆 FFT | — |
| lowpass | 低通滤波 | cutoff, fs |
| highpass | 高通滤波 | cutoff, fs |
| bandpass | 带通滤波 | low_cutoff, high_cutoff, fs |
| psd | 功率谱密度 | nfft, fs |
| spectrogram | 时频谱图 | nfft, fs |
| filter_design | 滤波器设计 | order, cutoff, fs |

## 使用示例

```
1. 先用 run_matlab_function 生成信号：
   t = 0:0.001:1; x = sin(2*pi*50*t) + sin(2*pi*120*t);

2. 调用 signal_processing：
   operation: "fft"
   input_variable: "x"
   params: { "fs": 1000 }

3. 用 create_plot 可视化频谱
```

## 注意事项
- 采样率 fs 必须 > 2 × 最高信号频率（奈奎斯特定理）
- Butterworth 滤波器默认 4 阶
"""


TROUBLESHOOTING = """# 常见错误与解决方案

## MATLAB 引擎错误

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| Undefined function | 函数名拼写错误或工具箱未加载 | 检查拼写，确认所需工具箱已安装 |
| Index exceeds dimensions | 数组越界 | MATLAB 索引从 1 开始 |
| Out of memory | 数据规模过大 | 减小数据或使用降采样 |
| License checkout failed | 工具箱许可证问题 | 检查 MATLAB 许可证状态 |

## 安全相关

| 状态 | 说明 | 操作 |
|------|------|------|
| L0_AUTO | 白名单内，自动放行 | 无需操作 |
| L2_APPROVAL | 需用户审批 | 调用 approve_operation 或 reject_operation |
| L3_BLOCKED | 安全阻止 | 此操作不允许执行 |

## 任务管理

- 长时间任务用 `check_task_status` 轮询
- 卡住的任务用 `cancel_task` 取消
- 工作区混乱用 `reset_workspace` 重置

## 文件路径

- 所有文件操作限制在沙盒目录内
- 路径穿越攻击会被自动拦截
- 使用相对路径（如 "data/test.csv"）
"""


def register_prompts(mcp):
    @mcp.prompt(
        name="simulation_guide",
        description="Simulink 仿真指南（含三种模式选择流程）",
    )
    def simulation_guide() -> str:
        return SIMULATION_GUIDE

    @mcp.prompt(
        name="plot_styling",
        description="MATLAB 画图样式配置指南",
    )
    def plot_styling() -> str:
        return PLOT_STYLING

    @mcp.prompt(
        name="data_analysis_workflow",
        description="数据分析标准工作流",
    )
    def data_analysis_workflow() -> str:
        return DATA_ANALYSIS_WORKFLOW

    @mcp.prompt(
        name="signal_processing_guide",
        description="信号处理工具使用指南",
    )
    def signal_processing_guide() -> str:
        return SIGNAL_PROCESSING_GUIDE

    @mcp.prompt(
        name="troubleshooting",
        description="常见错误与解决方案",
    )
    def troubleshooting() -> str:
        return TROUBLESHOOTING

import numpy as np
from typing import Any


def downsample_lttb(data_x: np.ndarray, data_y: np.ndarray, threshold: int) -> tuple:
    n = len(data_x)
    if n <= threshold:
        return data_x, data_y
    sampled_x = np.zeros(threshold)
    sampled_y = np.zeros(threshold)
    sampled_x[0], sampled_y[0] = data_x[0], data_y[0]
    sampled_x[-1], sampled_y[-1] = data_x[-1], data_y[-1]
    every = (n - 2) / (threshold - 2)
    a = 0
    for i in range(1, threshold - 1):
        avg_start = int(np.floor((i - 1) * every)) + 1
        avg_end = min(int(np.floor(i * every)) + 1, n)
        avg_x = np.mean(data_x[avg_start:avg_end])
        avg_y = np.mean(data_y[avg_start:avg_end])
        range_start = int(np.floor(i * every)) + 1
        range_end = min(int(np.floor((i + 1) * every)) + 1, n)
        max_area, selected = -1.0, avg_start
        for j in range(range_start, range_end):
            area = abs((data_x[a] - avg_x) * (data_y[j] - data_y[a])
                       - (data_x[a] - data_x[j]) * (avg_y - data_y[a])) * 0.5
            if area > max_area:
                max_area, selected = area, j
        sampled_x[i], sampled_y[i] = data_x[selected], data_y[selected]
        a = selected
    return sampled_x, sampled_y


def compute_statistics(data: np.ndarray) -> dict:
    return {
        "mean": float(np.nanmean(data)),
        "std": float(np.nanstd(data)),
        "min": float(np.nanmin(data)),
        "max": float(np.nanmax(data)),
        "median": float(np.nanmedian(data)),
        "size": list(data.shape),
    }


def serialize_variable(data: Any, max_rows: int = 100,
                       downsample_threshold: int = 1000,
                       metadata_only_threshold: int = 1000000) -> dict:
    if isinstance(data, np.ndarray):
        element_count = data.size
        if element_count > metadata_only_threshold:
            return {"truncated": True, "metadata": compute_statistics(data),
                    "suggestion": "数据量超过 100 万，仅返回元数据。请使用绘图工具可视化。"}
        if element_count > downsample_threshold and data.ndim == 1:
            x = np.arange(len(data))
            sx, sy = downsample_lttb(x, data, downsample_threshold)
            return {"truncated": True, "downsampled": {"x": sx.tolist(), "y": sy.tolist()},
                    "metadata": compute_statistics(data)}
        if element_count > max_rows:
            return {"truncated": True, "partial_data": data.flat[:max_rows].tolist(),
                    "metadata": compute_statistics(data)}
        return {"data": data.tolist(), "metadata": compute_statistics(data)}
    return {"data": str(data)[:5000]}

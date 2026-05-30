import numpy as np
from matlab_mcp_server.output.data_serializer import (
    downsample_lttb, compute_statistics, serialize_variable,
)


def test_downsample_lttb_reduces_size():
    x = np.linspace(0, 10, 10000)
    y = np.sin(x)
    sx, sy = downsample_lttb(x, y, 500)
    assert len(sx) == 500
    assert len(sy) == 500


def test_downsample_no_change_if_small():
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([4.0, 5.0, 6.0])
    sx, sy = downsample_lttb(x, y, 100)
    assert len(sx) == 3


def test_compute_statistics():
    data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    stats = compute_statistics(data)
    assert stats["mean"] == 3.0
    assert stats["min"] == 1.0
    assert stats["max"] == 5.0
    assert stats["median"] == 3.0
    assert "std" in stats
    assert stats["size"] == [5]


def test_serialize_small_array():
    data = np.array([1.0, 2.0, 3.0])
    result = serialize_variable(data, max_rows=100, downsample_threshold=1000)
    assert "data" in result
    assert "metadata" in result
    assert result["data"] == [1.0, 2.0, 3.0]


def test_serialize_large_array_downsampled():
    data = np.random.randn(5000)
    result = serialize_variable(data, max_rows=100, downsample_threshold=1000)
    assert result["truncated"] is True
    assert "downsampled" in result
    assert len(result["downsampled"]["y"]) == 1000


def test_serialize_metadata_only():
    data = np.random.randn(2000000)
    result = serialize_variable(data, max_rows=100, downsample_threshold=1000,
                                metadata_only_threshold=1000000)
    assert result["truncated"] is True
    assert "metadata" in result
    assert "data" not in result
    assert "downsampled" not in result
    assert "suggestion" in result


def test_serialize_partial_data():
    data = np.arange(500, dtype=float)
    result = serialize_variable(data, max_rows=100, downsample_threshold=1000)
    assert result["truncated"] is True
    assert "partial_data" in result
    assert len(result["partial_data"]) == 100


def test_serialize_non_array():
    result = serialize_variable("hello world")
    assert result["data"] == "hello world"


def test_serialize_non_array_truncates_long_string():
    long_str = "x" * 10000
    result = serialize_variable(long_str)
    assert len(result["data"]) == 5000


def test_compute_statistics_with_nan():
    data = np.array([1.0, np.nan, 3.0])
    stats = compute_statistics(data)
    assert stats["mean"] == 2.0
    assert stats["min"] == 1.0
    assert stats["max"] == 3.0


def test_downsample_preserves_endpoints():
    x = np.linspace(0, 100, 10000)
    y = np.sin(x)
    sx, sy = downsample_lttb(x, y, 500)
    assert sx[0] == x[0]
    assert sx[-1] == x[-1]
    assert sy[0] == y[0]
    assert sy[-1] == y[-1]

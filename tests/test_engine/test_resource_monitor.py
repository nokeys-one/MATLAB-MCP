import time
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from matlab_mcp_server.engine.resource_monitor import ResourceMonitor


def test_initialization_defaults():
    monitor = ResourceMonitor()
    assert monitor.pid is None
    assert monitor.cpu_threshold == 0.95
    assert monitor.memory_threshold == 0.80
    assert monitor.heartbeat_interval == 10
    assert monitor._running is False


def test_initialization_custom():
    on_exceeded = MagicMock()
    on_unresponsive = MagicMock()
    monitor = ResourceMonitor(
        pid=1234,
        cpu_threshold=0.8,
        memory_threshold=0.6,
        heartbeat_interval=5,
        on_resource_exceeded=on_exceeded,
        on_process_unresponsive=on_unresponsive,
    )
    assert monitor.pid == 1234
    assert monitor.cpu_threshold == 0.8
    assert monitor.memory_threshold == 0.6
    assert monitor.heartbeat_interval == 5
    assert monitor._on_resource_exceeded is on_exceeded
    assert monitor._on_process_unresponsive is on_unresponsive


def test_start_with_nonexistent_pid():
    monitor = ResourceMonitor()
    with patch("matlab_mcp_server.engine.resource_monitor.psutil") as mock_psutil:
        mock_psutil.NoSuchProcess = Exception
        mock_psutil.Process.side_effect = Exception("No such process")
        monitor.start(pid=99999)
    assert monitor._running is False


def test_start_success():
    monitor = ResourceMonitor(heartbeat_interval=1)
    mock_process = MagicMock()
    mock_process.is_running.side_effect = [True, False]
    mock_process.cpu_percent.return_value = 10.0
    mock_process.memory_info.return_value = MagicMock(rss=100 * 1024 * 1024)

    with patch("matlab_mcp_server.engine.resource_monitor.psutil") as mock_psutil:
        mock_psutil.Process.return_value = mock_process
        mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
        mock_psutil.AccessDenied = type("AccessDenied", (Exception,), {})
        mock_psutil.virtual_memory.return_value = MagicMock(total=16 * 1024**3)
        monitor.start(pid=1234)
        time.sleep(0.5)

    assert monitor._running is True
    assert monitor._process is mock_process
    monitor.stop()


def test_stop():
    monitor = ResourceMonitor()
    monitor._running = True
    monitor._thread = MagicMock()
    monitor.stop()
    assert monitor._running is False
    monitor._thread.join.assert_called_once_with(timeout=5)


def test_get_status_not_running():
    monitor = ResourceMonitor()
    status = monitor.get_status()
    assert status["monitoring"] is False
    assert status["pid"] is None
    assert status["warnings"] == []


def test_get_status_running():
    monitor = ResourceMonitor()
    monitor._running = True
    monitor.pid = 1234
    mock_process = MagicMock()
    mock_process.is_running.return_value = True
    mock_process.cpu_percent.return_value = 45.0
    mock_process.memory_info.return_value = MagicMock(rss=512 * 1024 * 1024)
    monitor._process = mock_process

    status = monitor.get_status()
    assert status["monitoring"] is True
    assert status["pid"] == 1234
    assert status["cpu_percent"] == 45.0
    assert status["memory_rss_mb"] == 512.0


def test_get_status_process_dead():
    monitor = ResourceMonitor()
    monitor._running = True
    monitor.pid = 1234
    mock_process = MagicMock()
    mock_process.is_running.return_value = False
    monitor._process = mock_process

    status = monitor.get_status()
    assert status["monitoring"] is True
    assert "cpu_percent" not in status


def test_get_status_access_denied():
    monitor = ResourceMonitor()
    monitor._running = True
    monitor.pid = 1234
    mock_process = MagicMock()
    mock_process.is_running.return_value = True
    mock_process.cpu_percent.side_effect = Exception("Access denied")
    monitor._process = mock_process

    status = monitor.get_status()
    assert "cpu_percent" not in status


def test_force_kill_success():
    monitor = ResourceMonitor()
    mock_process = MagicMock()
    mock_process.wait.return_value = 0
    monitor._process = mock_process

    result = monitor.force_kill()
    assert result is True
    mock_process.terminate.assert_called_once()


def test_force_kill_no_process():
    monitor = ResourceMonitor()
    monitor._process = None
    result = monitor.force_kill()
    assert result is False


def test_force_kill_terminate_timeout():
    monitor = ResourceMonitor()
    mock_process = MagicMock()

    import psutil as real_psutil
    mock_process.terminate.side_effect = None
    mock_process.wait.side_effect = [
        real_psutil.TimeoutExpired(5),
        0,
    ]
    mock_process.kill.return_value = None
    monitor._process = mock_process

    result = monitor.force_kill()
    assert result is True
    mock_process.kill.assert_called_once()


def test_high_cpu_warning():
    warnings_list = []

    def on_exceeded(resource_type, value):
        warnings_list.append({"type": resource_type, "value": value})

    monitor = ResourceMonitor(
        cpu_threshold=0.5,
        on_resource_exceeded=on_exceeded,
        heartbeat_interval=1,
    )

    mock_process = MagicMock()
    mock_process.is_running.side_effect = [True, False]
    mock_process.cpu_percent.return_value = 80.0

    with patch("matlab_mcp_server.engine.resource_monitor.psutil") as mock_psutil:
        mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
        mock_psutil.AccessDenied = type("AccessDenied", (Exception,), {})
        mock_psutil.Process.return_value = mock_process
        mock_psutil.virtual_memory.return_value = MagicMock(total=16 * 1024**3)
        mock_process.memory_info.return_value = MagicMock(rss=1 * 1024**3)

        monitor.start(pid=1234)
        time.sleep(0.5)
        monitor.stop()

    assert len(warnings_list) >= 1
    assert warnings_list[0]["type"] == "cpu"


def test_high_memory_warning():
    warnings_list = []

    def on_exceeded(resource_type, value):
        warnings_list.append({"type": resource_type, "value": value})

    monitor = ResourceMonitor(
        memory_threshold=0.01,
        on_resource_exceeded=on_exceeded,
        heartbeat_interval=1,
    )

    mock_process = MagicMock()
    mock_process.is_running.side_effect = [True, False]
    mock_process.cpu_percent.return_value = 10.0

    with patch("matlab_mcp_server.engine.resource_monitor.psutil") as mock_psutil:
        mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
        mock_psutil.AccessDenied = type("AccessDenied", (Exception,), {})
        mock_psutil.Process.return_value = mock_process
        mock_psutil.virtual_memory.return_value = MagicMock(total=1024)
        mock_process.memory_info.return_value = MagicMock(rss=512)

        monitor.start(pid=1234)
        time.sleep(0.5)
        monitor.stop()

    assert len(warnings_list) >= 1
    assert any(w["type"] == "memory" for w in warnings_list)


def test_process_unresponsive_callback():
    unresponsive_called = []

    def on_unresponsive(pid):
        unresponsive_called.append(pid)

    monitor = ResourceMonitor(
        on_process_unresponsive=on_unresponsive,
        heartbeat_interval=1,
    )

    mock_process = MagicMock()
    mock_process.is_running.return_value = False

    with patch("matlab_mcp_server.engine.resource_monitor.psutil") as mock_psutil:
        mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
        mock_psutil.Process.return_value = mock_process
        monitor.start(pid=1234)
        time.sleep(0.5)
        monitor.stop()

    assert len(unresponsive_called) >= 1
    assert unresponsive_called[0] == 1234

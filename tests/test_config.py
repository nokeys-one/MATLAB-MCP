import os
import pytest
from pathlib import Path


def test_settings_defaults():
    from matlab_mcp_server.config import Settings

    s = Settings()
    assert s.matlab_timeout == 3600
    assert s.matlab_max_memory_mb == 8192
    assert s.transport == "stdio"
    assert s.http_port == 3000
    assert s.http_bind == "127.0.0.1"
    assert s.http_token is None
    assert s.payload_max_mb == 5
    assert s.client_vision is True
    assert s.context_limit == 200000
    assert s.full_data_threshold == 100
    assert s.downsample_threshold == 1000
    assert s.metadata_only_threshold == 1000000
    assert s.steady_state_enabled is True
    assert s.steady_state_window_size == 10
    assert s.steady_state_mean_tolerance == pytest.approx(1e-3)
    assert s.integrity_check_enabled is True
    assert s.integrity_algorithm == "sha256"
    assert s.integrity_auto_retry == 2
    assert s.orphan_ttl_seconds == 7200
    assert s.enable_shadow_functions is True


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("MATLAB_MCP_MATLAB_TIMEOUT", "7200")
    monkeypatch.setenv("MATLAB_MCP_HTTP_PORT", "8080")
    monkeypatch.setenv("MATLAB_MCP_CLIENT_VISION", "false")
    from matlab_mcp_server.config import Settings

    s = Settings()
    assert s.matlab_timeout == 7200
    assert s.http_port == 8080
    assert s.client_vision is False


def test_sandbox_dir_is_path():
    from matlab_mcp_server.config import Settings

    s = Settings()
    assert isinstance(s.sandbox_dir, Path)

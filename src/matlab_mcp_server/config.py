from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    matlab_timeout: int = 3600
    matlab_max_memory_mb: int = 8192
    matlab_cpu_threshold: float = 0.95
    matlab_heartbeat_interval: int = 10

    sandbox_dir: Path = Path.home() / "matlab_mcp_sandbox"
    auto_cleanup: bool = True

    transport: str = "stdio"
    http_port: int = 3000
    http_bind: str = "127.0.0.1"
    http_token: str | None = None

    payload_max_mb: int = 5
    image_max_mb: int = 10

    client_vision: bool = True
    context_limit: int = 200000

    full_data_threshold: int = 100
    downsample_threshold: int = 1000
    metadata_only_threshold: int = 1000000

    orphan_ttl_seconds: int = 7200
    checkpoint_enabled: bool = True
    max_concurrent_tasks: int = 1

    steady_state_enabled: bool = True
    steady_state_window_size: int = 10
    steady_state_mean_tolerance: float = 1e-3
    steady_state_std_tolerance: float = 1e-3
    steady_state_check_interval: float = 1.0

    integrity_check_enabled: bool = True
    integrity_algorithm: str = "sha256"
    integrity_auto_retry: int = 2

    enable_regex_injection_analysis: bool = True
    enable_shadow_functions: bool = True
    audit_log_path: Path = Path.home() / "matlab_mcp_sandbox" / "audit.log"

    simulink_cleanup_callbacks: bool = True
    simulink_max_sim_time: float = 86400.0

    model_config = {"env_prefix": "MATLAB_MCP_", "env_file": ".env"}

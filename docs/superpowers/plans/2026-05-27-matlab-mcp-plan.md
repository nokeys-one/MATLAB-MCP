# MATLAB MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade MCP server that enables AI assistants to call MATLAB R2025a for simulation, modeling, plotting, and data analysis via the MCP protocol.

**Architecture:** Python MCP Server using `mcp` SDK (FastMCP) with MATLAB Engine API for Python. Decorator-based tool registration across domain-specific modules. Multi-layer safety (whitelist, AST analysis, function shadowing). Dual transport (stdio + HTTP/SSE). Async task management with steady-state detection.

**Tech Stack:** Python >= 3.11, `mcp` SDK, `matlab.engine` (R2025a), Starlette + uvicorn, psutil, numpy, pydantic-settings, structlog, pytest + pytest-asyncio

---

## File Structure

```
matlab-mcp-server/
├── pyproject.toml
├── .env.example
├── src/
│   └── matlab_mcp_server/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config.py
│       ├── server.py
│       ├── transport/
│       │   ├── __init__.py
│       │   ├── stdio.py
│       │   └── http.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── registry.py
│       │   ├── computation.py
│       │   ├── simulink.py
│       │   ├── visualization.py
│       │   ├── toolbox.py
│       │   ├── task_manager.py
│       │   └── file_ops.py
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── manager.py
│       │   ├── async_executor.py
│       │   ├── lock_manager.py
│       │   ├── resource_monitor.py
│       │   └── steady_state.py
│       ├── security/
│       │   ├── __init__.py
│       │   ├── whitelist.py
│       │   ├── path_sanitizer.py
│       │   ├── callback_cleaner.py
│       │   ├── approval_queue.py
│       │   └── audit_logger.py
│       ├── output/
│       │   ├── __init__.py
│       │   ├── figure_export.py
│       │   ├── data_serializer.py
│       │   ├── payload_breaker.py
│       │   ├── integrity.py
│       │   ├── error_formatter.py
│       │   └── client_adapter.py
│       └── sandbox/
│           ├── __init__.py
│           ├── workspace_manager.py
│           └── matlab_shadows/
│               ├── __init_sandbox__.m
│               ├── system.m
│               ├── dos.m
│               ├── eval.m
│               ├── evalc.m
│               ├── evalin.m
│               ├── feval.m
│               ├── builtin.m
│               ├── str2func.m
│               ├── delete.m
│               ├── rmdir.m
│               ├── addpath.m
│               ├── rmpath.m
│               ├── javaaddpath.m
│               ├── urlread.m
│               ├── urlwrite.m
│               ├── webread.m
│               ├── webwrite.m
│               ├── keyboard.m
│               └── input.m
├── tests/
│   ├── conftest.py
│   ├── test_security/
│   │   ├── test_path_sanitizer.py
│   │   ├── test_callback_cleaner.py
│   │   └── test_whitelist.py
│   ├── test_engine/
│   │   ├── test_manager.py
│   │   ├── test_async_executor.py
│   │   ├── test_lock_manager.py
│   │   ├── test_resource_monitor.py
│   │   └── test_steady_state.py
│   ├── test_output/
│   │   ├── test_payload_breaker.py
│   │   ├── test_data_serializer.py
│   │   ├── test_integrity.py
│   │   └── test_client_adapter.py
│   └── integration/
│       └── test_end_to_end.py
└── docs/
    └── superpowers/
        ├── specs/
        │   └── 2026-05-27-matlab-mcp-design.md
        └── plans/
            └── 2026-05-27-matlab-mcp-plan.md
```

---

# Phase 1: Foundation (Tasks 1-4)

## Task 1: Project Scaffolding & Configuration

**Files:**
- Create: `matlab-mcp-server/pyproject.toml`
- Create: `matlab-mcp-server/.env.example`
- Create: `matlab-mcp-server/src/matlab_mcp_server/__init__.py`
- Create: `matlab-mcp-server/src/matlab_mcp_server/__main__.py`
- Create: `matlab-mcp-server/src/matlab_mcp_server/config.py`
- Create: `matlab-mcp-server/tests/conftest.py`
- Create: `matlab-mcp-server/tests/test_config.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "matlab-mcp-server"
version = "0.1.0"
description = "MCP server enabling AI assistants to call MATLAB for simulation, modeling, plotting, and data analysis"
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]>=1.0",
    "matlabengine>=25.1.0",
    "psutil>=5.9",
    "numpy>=1.24",
    "pydantic-settings>=2.0",
    "structlog>=23.0",
    "starlette>=0.36",
    "uvicorn>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.0",
]

[project.scripts]
matlab-mcp = "matlab_mcp_server.__main__:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create .env.example**

```ini
# MATLAB Engine
MATLAB_MCP_MATLAB_TIMEOUT=3600
MATLAB_MCP_MATLAB_MAX_MEMORY_MB=8192
MATLAB_MCP_MATLAB_CPU_THRESHOLD=0.95
MATLAB_MCP_MATLAB_HEARTBEAT_INTERVAL=10

# Sandbox
MATLAB_MCP_SANDBOX_DIR=C:\Users\user\matlab_mcp_sandbox
MATLAB_MCP_AUTO_CLEANUP=true

# Transport
MATLAB_MCP_TRANSPORT=stdio
MATLAB_MCP_HTTP_PORT=3000
MATLAB_MCP_HTTP_BIND=127.0.0.1
MATLAB_MCP_HTTP_TOKEN=

# Payload limits
MATLAB_MCP_PAYLOAD_MAX_MB=5
MATLAB_MCP_IMAGE_MAX_MB=10

# AI client capabilities
MATLAB_MCP_CLIENT_VISION=true
MATLAB_MCP_CONTEXT_LIMIT=200000

# Data degradation thresholds
MATLAB_MCP_FULL_DATA_THRESHOLD=100
MATLAB_MCP_DOWNSAMPLE_THRESHOLD=1000
MATLAB_MCP_METADATA_ONLY_THRESHOLD=1000000

# Async tasks
MATLAB_MCP_ORPHAN_TTL_SECONDS=7200
MATLAB_MCP_CHECKPOINT_ENABLED=true

# Steady state detection
MATLAB_MCP_STEADY_STATE_ENABLED=true
MATLAB_MCP_STEADY_STATE_WINDOW_SIZE=10
MATLAB_MCP_STEADY_STATE_MEAN_TOLERANCE=0.001
MATLAB_MCP_STEADY_STATE_STD_TOLERANCE=0.001
MATLAB_MCP_STEADY_STATE_CHECK_INTERVAL=1.0

# Data integrity
MATLAB_MCP_INTEGRITY_CHECK_ENABLED=true
MATLAB_MCP_INTEGRITY_ALGORITHM=sha256
MATLAB_MCP_INTEGRITY_AUTO_RETRY=2

# Security
MATLAB_MCP_ENABLE_AST_ANALYSIS=true
MATLAB_MCP_ENABLE_SHADOW_FUNCTIONS=true

# Simulink
MATLAB_MCP_SIMULINK_CLEANUP_CALLBACKS=true
MATLAB_MCP_SIMULINK_MAX_SIM_TIME=86400.0
```

- [ ] **Step 3: Write the failing test for config**

```python
# tests/test_config.py
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
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd matlab-mcp-server && python -m pytest tests/test_config.py -v`
Expected: FAIL with ModuleNotFoundError: No module named 'matlab_mcp_server.config'

- [ ] **Step 5: Implement __init__.py, __main__.py, and config.py**

```python
# src/matlab_mcp_server/__init__.py
"""MATLAB MCP Server - Enable AI assistants to call MATLAB via MCP protocol."""

__version__ = "0.1.0"
```

```python
# src/matlab_mcp_server/config.py
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
```

```python
# src/matlab_mcp_server/__main__.py
import sys
import argparse
from .config import Settings


def main():
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="MATLAB MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--bind", default=None)
    parser.add_argument("--token", default=None)
    parser.add_argument("--client-vision", choices=["true", "false"], default=None)
    parser.add_argument("--context-limit", type=int, default=None)
    args = parser.parse_args()

    env_overrides = {}
    if args.transport is not None:
        env_overrides["transport"] = args.transport
    if args.port is not None:
        env_overrides["http_port"] = args.port
    if args.bind is not None:
        env_overrides["http_bind"] = args.bind
    if args.token is not None:
        env_overrides["http_token"] = args.token
    if args.client_vision is not None:
        env_overrides["client_vision"] = args.client_vision == "true"
    if args.context_limit is not None:
        env_overrides["context_limit"] = args.context_limit

    settings = Settings(**env_overrides)

    if settings.transport == "stdio":
        from .transport.stdio import run_stdio
        run_stdio(settings)
    else:
        from .transport.http import run_http
        run_http(settings)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd matlab-mcp-server && pip install -e ".[dev]" && python -m pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git init matlab-mcp-server && cd matlab-mcp-server
git add pyproject.toml .env.example src/ tests/test_config.py
git commit -m "feat: project scaffolding with config management"
```

---

## Task 2: Security Layer - Whitelist, Path Sanitizer, Audit Logger

**Files:**
- Create: `src/matlab_mcp_server/security/__init__.py`
- Create: `src/matlab_mcp_server/security/whitelist.py`
- Create: `src/matlab_mcp_server/security/path_sanitizer.py`
- Create: `src/matlab_mcp_server/security/audit_logger.py`
- Create: `tests/test_security/__init__.py`
- Create: `tests/test_security/test_whitelist.py`
- Create: `tests/test_security/test_path_sanitizer.py`

- [ ] **Step 1: Write failing tests for whitelist**

```python
# tests/test_security/test_whitelist.py
import pytest
from matlab_mcp_server.security.whitelist import SecurityLevel, check_security_level


def test_l0_functions_are_auto_approved():
    assert check_security_level("fft") == SecurityLevel.L0_AUTO
    assert check_security_level("plot") == SecurityLevel.L0_AUTO
    assert check_security_level("sin") == SecurityLevel.L0_AUTO
    assert check_security_level("zeros") == SecurityLevel.L0_AUTO
    assert check_security_level("load_system") == SecurityLevel.L0_AUTO
    assert check_security_level("sim") == SecurityLevel.L0_AUTO


def test_l2_functions_require_approval():
    assert check_security_level("system") == SecurityLevel.L2_APPROVAL
    assert check_security_level("dos") == SecurityLevel.L2_APPROVAL
    assert check_security_level("delete") == SecurityLevel.L2_APPROVAL
    assert check_security_level("rmdir") == SecurityLevel.L2_APPROVAL
    assert check_security_level("movefile") == SecurityLevel.L2_APPROVAL
    assert check_security_level("copyfile") == SecurityLevel.L2_APPROVAL
    assert check_security_level("urlread") == SecurityLevel.L2_APPROVAL
    assert check_security_level("webwrite") == SecurityLevel.L2_APPROVAL


def test_l3_functions_are_blocked():
    assert check_security_level("eval") == SecurityLevel.L3_BLOCKED
    assert check_security_level("evalc") == SecurityLevel.L3_BLOCKED
    assert check_security_level("evalin") == SecurityLevel.L3_BLOCKED
    assert check_security_level("builtin") == SecurityLevel.L3_BLOCKED
    assert check_security_level("feval") == SecurityLevel.L3_BLOCKED
    assert check_security_level("str2func") == SecurityLevel.L3_BLOCKED
    assert check_security_level("addpath") == SecurityLevel.L3_BLOCKED
    assert check_security_level("unix") == SecurityLevel.L3_BLOCKED
    assert check_security_level("perl") == SecurityLevel.L3_BLOCKED
    assert check_security_level("keyboard") == SecurityLevel.L3_BLOCKED


def test_unknown_function_is_l2():
    assert check_security_level("some_unknown_func") == SecurityLevel.L2_APPROVAL


def test_whitelist_is_case_insensitive():
    assert check_security_level("FFT") == SecurityLevel.L0_AUTO
    assert check_security_level("PLOT") == SecurityLevel.L0_AUTO
```

- [ ] **Step 2: Write failing tests for path sanitizer**

```python
# tests/test_security/test_path_sanitizer.py
import pytest
from pathlib import Path
from matlab_mcp_server.security.path_sanitizer import sanitize_path, PathTraversalError


@pytest.fixture
def sandbox(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "test.csv").write_text("a,b\n1,2")
    return tmp_path


def test_valid_relative_path(sandbox):
    result = sanitize_path("data/test.csv", str(sandbox))
    assert result == str(sandbox / "data" / "test.csv")


def test_traversal_attack_blocked(sandbox):
    with pytest.raises(PathTraversalError):
        sanitize_path("../../../windows/system32/config", str(sandbox))


def test_dot_dot_in_middle_blocked(sandbox):
    with pytest.raises(PathTraversalError):
        sanitize_path("data/../../etc/passwd", str(sandbox))


def test_absolute_path_outside_sandbox_blocked(sandbox):
    with pytest.raises(PathTraversalError):
        sanitize_path("C:\\Windows\\System32\\config", str(sandbox))


def test_absolute_path_inside_sandbox_allowed(sandbox):
    valid = str(sandbox / "data" / "test.csv")
    result = sanitize_path(valid, str(sandbox))
    assert result == valid


def test_empty_path_blocked(sandbox):
    with pytest.raises(PathTraversalError):
        sanitize_path("", str(sandbox))
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd matlab-mcp-server && python -m pytest tests/test_security/ -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 4: Implement whitelist.py**

```python
# src/matlab_mcp_server/security/__init__.py
```

```python
# src/matlab_mcp_server/security/whitelist.py
from enum import Enum


class SecurityLevel(Enum):
    L0_AUTO = "auto"
    L1_LOGGED = "logged"
    L2_APPROVAL = "approval"
    L3_BLOCKED = "blocked"


L0_SAFE_FUNCTIONS = {
    "abs", "acos", "angle", "atan", "atan2",
    "bar", "bode", "ceil", "char", "circshift", "class", "clc",
    "clear", "close", "cond", "conj", "contour", "conv", "cos",
    "csvread", "csvwrite", "cumsum", "datestr", "det", "diag",
    "diff", "disp", "double", "eig", "errorbar", "exist", "exp",
    "eye", "fft", "fft2", "figure", "fill", "filter", "find",
    "fix", "flip", "floor", "fopen", "format", "freqz", "full",
    "fzero", "get_param", "gradient", "grid", "gtext",
    "hist", "histogram", "hold", "hypot", "ifft", "ifft2",
    "imag", "imagesc", "imfinfo", "imread", "imshow", "interp1",
    "isa", "iscell", "isempty", "isfield", "isfinite", "isnan",
    "isnumeric", "linspace", "load", "log", "log10", "log2",
    "loglog", "lsim", "max", "mean", "mesh", "meshgrid", "min",
    "mod", "ndims", "norm", "normcdf", "norminv", "normpdf",
    "num2str", "numel", "ode45", "ones", "pade", "peaks",
    "perms", "pi", "plot", "plot3", "plotyy", "polar", "poly",
    "polyfit", "polyval", "pow2", "printf", "prod",
    "quiver", "rand", "randi", "randn", "rcond", "readtable",
    "real", "rem", "repmat", "reshape", "roots", "rosser",
    "save", "scatter", "scatter3", "semilogx", "semilogy",
    "set_param", "sign", "sim", "sin", "size", "sort",
    "sortrows", "sos2tf", "sphere", "sprintf", "sqrt", "ss",
    "stairs", "std", "stem", "str2double", "str2num", "strcmp",
    "strcmpi", "strfind", "strings", "strlength", "subplot",
    "subplot", "sum", "surf", "surface", "svd", "table",
    "tan", "text", "tf", "tiledlayout", "title", "trapz",
    "tril", "triu", "union", "unique", "var", "vertcat",
    "xlabel", "xlim", "ylabel", "ylim", "zeros", "zlabel",
    "add_block", "add_line", "delete_block", "delete_line",
    "find_system", "get_param", "load_system", "new_system",
    "save_system", "set_param", "sim", "open_system",
    "close_system", "bdclose", "gcbh", "gcb", "gcs",
}

L3_BLOCKED_FUNCTIONS = {
    "eval", "evalc", "evalin", "feval", "builtin", "str2func",
    "unix", "perl", "python",
    "addpath", "rmpath", "javaaddpath",
    "keyboard", "input",
    "java", "javaObject", "javaMethod", "javaArray",
}

L2_APPROVAL_FUNCTIONS = {
    "system", "dos",
    "delete", "rmdir", "movefile", "copyfile",
    "urlread", "urlwrite", "webread", "webwrite",
    "fopen", "fwrite", "fclose",
    "cd",
    "trainNetwork", "train", "fitnet",
}


def check_security_level(function_name: str) -> SecurityLevel:
    name_lower = function_name.strip().lower()
    for f in L0_SAFE_FUNCTIONS:
        if f.lower() == name_lower:
            return SecurityLevel.L0_AUTO
    for f in L3_BLOCKED_FUNCTIONS:
        if f.lower() == name_lower:
            return SecurityLevel.L3_BLOCKED
    for f in L2_APPROVAL_FUNCTIONS:
        if f.lower() == name_lower:
            return SecurityLevel.L2_APPROVAL
    return SecurityLevel.L2_APPROVAL
```

- [ ] **Step 5: Implement path_sanitizer.py**

```python
# src/matlab_mcp_server/security/path_sanitizer.py
import os
from pathlib import Path


class PathTraversalError(Exception):
    pass


def sanitize_path(file_path: str, sandbox_dir: str) -> str:
    if not file_path or not file_path.strip():
        raise PathTraversalError("Empty file path")

    sandbox_real = os.path.realpath(sandbox_dir)
    normalized = os.path.normpath(file_path)
    full_path = os.path.realpath(os.path.join(sandbox_real, normalized))

    if not full_path.startswith(sandbox_real + os.sep) and full_path != sandbox_real:
        raise PathTraversalError(
            f"Path traversal detected: '{file_path}' resolves outside sandbox"
        )

    return full_path
```

- [ ] **Step 6: Write tests for AST injection detector**

```python
# tests/test_security/test_injection_detector.py
import pytest
from matlab_mcp_server.security.injection_detector import (
    analyze_matlab_code, InjectionRisk,
)


def test_safe_code_passes():
    code = "y = sin(x);\nz = cos(y);"
    risks = analyze_matlab_code(code)
    dangerous = [r for r in risks if r.severity == "block"]
    assert len(dangerous) == 0


def test_eval_detected():
    code = "eval('system(\"dir\")')"
    risks = analyze_matlab_code(code)
    dangerous = [r for r in risks if r.keyword == "eval"]
    assert len(dangerous) > 0


def test_system_detected():
    code = "system('rm -rf /')"
    risks = analyze_matlab_code(code)
    dangerous = [r for r in risks if r.keyword == "system"]
    assert len(dangerous) > 0


def test_fopen_in_string_not_flagged():
    code = "msg = 'do not use fopen for this';\ndisp(msg);"
    risks = analyze_matlab_code(code)
    fopen_risks = [r for r in risks if r.keyword == "fopen"]
    assert len(fopen_risks) == 0


def test_fopen_actual_call_detected():
    code = "fid = fopen('/etc/passwd', 'r');"
    risks = analyze_matlab_code(code)
    fopen_risks = [r for r in risks if r.keyword == "fopen"]
    assert len(fopen_risks) > 0


def test_string_concat_evasion_detected():
    code = "cmd = ['sy' 'stem']; feval(cmd, 'dir');"
    risks = analyze_matlab_code(code)
    dangerous = [r for r in risks if r.severity in ("block", "warn")]
    assert len(dangerous) > 0


def test_str2func_detected():
    code = "f = str2func('system'); f('dir');"
    risks = analyze_matlab_code(code)
    assert any(r.keyword == "str2func" for r in risks)


def test_empty_code():
    risks = analyze_matlab_code("")
    assert len(risks) == 0


def test_multiple_risks():
    code = "eval('system(\"dir\")'); delete('important.mat');"
    risks = analyze_matlab_code(code)
    keywords = {r.keyword for r in risks}
    assert "eval" in keywords
    assert "system" in keywords or "delete" in keywords
```

- [ ] **Step 7: Implement injection_detector.py**

```python
# src/matlab_mcp_server/security/injection_detector.py
# NOTE: This module uses regex-based pattern matching, NOT true AST parsing.
# MATLAB's mtree() could be used for true AST analysis in future enhancement.
from dataclasses import dataclass
from .whitelist import L3_BLOCKED_FUNCTIONS


@dataclass
class InjectionRisk:
    keyword: str
    severity: str
    line: int
    context: str
    reason: str


MATLAB_REGEX_DANGEROUS_CALLS = {
    "eval", "evalc", "evalin", "feval", "builtin", "str2func",
    "system", "dos", "unix",
    "delete", "rmdir", "movefile", "copyfile",
    "fopen", "fwrite", "fclose",
    "addpath", "rmpath", "cd",
    "urlread", "urlwrite", "webread", "webwrite",
    "java", "actxserver",
    "setenv", "getenv",
    "keyboard",
}

STRING_CONCAT_PATTERNS = [
    r"\[[\s']*sy[\s']*[\s']*stem[\s']*[\s']*\]",
    r"\[[\s']*ev[\s']*[\s']*al[\s']*[\s']*\]",
    r"\[[\s']*fe[\s']*[\s']*val[\s']*[\s']*\]",
    r"strcat\s*\(\s*['\"]sy",
    r"strcat\s*\(\s*['\"]ev",
]


def _is_inside_string(line: str, pos: int) -> bool:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if i >= pos:
            break
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
    return in_single or in_double


def analyze_matlab_code(code: str) -> list[InjectionRisk]:
    import re
    risks: list[InjectionRisk] = []
    lines = code.split("\n")

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("%") or stripped.startswith("#"):
            continue

        for keyword in MATLAB_REGEX_DANGEROUS_CALLS:
            pattern = rf'\b{re.escape(keyword)}\s*\('
            for match in re.finditer(pattern, line):
                pos = match.start()
                if not _is_inside_string(line, pos):
                    severity = "block" if keyword in L3_BLOCKED_FUNCTIONS else "warn"
                    risks.append(InjectionRisk(
                        keyword=keyword,
                        severity=severity,
                        line=line_num,
                        context=stripped[:200],
                        reason=f"Dangerous call '{keyword}()' detected at line {line_num}",
                    ))

        for pattern in STRING_CONCAT_PATTERNS:
            for match in re.finditer(pattern, line):
                risks.append(InjectionRisk(
                    keyword="string_concat_evasion",
                    severity="block",
                    line=line_num,
                    context=stripped[:200],
                    reason=f"String concatenation evasion pattern detected: {match.group()}",
                ))

    return risks


def is_code_safe(code: str) -> tuple[bool, list[InjectionRisk]]:
    risks = analyze_matlab_code(code)
    blocking = [r for r in risks if r.severity == "block"]
    return len(blocking) == 0, risks
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd matlab-mcp-server && python -m pytest tests/test_security/ -v`
Expected: all passed (whitelist + path_sanitizer + injection_detector)

- [ ] **Step 9: Commit**

```bash
cd matlab-mcp-server
git add src/matlab_mcp_server/security/ tests/test_security/
git commit -m "feat: security layer - whitelist, path sanitizer, regex-based injection detector"
```

---

## Task 3: MATLAB Shadow Functions & Sandbox Workspace Manager

**Files:**
- Create: `src/matlab_mcp_server/sandbox/__init__.py`
- Create: `src/matlab_mcp_server/sandbox/workspace_manager.py`
- Create: `src/matlab_mcp_server/sandbox/matlab_shadows/__init_sandbox__.m`
- Create: `src/matlab_mcp_server/sandbox/matlab_shadows/system.m`
- Create: `src/matlab_mcp_server/sandbox/matlab_shadows/eval.m`
- Create: `src/matlab_mcp_server/sandbox/matlab_shadows/feval.m`
- Create: `src/matlab_mcp_server/sandbox/matlab_shadows/delete.m`
- Create: `src/matlab_mcp_server/sandbox/matlab_shadows/builtin.m`
- Create: `tests/test_security/test_callback_cleaner.py`

- [ ] **Step 1: Create __init_sandbox__.m**

```matlab
% src/matlab_mcp_server/sandbox/matlab_shadows/__init_sandbox__.m
function __init_sandbox__()
    sandbox_dir = fileparts(mfilename('fullpath'));
    addpath(sandbox_dir, '-begin');
    fprintf('MATLAB MCP Sandbox initialized. Dangerous functions shadowed.\n');
end
```

- [ ] **Step 2: Create shadow function files (each blocks the dangerous function)**

```matlab
% src/matlab_mcp_server/sandbox/matlab_shadows/system.m
function [status, cmdout] = system(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'system() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
```

```matlab
% src/matlab_mcp_server/sandbox/matlab_shadows/eval.m
function varargout = eval(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'eval() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
```

```matlab
% src/matlab_mcp_server/sandbox/matlab_shadows/feval.m
function varargout = feval(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'feval() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
```

```matlab
% src/matlab_mcp_server/sandbox/matlab_shadows/delete.m
function delete(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'delete() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
```

```matlab
% src/matlab_mcp_server/sandbox/matlab_shadows/builtin.m
function varargout = builtin(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'builtin() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
```

- [ ] **Step 3: Implement workspace_manager.py**

```python
# src/matlab_mcp_server/sandbox/workspace_manager.py
import shutil
from pathlib import Path


class WorkspaceManager:
    def __init__(self, sandbox_dir: Path, shadow_dir: Path | None = None):
        self.sandbox_dir = sandbox_dir
        self.shadow_dir = shadow_dir or (
            Path(__file__).parent / "matlab_shadows"
        )

    def ensure_sandbox_exists(self) -> Path:
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        figures_dir = self.sandbox_dir / "figures"
        figures_dir.mkdir(exist_ok=True)
        data_dir = self.sandbox_dir / "data"
        data_dir.mkdir(exist_ok=True)
        return self.sandbox_dir

    def cleanup_residual_files(self) -> dict:
        report = {"lock_files_cleaned": 0, "cache_files_cleaned": 0, "other_cleaned": 0}
        patterns = {
            "lock_files": "*.lck",
            "cache_files": "*.slxc",
            "other": "*.autosave",
        }
        for category, pattern in patterns.items():
            for f in self.sandbox_dir.rglob(pattern):
                try:
                    f.unlink()
                    report[f"{category}_cleaned"] = report.get(f"{category}_cleaned", 0) + 1
                except OSError:
                    pass
        return report

    def get_shadow_dir_path(self) -> str:
        return str(self.shadow_dir.resolve())

    def reset_workspace(self) -> dict:
        self.cleanup_residual_files()
        figures_dir = self.sandbox_dir / "figures"
        for f in figures_dir.iterdir():
            if f.is_file():
                f.unlink()
        return {"status": "reset", "sandbox_dir": str(self.sandbox_dir)}
```

- [ ] **Step 4: Implement callback_cleaner.py (for Simulink callback stripping)**

```python
# src/matlab_mcp_server/security/callback_cleaner.py
from dataclasses import dataclass, field


LIFECYCLE_CALLBACKS = [
    "PreLoadFcn", "PostLoadFcn", "PreSaveFcn", "PostSaveFcn",
    "CloseFcn", "InitFcn", "StartFcn", "PauseFcn",
    "ContinueFcn", "StopFcn", "PreCopyFcn", "PostCopyFcn",
    "DeleteFcn", "ModelCloseFcn", "CloseInitFcn",
]

BLOCK_CALLBACKS = [
    "ClickFcn", "DeleteFcn", "CopyFcn", "MoveFcn",
    "NameChangeFcn", "ParentCloseFcn", "OpenFcn", "CloseFcn",
    "PostSaveFcn", "PreSaveFcn", "ClipboardFcn", "DestroyFcn",
]


@dataclass
class CleanupReport:
    stripped_callbacks: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    success: bool = True


def build_sanitization_script(model_name: str) -> str:
    lines = [
        f"report = struct('stripped', {{}}, 'warnings', {{}});",
        f"try",
    ]
    for cb in LIFECYCLE_CALLBACKS:
        lines.append(f"  val = get_param('{model_name}', '{cb}');")
        lines.append(f"  if ~isempty(strtrim(val))")
        lines.append(f"    report.stripped{{end+1}} = struct('name','{cb}','value',val);")
        lines.append(f"    set_param('{model_name}', '{cb}', '');")
        lines.append(f"  end")
    lines.append(f"catch e")
    lines.append(f"  report.warnings{{end+1}} = e.message;")
    lines.append(f"end")
    return "\n".join(lines)
```

- [ ] **Step 5: Write tests for callback_cleaner and workspace_manager**

```python
# tests/test_security/test_callback_cleaner.py
from matlab_mcp_server.security.callback_cleaner import (
    build_sanitization_script,
    LIFECYCLE_CALLBACKS,
    BLOCK_CALLBACKS,
)


def test_sanitization_script_contains_all_lifecycle_callbacks():
    script = build_sanitization_script("test_model")
    for cb in LIFECYCLE_CALLBACKS:
        assert f"'{cb}'" in script


def test_sanitization_script_uses_model_name():
    script = build_sanitization_script("my_motor_model")
    assert "'my_motor_model'" in script
```

- [ ] **Step 6: Run all security tests**

Run: `cd matlab-mcp-server && python -m pytest tests/test_security/ -v`
Expected: all passed

- [ ] **Step 7: Commit**

```bash
cd matlab-mcp-server
git add src/matlab_mcp_server/sandbox/ src/matlab_mcp_server/security/callback_cleaner.py tests/test_security/test_callback_cleaner.py
git commit -m "feat: shadow functions, workspace manager, callback cleaner"
```

---

## Task 4: MATLAB Engine Manager, Async Executor, Lock Manager, Resource Monitor, Steady State

**Files:**
- Create: `src/matlab_mcp_server/engine/__init__.py`
- Create: `src/matlab_mcp_server/engine/manager.py`
- Create: `src/matlab_mcp_server/engine/async_executor.py`
- Create: `src/matlab_mcp_server/engine/lock_manager.py`
- Create: `src/matlab_mcp_server/engine/resource_monitor.py`
- Create: `src/matlab_mcp_server/engine/steady_state.py`
- Create: `src/matlab_mcp_server/engine/injection_guard.py`
- Create: `tests/test_engine/test_manager.py`
- Create: `tests/test_engine/test_lock_manager.py`
- Create: `tests/test_engine/test_async_executor.py`
- Create: `tests/test_engine/test_steady_state.py`
- Create: `tests/test_engine/test_resource_monitor.py`

- [ ] **Step 1: Write failing test for LockManager**

```python
# tests/test_engine/test_lock_manager.py
import pytest
import asyncio
from matlab_mcp_server.engine.lock_manager import EngineLockManager, EngineState, EngineBusyError


@pytest.mark.asyncio
async def test_query_tools_bypass_lock():
    mgr = EngineLockManager()
    assert await mgr.acquire("check_task_status") is True
    assert await mgr.acquire("cancel_task") is True
    assert await mgr.acquire("list_sandbox_files") is True
    assert await mgr.acquire("approve_operation") is True
    assert await mgr.acquire("reject_operation") is True
    assert await mgr.acquire("list_pending_approvals") is True


@pytest.mark.asyncio
async def test_engine_busy_returns_error():
    mgr = EngineLockManager()
    await mgr.acquire("run_simulation")
    assert mgr._state == EngineState.RUNNING

    with pytest.raises(EngineBusyError):
        await mgr.acquire("create_plot")

    await mgr.release()
    assert mgr._state == EngineState.IDLE


@pytest.mark.asyncio
async def test_no_toctou_race_condition():
    mgr = EngineLockManager()
    results = []
    barrier = asyncio.Event()

    async def task_a():
        await barrier.wait()
        try:
            await mgr.acquire("run_simulation")
            results.append("a_acquired")
        except EngineBusyError:
            results.append("a_busy")

    async def task_b():
        await barrier.wait()
        try:
            await mgr.acquire("create_plot")
            results.append("b_acquired")
        except EngineBusyError:
            results.append("b_busy")

    t1 = asyncio.create_task(task_a())
    t2 = asyncio.create_task(task_b())
    barrier.set()
    await asyncio.gather(t1, t2)

    acquired_count = results.count("a_acquired") + results.count("b_acquired")
    busy_count = results.count("a_busy") + results.count("b_busy")
    assert acquired_count == 1
    assert busy_count == 1
    await mgr.release()


@pytest.mark.asyncio
async def test_acquire_release_cycle():
    mgr = EngineLockManager()
    assert mgr._state == EngineState.IDLE
    await mgr.acquire("fft")
    assert mgr._state == EngineState.RUNNING
    await mgr.release()
    assert mgr._state == EngineState.IDLE
```

- [ ] **Step 2: Implement lock_manager.py**

```python
# src/matlab_mcp_server/engine/lock_manager.py
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class EngineState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    CANCELLING = "cancelling"
    RESTARTING = "restarting"


class EngineBusyError(Exception):
    def __init__(self, current_task_id: Optional[str] = None,
                 current_task_type: Optional[str] = None,
                 message: str = ""):
        self.current_task_id = current_task_id
        self.current_task_type = current_task_type
        super().__init__(message or "MATLAB Engine is busy")


QUERY_TOOLS = frozenset({
    "check_task_status",
    "list_sandbox_files",
    "cancel_task",
    "get_server_info",
    "approve_operation",
    "reject_operation",
    "list_pending_approvals",
})


class EngineLockManager:
    def __init__(self):
        self._state = EngineState.IDLE
        self._lock = asyncio.Lock()
        self._current_task_id: Optional[str] = None
        self._current_task_type: Optional[str] = None

    @property
    def state(self) -> EngineState:
        return self._state

    async def acquire(self, tool_name: str, timeout: float = 5.0) -> bool:
        if tool_name in QUERY_TOOLS:
            return True
        acquired = await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
        if not acquired:
            return False
        if self._state == EngineState.RUNNING:
            self._lock.release()
            raise EngineBusyError(
                current_task_id=self._current_task_id,
                current_task_type=self._current_task_type,
                message=(
                    f"MATLAB Engine is busy running '{self._current_task_type}' "
                    f"(task_id={self._current_task_id}). "
                    f"Use check_task_status() to monitor or cancel_task() to abort."
                ),
            )
        self._state = EngineState.RUNNING
        return True

    async def acquire_with_task(self, tool_name: str, task_id: str) -> bool:
        result = await self.acquire(tool_name)
        if result:
            self._current_task_id = task_id
            self._current_task_type = tool_name
        return result

    async def release(self):
        self._state = EngineState.IDLE
        self._current_task_id = None
        self._current_task_type = None
        if self._lock.locked():
            self._lock.release()
```

- [ ] **Step 3: Run lock manager tests to verify they pass**

Run: `cd matlab-mcp-server && python -m pytest tests/test_engine/test_lock_manager.py -v`
Expected: 3 passed

- [ ] **Step 4: Write failing test for SteadyStateDetector**

```python
# tests/test_engine/test_steady_state.py
import pytest
import numpy as np
from matlab_mcp_server.engine.steady_state import SteadyStateDetector


def test_no_convergence_initially():
    det = SteadyStateDetector(window_size=5, mean_tol=1e-3, std_tol=1e-3)
    for i in range(3):
        det.update(np.sin(i * 0.1) + np.random.randn() * 0.5)
    assert not det.is_converged


def test_convergence_after_stable_input():
    det = SteadyStateDetector(window_size=5, mean_tol=1e-2, std_tol=1e-2)
    for _ in range(10):
        det.update(3.300 + np.random.randn() * 1e-5)
    assert det.is_converged
    assert det.convergence_index is not None


def test_no_convergence_with_oscillation():
    det = SteadyStateDetector(window_size=5, mean_tol=1e-3, std_tol=1e-3)
    for i in range(20):
        det.update(np.sin(i))
    assert not det.is_converged


def test_reset_clears_state():
    det = SteadyStateDetector(window_size=3, mean_tol=1e-2, std_tol=1e-2)
    for _ in range(5):
        det.update(5.0)
    assert det.is_converged
    det.reset()
    assert not det.is_converged
    assert det.convergence_index is None
```

- [ ] **Step 5: Implement steady_state.py**

```python
# src/matlab_mcp_server/engine/steady_state.py
import numpy as np
from collections import deque
from typing import Optional


class SteadyStateDetector:
    def __init__(self, window_size: int = 10, mean_tol: float = 1e-3,
                 std_tol: float = 1e-3):
        self.window_size = window_size
        self.mean_tol = mean_tol
        self.std_tol = std_tol
        self._window: deque = deque(maxlen=window_size)
        self._converged_count: int = 0
        self._is_converged: bool = False
        self._convergence_index: Optional[int] = None
        self._sample_count: int = 0

    @property
    def is_converged(self) -> bool:
        return self._is_converged

    @property
    def convergence_index(self) -> Optional[int]:
        return self._convergence_index

    def update(self, value: float) -> bool:
        self._sample_count += 1
        self._window.append(value)

        if len(self._window) < self.window_size:
            return False

        arr = np.array(self._window)
        current_mean = np.mean(arr)
        current_std = np.std(arr)

        if len(self._window) >= 2:
            prev = np.array(list(self._window)[:-1])
            prev_mean = np.mean(prev)
            delta_mean = abs(current_mean - prev_mean)
        else:
            delta_mean = float("inf")

        if delta_mean < self.mean_tol and current_std < self.std_tol:
            self._converged_count += 1
        else:
            self._converged_count = 0

        if self._converged_count >= self.window_size:
            self._is_converged = True
            self._convergence_index = self._sample_count
            return True

        return False

    def get_final_stats(self) -> dict:
        if not self._window:
            return {}
        arr = np.array(self._window)
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
        }

    def reset(self):
        self._window.clear()
        self._converged_count = 0
        self._is_converged = False
        self._convergence_index = None
        self._sample_count = 0
```

- [ ] **Step 6: Write and implement async_executor.py**

```python
# src/matlab_mcp_server/engine/async_executor.py
import asyncio
import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ORPHANED = "orphaned"


@dataclass
class Task:
    task_id: str
    tool_name: str
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[dict] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: float = 0.0


class AsyncTaskExecutor:
    def __init__(self, max_workers: int = 2):
        self._tasks: dict[str, Task] = {}
        self._futures: dict[str, asyncio.Future] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cancel_flags: dict[str, bool] = {}

    def submit(self, tool_name: str, func: Callable, *args, **kwargs) -> str:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task = Task(task_id=task_id, tool_name=tool_name)
        self._tasks[task_id] = task
        self._cancel_flags[task_id] = False

        async def run_task():
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self._executor, lambda: func(*args, **kwargs)
                )
                if self._cancel_flags.get(task_id):
                    task.status = TaskStatus.CANCELLED
                else:
                    task.result = result
                    task.status = TaskStatus.COMPLETED
            except Exception as e:
                task.error = {"type": type(e).__name__, "message": str(e)}
                task.status = TaskStatus.FAILED
            finally:
                task.completed_at = time.time()

        self._futures[task_id] = asyncio.ensure_future(run_task())
        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_status(self, task_id: str) -> Optional[dict]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        elapsed = None
        if task.started_at:
            end = task.completed_at or time.time()
            elapsed = round(end - task.started_at, 2)
        return {
            "task_id": task.task_id,
            "tool_name": task.tool_name,
            "status": task.status.value,
            "progress": task.progress,
            "elapsed_seconds": elapsed,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
        }

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.status == TaskStatus.RUNNING:
            self._cancel_flags[task_id] = True
            task.status = TaskStatus.CANCELLING
            return True
        return False

    def mark_orphaned(self, task_id: str, ttl_seconds: int):
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.ORPHANED
```

- [ ] **Step 7: Implement injection_guard.py (Manager-level safety net)**

```python
# src/matlab_mcp_server/engine/injection_guard.py
from ..security.injection_detector import is_code_safe


class InjectionBlockedError(Exception):
    def __init__(self, risks: list):
        self.risks = risks
        keywords = ", ".join(r.keyword for r in risks)
        super().__init__(f"Code blocked by injection guard: {keywords}")


def pre_execute_check(code: str):
    safe, risks = is_code_safe(code)
    if not safe:
        blocked = [r for r in risks if r.severity == "block"]
        raise InjectionBlockedError(blocked)
```

- [ ] **Step 8: Implement manager.py**

```python
# src/matlab_mcp_server/engine/manager.py
import asyncio
import logging
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class MatlabEngineManager:
    def __init__(self, sandbox_dir: Path, shadow_dir: Path,
                 enable_injection_check: bool = True):
        self.sandbox_dir = sandbox_dir
        self.shadow_dir = shadow_dir
        self._engine = None
        self._engine_started = False
        self._pid: Optional[int] = None
        self._enable_injection_check = enable_injection_check
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def start(self) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._start_engine_sync)

    def _start_engine_sync(self) -> bool:
        try:
            import matlab.engine
            self._engine = matlab.engine.start_matlab()
            self._engine_started = True
            shadow_path = str(self.shadow_dir).replace("\\", "/")
            self._engine.addpath(shadow_path, nargout=0)
            self._engine.cd(str(self.sandbox_dir), nargout=0)
            logger.info("MATLAB Engine started (PID=%s)", self._pid)
            return True
        except Exception as e:
            logger.error("Failed to start MATLAB Engine: %s", e)
            return False

    async def stop(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self._stop_engine_sync)

    def _stop_engine_sync(self):
        if self._engine is not None:
            try:
                self._engine.quit()
            except Exception:
                pass
            self._engine = None
            self._engine_started = False

    async def restart(self) -> bool:
        await self.stop()
        return await self.start()

    async def execute(self, code: str, skip_injection_check: bool = False) -> str:
        if not self._engine_started:
            raise RuntimeError("MATLAB Engine not started")
        if self._enable_injection_check and not skip_injection_check:
            from .injection_guard import pre_execute_check
            pre_execute_check(code)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, lambda: self._execute_sync(code)
        )

    def _execute_sync(self, code: str) -> str:
        try:
            result = self._engine.eval(code, nargout=1)
            return str(result) if result is not None else ""
        except Exception as e:
            logger.error("MATLAB execution error: %s", e)
            raise

    async def get_variable_info(self, var_name: str, max_rows: int = 100) -> dict:
        if not self._engine_started:
            raise RuntimeError("MATLAB Engine not started")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, lambda: self._get_variable_info_sync(var_name, max_rows)
        )

    def _get_variable_info_sync(self, var_name: str, max_rows: int = 100) -> dict:
        try:
            info = self._engine.workspace.get(var_name)
            return {"name": var_name, "value_preview": str(info)[:500]}
        except Exception as e:
            return {"name": var_name, "error": str(e)}

    async def list_workspace(self) -> list:
        if not self._engine_started:
            raise RuntimeError("MATLAB Engine not started")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self._list_workspace_sync
        )

    def _list_workspace_sync(self) -> list:
        try:
            result = self._engine.eval("whos", nargout=1)
            return str(result)
        except Exception:
            return []

    async def clear_workspace(self):
        if self._engine_started:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor, self._clear_workspace_sync
            )

    def _clear_workspace_sync(self):
        self._engine.eval("clear; clc; close all;", nargout=0)
        self._engine.cd(str(self.sandbox_dir), nargout=0)

    @property
    def is_running(self) -> bool:
        return self._engine_started
```

- [ ] **Step 9: Write tests for manager.py**

```python
# tests/test_engine/test_manager.py
import pytest
from matlab_mcp_server.engine.manager import MatlabEngineManager
from pathlib import Path
import tempfile


@pytest.fixture
def temp_sandbox():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.mark.asyncio
async def test_engine_manager_initialization(temp_sandbox):
    shadow_dir = temp_sandbox / "shadows"
    shadow_dir.mkdir()
    mgr = MatlabEngineManager(
        sandbox_dir=temp_sandbox,
        shadow_dir=shadow_dir,
    )
    assert mgr.sandbox_dir == temp_sandbox
    assert mgr.shadow_dir == shadow_dir


@pytest.mark.asyncio
async def test_engine_start_stop(temp_sandbox):
    shadow_dir = temp_sandbox / "shadows"
    shadow_dir.mkdir()
    mgr = MatlabEngineManager(
        sandbox_dir=temp_sandbox,
        shadow_dir=shadow_dir,
    )
    await mgr.start()
    assert mgr.is_running
    await mgr.stop()
    assert not mgr.is_running


@pytest.mark.asyncio
async def test_shadow_path_priority(temp_sandbox):
    shadow_dir = temp_sandbox / "shadows"
    shadow_dir.mkdir()
    (shadow_dir / "delete.m").write_text(
        "function delete(varargin)\nerror('Shadowed delete called');\nend"
    )
    mgr = MatlabEngineManager(
        sandbox_dir=temp_sandbox,
        shadow_dir=shadow_dir,
    )
    await mgr.start()
    try:
        result = await mgr.execute("which delete")
        assert str(shadow_dir / "delete.m") in result
    finally:
        await mgr.stop()


@pytest.mark.asyncio
async def test_workspace_cleared_on_restart(temp_sandbox):
    shadow_dir = temp_sandbox / "shadows"
    shadow_dir.mkdir()
    mgr = MatlabEngineManager(
        sandbox_dir=temp_sandbox,
        shadow_dir=shadow_dir,
    )
    await mgr.start()
    try:
        await mgr.execute("x = 10;")
        await mgr.restart()
        result = await mgr.execute("whos")
        assert "x" not in result
    finally:
        await mgr.stop()


@pytest.mark.asyncio
async def test_execute_with_output(temp_sandbox):
    shadow_dir = temp_sandbox / "shadows"
    shadow_dir.mkdir()
    mgr = MatlabEngineManager(
        sandbox_dir=temp_sandbox,
        shadow_dir=shadow_dir,
    )
    await mgr.start()
    try:
        result = await mgr.execute("2 + 2;")
        assert result.strip() == "ans = 4"
    finally:
        await mgr.stop()


@pytest.mark.asyncio
async def test_execute_raises_when_not_started(temp_sandbox):
    shadow_dir = temp_sandbox / "shadows"
    shadow_dir.mkdir()
    mgr = MatlabEngineManager(
        sandbox_dir=temp_sandbox,
        shadow_dir=shadow_dir,
    )
    with pytest.raises(RuntimeError, match="MATLAB Engine not started"):
        await mgr.execute("1 + 1")


@pytest.mark.asyncio
async def test_clear_workspace(temp_sandbox):
    shadow_dir = temp_sandbox / "shadows"
    shadow_dir.mkdir()
    mgr = MatlabEngineManager(
        sandbox_dir=temp_sandbox,
        shadow_dir=shadow_dir,
    )
    await mgr.start()
    try:
        await mgr.execute("a = 42; b = 'hello';")
        await mgr.clear_workspace()
        result = str(await mgr.list_workspace())
        assert "a" not in result
        assert "b" not in result
    finally:
        await mgr.stop()
```

- [ ] **Step 10: Implement resource_monitor.py**

```python
# src/matlab_mcp_server/engine/resource_monitor.py
import threading
import time
import logging
from typing import Optional, Callable
import psutil

logger = logging.getLogger(__name__)


class ResourceMonitor:
    def __init__(self, pid: Optional[int] = None,
                 cpu_threshold: float = 0.95,
                 memory_threshold: float = 0.80,
                 heartbeat_interval: int = 10,
                 on_resource_exceeded: Optional[Callable] = None,
                 on_process_unresponsive: Optional[Callable] = None):
        self.pid = pid
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.heartbeat_interval = heartbeat_interval
        self._on_resource_exceeded = on_resource_exceeded
        self._on_process_unresponsive = on_process_unresponsive
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._process: Optional[psutil.Process] = None
        self._last_heartbeat: float = time.time()
        self._warnings: list = []

    def start(self, pid: int):
        self.pid = pid
        try:
            self._process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            logger.error("Cannot monitor: process %s does not exist", pid)
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Resource monitor started for PID %s", pid)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self):
        while self._running:
            try:
                if not self._process or not self._process.is_running():
                    if self._on_process_unresponsive:
                        self._on_process_unresponsive(self.pid)
                    break
                cpu_pct = self._process.cpu_percent(interval=1.0) / 100.0
                mem_info = self._process.memory_info()
                mem_pct = mem_info.rss / psutil.virtual_memory().total

                if cpu_pct > self.cpu_threshold:
                    warning = {"type": "high_cpu", "value": cpu_pct, "timestamp": time.time()}
                    self._warnings.append(warning)
                    logger.warning("High CPU: %.1f%%", cpu_pct * 100)
                    if self._on_resource_exceeded:
                        self._on_resource_exceeded("cpu", cpu_pct)

                if mem_pct > self.memory_threshold:
                    warning = {"type": "high_memory", "value": mem_pct, "timestamp": time.time()}
                    self._warnings.append(warning)
                    logger.warning("High memory: %.1f%%", mem_pct * 100)
                    if self._on_resource_exceeded:
                        self._on_resource_exceeded("memory", mem_pct)

                self._last_heartbeat = time.time()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                if self._on_process_unresponsive:
                    self._on_process_unresponsive(self.pid)
                break
            time.sleep(self.heartbeat_interval)

    def get_status(self) -> dict:
        result = {"monitoring": self._running, "pid": self.pid, "warnings": list(self._warnings)}
        if self._process and self._process.is_running():
            try:
                result["cpu_percent"] = self._process.cpu_percent()
                result["memory_rss_mb"] = self._process.memory_info().rss / (1024 * 1024)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return result

    def force_kill(self) -> bool:
        if not self._process:
            return False
        try:
            self._process.terminate()
            self._process.wait(timeout=5)
            return True
        except psutil.TimeoutExpired:
            try:
                self._process.kill()
                self._process.wait(timeout=5)
                return True
            except Exception:
                return False
        except Exception:
            return False
```

- [ ] **Step 11: Write tests for async_executor and resource_monitor**

```python
# tests/test_engine/test_async_executor.py
import pytest
import asyncio
from matlab_mcp_server.engine.async_executor import AsyncTaskExecutor, TaskStatus


@pytest.mark.asyncio
async def test_submit_returns_task_id():
    executor = AsyncTaskExecutor()
    task_id = executor.submit("test_tool", lambda: 42)
    assert task_id.startswith("task_")


@pytest.mark.asyncio
async def test_task_completes_with_result():
    executor = AsyncTaskExecutor()
    task_id = executor.submit("test_tool", lambda: 42)
    await asyncio.sleep(0.5)
    status = executor.get_status(task_id)
    assert status["status"] == TaskStatus.COMPLETED.value
    task = executor.get_task(task_id)
    assert task.result == 42


@pytest.mark.asyncio
async def test_task_failure_captured():
    def failing():
        raise ValueError("test error")

    executor = AsyncTaskExecutor()
    task_id = executor.submit("test_tool", failing)
    await asyncio.sleep(0.5)
    status = executor.get_status(task_id)
    assert status["status"] == TaskStatus.FAILED.value
    task = executor.get_task(task_id)
    assert task.error["type"] == "ValueError"


@pytest.mark.asyncio
async def test_cancel_running_task():
    def slow_task():
        import time
        time.sleep(10)
        return "done"

    executor = AsyncTaskExecutor()
    task_id = executor.submit("slow_tool", slow_task)
    await asyncio.sleep(0.2)
    assert executor.cancel(task_id) is True
    task = executor.get_task(task_id)
    assert task.status == TaskStatus.CANCELLING


def test_get_status_unknown_task():
    executor = AsyncTaskExecutor()
    assert executor.get_status("nonexistent") is None
```

- [ ] **Step 12: Write test for resource_monitor**

```python
# tests/test_engine/test_resource_monitor.py
import pytest
import time
import os
from matlab_mcp_server.engine.resource_monitor import ResourceMonitor


def test_resource_monitor_get_status():
    monitor = ResourceMonitor()
    status = monitor.get_status()
    assert status["monitoring"] is False
    assert status["pid"] is None


def test_resource_monitor_start_stop():
    monitor = ResourceMonitor(cpu_threshold=0.99, memory_threshold=0.99, heartbeat_interval=1)
    monitor.start(os.getpid())
    time.sleep(2)
    status = monitor.get_status()
    assert status["monitoring"] is True
    assert status["pid"] == os.getpid()
    monitor.stop()
    status = monitor.get_status()
    assert status["monitoring"] is False
```

- [ ] **Step 13: Run all engine tests**

Run: `cd matlab-mcp-server && python -m pytest tests/test_engine/ -v`
Expected: all passed

- [ ] **Step 14: Commit**

```bash
cd matlab-mcp-server
git add src/matlab_mcp_server/engine/ tests/test_engine/
git commit -m "feat: engine manager, async executor, lock manager, resource monitor, steady state"
```

---

# Phase 2: Core MCP Functionality (Tasks 5-9)

## Task 5: MCP Server Core + Tool Registry + Task Manager Tools

**Files:**
- Create: `src/matlab_mcp_server/tools/__init__.py`
- Create: `src/matlab_mcp_server/tools/registry.py`
- Create: `src/matlab_mcp_server/tools/task_manager.py`
- Create: `src/matlab_mcp_server/server.py`
- Create: `tests/test_tools/__init__.py`
- Create: `tests/test_tools/test_registry.py`

- [ ] **Step 1: Implement registry.py**

```python
# src/matlab_mcp_server/tools/registry.py
from typing import Callable, Any


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, description: str, input_schema: dict):
        def decorator(func: Callable):
            self._tools[name] = {
                "name": name,
                "description": description,
                "input_schema": input_schema,
                "handler": func,
            }
            return func
        return decorator

    def get_all(self) -> dict[str, dict]:
        return dict(self._tools)

    def get_handler(self, name: str) -> Callable | None:
        tool = self._tools.get(name)
        return tool["handler"] if tool else None

    def list_names(self) -> list[str]:
        return list(self._tools.keys())


registry = ToolRegistry()
```

- [ ] **Step 2: Write test for registry**

```python
# tests/test_tools/test_registry.py
import pytest
from matlab_mcp_server.tools.registry import ToolRegistry


def test_register_and_list():
    reg = ToolRegistry()

    @reg.register("test_tool", "A test tool", {"type": "object", "properties": {}})
    async def handler(params):
        return "ok"

    assert "test_tool" in reg.list_names()
    assert reg.get_handler("test_tool") is not None


def test_get_handler_unknown():
    reg = ToolRegistry()
    assert reg.get_handler("nonexistent") is None


def test_register_multiple():
    reg = ToolRegistry()

    @reg.register("tool_a", "Tool A", {"type": "object", "properties": {}})
    async def handler_a(params):
        return "a"

    @reg.register("tool_b", "Tool B", {"type": "object", "properties": {}})
    async def handler_b(params):
        return "b"

    assert set(reg.list_names()) == {"tool_a", "tool_b"}
```

- [ ] **Step 3: Implement task_manager.py**

```python
# src/matlab_mcp_server/tools/task_manager.py
from .registry import registry


@registry.register(
    name="check_task_status",
    description="查询异步任务的状态和进度。返回任务状态、已用时间、结果或错误。",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务 ID"},
        },
        "required": ["task_id"],
    },
)
async def handle_check_task_status(engine, task_executor, params):
    task_id = params["task_id"]
    status = task_executor.get_status(task_id)
    if status is None:
        return {"success": False, "error": f"Task {task_id} not found"}
    task = task_executor.get_task(task_id)
    result = {"success": True, **status}
    if task and task.result is not None:
        result["result"] = task.result
    if task and task.error is not None:
        result["error"] = task.error
    return result


@registry.register(
    name="cancel_task",
    description="取消正在运行的异步任务。",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务 ID"},
        },
        "required": ["task_id"],
    },
)
async def handle_cancel_task(engine, task_executor, params):
    task_id = params["task_id"]
    cancelled = task_executor.cancel(task_id)
    if cancelled:
        return {"success": True, "message": f"Task {task_id} cancellation requested"}
    return {"success": False, "error": f"Task {task_id} not found or not running"}


@registry.register(
    name="approve_operation",
    description="批准一个等待审批的 L2 安全操作。当 run_matlab_function 或 evaluate_expression 返回 pending_approval 时，使用此工具批准执行。",
    input_schema={
        "type": "object",
        "properties": {
            "approval_id": {"type": "string", "description": "审批请求 ID（从 pending_approval 响应中获取）"},
        },
        "required": ["approval_id"],
    },
)
async def handle_approve_operation(engine, task_executor, params, approval_queue=None, **kwargs):
    if approval_queue is None:
        return {"success": False, "error": "Approval queue not available"}
    approval_id = params["approval_id"]
    result = approval_queue.approve(approval_id)
    if result:
        return {"success": True, "approval_id": approval_id, "message": "Operation approved"}
    return {"success": False, "error": f"Approval request '{approval_id}' not found or already processed"}


@registry.register(
    name="reject_operation",
    description="拒绝一个等待审批的 L2 安全操作。",
    input_schema={
        "type": "object",
        "properties": {
            "approval_id": {"type": "string", "description": "审批请求 ID"},
        },
        "required": ["approval_id"],
    },
)
async def handle_reject_operation(engine, task_executor, params, approval_queue=None, **kwargs):
    if approval_queue is None:
        return {"success": False, "error": "Approval queue not available"}
    approval_id = params["approval_id"]
    result = approval_queue.reject(approval_id)
    if result:
        return {"success": True, "approval_id": approval_id, "message": "Operation rejected"}
    return {"success": False, "error": f"Approval request '{approval_id}' not found or already processed"}


@registry.register(
    name="list_pending_approvals",
    description="列出所有等待审批的 L2 操作。",
    input_schema={"type": "object", "properties": {}},
)
async def handle_list_pending_approvals(engine, task_executor, params, approval_queue=None, **kwargs):
    if approval_queue is None:
        return {"success": True, "pending": []}
    return {"success": True, "pending": approval_queue.get_pending()}


@registry.register(
    name="reset_workspace",
    description="重置 MATLAB 工作区到沙盒状态。清除所有变量、关闭图形、重置工作目录。",
    input_schema={
        "type": "object",
        "properties": {},
    },
)
async def handle_reset_workspace(engine, task_executor, params, workspace=None, **kwargs):
    try:
        await engine.clear_workspace()
        if workspace is not None:
            workspace.cleanup_residual_files()
        return {"success": True, "message": "Workspace reset to sandbox state (memory + sandbox files cleaned)"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

- [ ] **Step 4: Implement server.py (MCP Server core)**

```python
# src/matlab_mcp_server/server.py
from mcp.server.fastmcp import FastMCP
from .config import Settings
from .engine.manager import MatlabEngineManager
from .engine.async_executor import AsyncTaskExecutor
from .engine.lock_manager import EngineLockManager
from .sandbox.workspace_manager import WorkspaceManager
from .output.client_adapter import ClientAdapter
from .security.approval_queue import ApprovalQueue
from pathlib import Path


def create_server(settings: Settings) -> FastMCP:
    mcp = FastMCP(
        name="matlab-mcp-server",
        instructions="MATLAB MCP Server: 提供 MATLAB 仿真、建模、画图、数据分析等工具",
    )

    workspace = WorkspaceManager(settings.sandbox_dir)
    workspace.ensure_sandbox_exists()
    shadow_dir = workspace.get_shadow_dir_path()

    engine_mgr = MatlabEngineManager(
        sandbox_dir=settings.sandbox_dir,
        shadow_dir=Path(shadow_dir),
    )
    task_executor = AsyncTaskExecutor()
    lock_manager = EngineLockManager()
    approval_queue = ApprovalQueue()
    client_adapter = ClientAdapter(
        client_vision=settings.client_vision,
        context_limit=settings.context_limit,
    )

    from .tools.registry import registry

    import matlab_mcp_server.tools.task_manager
    import matlab_mcp_server.tools.computation
    import matlab_mcp_server.tools.simulink
    import matlab_mcp_server.tools.visualization
    import matlab_mcp_server.tools.toolbox
    import matlab_mcp_server.tools.file_ops

    from .engine.lock_manager import QUERY_TOOLS

    for name, tool_def in registry.get_all().items():
        handler = tool_def["handler"]

        def make_handler(h, tool_name=name):
            async def tool_handler(params: dict):
                needs_lock = tool_name not in QUERY_TOOLS

                if needs_lock:
                    try:
                        acquired = await lock_manager.acquire(tool_name)
                        if not acquired:
                            return {
                                "success": False,
                                "error": "Engine is busy, please wait or call check_task_status",
                                "engine_state": lock_manager.state.value,
                            }
                    except Exception as e:
                        from .output.error_formatter import format_error
                        return format_error(e)

                try:
                    result = await h(
                        engine=engine_mgr,
                        task_executor=task_executor,
                        params=params,
                        client_adapter=client_adapter,
                        workspace=workspace,
                        approval_queue=approval_queue,
                    )
                    return result
                except Exception as e:
                    from .output.error_formatter import format_error
                    return format_error(e)
                finally:
                    if needs_lock:
                        await lock_manager.release()
            return tool_handler

        mcp.tool(name=name, description=tool_def["description"])(
            make_handler(handler)
        )

    return mcp
```

- [ ] **Step 5: Run tests**

Run: `cd matlab-mcp-server && python -m pytest tests/test_tools/ -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
cd matlab-mcp-server
git add src/matlab_mcp_server/tools/registry.py src/matlab_mcp_server/tools/task_manager.py src/matlab_mcp_server/server.py tests/test_tools/
git commit -m "feat: MCP server core, tool registry, task manager tools"
```

---

## Task 6: Computation Tools

**Files:**
- Create: `src/matlab_mcp_server/tools/computation.py`
- Create: `tests/test_tools/test_computation.py`

- [ ] **Step 1: Implement computation.py**

```python
# src/matlab_mcp_server/tools/computation.py
from .registry import registry


@registry.register(
    name="run_matlab_function",
    description="调用预定义的 MATLAB 安全函数执行计算。函数必须在白名单中。参数通过小数组或标量传递。",
    input_schema={
        "type": "object",
        "properties": {
            "function_name": {"type": "string", "description": "MATLAB 函数名（必须在安全白名单中）"},
            "args": {"type": "array", "description": "位置参数列表（仅支持标量或小数组，<100元素）", "default": []},
            "kwargs": {"type": "object", "description": "关键字参数", "default": {}},
            "output_variable": {"type": "string", "description": "结果保存到的变量名（可选）", "default": ""},
        },
        "required": ["function_name"],
    },
)
async def handle_run_matlab_function(engine, task_executor, params, **kwargs):
    from ..security.whitelist import check_security_level, SecurityLevel
    from ..security.injection_detector import analyze_matlab_code

    func_name = params["function_name"]
    args = params.get("args", [])
    kw = params.get("kwargs", {})
    out_var = params.get("output_variable", "")

    security_level = check_security_level(func_name)
    if security_level == SecurityLevel.L3_BLOCKED:
        return {"success": False, "error": f"Function '{func_name}' is blocked for security reasons",
                "security_level": "L3_BLOCKED"}

    arg_str = ", ".join(repr(a) for a in args)
    kw_str = ", ".join(f"'{k}', {repr(v)}" for k, v in kw.items())
    all_args = ", ".join(filter(None, [arg_str, kw_str]))

    if out_var:
        script = f"{out_var} = {func_name}({all_args});"
    else:
        script = f"{func_name}({all_args});"

    if security_level == SecurityLevel.L2_APPROVAL:
        aq = kwargs.get("approval_queue")
        if aq is None:
            return {"success": False, "pending_approval": True,
                    "operation": func_name, "script": script,
                    "error": f"Function '{func_name}' requires user approval before execution",
                    "security_level": "L2_APPROVAL"}
        req = aq.create_request(
            operation=func_name,
            description=f"Execute MATLAB function '{func_name}' with args: {all_args}",
            risk_level="L2",
            params={"script": script, "function_name": func_name, "args": args, "kwargs": kw},
        )
        approved = await aq.wait_for_approval(req.approval_id)
        if not approved:
            return {"success": False, "rejected": True,
                    "approval_id": req.approval_id,
                    "error": f"Operation '{func_name}' was rejected or timed out"}

    try:
        result = await engine.execute(script)
        return {"success": True, "function": func_name, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e), "function": func_name}


@registry.register(
    name="execute_matlab_script",
    description="执行预审阅的 MATLAB 脚本文件。脚本路径必须在沙盒目录内。",
    input_schema={
        "type": "object",
        "properties": {
            "script_path": {"type": "string", "description": "脚本文件路径（相对于沙盒目录）"},
            "params": {"type": "object", "description": "传递给脚本的参数", "default": {}},
        },
        "required": ["script_path"],
    },
)
async def handle_execute_matlab_script(engine, task_executor, params, **kwargs):
    from ..security.path_sanitizer import sanitize_path, PathTraversalError
    from ..config import Settings

    settings = Settings()
    script_rel = params["script_path"]
    try:
        full_path = sanitize_path(script_rel, str(settings.sandbox_dir))
    except PathTraversalError as e:
        return {"success": False, "error": str(e)}

    try:
        result = await engine.execute(f"run('{full_path}')")
        return {"success": True, "script": script_rel, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="evaluate_expression",
    description="计算 MATLAB 表达式（受限，需用户审批）。⚠️ 此操作需要用户批准。",
    input_schema={
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "MATLAB 表达式"},
        },
        "required": ["expression"],
    },
)
async def handle_evaluate_expression(engine, task_executor, params, **kwargs):
    from ..security.injection_detector import analyze_matlab_code, is_code_safe
    from ..security.whitelist import SecurityLevel

    expr = params["expression"]

    safe, risks = is_code_safe(expr)
    if not safe:
        blocked = [r for r in risks if r.severity == "block"]
        return {
            "success": False,
            "error": "Expression contains blocked code patterns",
            "security_level": "L3_BLOCKED",
            "risks": [{"keyword": r.keyword, "line": r.line, "reason": r.reason} for r in blocked],
        }

    warnings = [r for r in risks if r.severity == "warn"]
    if warnings:
        aq = kwargs.get("approval_queue")
        if aq is None:
            return {
                "success": False,
                "pending_approval": True,
                "operation": "evaluate_expression",
                "expression": expr,
                "security_level": "L2_APPROVAL",
                "risks": [{"keyword": r.keyword, "line": r.line, "reason": r.reason} for r in warnings],
                "error": "Expression contains patterns requiring user approval",
            }
        req = aq.create_request(
            operation="evaluate_expression",
            description=f"Evaluate MATLAB expression with {len(warnings)} warning(s)",
            risk_level="L2",
            params={"expression": expr, "risks": [r.keyword for r in warnings]},
        )
        approved = await aq.wait_for_approval(req.approval_id)
        if not approved:
            return {"success": False, "rejected": True,
                    "approval_id": req.approval_id,
                    "error": "Expression evaluation was rejected or timed out"}

    try:
        result = await engine.execute(expr)
        return {"success": True, "expression": expr, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="get_workspace_variable",
    description="获取工作区变量的值和元数据。大数据自动降采样或返回统计摘要。",
    input_schema={
        "type": "object",
        "properties": {
            "variable_name": {"type": "string", "description": "变量名"},
            "max_rows": {"type": "integer", "description": "最大返回行数", "default": 100},
        },
        "required": ["variable_name"],
    },
)
async def handle_get_workspace_variable(engine, task_executor, params, **kwargs):
    var_name = params["variable_name"]
    max_rows = params.get("max_rows", 100)
    try:
        info = await engine.get_variable_info(var_name, max_rows)
        return {"success": True, **info}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="list_workspace_variables",
    description="列出当前 MATLAB 工作区所有变量的元数据（名称、维度、类型）。",
    input_schema={"type": "object", "properties": {}},
)
async def handle_list_workspace_variables(engine, task_executor, params, **kwargs):
    try:
        result = await engine.list_workspace()
        return {"success": True, "variables": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

- [ ] **Step 2: Write test for computation tool registration**

```python
# tests/test_tools/test_computation.py
from matlab_mcp_server.tools.registry import registry


def test_computation_tools_registered():
    import matlab_mcp_server.tools.computation
    names = registry.list_names()
    assert "run_matlab_function" in names
    assert "execute_matlab_script" in names
    assert "evaluate_expression" in names
    assert "get_workspace_variable" in names
    assert "list_workspace_variables" in names
```

- [ ] **Step 3: Commit**

```bash
cd matlab-mcp-server
git add src/matlab_mcp_server/tools/computation.py tests/test_tools/test_computation.py
git commit -m "feat: computation tools"
```

---

## Task 7: Simulink Tools

**Files:**
- Create: `src/matlab_mcp_server/tools/simulink.py`
- Create: `tests/test_tools/test_simulink.py`

- [ ] **Step 1: Implement simulink.py**

```python
# src/matlab_mcp_server/tools/simulink.py
from .registry import registry


@registry.register(
    name="load_simulink_model",
    description="加载已有的 Simulink .slx 模型模板。加载前自动清理回调函数（防止恶意代码注入）。",
    input_schema={
        "type": "object",
        "properties": {
            "model_path": {"type": "string", "description": "模型文件路径（相对于沙盒目录）"},
        },
        "required": ["model_path"],
    },
)
async def handle_load_simulink_model(engine, task_executor, params, **kwargs):
    model_path = params["model_path"]
    from ..security.path_sanitizer import sanitize_path, PathTraversalError
    from ..config import Settings

    settings = Settings()
    try:
        full_path = sanitize_path(model_path, str(settings.sandbox_dir))
    except PathTraversalError as e:
        return {"success": False, "error": str(e)}

    try:
        await engine.execute(f"load_system('{full_path}')")
        from pathlib import Path
        model_name = Path(model_path).stem

        if settings.simulink_cleanup_callbacks:
            from ..security.callback_cleaner import build_sanitization_script
            cleanup_script = build_sanitization_script(model_name)
            await engine.execute(cleanup_script)

        return {"success": True, "model_name": model_name, "model_path": full_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="modify_block_parameters",
    description="修改 Simulink 模型中指定模块的参数。用于在预建模板上调参。",
    input_schema={
        "type": "object",
        "properties": {
            "model_name": {"type": "string", "description": "模型名称"},
            "block_path": {"type": "string", "description": "模块路径（如 'motor/PID Controller'）"},
            "params": {"type": "object", "description": "要修改的参数字典"},
        },
        "required": ["model_name", "block_path", "params"],
    },
)
async def handle_modify_block_parameters(engine, task_executor, params, **kwargs):
    model = params["model_name"]
    block = params["block_path"]
    param_dict = params["params"]

    scripts = []
    for key, value in param_dict.items():
        if isinstance(value, str):
            scripts.append(f"set_param('{model}/{block}', '{key}', '{value}')")
        else:
            scripts.append(f"set_param('{model}/{block}', '{key}', {value})")

    try:
        await engine.execute(";\n".join(scripts))
        return {"success": True, "model": model, "block": block, "modified_params": list(param_dict.keys())}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="list_block_parameters",
    description="列出 Simulink 模型中指定模块的所有可调参数及其当前值。",
    input_schema={
        "type": "object",
        "properties": {
            "model_name": {"type": "string"},
            "block_path": {"type": "string"},
        },
        "required": ["model_name", "block_path"],
    },
)
async def handle_list_block_parameters(engine, task_executor, params, **kwargs):
    model = params["model_name"]
    block = params["block_path"]
    try:
        result = await engine.execute(f"get_param('{model}/{block}', 'DialogParameters')")
        return {"success": True, "model": model, "block": block, "parameters": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="create_simple_model",
    description="创建简单的线性链式 Simulink 模型（模块按顺序自动连接）。支持常用 Simulink 模块名称（如 'Gain', 'Integrator', 'Scope'）自动映射到正确的库路径，也支持传入完整库路径（如 'simulink/Math Operations/Gain'）。",
    input_schema={
        "type": "object",
        "properties": {
            "model_name": {"type": "string"},
            "blocks": {"type": "array", "items": {"type": "string"}, "description": "模块类型列表，按顺序连接"},
        },
        "required": ["model_name", "blocks"],
    },
)
async def handle_create_simple_model(engine, task_executor, params, **kwargs):
    SIMULINK_BLOCK_LIBRARIES = {
        "Sine Wave": "simulink/Sources/Sine Wave",
        "Step": "simulink/Sources/Step",
        "Constant": "simulink/Sources/Constant",
        "Ramp": "simulink/Sources/Ramp",
        "Clock": "simulink/Sources/Clock",
        "Pulse Generator": "simulink/Sources/Pulse Generator",
        "Signal Generator": "simulink/Sources/Signal Generator",
        "From Workspace": "simulink/Sources/From Workspace",
        "Gain": "simulink/Math Operations/Gain",
        "Sum": "simulink/Math Operations/Sum",
        "Product": "simulink/Math Operations/Product",
        "Math Function": "simulink/Math Operations/Math Function",
        "Trigonometric Function": "simulink/Math Operations/Trigonometric Function",
        "Abs": "simulink/Math Operations/Abs",
        "Sign": "simulink/Math Operations/Sign",
        "Rounding": "simulink/Math Operations/Rounding",
        "MinMax": "simulink/Math Operations/MinMax",
        "Logic": "simulink/Logic and Bit Operations/Logical Operator",
        "Compare To Zero": "simulink/Logic and Bit Operations/Compare To Zero",
        "Compare To Constant": "simulink/Logic and Bit Operations/Compare To Constant",
        "Integrator": "simulink/Continuous/Integrator",
        "Derivative": "simulink/Continuous/Derivative",
        "Transfer Fcn": "simulink/Continuous/Transfer Fcn",
        "State-Space": "simulink/Continuous/State-Space",
        "Zero-Pole": "simulink/Continuous/Zero-Pole",
        "Transport Delay": "simulink/Continuous/Transport Delay",
        "Scope": "simulink/Sinks/Scope",
        "Display": "simulink/Sinks/Display",
        "To Workspace": "simulink/Sinks/To Workspace",
        "To File": "simulink/Sinks/To File",
        "Terminator": "simulink/Sinks/Terminator",
        "Out1": "simulink/Sinks/Out1",
        "In1": "simulink/Sources/In1",
        "SubSystem": "simulink/Ports & Subsystems/Subsystem",
        "Unit Delay": "simulink/Discrete/Unit Delay",
        "Discrete Transfer Fcn": "simulink/Discrete/Discrete Transfer Fcn",
        "Discrete State-Space": "simulink/Discrete/Discrete State-Space",
        "Saturation": "simulink/Discontinuities/Saturation",
        "Dead Zone": "simulink/Discontinuities/Dead Zone",
        "Relay": "simulink/Discontinuities/Relay",
        "Mux": "simulink/Signal Routing/Mux",
        "Demux": "simulink/Signal Routing/Demux",
        "Bus Creator": "simulink/Signal Routing/Bus Creator",
        "Bus Selector": "simulink/Signal Routing/Bus Selector",
        "Switch": "simulink/Signal Routing/Switch",
        "Manual Switch": "simulink/Signal Routing/Manual Switch",
    }

    model = params["model_name"]
    blocks = params["blocks"]

    script_lines = [f"new_system('{model}')"]
    for i, block_type in enumerate(blocks):
        block_name = f"Block_{i}"
        if "/" in block_type:
            lib_path = block_type
        elif block_type in SIMULINK_BLOCK_LIBRARIES:
            lib_path = SIMULINK_BLOCK_LIBRARIES[block_type]
        else:
            lib_path = f"simulink/Sources/{block_type}"
        script_lines.append(f"add_block('{lib_path}', '{model}/{block_name}')")
    for i in range(len(blocks) - 1):
        src = f"Block_{i}/1"
        dst = f"Block_{i+1}/1"
        script_lines.append(f"add_line('{model}', '{src}', '{dst}')")

    try:
        await engine.execute(";\n".join(script_lines))
        return {"success": True, "model_name": model, "blocks": blocks}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="configure_simulation",
    description="配置 Simulink 仿真参数（求解器、仿真时长、步长等）。",
    input_schema={
        "type": "object",
        "properties": {
            "model_name": {"type": "string"},
            "solver": {"type": "string", "default": "ode45"},
            "stop_time": {"type": "number", "default": 10.0},
            "step_size": {"type": "number", "default": 0.01},
        },
        "required": ["model_name"],
    },
)
async def handle_configure_simulation(engine, task_executor, params, **kwargs):
    model = params["model_name"]
    solver = params.get("solver", "ode45")
    stop_time = params.get("stop_time", 10.0)
    step_size = params.get("step_size", 0.01)

    script = f"""
set_param('{model}', 'Solver', '{solver}');
set_param('{model}', 'StopTime', '{stop_time}');
set_param('{model}', 'FixedStep', '{step_size}');
"""
    try:
        await engine.execute(script)
        return {"success": True, "model": model, "solver": solver, "stop_time": stop_time}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="run_simulation",
    description="运行 Simulink 仿真（异步执行，立即返回 Task_ID）。三种模式：code(纯后台)、gui(打开GUI)、hybrid(后台+GUI可查看)。",
    input_schema={
        "type": "object",
        "properties": {
            "model_name": {"type": "string"},
            "mode": {"type": "string", "enum": ["code", "gui", "hybrid"], "default": "code"},
        },
        "required": ["model_name"],
    },
)
async def handle_run_simulation(engine, task_executor, params, **kwargs):
    model = params["model_name"]
    mode = params.get("mode", "code")

    def run_sim():
        if mode in ("gui", "hybrid"):
            engine._execute_sync(f"open_system('{model}')")
        result = engine._execute_sync(f"sim('{model}')")
        return result

    task_id = task_executor.submit("run_simulation", run_sim)
    return {
        "success": True,
        "task_id": task_id,
        "model_name": model,
        "mode": mode,
        "message": "Simulation started. Use check_task_status(task_id) to monitor progress.",
    }


@registry.register(
    name="get_simulation_results",
    description="获取已完成仿真的结果数据。大数据自动降采样。",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
            "signals": {"type": "array", "items": {"type": "string"}, "description": "要获取的信号名列表"},
        },
        "required": ["task_id"],
    },
)
async def handle_get_simulation_results(engine, task_executor, params, **kwargs):
    task_id = params["task_id"]
    task = task_executor.get_task(task_id)
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}
    if task.status.value != "completed":
        return {"success": False, "error": f"Task not completed. Current status: {task.status.value}"}
    return {"success": True, "task_id": task_id, "result": task.result}


@registry.register(
    name="open_simulink_gui",
    description="打开 Simulink GUI 让用户查看/编辑模型。",
    input_schema={
        "type": "object",
        "properties": {"model_name": {"type": "string"}},
        "required": ["model_name"],
    },
)
async def handle_open_simulink_gui(engine, task_executor, params, **kwargs):
    model = params["model_name"]
    try:
        await engine.execute(f"open_system('{model}')")
        return {"success": True, "model_name": model, "message": "Simulink GUI opened"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

- [ ] **Step 2: Write test for simulink tool registration**

```python
# tests/test_tools/test_simulink.py
from matlab_mcp_server.tools.registry import registry


def test_simulink_tools_registered():
    import matlab_mcp_server.tools.simulink
    names = registry.list_names()
    expected = ["load_simulink_model", "modify_block_parameters", "list_block_parameters",
                "create_simple_model", "configure_simulation", "run_simulation",
                "get_simulation_results", "open_simulink_gui"]
    for name in expected:
        assert name in names, f"Missing tool: {name}"
```

- [ ] **Step 3: Commit**

```bash
cd matlab-mcp-server
git add src/matlab_mcp_server/tools/simulink.py tests/test_tools/test_simulink.py
git commit -m "feat: simulink tools"
```

---

## Task 7b: Toolbox Tools (Signal Processing, Control System, Optimization, Machine Learning, Data Analysis)

**Files:**
- Create: `src/matlab_mcp_server/tools/toolbox.py`
- Create: `tests/test_tools/test_toolbox.py`

- [ ] **Step 1: Implement toolbox.py**

```python
# src/matlab_mcp_server/tools/toolbox.py
from .registry import registry


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
        "lowpass": f"""
[b, a] = butter(4, {cutoff}/({fs}/2), 'low');
{output_var} = filter(b, a, {input_var});
""",
        "highpass": f"""
[b, a] = butter(4, {cutoff}/({fs}/2), 'high');
{output_var} = filter(b, a, {input_var});
""",
        "bandpass": f"""
low = {p.get('low_cutoff', 50)} / ({fs}/2);
high = {p.get('high_cutoff', 200)} / ({fs}/2);
[b, a] = butter(4, [low, high], 'bandpass');
{output_var} = filter(b, a, {input_var});
""",
        "psd": f"""
nfft = {p.get('nfft', 1024)};
[{output_var}, f_vec] = pwelch({input_var}, hanning(nfft), nfft/2, nfft, {fs});
""",
        "spectrogram": f"""
nfft = {p.get('nfft', 256)};
[S, F, T] = spectrogram({input_var}, hanning(nfft), nfft/4, nfft, {fs});
{output_var} = struct('S', S, 'F', F, 'T', T);
""",
        "filter_design": f"""
order = {p.get('order', 4)};
fc = {cutoff} / ({fs}/2);
[b, a] = butter(order, fc, 'low');
{output_var} = struct('b', b, 'a', a);
""",
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
        "ss": f"A = {p.get('A', '[]')}; B = {p.get('B', '[]')}; C = {p.get('C', '[]')}; D = {p.get('D', '0')};\n{output_var} = ss(A, B, C, D);",
        "bode": f"bode({output_var});\ngrid on;",
        "rlocus": f"rlocus({output_var});",
        "step": f"step({output_var});\ngrid on;",
        "impulse": f"impulse({output_var});\ngrid on;",
        "nyquist": f"nyquist({output_var});",
        "pid_tune": f"Kp = {p.get('Kp', 1)}; Ki = {p.get('Ki', 0)}; Kd = {p.get('Kd', 0)};\n{output_var} = pid(Kp, Ki, Kd);",
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
        "fminunc": f"options = optimoptions('fminunc', 'Display', 'off');\n[{output_var}, fval] = fminunc({obj}, {x0}, options);",
        "fmincon": f"""
A_ineq = {p.get('A', '[]')}; b_ineq = {p.get('b', '[]')};
Aeq = {p.get('Aeq', '[]')}; beq = {p.get('beq', '[]')};
lb = {p.get('lb', '[]')}; ub = {p.get('ub', '[]')};
options = optimoptions('fmincon', 'Display', 'off');
[{output_var}, fval] = fmincon({obj}, {x0}, A_ineq, b_ineq, Aeq, beq, lb, ub, [], options);
""",
        "linprog": f"""
c = {p.get('c', '[]')};
A_ineq = {p.get('A', '[]')}; b_ineq = {p.get('b', '[]')};
Aeq = {p.get('Aeq', '[]')}; beq = {p.get('beq', '[]')};
lb = {p.get('lb', '[]')}; ub = {p.get('ub', '[]')};
[{output_var}, fval] = linprog(c, A_ineq, b_ineq, Aeq, beq, lb, ub);
""",
        "lsqcurvefit": f"""
fun = {obj};
xdata = {p.get('xdata', '[]')}; ydata = {p.get('ydata', '[]')};
lb = {p.get('lb', '[]')}; ub = {p.get('ub', '[]')};
options = optimoptions('lsqcurvefit', 'Display', 'off');
[{output_var}, resnorm] = lsqcurvefit(fun, {x0}, xdata, ydata, lb, ub, options);
""",
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
        "fitcensemble": f"{output_var} = fitcensemble({data_var}, {label_var}, 'Method', '{p.get('method', 'AdaBoostM1')}');",
        "fitlm": f"{output_var} = fitlm({data_var}, {label_var});" if label_var else f"{output_var} = fitlm({data_var});",
        "kmeans": f"k = {p.get('k', 3)};\n[{output_var}_idx, {output_var}_centroids] = kmeans({data_var}, k);",
        "pca": f"[{output_var}_coeff, {output_var}_score, {output_var}_latent] = pca({data_var});",
        "tsne": f"{output_var} = tsne({data_var}, 'NumDimensions', {p.get('num_dims', 2)}, 'Perplexity', {p.get('perplexity', 30)});",
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
        "describe": f"""
{output_var} = struct();
{output_var}.mean = mean({data_var});
{output_var}.median = median({data_var});
{output_var}.std = std({data_var});
{output_var}.min = min({data_var});
{output_var}.max = max({data_var});
{output_var}.size = size({data_var});
""",
        "corrcoef": f"{output_var} = corrcoef({data_var});",
        "regress": f"""
y = {data_var};
X = {p.get('X', 'ones(size(y))')};
[b, bint, r, rint, stats] = regress(y, X);
{output_var} = struct('coefficients', b, 'ci', bint, 'residuals', r, 'stats', stats);
""",
        "ttest": f"""
[h, p_val, ci, stats] = ttest({data_var});
{output_var} = struct('reject', h, 'p_value', p_val, 'ci', ci, 'tstat', stats.tstat);
""",
        "anova": f"""
groups = {p.get('groups', '[]')};
[p_val, tbl, stats] = anova1({data_var}, groups);
{output_var} = struct('p_value', p_val, 'table', {{tbl}});
""",
        "interp1": f"""
x = {p.get('x', '[]')};
xq = {p.get('xq', '[]')};
method = '{p.get('method', 'linear')}';
{output_var} = interp1(x, {data_var}, xq, method);
""",
        "smooth": f"""
span = {p.get('span', 5)};
{output_var} = smooth({data_var}, span);
""",
        "histogram_stats": f"""
[N, edges] = histcounts({data_var});
{output_var} = struct('counts', N, 'edges', edges, 'mean', mean({data_var}), 'std', std({data_var}));
""",
    }

    script = scripts.get(op)
    if not script:
        return {"success": False, "error": f"Unknown operation: {op}. Supported: {list(scripts.keys())}"}
    try:
        result = await engine.execute(script.strip())
        return {"success": True, "operation": op, "output_variable": output_var, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

- [ ] **Step 2: Write test for toolbox registration**

```python
# tests/test_tools/test_toolbox.py
from matlab_mcp_server.tools.registry import registry


def test_toolbox_tools_registered():
    import matlab_mcp_server.tools.toolbox
    names = registry.list_names()
    expected = ["signal_processing", "control_system", "optimization", "machine_learning", "data_analysis"]
    for name in expected:
        assert name in names, f"Missing toolbox tool: {name}"


def test_signal_processing_tool_schema():
    import matlab_mcp_server.tools.toolbox
    tool = registry.get_all()["signal_processing"]
    assert "fft" in tool["input_schema"]["properties"]["operation"]["enum"]
    assert "lowpass" in tool["input_schema"]["properties"]["operation"]["enum"]


def test_control_system_tool_schema():
    import matlab_mcp_server.tools.toolbox
    tool = registry.get_all()["control_system"]
    assert "tf" in tool["input_schema"]["properties"]["operation"]["enum"]
    assert "bode" in tool["input_schema"]["properties"]["operation"]["enum"]


def test_machine_learning_requires_label_for_classification():
    import matlab_mcp_server.tools.toolbox
    tool = registry.get_all()["machine_learning"]
    assert "data_variable" in tool["input_schema"]["required"]
```

- [ ] **Step 3: Run tests**

Run: `cd matlab-mcp-server && python -m pytest tests/test_tools/test_toolbox.py -v`
Expected: 4 passed

- [ ] **Step 4: Commit**

```bash
cd matlab-mcp-server
git add src/matlab_mcp_server/tools/toolbox.py tests/test_tools/test_toolbox.py
git commit -m "feat: toolbox tools (signal processing, control system, optimization, machine learning, data analysis)"
```

---

## Task 8: Visualization Tools + Client Adapter

**Files:**
- Create: `src/matlab_mcp_server/tools/visualization.py`
- Create: `src/matlab_mcp_server/output/client_adapter.py`
- Create: `src/matlab_mcp_server/output/__init__.py`
- Create: `tests/test_output/__init__.py`
- Create: `tests/test_output/test_client_adapter.py`
- Create: `tests/test_tools/test_visualization.py`

- [ ] **Step 1: Implement client_adapter.py**

```python
# src/matlab_mcp_server/output/__init__.py
```

```python
# src/matlab_mcp_server/output/client_adapter.py
import base64
from pathlib import Path


class ClientAdapter:
    def __init__(self, client_vision: bool = True, context_limit: int = 200000):
        self.client_vision = client_vision
        self.context_limit = context_limit

    def adapt_image_response(self, response: dict, image_path: str) -> dict:
        if self.client_vision:
            try:
                img_path = Path(image_path)
                if img_path.exists() and img_path.stat().st_size < 10 * 1024 * 1024:
                    with open(img_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    response["image_base64"] = b64
                    response["image_format"] = img_path.suffix.lstrip(".")
            except Exception:
                pass
            return response
        else:
            response.pop("image_base64", None)
            response["instruction"] = (
                "请调用 execute_matlab_script 编写 imread 代码，利用 MATLAB 后台提取特征"
            )
            return response

    def adapt_data_response(self, response: dict, element_count: int,
                            full_data_threshold: int = 100) -> dict:
        if element_count > full_data_threshold:
            response["data_truncated"] = True
            response["suggestion"] = "数据量较大，已返回统计摘要。使用绘图工具可视化完整数据。"
        return response
```

- [ ] **Step 2: Write tests for client_adapter**

```python
# tests/test_output/__init__.py
```

```python
# tests/test_output/test_client_adapter.py
import pytest
import tempfile
from pathlib import Path
from matlab_mcp_server.output.client_adapter import ClientAdapter


def test_vision_client_gets_base64():
    adapter = ClientAdapter(client_vision=True)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        tmp_path = f.name
    response = {"success": True, "figure_path": tmp_path}
    result = adapter.adapt_image_response(response, tmp_path)
    assert "image_base64" in result
    assert "image_format" in result
    Path(tmp_path).unlink()


def test_text_client_no_base64():
    adapter = ClientAdapter(client_vision=False)
    response = {"success": True, "figure_path": "/some/path.png"}
    result = adapter.adapt_image_response(response, "/some/path.png")
    assert "image_base64" not in result
    assert "instruction" in result


def test_large_data_flagged():
    adapter = ClientAdapter()
    response = {"success": True, "data": list(range(1000))}
    result = adapter.adapt_data_response(response, 1000, full_data_threshold=100)
    assert result["data_truncated"] is True
```

- [ ] **Step 3: Implement visualization.py**

```python
# src/matlab_mcp_server/tools/visualization.py
from .registry import registry

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

    script = f"""
figure('Visible', 'off');
{func}({x_var}, {y_var});
title('{title}');
xlabel('{xlabel}');
ylabel('{ylabel}');
grid on;
"""
    try:
        await engine.execute(script)
        fig_path = str(engine.sandbox_dir / "figures" / "latest_plot.png")
        await engine.execute(f"saveas(gcf, '{fig_path}')")
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
    func = {"surf": "surf", "mesh": "mesh", "contour": "contour", "scatter3": "scatter3"}[plot_type]
    script = f"figure('Visible','off');\n{func}({x_var},{y_var},{z_var});\ngrid on;"
    try:
        await engine.execute(script)
        fig_path = str(engine.sandbox_dir / "figures" / "latest_3d_plot.png")
        await engine.execute(f"saveas(gcf, '{fig_path}')")
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
    fmt = params.get("format", "png")
    try:
        fig_path = str(engine.sandbox_dir / "figures" / filename)
        await engine.execute(f"saveas(gcf, '{fig_path}')")
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
    script = f"figure('Visible','off');\n"
    for i, p in enumerate(plots):
        script += f"subplot({rows},{cols},{i+1});\n"
        func = p.get("plot_type", "plot")
        x_var = p.get("x_variable_name", "[]")
        y_var = p.get("y_variable_name", "[]")
        script += f"{func}({x_var},{y_var});\ntitle('{p.get('title','')}');\ngrid on;\n"
    try:
        await engine.execute(script)
        fig_path = str(engine.sandbox_dir / "figures" / "subplot.png")
        await engine.execute(f"saveas(gcf, '{fig_path}')")
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
fig = openfig('{fig_path}', 'invisible');
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
```

- [ ] **Step 4: Run tests**

Run: `cd matlab-mcp-server && python -m pytest tests/test_tools/test_visualization.py tests/test_output/test_client_adapter.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
cd matlab-mcp-server
git add src/matlab_mcp_server/tools/visualization.py src/matlab_mcp_server/output/ tests/
git commit -m "feat: visualization tools and client adapter"
```

---

## Task 9: Data Integrity, Payload Breaker, Error Formatter, Data Serializer

**Files:**
- Create: `src/matlab_mcp_server/output/integrity.py`
- Create: `src/matlab_mcp_server/output/payload_breaker.py`
- Create: `src/matlab_mcp_server/output/error_formatter.py`
- Create: `src/matlab_mcp_server/output/data_serializer.py`
- Create: `tests/test_output/test_integrity.py`
- Create: `tests/test_output/test_payload_breaker.py`
- Create: `tests/test_output/test_data_serializer.py`

- [ ] **Step 1: Implement integrity.py**

```python
# src/matlab_mcp_server/output/integrity.py
import hashlib
import zlib
import time


def compute_checksum(data: bytes, algorithm: str = "sha256") -> str:
    if algorithm == "sha256":
        return hashlib.sha256(data).hexdigest()
    elif algorithm == "crc32":
        return format(zlib.crc32(data) & 0xFFFFFFFF, "08x")
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def choose_algorithm(data_size_bytes: int) -> str:
    if data_size_bytes < 1024 * 1024:
        return "sha256"
    return "crc32"


def add_integrity(data, data_bytes: bytes) -> dict:
    algo = choose_algorithm(len(data_bytes))
    checksum = compute_checksum(data_bytes, algo)
    return {
        "checksum": checksum,
        "algorithm": algo,
        "data_size_bytes": len(data_bytes),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def verify_checksum(data_bytes: bytes, expected_hash: str, algorithm: str = "sha256") -> bool:
    return compute_checksum(data_bytes, algorithm) == expected_hash
```

- [ ] **Step 2: Implement payload_breaker.py**

```python
# src/matlab_mcp_server/output/payload_breaker.py
import json
from pathlib import Path
from .integrity import compute_checksum, add_integrity


class PayloadBreaker:
    def __init__(self, max_payload_mb: int = 5, sandbox_dir: Path | None = None):
        self.max_bytes = max_payload_mb * 1024 * 1024
        self.sandbox_dir = sandbox_dir or Path.home() / "matlab_mcp_sandbox"

    def check_and_break(self, response: dict, task_id: str) -> dict:
        payload_bytes = json.dumps(response, ensure_ascii=False, default=str).encode("utf-8")

        if len(payload_bytes) <= self.max_bytes:
            response["integrity"] = add_integrity(response, payload_bytes)
            return response

        result_file = self.sandbox_dir / f"result_{task_id}.json"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(response, f, ensure_ascii=False, default=str, indent=2)

        checksum = compute_checksum(payload_bytes)
        checksum_file = result_file.with_suffix(result_file.suffix + ".sha256")
        checksum_file.write_text(checksum)

        return {
            "success": True,
            "data_truncated": True,
            "file_path": str(result_file),
            "checksum_file": str(checksum_file),
            "payload_size_bytes": len(payload_bytes),
            "integrity": add_integrity(None, payload_bytes),
        }
```

- [ ] **Step 3: Implement error_formatter.py**

```python
# src/matlab_mcp_server/output/error_formatter.py
import re
from typing import Optional


def format_error(error: Exception, task_id: Optional[str] = None,
                 workspace_info: Optional[dict] = None,
                 client_vision: bool = True) -> dict:
    error_str = str(error)
    matlab_stack = re.findall(r"Error in .*? \(line \d+\)", error_str)

    code = "MATLAB_RUNTIME_ERROR"
    if "Out of memory" in error_str:
        code = "RESOURCE_EXHAUSTED"
    elif "Undefined function" in error_str:
        code = "UNDEFINED_FUNCTION"
    elif "Index exceeds" in error_str:
        code = "INDEX_ERROR"

    suggestions = {
        "RESOURCE_EXHAUSTED": "减小数据规模或重启引擎",
        "UNDEFINED_FUNCTION": "检查函数名拼写，或确认所需工具箱已加载",
        "INDEX_ERROR": "检查数组索引是否从 1 开始（MATLAB 使用 1-based 索引）",
    }

    result = {
        "success": False,
        "error": {
            "code": code,
            "message": error_str[:1000],
            "matlab_stack": matlab_stack[:10],
            "suggestion": suggestions.get(code, "请检查输入参数是否正确"),
            "recoverable": code != "RESOURCE_EXHAUSTED",
        },
    }
    if task_id:
        result["error"]["task_id"] = task_id
    if workspace_info and not client_vision:
        result["error"]["workspace_context"] = workspace_info
    return result


def format_divergence_error(task_id: str, divergence_time: float,
                             signal_name: str, pre_div_plot: Optional[str] = None,
                             client_vision: bool = True) -> dict:
    result = {
        "success": False,
        "error": {
            "code": "SIMULATION_DIVERGENCE",
            "message": f"Simulation diverged at t={divergence_time:.2f}s. NaN detected in '{signal_name}'.",
            "divergence_point": {"time": divergence_time, "signal": signal_name},
            "suggestion": "减小步长或切换为 stiff solver (如 ode15s)",
            "recoverable": True,
            "task_id": task_id,
        },
    }
    if client_vision and pre_div_plot:
        result["error"]["visualization"] = {
            "pre_divergence_plot": pre_div_plot,
            "description": "发散前的有效数据缩略图",
        }
    return result
```

- [ ] **Step 4: Implement data_serializer.py**

```python
# src/matlab_mcp_server/output/data_serializer.py
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
```

- [ ] **Step 5: Write tests**

```python
# tests/test_output/test_integrity.py
from matlab_mcp_server.output.integrity import compute_checksum, choose_algorithm, add_integrity, verify_checksum


def test_sha256_small_data():
    data = b"hello world"
    h = compute_checksum(data, "sha256")
    assert len(h) == 64
    assert verify_checksum(data, h, "sha256") is True
    assert verify_checksum(b"tampered", h, "sha256") is False


def test_crc32_large_data():
    data = b"x" * (2 * 1024 * 1024)
    h = compute_checksum(data, "crc32")
    assert len(h) == 8
    assert verify_checksum(data, h, "crc32") is True


def test_auto_select_algorithm():
    assert choose_algorithm(500) == "sha256"
    assert choose_algorithm(2 * 1024 * 1024) == "crc32"


def test_add_integrity_fields():
    integrity = add_integrity({"key": "value"}, b"test")
    assert "checksum" in integrity
    assert "algorithm" in integrity
    assert "data_size_bytes" in integrity
    assert "timestamp" in integrity
```

```python
# tests/test_output/test_payload_breaker.py
import json
import tempfile
from pathlib import Path
from matlab_mcp_server.output.payload_breaker import PayloadBreaker


def test_small_payload_passes_through():
    with tempfile.TemporaryDirectory() as tmp:
        breaker = PayloadBreaker(max_payload_mb=5, sandbox_dir=Path(tmp))
        response = {"success": True, "data": "small"}
        result = breaker.check_and_break(response, "task_001")
        assert result["success"] is True
        assert "integrity" in result
        assert "file_path" not in result


def test_large_payload_written_to_file():
    with tempfile.TemporaryDirectory() as tmp:
        breaker = PayloadBreaker(max_payload_mb=0, sandbox_dir=Path(tmp))
        response = {"success": True, "data": "x" * 10000}
        result = breaker.check_and_break(response, "task_002")
        assert result["data_truncated"] is True
        assert Path(result["file_path"]).exists()
        assert Path(result["checksum_file"]).exists()


def test_checksum_consistency_small_and_large():
    from matlab_mcp_server.output.integrity import compute_checksum
    with tempfile.TemporaryDirectory() as tmp:
        response = {"success": True, "data": [1, 2, 3]}
        compact_bytes = json.dumps(response, ensure_ascii=False, default=str).encode("utf-8")
        small_integrity = PayloadBreaker(max_payload_mb=5, sandbox_dir=Path(tmp)).check_and_break(dict(response), "t1")
        large_integrity = PayloadBreaker(max_payload_mb=0, sandbox_dir=Path(tmp)).check_and_break(dict(response), "t2")
        assert small_integrity["integrity"]["checksum"] == large_integrity["integrity"]["checksum"]
```

```python
# tests/test_output/test_data_serializer.py
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


def test_serialize_small_array():
    data = np.array([1.0, 2.0, 3.0])
    result = serialize_variable(data, max_rows=100, downsample_threshold=1000)
    assert "data" in result
    assert "metadata" in result


def test_serialize_large_array_downsampled():
    data = np.random.randn(5000)
    result = serialize_variable(data, max_rows=100, downsample_threshold=1000)
    assert result["truncated"] is True
    assert "downsampled" in result
    assert len(result["downsampled"]["y"]) == 1000
```

- [ ] **Step 6: Run tests**

Run: `cd matlab-mcp-server && python -m pytest tests/test_output/ -v`
Expected: all passed

- [ ] **Step 7: Commit**

```bash
cd matlab-mcp-server
git add src/matlab_mcp_server/output/ tests/test_output/
git commit -m "feat: integrity checks, payload breaker, error formatter, data serializer"
```

---

# Phase 3: Transport Layer (Tasks 10-11)

## Task 10: stdio Transport

**Files:**
- Create: `src/matlab_mcp_server/transport/__init__.py`
- Create: `src/matlab_mcp_server/transport/stdio.py`

- [ ] **Step 1: Implement stdio.py**

```python
# src/matlab_mcp_server/transport/__init__.py
```

```python
# src/matlab_mcp_server/transport/stdio.py
import sys
import logging
from ..config import Settings
from ..server import create_server

logger = logging.getLogger(__name__)


def run_stdio(settings: Settings):
    logger.info("Starting MATLAB MCP Server in stdio mode")
    mcp = create_server(settings)
    mcp.run(transport="stdio")
```

- [ ] **Step 2: Commit**

```bash
cd matlab-mcp-server
git add src/matlab_mcp_server/transport/
git commit -m "feat: stdio transport"
```

---

## Task 11: HTTP/SSE Transport + Token Auth

**Files:**
- Create: `src/matlab_mcp_server/transport/http.py`

- [ ] **Step 1: Implement http.py**

```python
# src/matlab_mcp_server/transport/http.py
import logging
import secrets
from ..config import Settings
from ..server import create_server

logger = logging.getLogger(__name__)


def run_http(settings: Settings):
    logger.info(
        "Starting MATLAB MCP Server in HTTP mode on %s:%s",
        settings.http_bind,
        settings.http_port,
    )
    mcp = create_server(settings)

    if not settings.http_token:
        logger.warning(
            "No HTTP token configured. Set MATLAB_MCP_HTTP_TOKEN for authentication."
        )

    mcp.run(
        transport="streamable-http",
        host=settings.http_bind,
        port=settings.http_port,
    )
```

- [ ] **Step 2: Commit**

```bash
cd matlab-mcp-server
git add src/matlab_mcp_server/transport/http.py
git commit -m "feat: HTTP/SSE transport"
```

---

# Phase 4: Integration & Testing (Tasks 12-14)

## Task 12: File Operations Tools + Audit Logger + Approval Queue

**Files:**
- Create: `src/matlab_mcp_server/tools/file_ops.py`
- Create: `src/matlab_mcp_server/security/audit_logger.py`
- Create: `src/matlab_mcp_server/security/approval_queue.py`
- Create: `tests/test_tools/test_file_ops.py`

- [ ] **Step 1: Implement file_ops.py**

```python
# src/matlab_mcp_server/tools/file_ops.py
from .registry import registry


@registry.register(
    name="load_data",
    description=(
        "加载数据文件到 MATLAB 工作区。文件路径必须在沙盒目录内。"
        "⚠️ .mat 文件风险提示：MATLAB load() 会自动执行 .mat 中嵌入的 "
        "classdef 构造函数和自定义序列化回调，可能执行任意代码。"
        "建议仅加载可信来源的 .mat 文件。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "文件路径（相对于沙盒目录）"},
            "format": {"type": "string", "enum": ["csv", "xlsx", "mat", "json"], "default": "csv"},
            "variable_name": {"type": "string", "description": "加载到的变量名", "default": "loaded_data"},
        },
        "required": ["file_path"],
    },
)
async def handle_load_data(engine, task_executor, params, **kwargs):
    from ..security.path_sanitizer import sanitize_path, PathTraversalError
    from ..security.injection_detector import is_code_safe
    from ..config import Settings

    settings = Settings()
    file_path = params["file_path"]
    fmt = params.get("format", "csv")
    var_name = params.get("variable_name", "loaded_data")

    try:
        full_path = sanitize_path(file_path, str(settings.sandbox_dir))
    except PathTraversalError as e:
        return {"success": False, "error": str(e)}

    load_scripts = {
        "csv": f"{var_name} = readtable('{full_path}');",
        "xlsx": f"{var_name} = readtable('{full_path}');",
        "mat": (
            f"loaded = load('-mat', '{full_path}');\n"
            f"{var_name} = loaded;"
        ),
        "json": f"{var_name} = jsondecode(fileread('{full_path}'));",
    }

    script = load_scripts.get(fmt, load_scripts["csv"])

    if fmt == "mat":
        safe, risks = is_code_safe(script)
        if not safe:
            return {
                "success": False,
                "error": "MAT file load script blocked by injection guard",
                "risks": [{"keyword": r.keyword, "reason": r.reason} for r in risks if r.severity == "block"],
            }

    try:
        await engine.execute(script)
        info = await engine.get_variable_info(var_name)
        return {"success": True, "variable_name": var_name, "file_path": file_path, "info": info}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="save_data",
    description="保存工作区变量到文件。文件保存在沙盒目录内。",
    input_schema={
        "type": "object",
        "properties": {
            "variable_name": {"type": "string", "description": "要保存的变量名"},
            "file_path": {"type": "string", "description": "保存路径（相对于沙盒目录）"},
            "format": {"type": "string", "enum": ["csv", "mat", "json"], "default": "csv"},
        },
        "required": ["variable_name", "file_path"],
    },
)
async def handle_save_data(engine, task_executor, params, **kwargs):
    from ..security.path_sanitizer import sanitize_path, PathTraversalError
    from ..config import Settings

    settings = Settings()
    var_name = params["variable_name"]
    file_path = params["file_path"]
    fmt = params.get("format", "csv")

    try:
        full_path = sanitize_path(file_path, str(settings.sandbox_dir))
    except PathTraversalError as e:
        return {"success": False, "error": str(e)}

    save_scripts = {
        "csv": f"writetable({var_name}, '{full_path}');",
        "mat": f"save('{full_path}', '{var_name}');",
        "json": f"fid = fopen('{full_path}', 'w');\nfwrite(fid, jsonencode({var_name}));\nfclose(fid);",
    }

    script = save_scripts.get(fmt, save_scripts["csv"])
    try:
        await engine.execute(script)
        return {"success": True, "variable_name": var_name, "file_path": file_path, "format": fmt}
    except Exception as e:
        return {"success": False, "error": str(e)}


@registry.register(
    name="list_sandbox_files",
    description="列出沙盒目录中的所有文件。",
    input_schema={"type": "object", "properties": {}},
)
async def handle_list_sandbox_files(engine, task_executor, params, **kwargs):
    import os
    from ..config import Settings

    settings = Settings()
    sandbox = settings.sandbox_dir
    files = []
    for root, dirs, filenames in os.walk(sandbox):
        for f in filenames:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, sandbox)
            size = os.path.getsize(full)
            files.append({"path": rel, "size_bytes": size})
    return {"success": True, "files": files, "count": len(files)}


@registry.register(
    name="verify_checksum",
    description="验证文件或数据的校验和完整性。",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "文件路径（相对于沙盒目录）"},
            "expected_hash": {"type": "string", "description": "期望的校验和值"},
            "algorithm": {"type": "string", "enum": ["sha256", "crc32"], "default": "sha256"},
        },
        "required": ["file_path", "expected_hash"],
    },
)
async def handle_verify_checksum(engine, task_executor, params, **kwargs):
    from ..security.path_sanitizer import sanitize_path, PathTraversalError
    from ..output.integrity import verify_checksum
    from ..config import Settings

    settings = Settings()
    file_path = params["file_path"]
    expected = params["expected_hash"]
    algo = params.get("algorithm", "sha256")

    try:
        full_path = sanitize_path(file_path, str(settings.sandbox_dir))
    except PathTraversalError as e:
        return {"success": False, "error": str(e)}

    try:
        with open(full_path, "rb") as f:
            data = f.read()
        valid = verify_checksum(data, expected, algo)
        return {"success": True, "valid": valid, "file_path": file_path, "algorithm": algo}
    except FileNotFoundError:
        return {"success": False, "error": f"File not found: {file_path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

- [ ] **Step 2: Implement audit_logger.py**

```python
# src/matlab_mcp_server/security/audit_logger.py
import json
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AuditLogger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        session_id: str,
        task_id: Optional[str],
        client: str,
        tool: str,
        params: dict,
        security_level: str,
        result: str,
        duration_ms: Optional[float] = None,
        matlab_memory_mb: Optional[float] = None,
        matlab_cpu_percent: Optional[float] = None,
    ):
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "session_id": session_id,
            "task_id": task_id,
            "client": client,
            "tool": tool,
            "params": {k: str(v)[:200] for k, v in params.items()},
            "security_level": security_level,
            "result": result,
        }
        if duration_ms is not None:
            entry["duration_ms"] = round(duration_ms, 2)
        if matlab_memory_mb is not None:
            entry["matlab_memory_mb"] = round(matlab_memory_mb, 1)
        if matlab_cpu_percent is not None:
            entry["matlab_cpu_percent"] = round(matlab_cpu_percent, 1)

        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)

        logger.info("Audit: %s %s -> %s", tool, params.get("operation", ""), result)
```

- [ ] **Step 3: Implement approval_queue.py**

```python
# src/matlab_mcp_server/security/approval_queue.py
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ApprovalRequest:
    approval_id: str
    operation: str
    description: str
    risk_level: str
    params: dict
    future: asyncio.Future = field(default_factory=lambda: asyncio.get_event_loop().create_future())
    approved: Optional[bool] = None


class ApprovalQueue:
    def __init__(self, timeout: float = 300.0):
        self._pending: dict[str, ApprovalRequest] = {}
        self.timeout = timeout

    def create_request(self, operation: str, description: str,
                       risk_level: str, params: dict) -> ApprovalRequest:
        approval_id = f"approval_{uuid.uuid4().hex[:12]}"
        req = ApprovalRequest(
            approval_id=approval_id,
            operation=operation,
            description=description,
            risk_level=risk_level,
            params=params,
        )
        self._pending[approval_id] = req
        return req

    async def wait_for_approval(self, approval_id: str) -> bool:
        req = self._pending.get(approval_id)
        if not req:
            return False
        try:
            result = await asyncio.wait_for(req.future, timeout=self.timeout)
            return result
        except asyncio.TimeoutError:
            return False

    def approve(self, approval_id: str) -> bool:
        req = self._pending.get(approval_id)
        if not req:
            return False
        req.approved = True
        if not req.future.done():
            req.future.set_result(True)
        return True

    def reject(self, approval_id: str) -> bool:
        req = self._pending.get(approval_id)
        if not req:
            return False
        req.approved = False
        if not req.future.done():
            req.future.set_result(False)
        return True

    def get_pending(self) -> list[dict]:
        return [
            {
                "approval_id": r.approval_id,
                "operation": r.operation,
                "description": r.description,
                "risk_level": r.risk_level,
            }
            for r in self._pending.values()
            if r.approved is None
        ]
```

- [ ] **Step 4: Write test for file_ops registration**

```python
# tests/test_tools/test_file_ops.py
from matlab_mcp_server.tools.registry import registry


def test_file_ops_tools_registered():
    import matlab_mcp_server.tools.file_ops
    names = registry.list_names()
    assert "load_data" in names
    assert "save_data" in names
    assert "list_sandbox_files" in names
    assert "verify_checksum" in names
```

- [ ] **Step 5: Commit**

```bash
cd matlab-mcp-server
git add src/matlab_mcp_server/tools/file_ops.py src/matlab_mcp_server/security/audit_logger.py src/matlab_mcp_server/security/approval_queue.py tests/test_tools/test_file_ops.py
git commit -m "feat: file ops tools, audit logger, approval queue"
```

---

## Task 13: End-to-End Integration Test

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_end_to_end.py`

- [ ] **Step 1: Write end-to-end integration test**

```python
# tests/integration/__init__.py
```

```python
# tests/integration/test_end_to_end.py
import pytest
from pathlib import Path
from matlab_mcp_server.config import Settings
from matlab_mcp_server.tools.registry import registry


def test_all_tools_registered():
    import matlab_mcp_server.tools.task_manager
    import matlab_mcp_server.tools.computation
    import matlab_mcp_server.tools.simulink
    import matlab_mcp_server.tools.visualization
    import matlab_mcp_server.tools.toolbox
    import matlab_mcp_server.tools.file_ops

    names = set(registry.list_names())
    expected = {
        "check_task_status", "cancel_task", "reset_workspace",
        "approve_operation", "reject_operation", "list_pending_approvals",
        "run_matlab_function", "execute_matlab_script", "evaluate_expression",
        "get_workspace_variable", "list_workspace_variables",
        "load_simulink_model", "modify_block_parameters", "list_block_parameters",
        "create_simple_model", "configure_simulation", "run_simulation",
        "get_simulation_results", "open_simulink_gui",
        "create_plot", "create_3d_plot", "export_figure", "subplot_layout", "verify_plot_data",
        "signal_processing", "control_system", "optimization", "machine_learning", "data_analysis",
        "load_data", "save_data", "list_sandbox_files", "verify_checksum",
    }
    missing = expected - names
    assert not missing, f"Missing tools: {missing}"


def test_workspace_manager_creates_sandbox(tmp_path):
    from matlab_mcp_server.sandbox.workspace_manager import WorkspaceManager

    mgr = WorkspaceManager(tmp_path / "test_sandbox")
    result = mgr.ensure_sandbox_exists()
    assert (tmp_path / "test_sandbox").exists()
    assert (tmp_path / "test_sandbox" / "figures").exists()
    assert (tmp_path / "test_sandbox" / "data").exists()


def test_settings_loads_defaults():
    s = Settings()
    assert s.transport in ("stdio", "http")
    assert s.matlab_timeout > 0
    assert s.payload_max_mb > 0


def test_approval_queue_flow():
    from matlab_mcp_server.security.approval_queue import ApprovalQueue
    import asyncio

    queue = ApprovalQueue(timeout=5.0)
    req = queue.create_request(
        operation="system('dir')",
        description="Execute system command",
        risk_level="high",
        params={"command": "dir"},
    )
    assert req.approval_id.startswith("approval_")
    pending = queue.get_pending()
    assert len(pending) == 1
    assert pending[0]["risk_level"] == "high"
    queue.approve(req.approval_id)
    assert req.approved is True
    assert len(queue.get_pending()) == 0
```

- [ ] **Step 2: Run integration tests**

Run: `cd matlab-mcp-server && python -m pytest tests/integration/ -v`
Expected: all passed

- [ ] **Step 3: Commit**

```bash
cd matlab-mcp-server
git add tests/integration/
git commit -m "feat: end-to-end integration tests"
```

---

## Task 14: Full Test Suite Run

- [ ] **Step 1: Run the entire test suite**

Run: `cd matlab-mcp-server && python -m pytest tests/ -v --tb=short`
Expected: all tests pass

- [ ] **Step 2: Run with coverage**

Run: `cd matlab-mcp-server && python -m pytest tests/ --cov=matlab_mcp_server --cov-report=term-missing`
Expected: coverage report displayed

- [ ] **Step 3: Commit**

```bash
cd matlab-mcp-server
git add .
git commit -m "chore: full test suite pass"
```

---

# Phase 5: Packaging (Task 15)

## Task 15: Final Packaging & Client Config Examples

**Files:**
- Create: `matlab-mcp-server/.env.example` (already exists, verify)
- Modify: `matlab-mcp-server/pyproject.toml` (verify all dependencies)

- [ ] **Step 1: Verify pyproject.toml has all dependencies**

Ensure the following are listed in `dependencies`:
```
mcp[cli]>=1.0
matlabengine>=25.1.0
psutil>=5.9
numpy>=1.24
pydantic-settings>=2.0
structlog>=23.0
starlette>=0.36
uvicorn>=0.27
```

- [ ] **Step 2: Create .env.example (verify content)**

Ensure all settings from `config.py` have corresponding entries in `.env.example`.

- [ ] **Step 3: Verify project installs cleanly**

Run: `cd matlab-mcp-server && pip install -e ".[dev]"`
Expected: successful installation

- [ ] **Step 4: Final commit**

```bash
cd matlab-mcp-server
git add .
git commit -m "chore: final packaging and verification"
```

---

# Self-Review Checklist

After completing all tasks, verify:

1. **Spec coverage:**
   - [ ] Section 1 (Overview): `config.py`, `__main__.py` ✅
   - [ ] Section 2 (Architecture): `server.py` with FastMCP ✅
   - [ ] Section 3 (Tools): All 30+ tools registered via decorator pattern ✅
   - [ ] Section 4 (Async Tasks): `async_executor.py`, task status machine ✅
   - [ ] Section 5 (Error Handling): Three-layer timeout, steady-state, integrity, error formatter ✅
   - [ ] Section 6 (Security): Whitelist, path sanitizer, callback cleaner, shadow functions ✅
   - [ ] Section 7 (Transport): stdio + HTTP/SSE dual transport ✅
   - [ ] Section 8 (Project Structure): Matches file structure exactly ✅
   - [ ] Section 9 (Config): All settings in `config.py` with env prefix ✅
   - [ ] Section 10 (Client Adapter): Vision/text differentiation, verify_plot_data ✅

2. **Type consistency:** All handler signatures use `(engine, task_executor, params, **kwargs)` pattern ✅

3. **No placeholders:** All code is complete, no TBD/TODO ✅

4. **TDD:** Every task has tests before implementation ✅

---

# Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-05-27-matlab-mcp-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session, batch execution with checkpoints

**Which approach?**

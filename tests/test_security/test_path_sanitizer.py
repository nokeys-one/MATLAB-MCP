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

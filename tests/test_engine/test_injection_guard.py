import pytest
from unittest.mock import patch, MagicMock
from matlab_mcp_server.engine.injection_guard import pre_execute_check, InjectionBlockedError
from matlab_mcp_server.security.injection_detector import InjectionRisk


def test_safe_code_passes():
    pre_execute_check("x = sin(0); y = cos(pi);")


def test_blocked_code_raises():
    with pytest.raises(InjectionBlockedError) as exc_info:
        pre_execute_check("eval('dangerous code')")
    assert len(exc_info.value.risks) > 0


def test_blocked_code_contains_eval():
    with pytest.raises(InjectionBlockedError) as exc_info:
        pre_execute_check("eval('x = 1')")
    keywords = [r.keyword for r in exc_info.value.risks]
    assert "eval" in keywords


def test_blocked_code_contains_feval():
    with pytest.raises(InjectionBlockedError) as exc_info:
        pre_execute_check("feval('system', 'rm -rf /')")
    keywords = [r.keyword for r in exc_info.value.risks]
    assert "feval" in keywords


def test_warn_only_code_passes():
    pre_execute_check("system('ls')")


def test_injection_blocked_error_message():
    risks = [
        InjectionRisk(keyword="eval", severity="block", line=1, context="eval('x')", reason="test"),
        InjectionRisk(keyword="feval", severity="block", line=2, context="feval('f')", reason="test"),
    ]
    error = InjectionBlockedError(risks)
    assert "eval" in str(error)
    assert "feval" in str(error)


def test_injection_blocked_error_risks_attribute():
    risks = [
        InjectionRisk(keyword="eval", severity="block", line=1, context="eval('x')", reason="test"),
    ]
    error = InjectionBlockedError(risks)
    assert error.risks == risks


def test_pre_execute_check_with_empty_code():
    pre_execute_check("")


def test_pre_execute_check_with_comment_only():
    pre_execute_check("% this is a comment")


def test_pre_execute_check_with_safe_functions():
    pre_execute_check("result = fft([1 2 3 4]); plot(result);")


def test_pre_execute_check_string_concat_evasion():
    with pytest.raises(InjectionBlockedError):
        pre_execute_check("strcat('sy', 'stem', ' ls')")


def test_pre_execute_check_multiple_dangers():
    with pytest.raises(InjectionBlockedError) as exc_info:
        pre_execute_check("eval('x=1'); feval('system', 'ls')")
    assert len(exc_info.value.risks) >= 2

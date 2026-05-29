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

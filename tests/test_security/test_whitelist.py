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

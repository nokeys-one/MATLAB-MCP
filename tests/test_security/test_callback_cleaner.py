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

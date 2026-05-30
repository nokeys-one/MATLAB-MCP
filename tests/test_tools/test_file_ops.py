import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch


def test_file_ops_tools_registered():
    from matlab_mcp_server.tools.registry import registry
    import matlab_mcp_server.tools.file_ops
    names = registry.list_names()
    expected = ["load_data", "save_data", "list_sandbox_files", "verify_checksum", "delete_data"]
    for name in expected:
        assert name in names, f"Missing file ops tool: {name}"


def test_esc_helper():
    from matlab_mcp_server.tools.file_ops import _esc
    assert _esc("normal") == "normal"
    assert _esc("it's") == "it''s"
    assert _esc("a'b'c") == "a''b''c"
    assert _esc("") == ""


def test_validate_var_name():
    from matlab_mcp_server.tools.file_ops import _validate_var_name
    assert _validate_var_name("my_var") is None
    assert _validate_var_name("X1") is None
    assert _validate_var_name("_private") is None
    assert _validate_var_name("1bad") is not None
    assert _validate_var_name("has space") is not None
    assert _validate_var_name("eval('x')") is not None


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.execute = AsyncMock(return_value="")
    engine.get_variable_info = AsyncMock(return_value={"type": "double"})
    return engine


@pytest.fixture
def mock_task_executor():
    return MagicMock()


@pytest.fixture
def mock_settings(tmp_path):
    settings = MagicMock()
    settings.sandbox_dir = tmp_path / "sandbox"
    settings.sandbox_dir.mkdir(parents=True, exist_ok=True)
    return settings


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_load_data_csv(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_load_data

    result = await handle_load_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "data/test.csv"},
    )
    assert result["success"] is True
    assert result["variable_name"] == "loaded_data"
    script = mock_engine.execute.call_args[0][0]
    assert "readtable" in script


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_load_data_json(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_load_data

    result = await handle_load_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "data/test.json", "format": "json", "variable_name": "my_data"},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "jsondecode" in script
    assert "my_data" in script


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_load_data_path_traversal(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_load_data

    result = await handle_load_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "../../../etc/passwd"},
    )
    assert result["success"] is False
    assert "traversal" in result["error"].lower() or "outside sandbox" in result["error"].lower()


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_load_data_invalid_var_name(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_load_data

    result = await handle_load_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "data.csv", "variable_name": "1bad"},
    )
    assert result["success"] is False
    assert "variable name" in result["error"].lower()


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_save_data_csv(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_save_data

    result = await handle_save_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"variable_name": "T", "file_path": "output/result.csv"},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "writetable" in script
    assert "T" in script


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_save_data_mat(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_save_data

    result = await handle_save_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"variable_name": "myvar", "file_path": "output/result.mat", "format": "mat"},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "save(" in script


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_save_data_escapes_quotes(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_save_data

    result = await handle_save_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"variable_name": "T", "file_path": "output/it's.csv"},
    )
    assert result["success"] is True
    script = mock_engine.execute.call_args[0][0]
    assert "it''s" in script


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_save_data_path_traversal(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_save_data

    result = await handle_save_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"variable_name": "T", "file_path": "../../outside.csv"},
    )
    assert result["success"] is False


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_list_sandbox_files(MockSettings, mock_engine, mock_task_executor, mock_settings):
    sandbox = mock_settings.sandbox_dir
    (sandbox / "test.csv").write_text("a,b\n1,2")
    sub = sandbox / "sub"
    sub.mkdir()
    (sub / "data.mat").write_bytes(b"fake")

    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_list_sandbox_files

    result = await handle_list_sandbox_files(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={},
    )
    assert result["success"] is True
    assert result["count"] == 2
    paths = [f["path"] for f in result["files"]]
    assert any("test.csv" in p for p in paths)
    assert any("data.mat" in p for p in paths)


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_list_sandbox_files_empty(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_list_sandbox_files

    result = await handle_list_sandbox_files(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={},
    )
    assert result["success"] is True
    assert result["count"] == 0
    assert result["files"] == []


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_verify_checksum_valid(MockSettings, mock_engine, mock_task_executor, mock_settings):
    import hashlib
    sandbox = mock_settings.sandbox_dir
    content = b"test content"
    (sandbox / "data.txt").write_bytes(content)
    expected_hash = hashlib.sha256(content).hexdigest()

    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_verify_checksum

    result = await handle_verify_checksum(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "data.txt", "expected_hash": expected_hash},
    )
    assert result["success"] is True
    assert result["valid"] is True
    assert result["algorithm"] == "sha256"


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_verify_checksum_invalid(MockSettings, mock_engine, mock_task_executor, mock_settings):
    sandbox = mock_settings.sandbox_dir
    (sandbox / "data.txt").write_bytes(b"test content")

    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_verify_checksum

    result = await handle_verify_checksum(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "data.txt", "expected_hash": "00000000"},
    )
    assert result["success"] is True
    assert result["valid"] is False


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_verify_checksum_file_not_found(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_verify_checksum

    result = await handle_verify_checksum(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "missing.txt", "expected_hash": "abc"},
    )
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_verify_checksum_crc32(MockSettings, mock_engine, mock_task_executor, mock_settings):
    import zlib
    sandbox = mock_settings.sandbox_dir
    content = b"crc test"
    (sandbox / "bin.dat").write_bytes(content)
    expected_crc = format(zlib.crc32(content) & 0xFFFFFFFF, "08x")

    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_verify_checksum

    result = await handle_verify_checksum(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "bin.dat", "expected_hash": expected_crc, "algorithm": "crc32"},
    )
    assert result["success"] is True
    assert result["valid"] is True
    assert result["algorithm"] == "crc32"


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_verify_checksum_path_traversal(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_verify_checksum

    result = await handle_verify_checksum(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "../../etc/passwd", "expected_hash": "abc"},
    )
    assert result["success"] is False


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_delete_data(MockSettings, mock_engine, mock_task_executor, mock_settings):
    sandbox = mock_settings.sandbox_dir
    (sandbox / "to_delete.txt").write_bytes(b"delete me")

    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_delete_data

    result = await handle_delete_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "to_delete.txt", "reason": "cleanup"},
    )
    assert result["success"] is True
    assert result["file_path"] == "to_delete.txt"
    assert result["size_bytes"] == len(b"delete me")
    assert not (sandbox / "to_delete.txt").exists()


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_delete_data_not_found(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_delete_data

    result = await handle_delete_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "nonexistent.txt", "reason": "test"},
    )
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_delete_data_path_traversal(MockSettings, mock_engine, mock_task_executor, mock_settings):
    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_delete_data

    result = await handle_delete_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "../../important.txt", "reason": "malicious"},
    )
    assert result["success"] is False


@pytest.mark.asyncio
@patch("matlab_mcp_server.config.Settings")
async def test_delete_data_with_audit(MockSettings, mock_engine, mock_task_executor, mock_settings):
    sandbox = mock_settings.sandbox_dir
    (sandbox / "audit_test.txt").write_bytes(b"audit")

    MockSettings.return_value = mock_settings
    from matlab_mcp_server.tools.file_ops import handle_delete_data

    audit = MagicMock()
    result = await handle_delete_data(
        engine=mock_engine,
        task_executor=mock_task_executor,
        params={"file_path": "audit_test.txt", "reason": "test audit"},
        audit_logger=audit,
        session_id="sess_1",
        client="test",
    )
    assert result["success"] is True
    audit.log.assert_called_once()
    call_kwargs = audit.log.call_args
    assert call_kwargs[1]["tool"] == "delete_data"
    assert call_kwargs[1]["result"] == "deleted"

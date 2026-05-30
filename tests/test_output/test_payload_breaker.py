import pytest
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
    with tempfile.TemporaryDirectory() as tmp:
        response = {"success": True, "data": [1, 2, 3]}
        small_result = PayloadBreaker(max_payload_mb=5, sandbox_dir=Path(tmp)).check_and_break(dict(response), "t1")
        large_result = PayloadBreaker(max_payload_mb=0, sandbox_dir=Path(tmp)).check_and_break(dict(response), "t2")
        assert small_result["integrity"]["checksum"] == large_result["integrity"]["checksum"]


def test_large_payload_contains_correct_task_id():
    with tempfile.TemporaryDirectory() as tmp:
        breaker = PayloadBreaker(max_payload_mb=0, sandbox_dir=Path(tmp))
        response = {"success": True, "data": "x" * 10000}
        result = breaker.check_and_break(response, "task_abc")
        assert "task_abc" in result["file_path"]


def test_small_payload_has_integrity_fields():
    with tempfile.TemporaryDirectory() as tmp:
        breaker = PayloadBreaker(max_payload_mb=5, sandbox_dir=Path(tmp))
        response = {"success": True}
        result = breaker.check_and_break(response, "task_003")
        integrity = result["integrity"]
        assert "checksum" in integrity
        assert "algorithm" in integrity
        assert "data_size_bytes" in integrity
        assert "timestamp" in integrity


def test_large_payload_checksum_file_content():
    with tempfile.TemporaryDirectory() as tmp:
        breaker = PayloadBreaker(max_payload_mb=0, sandbox_dir=Path(tmp))
        response = {"success": True, "data": "x" * 10000}
        result = breaker.check_and_break(response, "task_004")
        checksum_from_file = Path(result["checksum_file"]).read_text()
        assert checksum_from_file == result["integrity"]["checksum"]

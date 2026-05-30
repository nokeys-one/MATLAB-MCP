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
    assert result["image_format"] == "png"
    Path(tmp_path).unlink()


def test_text_client_no_base64():
    adapter = ClientAdapter(client_vision=False)
    response = {"success": True, "figure_path": "/some/path.png"}
    result = adapter.adapt_image_response(response, "/some/path.png")
    assert "image_base64" not in result
    assert "instruction" in result
    assert "MATLAB" in result["instruction"]


def test_text_client_strips_existing_base64():
    adapter = ClientAdapter(client_vision=False)
    response = {"success": True, "image_base64": "should_be_removed"}
    result = adapter.adapt_image_response(response, "/nonexistent.png")
    assert "image_base64" not in result
    assert "instruction" in result


def test_large_data_flagged():
    adapter = ClientAdapter()
    response = {"success": True, "data": list(range(1000))}
    result = adapter.adapt_data_response(response, 1000, full_data_threshold=100)
    assert result["data_truncated"] is True
    assert "suggestion" in result


def test_small_data_not_flagged():
    adapter = ClientAdapter()
    response = {"success": True, "data": list(range(10))}
    result = adapter.adapt_data_response(response, 10, full_data_threshold=100)
    assert "data_truncated" not in result


def test_vision_client_missing_file():
    adapter = ClientAdapter(client_vision=True)
    response = {"success": True}
    result = adapter.adapt_image_response(response, "/nonexistent/path.png")
    assert result["success"] is True
    assert "image_base64" not in result


def test_get_capabilities():
    adapter = ClientAdapter(client_vision=True, context_limit=50000)
    caps = adapter.get_capabilities()
    assert caps["client_vision"] is True
    assert caps["context_limit"] == 50000


def test_truncate_output_no_truncation():
    adapter = ClientAdapter(context_limit=100)
    result = adapter.truncate_output("short text")
    assert result == "short text"


def test_truncate_output_with_truncation():
    adapter = ClientAdapter(context_limit=10)
    result = adapter.truncate_output("this is a long string")
    assert "truncated" in result
    assert len(result) < len("this is a long string") + 50


def test_adapt_image_response_svg():
    adapter = ClientAdapter(client_vision=True)
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        f.write(b"<svg></svg>")
        tmp_path = f.name
    response = {"success": True}
    result = adapter.adapt_image_response(response, tmp_path)
    assert result["image_format"] == "svg"
    Path(tmp_path).unlink()

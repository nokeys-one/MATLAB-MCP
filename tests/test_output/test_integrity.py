import pytest
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
    integrity = add_integrity(b"test")
    assert "checksum" in integrity
    assert "algorithm" in integrity
    assert "data_size_bytes" in integrity
    assert "timestamp" in integrity


def test_unsupported_algorithm():
    with pytest.raises(ValueError, match="Unsupported algorithm"):
        compute_checksum(b"test", "md5")


def test_crc32_deterministic():
    data = b"deterministic test"
    h1 = compute_checksum(data, "crc32")
    h2 = compute_checksum(data, "crc32")
    assert h1 == h2


def test_sha256_deterministic():
    data = b"deterministic test"
    h1 = compute_checksum(data, "sha256")
    h2 = compute_checksum(data, "sha256")
    assert h1 == h2


def test_add_integrity_auto_selects_crc32_for_large():
    data = b"x" * (2 * 1024 * 1024)
    integrity = add_integrity(data)
    assert integrity["algorithm"] == "crc32"


def test_add_integrity_auto_selects_sha256_for_small():
    data = b"small"
    integrity = add_integrity(data)
    assert integrity["algorithm"] == "sha256"

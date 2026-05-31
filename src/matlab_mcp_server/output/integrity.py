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


def add_integrity(data_bytes: bytes) -> dict:
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

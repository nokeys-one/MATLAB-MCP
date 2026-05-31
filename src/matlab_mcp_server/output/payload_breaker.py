import json
from pathlib import Path
from .integrity import compute_checksum, add_integrity


class PayloadBreaker:
    def __init__(self, max_payload_mb: int = 5, sandbox_dir: Path | None = None):
        self.max_bytes = max_payload_mb * 1024 * 1024
        self.sandbox_dir = sandbox_dir or Path.home() / "matlab_mcp_sandbox"

    def check_and_break(self, response: dict, task_id: str) -> dict:
        payload_bytes = json.dumps(response, ensure_ascii=False, default=str).encode("utf-8")

        if len(payload_bytes) <= self.max_bytes:
            response["integrity"] = add_integrity(payload_bytes)
            return response

        result_file = self.sandbox_dir / f"result_{task_id}.json"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(response, f, ensure_ascii=False, default=str, indent=2)

        checksum = compute_checksum(payload_bytes)
        checksum_file = result_file.with_suffix(result_file.suffix + ".sha256")
        checksum_file.write_text(checksum)

        return {
            "success": True,
            "data_truncated": True,
            "file_path": str(result_file),
            "checksum_file": str(checksum_file),
            "payload_size_bytes": len(payload_bytes),
            "integrity": add_integrity(payload_bytes),
        }

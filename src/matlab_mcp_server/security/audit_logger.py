import json
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AuditLogger:
    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        session_id: str,
        task_id: Optional[str],
        client: str,
        tool: str,
        params: dict,
        security_level: str,
        result: str,
        duration_ms: Optional[float] = None,
        matlab_memory_mb: Optional[float] = None,
        matlab_cpu_percent: Optional[float] = None,
    ):
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "session_id": session_id,
            "task_id": task_id,
            "client": client,
            "tool": tool,
            "params": {k: str(v)[:200] for k, v in params.items()},
            "security_level": security_level,
            "result": result,
        }
        if duration_ms is not None:
            entry["duration_ms"] = round(duration_ms, 2)
        if matlab_memory_mb is not None:
            entry["matlab_memory_mb"] = round(matlab_memory_mb, 1)
        if matlab_cpu_percent is not None:
            entry["matlab_cpu_percent"] = round(matlab_cpu_percent, 1)

        line = json.dumps(entry, ensure_ascii=False) + "\n"
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError as e:
            logger.warning("Failed to write audit log: %s", e)

        logger.info("Audit: %s %s -> %s", tool, params.get("operation", ""), result)

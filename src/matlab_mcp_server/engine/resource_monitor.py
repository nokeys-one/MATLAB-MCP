import threading
import time
import logging
from typing import Optional, Callable
import psutil

logger = logging.getLogger(__name__)


class ResourceMonitor:
    def __init__(self, pid: Optional[int] = None,
                 cpu_threshold: float = 0.95,
                 memory_threshold: float = 0.80,
                 heartbeat_interval: int = 10,
                 on_resource_exceeded: Optional[Callable] = None,
                 on_process_unresponsive: Optional[Callable] = None):
        self.pid = pid
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.heartbeat_interval = heartbeat_interval
        self._on_resource_exceeded = on_resource_exceeded
        self._on_process_unresponsive = on_process_unresponsive
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._process: Optional[psutil.Process] = None
        self._last_heartbeat: float = time.time()
        self._warnings: list = []

    def start(self, pid: int):
        self.pid = pid
        try:
            self._process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            logger.error("Cannot monitor: process %s does not exist", pid)
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Resource monitor started for PID %s", pid)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self):
        while self._running:
            try:
                if not self._process or not self._process.is_running():
                    if self._on_process_unresponsive:
                        self._on_process_unresponsive(self.pid)
                    break
                cpu_pct = self._process.cpu_percent(interval=1.0) / 100.0
                mem_info = self._process.memory_info()
                mem_pct = mem_info.rss / psutil.virtual_memory().total

                if cpu_pct > self.cpu_threshold:
                    warning = {"type": "high_cpu", "value": cpu_pct, "timestamp": time.time()}
                    self._warnings.append(warning)
                    logger.warning("High CPU: %.1f%%", cpu_pct * 100)
                    if self._on_resource_exceeded:
                        self._on_resource_exceeded("cpu", cpu_pct)

                if mem_pct > self.memory_threshold:
                    warning = {"type": "high_memory", "value": mem_pct, "timestamp": time.time()}
                    self._warnings.append(warning)
                    logger.warning("High memory: %.1f%%", mem_pct * 100)
                    if self._on_resource_exceeded:
                        self._on_resource_exceeded("memory", mem_pct)

                self._last_heartbeat = time.time()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                if self._on_process_unresponsive:
                    self._on_process_unresponsive(self.pid)
                break
            except Exception:
                logger.debug("Resource monitor iteration failed", exc_info=True)
                break
            time.sleep(self.heartbeat_interval)

    def get_status(self) -> dict:
        result = {"monitoring": self._running, "pid": self.pid, "warnings": list(self._warnings)}
        if self._process and self._process.is_running():
            try:
                result["cpu_percent"] = self._process.cpu_percent()
                result["memory_rss_mb"] = self._process.memory_info().rss / (1024 * 1024)
            except Exception:
                pass
        return result

    def force_kill(self) -> bool:
        if not self._process:
            return False
        try:
            self._process.terminate()
            self._process.wait(timeout=5)
            return True
        except psutil.TimeoutExpired:
            try:
                self._process.kill()
                self._process.wait(timeout=5)
                return True
            except Exception:
                return False
        except Exception:
            return False

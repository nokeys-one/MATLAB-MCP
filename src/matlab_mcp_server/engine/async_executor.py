import asyncio
import threading
import uuid
import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ORPHANED = "orphaned"


@dataclass
class Task:
    task_id: str
    tool_name: str
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[dict] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: float = 0.0


TERMINAL_STATUSES = frozenset({
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
})


class AsyncTaskExecutor:
    def __init__(self, max_workers: int = 2, task_ttl_seconds: float = 3600.0):
        self._tasks: dict[str, Task] = {}
        self._futures: dict[str, asyncio.Future] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cancel_events: dict[str, threading.Event] = {}
        self._task_ttl_seconds = task_ttl_seconds

    def submit(self, tool_name: str, func: Callable, *args, **kwargs) -> str:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task = Task(task_id=task_id, tool_name=tool_name)
        self._tasks[task_id] = task
        cancel_event = threading.Event()
        self._cancel_events[task_id] = cancel_event

        async def run_task():
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self._executor, lambda: func(*args, **kwargs)
                )
                if cancel_event.is_set():
                    task.status = TaskStatus.CANCELLED
                else:
                    task.result = result
                    task.status = TaskStatus.COMPLETED
            except Exception as e:
                task.error = {"type": type(e).__name__, "message": str(e)}
                task.status = TaskStatus.FAILED
            finally:
                task.completed_at = time.time()
                self._cleanup_expired()

        self._futures[task_id] = asyncio.ensure_future(run_task())
        return task_id

    def _cleanup_expired(self):
        now = time.time()
        expired_ids = []
        for task_id, task in self._tasks.items():
            if task.status in TERMINAL_STATUSES and task.completed_at:
                if now - task.completed_at > self._task_ttl_seconds:
                    expired_ids.append(task_id)

        for tid in expired_ids:
            self._tasks.pop(tid, None)
            self._futures.pop(tid, None)
            self._cancel_events.pop(tid, None)

        if expired_ids:
            logger.debug("Cleaned up %d expired tasks", len(expired_ids))

    def cleanup_completed(self) -> int:
        removed = 0
        for task_id in list(self._tasks.keys()):
            task = self._tasks[task_id]
            if task.status in TERMINAL_STATUSES:
                self._tasks.pop(task_id, None)
                self._futures.pop(task_id, None)
                self._cancel_events.pop(task_id, None)
                removed += 1
        return removed

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_status(self, task_id: str) -> Optional[dict]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        elapsed = None
        if task.started_at:
            end = task.completed_at or time.time()
            elapsed = round(end - task.started_at, 2)
        return {
            "task_id": task.task_id,
            "tool_name": task.tool_name,
            "status": task.status.value,
            "progress": task.progress,
            "elapsed_seconds": elapsed,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
        }

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.status == TaskStatus.RUNNING:
            event = self._cancel_events.get(task_id)
            if event:
                event.set()
            task.status = TaskStatus.CANCELLING
            return True
        return False

    def is_cancelled(self, task_id: str) -> bool:
        event = self._cancel_events.get(task_id)
        return event.is_set() if event is not None else False

    def get_cancel_event(self, task_id: str) -> Optional[threading.Event]:
        return self._cancel_events.get(task_id)

    def mark_orphaned(self, task_id: str, ttl_seconds: int):
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.ORPHANED
            event = self._cancel_events.get(task_id)
            if event:
                event.set()

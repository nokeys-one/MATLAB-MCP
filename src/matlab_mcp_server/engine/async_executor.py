import asyncio
import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor


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


class AsyncTaskExecutor:
    def __init__(self, max_workers: int = 2):
        self._tasks: dict[str, Task] = {}
        self._futures: dict[str, asyncio.Future] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cancel_flags: dict[str, bool] = {}

    def submit(self, tool_name: str, func: Callable, *args, **kwargs) -> str:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task = Task(task_id=task_id, tool_name=tool_name)
        self._tasks[task_id] = task
        self._cancel_flags[task_id] = False

        async def run_task():
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self._executor, lambda: func(*args, **kwargs)
                )
                if self._cancel_flags.get(task_id):
                    task.status = TaskStatus.CANCELLED
                else:
                    task.result = result
                    task.status = TaskStatus.COMPLETED
            except Exception as e:
                task.error = {"type": type(e).__name__, "message": str(e)}
                task.status = TaskStatus.FAILED
            finally:
                task.completed_at = time.time()

        self._futures[task_id] = asyncio.ensure_future(run_task())
        return task_id

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

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.status == TaskStatus.RUNNING:
            self._cancel_flags[task_id] = True
            task.status = TaskStatus.CANCELLING
            return True
        return False

    def is_cancelled(self, task_id: str) -> bool:
        return self._cancel_flags.get(task_id, False)

    def mark_orphaned(self, task_id: str, ttl_seconds: int):
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.ORPHANED

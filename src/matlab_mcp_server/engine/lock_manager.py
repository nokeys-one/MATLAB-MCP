import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class EngineState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    CANCELLING = "cancelling"
    RESTARTING = "restarting"


class EngineBusyError(Exception):
    def __init__(self, current_task_id: Optional[str] = None,
                 current_task_type: Optional[str] = None,
                 message: str = ""):
        self.current_task_id = current_task_id
        self.current_task_type = current_task_type
        super().__init__(message or "MATLAB Engine is busy")


QUERY_TOOLS = frozenset({
    "check_task_status",
    "list_sandbox_files",
    "cancel_task",
    "get_server_info",
    "approve_operation",
    "reject_operation",
    "list_pending_approvals",
})


class EngineLockManager:
    def __init__(self):
        self._state = EngineState.IDLE
        self._lock = asyncio.Lock()
        self._current_task_id: Optional[str] = None
        self._current_task_type: Optional[str] = None

    @property
    def state(self) -> EngineState:
        return self._state

    async def acquire(self, tool_name: str, timeout: float = 5.0) -> bool:
        if tool_name in QUERY_TOOLS:
            return True
        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            raise EngineBusyError(
                current_task_id=self._current_task_id,
                current_task_type=self._current_task_type,
                message=(
                    f"MATLAB Engine is busy running '{self._current_task_type}' "
                    f"(task_id={self._current_task_id}). "
                    f"Use check_task_status() to monitor or cancel_task() to abort."
                ),
            )
        if self._state == EngineState.RUNNING:
            self._lock.release()
            raise EngineBusyError(
                current_task_id=self._current_task_id,
                current_task_type=self._current_task_type,
                message=(
                    f"MATLAB Engine is busy running '{self._current_task_type}' "
                    f"(task_id={self._current_task_id}). "
                    f"Use check_task_status() to monitor or cancel_task() to abort."
                ),
            )
        self._state = EngineState.RUNNING
        return True

    async def acquire_with_task(self, tool_name: str, task_id: str) -> bool:
        result = await self.acquire(tool_name)
        if result:
            self._current_task_id = task_id
            self._current_task_type = tool_name
        return result

    async def release(self):
        self._state = EngineState.IDLE
        self._current_task_id = None
        self._current_task_type = None
        if self._lock.locked():
            self._lock.release()

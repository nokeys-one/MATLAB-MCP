import pytest
import asyncio
from matlab_mcp_server.engine.async_executor import AsyncTaskExecutor, TaskStatus


@pytest.mark.asyncio
async def test_submit_returns_task_id():
    executor = AsyncTaskExecutor()
    task_id = executor.submit("test_tool", lambda: 42)
    assert task_id.startswith("task_")


@pytest.mark.asyncio
async def test_task_completes_with_result():
    executor = AsyncTaskExecutor()
    task_id = executor.submit("test_tool", lambda: 42)
    await asyncio.sleep(0.5)
    status = executor.get_status(task_id)
    assert status["status"] == TaskStatus.COMPLETED.value
    task = executor.get_task(task_id)
    assert task.result == 42


@pytest.mark.asyncio
async def test_task_failure_captured():
    def failing():
        raise ValueError("test error")

    executor = AsyncTaskExecutor()
    task_id = executor.submit("test_tool", failing)
    await asyncio.sleep(0.5)
    status = executor.get_status(task_id)
    assert status["status"] == TaskStatus.FAILED.value
    task = executor.get_task(task_id)
    assert task.error["type"] == "ValueError"


@pytest.mark.asyncio
async def test_cancel_running_task():
    def slow_task():
        import time
        time.sleep(10)
        return "done"

    executor = AsyncTaskExecutor()
    task_id = executor.submit("slow_tool", slow_task)
    await asyncio.sleep(0.2)
    assert executor.cancel(task_id) is True
    task = executor.get_task(task_id)
    assert task.status == TaskStatus.CANCELLING


def test_get_status_unknown_task():
    executor = AsyncTaskExecutor()
    assert executor.get_status("nonexistent") is None

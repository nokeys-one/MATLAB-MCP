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
    assert status is not None
    assert status["status"] == TaskStatus.COMPLETED.value
    task = executor.get_task(task_id)
    assert task is not None
    assert task.result == 42


@pytest.mark.asyncio
async def test_task_failure_captured():
    def failing():
        raise ValueError("test error")

    executor = AsyncTaskExecutor()
    task_id = executor.submit("test_tool", failing)
    await asyncio.sleep(0.5)
    status = executor.get_status(task_id)
    assert status is not None
    assert status["status"] == TaskStatus.FAILED.value
    task = executor.get_task(task_id)
    assert task is not None
    assert task.error is not None
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
    assert task is not None
    assert task.status == TaskStatus.CANCELLING


def test_get_status_unknown_task():
    executor = AsyncTaskExecutor()
    assert executor.get_status("nonexistent") is None


@pytest.mark.asyncio
async def test_cleanup_completed_removes_finished_tasks():
    executor = AsyncTaskExecutor()
    task_id1 = executor.submit("tool1", lambda: 1)
    task_id2 = executor.submit("tool2", lambda: 2)
    await asyncio.sleep(0.5)
    assert executor.task_count == 2
    removed = executor.cleanup_completed()
    assert removed == 2
    assert executor.task_count == 0
    assert executor.get_task(task_id1) is None
    assert executor.get_task(task_id2) is None


@pytest.mark.asyncio
async def test_cleanup_completed_preserves_running_tasks():
    def slow():
        import time
        time.sleep(10)
        return "done"

    executor = AsyncTaskExecutor()
    task_id = executor.submit("slow_tool", slow)
    await asyncio.sleep(0.1)
    removed = executor.cleanup_completed()
    assert removed == 0
    assert executor.task_count == 1
    executor.cancel(task_id)


@pytest.mark.asyncio
async def test_auto_cleanup_after_ttl():
    executor = AsyncTaskExecutor(task_ttl_seconds=0.1)
    executor.submit("tool1", lambda: 1)
    await asyncio.sleep(0.3)
    executor.submit("tool2", lambda: 2)
    await asyncio.sleep(0.3)
    assert executor.task_count == 1


@pytest.mark.asyncio
async def test_task_count_property():
    executor = AsyncTaskExecutor()
    assert executor.task_count == 0
    executor.submit("tool1", lambda: 1)
    assert executor.task_count == 1
    executor.submit("tool2", lambda: 2)
    assert executor.task_count == 2


@pytest.mark.asyncio
async def test_close_shuts_down_executor():
    executor = AsyncTaskExecutor()
    executor.submit("tool1", lambda: 1)
    await asyncio.sleep(0.3)
    await executor.close()
    assert executor._executor._shutdown is True


@pytest.mark.asyncio
async def test_close_cancels_running_tasks():
    def slow():
        import time
        time.sleep(30)
        return "done"

    executor = AsyncTaskExecutor()
    task_id = executor.submit("slow_tool", slow)
    await asyncio.sleep(0.1)
    await executor.close()
    task = executor.get_task(task_id)
    assert task is not None
    assert task.status == TaskStatus.CANCELLING

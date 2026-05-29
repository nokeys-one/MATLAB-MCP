import pytest
import asyncio
from matlab_mcp_server.engine.lock_manager import EngineLockManager, EngineState, EngineBusyError


@pytest.mark.asyncio
async def test_query_tools_bypass_lock():
    mgr = EngineLockManager()
    assert await mgr.acquire("check_task_status") is True
    assert await mgr.acquire("cancel_task") is True
    assert await mgr.acquire("list_sandbox_files") is True
    assert await mgr.acquire("approve_operation") is True
    assert await mgr.acquire("reject_operation") is True
    assert await mgr.acquire("list_pending_approvals") is True


@pytest.mark.asyncio
async def test_engine_busy_returns_error():
    mgr = EngineLockManager()
    await mgr.acquire("run_simulation", timeout=0.1)
    assert mgr._state == EngineState.RUNNING

    with pytest.raises(EngineBusyError):
        await mgr.acquire("create_plot", timeout=0.1)

    await mgr.release()
    assert mgr._state == EngineState.IDLE


@pytest.mark.asyncio
async def test_no_toctou_race_condition():
    mgr = EngineLockManager()
    results = []
    barrier = asyncio.Event()

    async def task_a():
        await barrier.wait()
        try:
            await mgr.acquire("run_simulation", timeout=0.1)
            results.append("a_acquired")
        except EngineBusyError:
            results.append("a_busy")

    async def task_b():
        await barrier.wait()
        try:
            await mgr.acquire("create_plot", timeout=0.1)
            results.append("b_acquired")
        except EngineBusyError:
            results.append("b_busy")

    t1 = asyncio.create_task(task_a())
    t2 = asyncio.create_task(task_b())
    barrier.set()
    await asyncio.gather(t1, t2)

    acquired_count = results.count("a_acquired") + results.count("b_acquired")
    busy_count = results.count("a_busy") + results.count("b_busy")
    assert acquired_count == 1
    assert busy_count == 1
    await mgr.release()


@pytest.mark.asyncio
async def test_acquire_release_cycle():
    mgr = EngineLockManager()
    assert mgr._state == EngineState.IDLE
    await mgr.acquire("fft", timeout=0.1)
    assert mgr._state == EngineState.RUNNING
    await mgr.release()
    assert mgr._state == EngineState.IDLE


@pytest.mark.asyncio
async def test_acquire_with_task():
    mgr = EngineLockManager()
    result = await mgr.acquire_with_task("run_simulation", "task_abc123")
    assert result is True
    assert mgr._current_task_id == "task_abc123"
    assert mgr._current_task_type == "run_simulation"
    await mgr.release()
    assert mgr._current_task_id is None


@pytest.mark.asyncio
async def test_state_property():
    mgr = EngineLockManager()
    assert mgr.state == EngineState.IDLE
    await mgr.acquire("fft", timeout=0.1)
    assert mgr.state == EngineState.RUNNING
    await mgr.release()
    assert mgr.state == EngineState.IDLE


@pytest.mark.asyncio
async def test_release_when_not_locked():
    mgr = EngineLockManager()
    await mgr.release()
    assert mgr._state == EngineState.IDLE

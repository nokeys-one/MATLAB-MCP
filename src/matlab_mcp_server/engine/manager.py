import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class MatlabEngineManager:
    def __init__(self, sandbox_dir: Path, shadow_dir: Path,
                 enable_injection_check: bool = True):
        self.sandbox_dir = sandbox_dir
        self.shadow_dir = shadow_dir
        self._engine: Any = None
        self._engine_started = False
        self._pid: Optional[int] = None
        self._enable_injection_check = enable_injection_check
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def start(self) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._start_engine_sync)

    def _start_engine_sync(self) -> bool:
        try:
            import matlab.engine  # pyright: ignore[reportMissingImports]
            self._engine = matlab.engine.start_matlab()
            self._engine_started = True
            try:
                self._pid = self._engine.pid if hasattr(self._engine, 'pid') else os.getpid()
            except Exception:
                self._pid = None
            shadow_path = str(self.shadow_dir).replace("\\", "/")
            self._engine.addpath(shadow_path, nargout=0)
            self._engine.cd(str(self.sandbox_dir), nargout=0)
            logger.info("MATLAB Engine started (PID=%s)", self._pid)
            return True
        except Exception as e:
            logger.error("Failed to start MATLAB Engine: %s", e)
            return False

    async def stop(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self._stop_engine_sync)

    async def close(self):
        await self.stop()
        self._executor.shutdown(wait=True)

    def _stop_engine_sync(self):
        if self._engine is not None:
            try:
                self._engine.quit()
            except Exception:
                pass
            self._engine = None
            self._engine_started = False
            self._pid = None

    async def restart(self) -> bool:
        await self.stop()
        return await self.start()

    async def execute(self, code: str, skip_injection_check: bool = False) -> str:
        if not self._engine_started:
            raise RuntimeError("MATLAB Engine not started")
        if self._enable_injection_check and not skip_injection_check:
            from .injection_guard import pre_execute_check
            pre_execute_check(code)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, lambda: self._execute_sync(code)
        )

    def _execute_sync(self, code: str) -> str:
        engine = self._engine
        assert engine is not None
        try:
            result = engine.eval(code, nargout=1)
            return str(result) if result is not None else ""
        except Exception as e:
            logger.error("MATLAB execution error: %s", e)
            raise

    async def get_variable_info(self, var_name: str, max_rows: int = 100) -> dict:
        if not self._engine_started:
            raise RuntimeError("MATLAB Engine not started")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, lambda: self._get_variable_info_sync(var_name, max_rows)
        )

    def _get_variable_info_sync(self, var_name: str, max_rows: int = 100) -> dict:
        engine = self._engine
        assert engine is not None
        try:
            escaped = var_name.replace("'", "''")
            value = engine.workspace[var_name]
            info = engine.eval(f"whos('{escaped}')", nargout=1)
            return {"name": var_name, "value_preview": str(value)[:500], "info": str(info)}
        except Exception as e:
            return {"name": var_name, "error": str(e)}

    async def list_workspace(self) -> str:
        if not self._engine_started:
            raise RuntimeError("MATLAB Engine not started")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self._list_workspace_sync
        )

    def _list_workspace_sync(self) -> str:
        engine = self._engine
        assert engine is not None
        result = engine.eval("whos", nargout=1)
        return str(result)

    async def clear_workspace(self):
        if self._engine_started:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor, self._clear_workspace_sync
            )

    def _clear_workspace_sync(self):
        engine = self._engine
        if engine is None:
            return
        engine.eval("clear; clc; close all;", nargout=0)
        engine.cd(str(self.sandbox_dir), nargout=0)

    @property
    def is_running(self) -> bool:
        return self._engine_started

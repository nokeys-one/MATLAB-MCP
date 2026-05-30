import asyncio
import uuid
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ApprovalRequest:
    approval_id: str
    operation: str
    description: str
    risk_level: str
    params: dict[str, Any]
    created_at: float = field(default_factory=time.time)
    resolved: bool = False
    approved: Optional[bool] = None
    future: Optional[asyncio.Future] = field(default=None)


class ApprovalQueue:
    def __init__(self, timeout: float = 300.0):
        self._pending: dict[str, ApprovalRequest] = {}
        self._timeout = timeout

    def create_request(self, operation: str, description: str,
                       risk_level: str, params: dict[str, Any]) -> ApprovalRequest:
        approval_id = f"approval_{uuid.uuid4().hex[:10]}"
        req = ApprovalRequest(
            approval_id=approval_id,
            operation=operation,
            description=description,
            risk_level=risk_level,
            params=params,
        )
        req.future = asyncio.get_running_loop().create_future()
        self._pending[approval_id] = req
        return req

    def approve(self, approval_id: str) -> bool:
        req = self._pending.get(approval_id)
        if not req or req.resolved:
            return False
        req.resolved = True
        req.approved = True
        if req.future and not req.future.done():
            req.future.set_result(True)
        return True

    def reject(self, approval_id: str) -> bool:
        req = self._pending.get(approval_id)
        if not req or req.resolved:
            return False
        req.resolved = True
        req.approved = False
        if req.future and not req.future.done():
            req.future.set_result(False)
        return True

    async def wait_for_approval(self, approval_id: str) -> bool:
        req = self._pending.get(approval_id)
        if not req or not req.future:
            return False
        try:
            result = await asyncio.wait_for(req.future, timeout=self._timeout)
            return result
        except asyncio.TimeoutError:
            req.resolved = True
            req.approved = False
            return False

    def get_pending(self) -> list[dict[str, Any]]:
        return [
            {
                "approval_id": req.approval_id,
                "operation": req.operation,
                "description": req.description,
                "risk_level": req.risk_level,
                "created_at": req.created_at,
            }
            for req in self._pending.values()
            if not req.resolved
        ]

    def get_request(self, approval_id: str) -> Optional[ApprovalRequest]:
        return self._pending.get(approval_id)

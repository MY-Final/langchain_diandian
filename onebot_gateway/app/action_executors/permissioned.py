"""带权限校验的 action 执行器基类。"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from onebot_gateway.app.action_executors.base import ActionExecutor
from onebot_gateway.app.permission import PermissionChecker
from onebot_gateway.app.protocol import ChatMessageSender
from onebot_gateway.app.types import ActionResult

T = TypeVar("T")


class PermissionedActionExecutor(ActionExecutor[T], Generic[T]):
    """需要权限校验的 action 执行器基类。"""

    def __init__(self, permission_checker: PermissionChecker) -> None:
        self._permission = permission_checker

    def _check_permission(self, event: Any, action_name: str) -> ActionResult | None:
        denied = self._permission.check(event, action_name)
        return denied

    async def _execute_if_permitted(
        self,
        sender: ChatMessageSender,
        action: T,
        action_name: str,
        executor: Any,
        *,
        bot_user_id: int | None = None,
        event: Any = None,
    ) -> ActionResult:
        denied = self._check_permission(event, action_name)
        if denied is not None:
            return denied
        return await executor(sender, action)

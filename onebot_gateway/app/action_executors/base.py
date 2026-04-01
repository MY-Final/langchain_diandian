"""Action 执行器基类与注册表。"""

from __future__ import annotations

import logging
from typing import Any, Protocol, TypeVar

from onebot_gateway.app.types import ActionResult, ChatMessageSender

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ActionExecutor(Protocol[T]):
    """单个 action 执行器。"""

    async def execute(
        self,
        sender: ChatMessageSender,
        action: T,
        *,
        bot_user_id: int | None = None,
        event: Any = None,
    ) -> ActionResult:
        """执行 action 并返回结果。"""


class ActionDispatcher:
    """根据 action 类型分发到对应执行器。"""

    def __init__(self) -> None:
        self._handlers: dict[type, ActionExecutor] = {}

    def register(self, action_type: type[T], executor: ActionExecutor[T]) -> None:
        self._handlers[action_type] = executor

    async def dispatch(
        self,
        sender: ChatMessageSender,
        action: Any,
        *,
        bot_user_id: int | None = None,
        event: Any = None,
    ) -> ActionResult:
        handler = self._handlers.get(type(action))
        if handler is None:
            return ActionResult(
                action="unknown",
                success=False,
                message=f"未知 action 类型: {type(action).__name__}",
            )
        return await handler.execute(
            sender, action, bot_user_id=bot_user_id, event=event
        )


def _can_operate(operator_role: str, target_role: str) -> bool:
    """判断 operator 是否有权操作 target。"""
    priority = {"owner": 3, "admin": 2, "member": 1}
    return priority.get(operator_role, 0) > priority.get(target_role, 0)


async def _load_roles_for_action(
    sender: ChatMessageSender,
    group_id: int,
    target_user_id: int,
    bot_user_id: int | None,
) -> tuple[dict[str, Any] | None, str | None, str | None, ActionResult | None]:
    """加载目标成员和机器人的角色信息。"""
    target_info = await sender.get_group_member_info(group_id, target_user_id)
    if target_info is None:
        return (
            None,
            None,
            None,
            ActionResult(
                action="unknown",
                success=False,
                message="无法获取目标成员信息。",
            ),
        )

    target_role = str(target_info.get("role", "member"))

    if bot_user_id is None:
        return (
            target_info,
            None,
            target_role,
            ActionResult(
                action="unknown",
                success=False,
                message="无法确认机器人身份。",
            ),
        )

    bot_info = await sender.get_group_member_info(group_id, bot_user_id)
    if bot_info is None:
        return (
            target_info,
            None,
            target_role,
            ActionResult(
                action="unknown",
                success=False,
                message="无法获取机器人自身群成员信息。",
            ),
        )

    bot_role = str(bot_info.get("role", "member"))
    return target_info, bot_role, target_role, None

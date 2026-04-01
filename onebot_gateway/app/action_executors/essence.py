"""精华消息 action 执行器。"""

from __future__ import annotations

from chat_app.skills.essence_message import (
    PendingAddEssenceMessageAction,
    PendingGetEssenceMessageListAction,
    PendingRemoveEssenceMessageAction,
)
from onebot_gateway.app.action_executors.base import (
    ActionExecutor,
    ActionResult,
    ChatMessageSender,
)
from onebot_gateway.app.action_executors.permissioned import PermissionedActionExecutor


class AddEssenceMessageActionExecutor(
    PermissionedActionExecutor[PendingAddEssenceMessageAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingAddEssenceMessageAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "add_essence_message")
        if denied is not None:
            return denied
        await sender.set_essence_msg(action.message_id)
        return ActionResult(
            action="add_essence_message",
            success=True,
            message=f"已添加精华消息 {action.message_id}。",
        )


class RemoveEssenceMessageActionExecutor(
    PermissionedActionExecutor[PendingRemoveEssenceMessageAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingRemoveEssenceMessageAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "remove_essence_message")
        if denied is not None:
            return denied
        await sender.delete_essence_msg(action.message_id)
        return ActionResult(
            action="remove_essence_message",
            success=True,
            message=f"已移除精华消息 {action.message_id}。",
        )


class GetEssenceMessageListActionExecutor(
    ActionExecutor[PendingGetEssenceMessageListAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingGetEssenceMessageListAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        result = await sender.get_essence_msg_list(action.group_id)
        return ActionResult(
            action="get_essence_message_list",
            success=True,
            message=f"已获取精华消息列表：{result}",
        )

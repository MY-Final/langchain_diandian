"""群公告 action 执行器。"""

from __future__ import annotations

from chat_app.skills.group_announcement import (
    PendingGetGroupNoticeAction,
    PendingSendGroupNoticeAction,
)
from onebot_gateway.app.action_executors.base import (
    ActionExecutor,
    ActionResult,
    ChatMessageSender,
)
from onebot_gateway.app.action_executors.permissioned import PermissionedActionExecutor


class SendGroupNoticeActionExecutor(
    PermissionedActionExecutor[PendingSendGroupNoticeAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSendGroupNoticeAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "send_group_notice")
        if denied is not None:
            return denied
        await sender._send_group_notice(
            action.group_id, action.content, is_pinned=action.is_pinned
        )
        return ActionResult(
            action="send_group_notice",
            success=True,
            message="已发送群公告。",
        )


class GetGroupNoticeActionExecutor(ActionExecutor[PendingGetGroupNoticeAction]):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingGetGroupNoticeAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        result = await sender._get_group_notice(action.group_id)
        return ActionResult(
            action="get_group_notice",
            success=True,
            message=f"已获取群公告：{result}",
        )

"""私聊/账号管理 action 执行器。"""

from __future__ import annotations

from chat_app.skills.account_profile import (
    PendingSetQQAvatarAction,
    PendingSetQQProfileAction,
    PendingSetSelfLongNickAction,
)
from chat_app.skills.account_status import (
    PendingSetDIYOnlineStatusAction,
    PendingSetOnlineStatusAction,
)
from chat_app.skills.friend_management import (
    PendingDeleteFriendAction,
    PendingSendLikeAction,
)
from chat_app.skills.friend_request_management import PendingSetFriendAddRequestAction
from chat_app.skills.message_state import PendingMarkConversationReadAction
from chat_app.skills.message_recall import PendingRecallMessageAction
from onebot_gateway.app.action_executors.base import (
    ActionExecutor,
    ActionResult,
    ChatMessageSender,
)
from onebot_gateway.app.action_executors.permissioned import PermissionedActionExecutor


class SendLikeActionExecutor(PermissionedActionExecutor[PendingSendLikeAction]):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSendLikeAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "send_like")
        if denied is not None:
            return denied
        await sender.send_like(action.user_id, action.times)
        return ActionResult(
            action="send_like",
            success=True,
            message=f"已给用户 {action.user_id} 点赞 {action.times} 次。",
        )


class DeleteFriendActionExecutor(PermissionedActionExecutor[PendingDeleteFriendAction]):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingDeleteFriendAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "delete_friend")
        if denied is not None:
            return denied
        await sender.delete_friend(
            action.user_id,
            temp_block=action.temp_block,
            temp_both_del=action.temp_both_del,
        )
        return ActionResult(
            action="delete_friend",
            success=True,
            message=f"已删除好友 {action.user_id}。",
        )


class SetQQProfileActionExecutor(PermissionedActionExecutor[PendingSetQQProfileAction]):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSetQQProfileAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "set_qq_profile")
        if denied is not None:
            return denied
        await sender.set_qq_profile(
            nickname=action.nickname,
            personal_note=action.personal_note,
            sex=action.sex,
        )
        return ActionResult(
            action="set_qq_profile",
            success=True,
            message="已更新账号资料。",
        )


class SetSelfLongNickActionExecutor(
    PermissionedActionExecutor[PendingSetSelfLongNickAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSetSelfLongNickAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "set_self_longnick")
        if denied is not None:
            return denied
        await sender.set_self_longnick(action.long_nick)
        return ActionResult(
            action="set_self_longnick",
            success=True,
            message="已更新个性签名。",
        )


class SetQQAvatarActionExecutor(PermissionedActionExecutor[PendingSetQQAvatarAction]):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSetQQAvatarAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "set_qq_avatar")
        if denied is not None:
            return denied
        await sender.set_qq_avatar(action.file)
        return ActionResult(
            action="set_qq_avatar",
            success=True,
            message="已更新头像。",
        )


class SetOnlineStatusActionExecutor(
    PermissionedActionExecutor[PendingSetOnlineStatusAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSetOnlineStatusAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "set_online_status")
        if denied is not None:
            return denied
        await sender.set_online_status(
            action.status,
            ext_status=action.ext_status,
            battery_status=action.battery_status,
        )
        return ActionResult(
            action="set_online_status",
            success=True,
            message="已更新在线状态。",
        )


class SetDIYOnlineStatusActionExecutor(
    PermissionedActionExecutor[PendingSetDIYOnlineStatusAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSetDIYOnlineStatusAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "set_diy_online_status")
        if denied is not None:
            return denied
        await sender.set_diy_online_status(
            action.face_id,
            face_type=action.face_type,
            wording=action.wording,
        )
        return ActionResult(
            action="set_diy_online_status",
            success=True,
            message="已更新自定义在线状态。",
        )


class SetFriendAddRequestActionExecutor(
    PermissionedActionExecutor[PendingSetFriendAddRequestAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSetFriendAddRequestAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "set_friend_add_request")
        if denied is not None:
            return denied
        await sender.set_friend_add_request(
            action.flag,
            approve=action.approve,
            remark=action.remark,
        )
        return ActionResult(
            action="set_friend_add_request",
            success=True,
            message="已处理好友请求。",
        )


class MarkConversationReadActionExecutor(
    PermissionedActionExecutor[PendingMarkConversationReadAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingMarkConversationReadAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "mark_conversation_read")
        if denied is not None:
            return denied

        scope = action.scope.strip().lower()
        if scope == "all":
            await sender.mark_all_as_read()
            return ActionResult(
                action="mark_conversation_read",
                success=True,
                message="已将所有会话标记为已读。",
            )

        if scope == "current":
            if event.is_group_message():
                if event.group_id is None:
                    return ActionResult(
                        action="mark_conversation_read",
                        success=False,
                        message="当前群聊缺少 group_id。",
                    )
                await sender.mark_group_msg_as_read(event.group_id)
            else:
                if event.user_id is None:
                    return ActionResult(
                        action="mark_conversation_read",
                        success=False,
                        message="当前私聊缺少 user_id。",
                    )
                await sender.mark_private_msg_as_read(event.user_id)
            return ActionResult(
                action="mark_conversation_read",
                success=True,
                message="已将当前会话标记为已读。",
            )

        if action.target_id is None:
            return ActionResult(
                action="mark_conversation_read",
                success=False,
                message="缺少 target_id，无法标记指定会话为已读。",
            )

        if scope == "private":
            await sender.mark_private_msg_as_read(action.target_id)
            return ActionResult(
                action="mark_conversation_read",
                success=True,
                message=f"已将私聊 {action.target_id} 标记为已读。",
            )

        if scope == "group":
            await sender.mark_group_msg_as_read(action.target_id)
            return ActionResult(
                action="mark_conversation_read",
                success=True,
                message=f"已将群聊 {action.target_id} 标记为已读。",
            )

        return ActionResult(
            action="mark_conversation_read",
            success=False,
            message=f"不支持的 scope: {action.scope}",
        )


class RecallMessageActionExecutor(ActionExecutor[PendingRecallMessageAction]):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingRecallMessageAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        await sender.recall_message(action.message_id)
        return ActionResult(
            action="recall_message",
            success=True,
            message=f"已撤回消息 {action.message_id}。",
        )

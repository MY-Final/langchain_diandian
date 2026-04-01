"""群管理 action 执行器。"""

from __future__ import annotations

from chat_app.skills.group_moderation import (
    PendingKickGroupMemberAction,
    PendingMuteAction,
    PendingSetGroupAdminAction,
    PendingSetGroupCardAction,
    PendingSetGroupSpecialTitleAction,
)
from onebot_gateway.app.action_executors.base import (
    ActionExecutor,
    ActionResult,
    ChatMessageSender,
    _can_operate,
    _load_roles_for_action,
)


class MuteActionExecutor(ActionExecutor[PendingMuteAction]):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingMuteAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        target_info = await sender.get_group_member_info(
            action.group_id, action.user_id
        )
        if target_info is None:
            return ActionResult(
                action="mute_group_member",
                success=False,
                message="无法获取目标成员信息。",
            )

        target_role = str(target_info.get("role", "member"))

        if bot_user_id is None:
            return ActionResult(
                action="mute_group_member",
                success=False,
                message="无法确认机器人身份。",
            )

        bot_info = await sender.get_group_member_info(action.group_id, bot_user_id)
        if bot_info is None:
            return ActionResult(
                action="mute_group_member",
                success=False,
                message="无法获取机器人自身群成员信息。",
            )

        bot_role = str(bot_info.get("role", "member"))

        if not _can_operate(bot_role, target_role):
            return ActionResult(
                action="mute_group_member",
                success=False,
                message=f"权限不足：{bot_role} 无法禁言 {target_role}。",
            )

        await sender.set_group_ban(action.group_id, action.user_id, action.duration)

        if action.duration == 0:
            desc = "已解除禁言"
        else:
            desc = f"已禁言 {action.duration} 秒"

        return ActionResult(
            action="mute_group_member",
            success=True,
            message=f"{desc}（目标 {action.user_id}）。",
        )


class SetGroupAdminActionExecutor(ActionExecutor[PendingSetGroupAdminAction]):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSetGroupAdminAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        if bot_user_id is None:
            return ActionResult(
                action="set_group_admin",
                success=False,
                message="无法确认机器人身份。",
            )

        bot_info = await sender.get_group_member_info(action.group_id, bot_user_id)
        if bot_info is None:
            return ActionResult(
                action="set_group_admin",
                success=False,
                message="无法获取机器人自身群成员信息。",
            )

        bot_role = str(bot_info.get("role", "member"))
        if bot_role != "owner":
            return ActionResult(
                action="set_group_admin",
                success=False,
                message=f"权限不足：{bot_role} 无法设置群管理员。",
            )

        target_info = await sender.get_group_member_info(
            action.group_id, action.user_id
        )
        if target_info is None:
            return ActionResult(
                action="set_group_admin",
                success=False,
                message="无法获取目标成员信息。",
            )

        target_role = str(target_info.get("role", "member"))
        if action.enable and target_role == "owner":
            return ActionResult(
                action="set_group_admin",
                success=False,
                message="群主不能被设置为管理员。",
            )

        await sender.set_group_admin(action.group_id, action.user_id, action.enable)

        desc = "已设置群管理员" if action.enable else "已取消群管理员"
        return ActionResult(
            action="set_group_admin",
            success=True,
            message=f"{desc}（目标 {action.user_id}）。",
        )


class KickGroupMemberActionExecutor(ActionExecutor[PendingKickGroupMemberAction]):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingKickGroupMemberAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        (
            target_info,
            bot_role,
            target_role,
            error,
        ) = await _load_roles_for_action(
            sender, action.group_id, action.user_id, bot_user_id
        )
        if error is not None:
            return error
        assert target_info is not None
        assert bot_role is not None
        assert target_role is not None

        if not _can_operate(bot_role, target_role):
            return ActionResult(
                action="kick_group_member",
                success=False,
                message=f"权限不足：{bot_role} 无法踢出 {target_role}。",
            )

        await sender.set_group_kick(
            action.group_id, action.user_id, action.reject_add_request
        )
        return ActionResult(
            action="kick_group_member",
            success=True,
            message=f"已踢出成员 {action.user_id}。",
        )


class SetGroupCardActionExecutor(ActionExecutor[PendingSetGroupCardAction]):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSetGroupCardAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        (
            target_info,
            bot_role,
            target_role,
            error,
        ) = await _load_roles_for_action(
            sender, action.group_id, action.user_id, bot_user_id
        )
        if error is not None:
            return ActionResult(
                action="set_group_card",
                success=error.success,
                message=error.message,
            )
        assert target_info is not None
        assert bot_role is not None
        assert target_role is not None

        if not _can_operate(bot_role, target_role):
            return ActionResult(
                action="set_group_card",
                success=False,
                message=f"权限不足：{bot_role} 无法修改 {target_role} 的群名片。",
            )

        await sender.set_group_card(action.group_id, action.user_id, action.card)
        desc = "已清空群名片" if not action.card else f"已设置群名片为 {action.card}"
        return ActionResult(
            action="set_group_card",
            success=True,
            message=f"{desc}（目标 {action.user_id}）。",
        )


class SetGroupSpecialTitleActionExecutor(
    ActionExecutor[PendingSetGroupSpecialTitleAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSetGroupSpecialTitleAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        (
            target_info,
            bot_role,
            _target_role,
            error,
        ) = await _load_roles_for_action(
            sender, action.group_id, action.user_id, bot_user_id
        )
        if error is not None:
            return ActionResult(
                action="set_group_special_title",
                success=error.success,
                message=error.message,
            )
        assert target_info is not None
        assert bot_role is not None

        if bot_role != "owner":
            return ActionResult(
                action="set_group_special_title",
                success=False,
                message=f"权限不足：{bot_role} 无法设置群头衔。",
            )

        await sender.set_group_special_title(
            action.group_id, action.user_id, action.special_title
        )
        desc = (
            "已清空群头衔"
            if not action.special_title
            else f"已设置群头衔为 {action.special_title}"
        )
        return ActionResult(
            action="set_group_special_title",
            success=True,
            message=f"{desc}（目标 {action.user_id}）。",
        )

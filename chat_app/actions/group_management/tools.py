"""群管理工具。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.actions.group_management.types import (
    DEFAULT_MUTE_DURATION,
    MAX_MUTE_DURATION,
    PendingKickGroupMemberAction,
    PendingMuteAction,
    PendingSetGroupCardAction,
    PendingSetGroupAdminAction,
    PendingSetGroupSpecialTitleAction,
)


@tool
def mute_group_member(
    user_id: int, group_id: int, duration: int = DEFAULT_MUTE_DURATION
) -> str:
    """禁言指定群成员。

    调用后会生成一条禁言指令，由服务层校验权限并执行。
    - duration 单位为秒，默认 600 秒（10 分钟），最大 2592000 秒（30 天），0 表示解除禁言。
    - 仅群聊场景可用；需要你有群管理权限。
    - owner 可禁言 admin 和 member，admin 可禁言 member，member 不可禁言。
    """
    clamped = max(0, min(duration, MAX_MUTE_DURATION))
    action = PendingMuteAction(group_id=group_id, user_id=user_id, duration=clamped)
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def set_group_admin(user_id: int, group_id: int, enable: bool = True) -> str:
    """设置或取消群管理员。

    调用后会生成一条待执行指令，由服务层校验权限并执行。
    - enable=true 表示设置管理员，false 表示取消管理员。
    - 仅群聊场景可用。
    - 该操作权限严格，默认只有 owner 可以执行。
    """
    action = PendingSetGroupAdminAction(
        group_id=group_id,
        user_id=user_id,
        enable=enable,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def kick_group_member(
    user_id: int, group_id: int, reject_add_request: bool = False
) -> str:
    """将指定成员踢出群聊。

    调用后会生成一条待执行指令，由服务层校验权限并执行。
    - reject_add_request=true 表示同时拒绝该成员再次加群。
    - 仅群聊场景可用。
    - owner 可踢 admin/member，admin 可踢 member。
    """
    action = PendingKickGroupMemberAction(
        group_id=group_id,
        user_id=user_id,
        reject_add_request=reject_add_request,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def set_group_card(user_id: int, group_id: int, card: str = "") -> str:
    """设置或清空指定成员的群名片。

    调用后会生成一条待执行指令，由服务层校验权限并执行。
    - card 为空字符串时表示清空群名片。
    - 仅群聊场景可用。
    - owner 可改 admin/member，admin 可改 member。
    """
    action = PendingSetGroupCardAction(group_id=group_id, user_id=user_id, card=card)
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def set_group_special_title(
    user_id: int, group_id: int, special_title: str = ""
) -> str:
    """设置或清空指定成员的群头衔。

    调用后会生成一条待执行指令，由服务层校验权限并执行。
    - special_title 为空字符串时表示清空头衔。
    - 仅群聊场景可用。
    - 该操作权限严格，默认只有 owner 可以执行。
    """
    action = PendingSetGroupSpecialTitleAction(
        group_id=group_id,
        user_id=user_id,
        special_title=special_title,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)

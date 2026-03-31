"""群禁言工具。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.actions.types import (
    DEFAULT_MUTE_DURATION,
    MAX_MUTE_DURATION,
    PendingMuteAction,
    PendingSetGroupAdminAction,
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

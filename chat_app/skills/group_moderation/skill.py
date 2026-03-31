"""群管理 skill。"""

from __future__ import annotations

from chat_app.actions.group_management import (
    kick_group_member,
    mute_group_member,
    set_group_admin,
    set_group_card,
    set_group_special_title,
)
from chat_app.skills.context import SkillContext
from chat_app.skills.types import SkillSpec


def _applies_to(context: SkillContext) -> bool:
    return context.is_group_message()


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 如需禁言某人，可调用 mute_group_member 工具（需传入 user_id 和 group_id）。",
        "- 禁言操作受权限限制：owner 可禁言 admin/member，admin 可禁言 member。",
        "- 如需设置或取消群管理员，可调用 set_group_admin 工具（需传入 user_id 和 group_id）。",
        "- 设置群管理员权限更严格：只有 owner 可以设置或取消管理员。",
        "- 如需踢出群成员，可调用 kick_group_member 工具；权限规则与禁言类似。",
        "- 如需修改群名片，可调用 set_group_card 工具；owner 可改 admin/member，admin 可改 member。",
        "- 如需设置或清空群头衔，可调用 set_group_special_title 工具；只有 owner 可以执行。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return (
        mute_group_member,
        set_group_admin,
        kick_group_member,
        set_group_card,
        set_group_special_title,
    )


GROUP_MODERATION_SKILL = SkillSpec(
    name="group_moderation",
    description="群管理动作能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=100,
)

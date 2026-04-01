"""群公告 skill。"""

from __future__ import annotations

from chat_app.skills.context import SkillContext
from chat_app.skills.group_announcement.tools import (
    get_group_notice,
    send_group_notice,
)
from chat_app.skills.types import SkillSpec


def _applies_to(context: SkillContext) -> bool:
    return context.is_group_message()


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 如需发送群公告，可调用 send_group_notice 工具（需传入 group_id 和 content）。",
        "- 如需查看群公告，可调用 get_group_notice 工具（需传入 group_id）。",
        "- 发送公告需要群主或管理员权限。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return (
        send_group_notice,
        get_group_notice,
    )


GROUP_ANNOUNCEMENT_SKILL = SkillSpec(
    name="group_announcement",
    description="群公告管理能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=100,
)

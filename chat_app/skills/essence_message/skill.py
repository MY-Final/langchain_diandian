"""精华消息 skill。"""

from __future__ import annotations

from chat_app.skills.context import SkillContext
from chat_app.skills.essence_message.tools import (
    add_essence_message,
    get_essence_message_list,
    remove_essence_message,
)
from chat_app.skills.types import SkillSpec


def _applies_to(context: SkillContext) -> bool:
    return context.is_group_message()


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 如需添加精华消息，可调用 add_essence_message 工具（需传入 message_id）。",
        "- 如需移除精华消息，可调用 remove_essence_message 工具（需传入 message_id）。",
        "- 如需查看精华消息列表，可调用 get_essence_message_list 工具（需传入 group_id）。",
        "- 添加或移除精华消息需要群主或管理员权限。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return (
        add_essence_message,
        remove_essence_message,
        get_essence_message_list,
    )


ESSENCE_MESSAGE_SKILL = SkillSpec(
    name="essence_message",
    description="精华消息管理能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=100,
)

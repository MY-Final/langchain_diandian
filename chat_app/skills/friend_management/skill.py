"""好友管理 skill。"""

from __future__ import annotations

from chat_app.skills.context import SkillContext
from chat_app.skills.friend_management.tools import delete_friend, send_like
from chat_app.skills.types import SkillSpec


def _applies_to(context: SkillContext) -> bool:
    return context.is_private_message() and context.is_trusted_operator


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 你当前可使用好友管理能力，但只应在明确需要时调用。",
        "- 如需点赞，可调用 send_like 工具。",
        "- 如需删除好友，可调用 delete_friend 工具；这是高风险操作，需确认对象明确。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return (send_like, delete_friend)


FRIEND_MANAGEMENT_SKILL = SkillSpec(
    name="friend_management",
    description="好友与互动能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=80,
)

"""消息状态 skill。"""

from __future__ import annotations

from chat_app.skills.context import SkillContext
from chat_app.skills.message_state.tools import mark_conversation_read
from chat_app.skills.types import SkillSpec


def _applies_to(context: SkillContext) -> bool:
    return context.is_private_message() and context.is_trusted_operator


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 你当前可使用消息状态管理能力，但只应在明确需要时调用。",
        "- 如需将当前会话标记为已读，可调用 mark_conversation_read 工具。",
        "- 如需标记指定私聊或群聊为已读，请明确提供 target_id。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return (mark_conversation_read,)


MESSAGE_STATE_SKILL = SkillSpec(
    name="message_state",
    description="消息已读状态管理能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=65,
)

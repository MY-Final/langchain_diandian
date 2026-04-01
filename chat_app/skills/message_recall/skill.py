"""消息撤回 skill。"""

from __future__ import annotations

from chat_app.skills.context import SkillContext
from chat_app.skills.message_recall.tools import recall_message
from chat_app.skills.types import SkillSpec


def _applies_to(_context: SkillContext) -> bool:
    return True


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 如需撤回消息，可调用 recall_message 工具（需传入 message_id）。",
        "- 仅支持撤回机器人自己发送的消息。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return (recall_message,)


MESSAGE_RECALL_SKILL = SkillSpec(
    name="message_recall",
    description="消息撤回能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=100,
)

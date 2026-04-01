"""合并转发消息 skill。"""

from __future__ import annotations

from chat_app.skills.context import SkillContext
from chat_app.skills.forward_message.tools import send_forward_message
from chat_app.skills.types import SkillSpec


def _applies_to(_context: SkillContext) -> bool:
    return True


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 如需发送合并转发消息，可调用 send_forward_message 工具。",
        "- nodes 参数为消息节点列表，每个节点需包含 user_id、nickname、content。",
        "- is_group=true 发送到群聊，false 发送到私聊。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return (send_forward_message,)


FORWARD_MESSAGE_SKILL = SkillSpec(
    name="forward_message",
    description="合并转发消息能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=100,
)

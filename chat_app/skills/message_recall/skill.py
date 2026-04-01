"""消息撤回 skill。"""

from __future__ import annotations

from chat_app.skills.context import SkillContext
from chat_app.skills.message_recall.tools import (
    recall_last_self_message,
    recall_last_user_message,
)
from chat_app.skills.types import SkillSpec


def _applies_to(_context: SkillContext) -> bool:
    return _context.message_index is not None


def _build_rules(context: SkillContext) -> tuple[str, ...]:
    rules = [
        "- 如需撤回机器人自己最近发送的消息，调用 recall_last_self_message 工具（需传入 chat_type 和 chat_id）。",
        "- 如需在群里撤回某群成员最近发送的消息，调用 recall_last_user_message 工具（需传入 group_id 和 sender_id，仅群主/管理员可用）。",
        "- 不需要提供 message_id，索引服务会自动查找。",
    ]
    if context.is_private_message():
        rules = [
            "- 如需撤回机器人自己最近发送的消息，调用 recall_last_self_message 工具（需传入 chat_type='private' 和 chat_id）。",
            "- 私聊仅支持撤回机器人自己发送的消息。",
        ]
    return tuple(rules)


def _build_tools(context: SkillContext) -> tuple:
    if context.is_private_message():
        return (recall_last_self_message,)
    return (recall_last_self_message, recall_last_user_message)


MESSAGE_RECALL_SKILL = SkillSpec(
    name="message_recall",
    description="消息撤回能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=100,
)

"""消息状态 skill。"""

from chat_app.skills.message_state.skill import MESSAGE_STATE_SKILL
from chat_app.skills.message_state.tools import mark_conversation_read
from chat_app.skills.message_state.types import PendingMarkConversationReadAction

__all__ = [
    "MESSAGE_STATE_SKILL",
    "PendingMarkConversationReadAction",
    "mark_conversation_read",
]

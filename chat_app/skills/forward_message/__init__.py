"""合并转发消息 skill。"""

from chat_app.skills.forward_message.skill import FORWARD_MESSAGE_SKILL
from chat_app.skills.forward_message.tools import (
    send_forward_message,
)
from chat_app.skills.forward_message.types import (
    PendingSendForwardMessageAction,
)

__all__ = [
    "FORWARD_MESSAGE_SKILL",
    "PendingSendForwardMessageAction",
    "send_forward_message",
]

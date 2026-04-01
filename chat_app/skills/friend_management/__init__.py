"""好友管理 skill。"""

from chat_app.skills.friend_management.skill import FRIEND_MANAGEMENT_SKILL
from chat_app.skills.friend_management.tools import delete_friend, send_like
from chat_app.skills.friend_management.types import (
    PendingDeleteFriendAction,
    PendingSendLikeAction,
)

__all__ = [
    "FRIEND_MANAGEMENT_SKILL",
    "PendingDeleteFriendAction",
    "PendingSendLikeAction",
    "delete_friend",
    "send_like",
]

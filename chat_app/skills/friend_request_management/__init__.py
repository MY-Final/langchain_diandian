"""好友请求管理 skill。"""

from chat_app.skills.friend_request_management.skill import (
    FRIEND_REQUEST_MANAGEMENT_SKILL,
)
from chat_app.skills.friend_request_management.tools import set_friend_add_request
from chat_app.skills.friend_request_management.types import (
    PendingSetFriendAddRequestAction,
)

__all__ = [
    "FRIEND_REQUEST_MANAGEMENT_SKILL",
    "PendingSetFriendAddRequestAction",
    "set_friend_add_request",
]

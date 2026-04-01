"""账号资料 skill。"""

from chat_app.skills.account_profile.skill import ACCOUNT_PROFILE_SKILL
from chat_app.skills.account_profile.tools import (
    set_qq_avatar,
    set_qq_profile,
    set_self_longnick,
)
from chat_app.skills.account_profile.types import (
    PendingSetQQAvatarAction,
    PendingSetQQProfileAction,
    PendingSetSelfLongNickAction,
)

__all__ = [
    "ACCOUNT_PROFILE_SKILL",
    "PendingSetQQAvatarAction",
    "PendingSetQQProfileAction",
    "PendingSetSelfLongNickAction",
    "set_qq_avatar",
    "set_qq_profile",
    "set_self_longnick",
]

"""群管理 skill。"""

from chat_app.skills.group_moderation.skill import GROUP_MODERATION_SKILL
from chat_app.skills.group_moderation.tools import (
    kick_group_member,
    mute_group_member,
    set_group_admin,
    set_group_card,
    set_group_special_title,
)
from chat_app.skills.group_moderation.types import (
    DEFAULT_MUTE_DURATION,
    MAX_MUTE_DURATION,
    PendingAction,
    PendingKickGroupMemberAction,
    PendingMuteAction,
    PendingSetGroupAdminAction,
    PendingSetGroupCardAction,
    PendingSetGroupSpecialTitleAction,
)

__all__ = [
    "DEFAULT_MUTE_DURATION",
    "MAX_MUTE_DURATION",
    "GROUP_MODERATION_SKILL",
    "PendingAction",
    "PendingKickGroupMemberAction",
    "PendingMuteAction",
    "PendingSetGroupAdminAction",
    "PendingSetGroupCardAction",
    "PendingSetGroupSpecialTitleAction",
    "kick_group_member",
    "mute_group_member",
    "set_group_admin",
    "set_group_card",
    "set_group_special_title",
]

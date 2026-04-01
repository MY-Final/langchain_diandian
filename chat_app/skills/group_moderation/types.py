"""群管理技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_MUTE_DURATION = 600
MAX_MUTE_DURATION = 2592000  # 30 天


@dataclass(frozen=True)
class PendingMuteAction:
    """待执行的群禁言动作。"""

    group_id: int
    user_id: int
    duration: int

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "mute_group_member",
            "group_id": self.group_id,
            "user_id": self.user_id,
            "duration": self.duration,
        }


@dataclass(frozen=True)
class PendingSetGroupAdminAction:
    """待执行的设置群管理员动作。"""

    group_id: int
    user_id: int
    enable: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "set_group_admin",
            "group_id": self.group_id,
            "user_id": self.user_id,
            "enable": self.enable,
        }


@dataclass(frozen=True)
class PendingKickGroupMemberAction:
    """待执行的群踢人动作。"""

    group_id: int
    user_id: int
    reject_add_request: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "kick_group_member",
            "group_id": self.group_id,
            "user_id": self.user_id,
            "reject_add_request": self.reject_add_request,
        }


@dataclass(frozen=True)
class PendingSetGroupCardAction:
    """待执行的设置群名片动作。"""

    group_id: int
    user_id: int
    card: str

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "set_group_card",
            "group_id": self.group_id,
            "user_id": self.user_id,
            "card": self.card,
        }


@dataclass(frozen=True)
class PendingSetGroupSpecialTitleAction:
    """待执行的设置群头衔动作。"""

    group_id: int
    user_id: int
    special_title: str

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "set_group_special_title",
            "group_id": self.group_id,
            "user_id": self.user_id,
            "special_title": self.special_title,
        }


PendingAction = (
    PendingMuteAction
    | PendingSetGroupAdminAction
    | PendingKickGroupMemberAction
    | PendingSetGroupCardAction
    | PendingSetGroupSpecialTitleAction
)

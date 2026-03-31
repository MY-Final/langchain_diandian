"""动作数据类型。"""

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


PendingAction = PendingMuteAction | PendingSetGroupAdminAction

"""账号状态技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingSetOnlineStatusAction:
    """待执行的在线状态设置动作。"""

    status: int
    ext_status: int
    battery_status: int

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "set_online_status",
            "status": self.status,
            "ext_status": self.ext_status,
            "battery_status": self.battery_status,
        }


@dataclass(frozen=True)
class PendingSetDIYOnlineStatusAction:
    """待执行的自定义在线状态动作。"""

    face_id: int
    face_type: int
    wording: str

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "set_diy_online_status",
            "face_id": self.face_id,
            "face_type": self.face_type,
            "wording": self.wording,
        }

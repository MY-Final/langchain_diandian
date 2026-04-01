"""好友管理技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingSendLikeAction:
    """待执行的点赞动作。"""

    user_id: int
    times: int

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "send_like",
            "user_id": self.user_id,
            "times": self.times,
        }


@dataclass(frozen=True)
class PendingDeleteFriendAction:
    """待执行的删除好友动作。"""

    user_id: int
    temp_block: bool
    temp_both_del: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "delete_friend",
            "user_id": self.user_id,
            "temp_block": self.temp_block,
            "temp_both_del": self.temp_both_del,
        }

"""好友请求管理技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingSetFriendAddRequestAction:
    """待执行的好友请求处理动作。"""

    flag: str
    approve: bool
    remark: str

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "set_friend_add_request",
            "flag": self.flag,
            "approve": self.approve,
            "remark": self.remark,
        }

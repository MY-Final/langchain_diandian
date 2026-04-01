"""群公告技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingSendGroupNoticeAction:
    """待执行的发送群公告动作。"""

    group_id: int
    content: str
    is_pinned: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "send_group_notice",
            "group_id": self.group_id,
            "content": self.content,
            "is_pinned": self.is_pinned,
        }


@dataclass(frozen=True)
class PendingGetGroupNoticeAction:
    """待执行的获取群公告动作。"""

    group_id: int

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "get_group_notice",
            "group_id": self.group_id,
        }


PendingAction = PendingSendGroupNoticeAction | PendingGetGroupNoticeAction

"""精华消息技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingAddEssenceMessageAction:
    """待执行的添加精华消息动作。"""

    message_id: int

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "add_essence_message",
            "message_id": self.message_id,
        }


@dataclass(frozen=True)
class PendingRemoveEssenceMessageAction:
    """待执行的移除精华消息动作。"""

    message_id: int

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "remove_essence_message",
            "message_id": self.message_id,
        }


@dataclass(frozen=True)
class PendingGetEssenceMessageListAction:
    """待执行的获取精华消息列表动作。"""

    group_id: int

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "get_essence_message_list",
            "group_id": self.group_id,
        }


PendingAction = (
    PendingAddEssenceMessageAction
    | PendingRemoveEssenceMessageAction
    | PendingGetEssenceMessageListAction
)

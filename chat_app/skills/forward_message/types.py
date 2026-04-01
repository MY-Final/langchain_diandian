"""合并转发消息技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ForwardMessageNode:
    """合并转发消息的单个节点。"""

    user_id: int
    nickname: str
    content: str

    def to_dict(self) -> dict[str, object]:
        return {
            "user_id": self.user_id,
            "nickname": self.nickname,
            "content": self.content,
        }


@dataclass(frozen=True)
class PendingSendForwardMessageAction:
    """待执行的发送合并转发消息动作。"""

    target_id: int
    nodes: tuple[ForwardMessageNode, ...]
    is_group: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "send_forward_message",
            "target_id": self.target_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "is_group": self.is_group,
        }


PendingAction = PendingSendForwardMessageAction

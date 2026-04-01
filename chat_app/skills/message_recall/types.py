"""消息撤回技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingRecallMessageAction:
    """待执行的消息撤回动作。"""

    message_id: int

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "recall_message",
            "message_id": self.message_id,
        }

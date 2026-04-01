"""消息撤回技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingRecallMessageAction:
    """待执行的消息撤回动作。"""

    chat_type: str
    chat_id: int
    target_user_id: int | None = None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "action": "recall_message",
            "chat_type": self.chat_type,
            "chat_id": self.chat_id,
        }
        if self.target_user_id is not None:
            result["target_user_id"] = self.target_user_id
        return result

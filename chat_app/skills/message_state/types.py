"""消息状态技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingMarkConversationReadAction:
    """待执行的会话已读动作。"""

    scope: str
    target_id: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "mark_conversation_read",
            "scope": self.scope,
            "target_id": self.target_id,
        }

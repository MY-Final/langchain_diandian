"""Skill 运行上下文。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from onebot_gateway.message.index import MessageIndexService


@dataclass(frozen=True)
class SkillContext:
    """用于选择当前启用 skill 的上下文。"""

    session_kind: Literal["private", "group"]
    user_id: int | None = None
    group_id: int | None = None
    is_trusted_operator: bool = False
    supports_live_onebot_queries: bool = False
    message_index: MessageIndexService | None = None
    onebot_sender: Any = None

    def is_private_message(self) -> bool:
        return self.session_kind == "private"

    def is_group_message(self) -> bool:
        return self.session_kind == "group"

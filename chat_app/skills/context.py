"""Skill 运行上下文。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SkillContext:
    """用于选择当前启用 skill 的上下文。"""

    session_kind: Literal["private", "group"]
    user_id: int | None = None
    group_id: int | None = None

    def is_private_message(self) -> bool:
        return self.session_kind == "private"

    def is_group_message(self) -> bool:
        return self.session_kind == "group"

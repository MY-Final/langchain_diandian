"""会话记忆数据结构。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryPolicy:
    """会话记忆策略。"""

    max_turns: int
    summary_trigger_turns: int
    summary_batch_turns: int


@dataclass(frozen=True)
class ConversationTurn:
    """单轮对话。"""

    user_text: str
    assistant_text: str


@dataclass(frozen=True)
class MemorySessionScope:
    """单个会话的记忆作用域。"""

    session_key: str
    session_kind: str
    user_id: int | None
    group_id: int | None


@dataclass(frozen=True)
class MemorySnapshot:
    """可持久化的记忆快照。"""

    summary_text: str
    turns: tuple[ConversationTurn, ...]

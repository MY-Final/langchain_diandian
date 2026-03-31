"""记忆存储抽象。"""

from __future__ import annotations

from typing import Protocol

from chat_app.memory.types import MemorySessionScope, MemorySnapshot


class MemoryStore(Protocol):
    """会话记忆存储接口。"""

    def load_snapshot(self, scope: MemorySessionScope) -> MemorySnapshot:
        """读取会话记忆快照。"""

    def save_snapshot(
        self, scope: MemorySessionScope, snapshot: MemorySnapshot
    ) -> None:
        """保存会话记忆快照。"""


class InMemoryMemoryStore:
    """进程内记忆存储。"""

    def __init__(self) -> None:
        self._snapshots: dict[str, MemorySnapshot] = {}

    def load_snapshot(self, scope: MemorySessionScope) -> MemorySnapshot:
        return self._snapshots.get(scope.session_key, MemorySnapshot("", ()))

    def save_snapshot(
        self, scope: MemorySessionScope, snapshot: MemorySnapshot
    ) -> None:
        self._snapshots[scope.session_key] = snapshot

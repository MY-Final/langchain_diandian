"""长期记忆接口与数据结构。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LongTermMemoryEntry:
    """单条长期记忆。"""

    id: int
    scope_type: str
    scope_id: int | None
    memory_type: str
    memory_key: str
    content: str
    confidence: float
    priority: int
    status: str
    pinned: bool
    metadata: dict[str, object]

    @classmethod
    def from_row(cls, row: dict[str, object]) -> LongTermMemoryEntry:
        """从数据库行构造。"""
        raw_meta = row.get("metadata", "{}")
        if isinstance(raw_meta, str):
            try:
                metadata = json.loads(raw_meta)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        elif isinstance(raw_meta, dict):
            metadata = raw_meta
        else:
            metadata = {}

        return cls(
            id=int(row["id"]),
            scope_type=str(row["scope_type"]),
            scope_id=int(row["scope_id"]) if row.get("scope_id") is not None else None,
            memory_type=str(row["memory_type"]),
            memory_key=str(row.get("memory_key", "")),
            content=str(row["content"]),
            confidence=float(row.get("confidence", 0.5)),
            priority=int(row.get("priority", 0)),
            status=str(row.get("status", "active")),
            pinned=bool(row.get("pinned", False)),
            metadata=metadata,
        )

    def to_prompt_line(self) -> str:
        """转为 prompt 中的一行。"""
        return f"- [{self.memory_type}] {self.content}"


class LongTermMemoryStore(Protocol):
    """长期记忆存储接口。"""

    def query(
        self,
        *,
        scope_type: str,
        scope_id: int | None,
        memory_types: tuple[str, ...] | None = None,
        keywords: tuple[str, ...] | None = None,
        limit: int = 20,
    ) -> list[LongTermMemoryEntry]:
        """查询长期记忆。"""


class InMemoryLongTermStore:
    """进程内长期记忆存储，用于测试和无 PG 环境。"""

    def __init__(self) -> None:
        self._entries: list[LongTermMemoryEntry] = []
        self._next_id = 1

    def add(self, entry: LongTermMemoryEntry) -> None:
        """添加一条记忆（用于测试）。"""
        self._entries.append(entry)

    def query(
        self,
        *,
        scope_type: str,
        scope_id: int | None,
        memory_types: tuple[str, ...] | None = None,
        keywords: tuple[str, ...] | None = None,
        limit: int = 20,
    ) -> list[LongTermMemoryEntry]:
        results = [
            e
            for e in self._entries
            if e.scope_type == scope_type
            and e.scope_id == scope_id
            and e.status == "active"
        ]

        if memory_types:
            results = [e for e in results if e.memory_type in memory_types]

        if keywords:
            filtered: list[LongTermMemoryEntry] = []
            for entry in results:
                content_lower = entry.content.lower()
                if any(kw.lower() in content_lower for kw in keywords):
                    filtered.append(entry)
            results = filtered

        results.sort(
            key=lambda e: (
                int(e.pinned),
                e.priority,
                e.confidence,
            ),
            reverse=True,
        )

        return results[:limit]

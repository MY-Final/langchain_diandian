"""PostgreSQL 长期记忆存储。"""

from __future__ import annotations

import importlib
import json
from types import ModuleType
from typing import Any

from chat_app.config import PostgresConfig
from chat_app.memory.long_term import LongTermMemoryEntry, LongTermMemoryStore


class PostgresLongTermStore(LongTermMemoryStore):
    """基于 PostgreSQL 的长期记忆存储。"""

    def __init__(self, config: PostgresConfig) -> None:
        self._config = config

    def query(
        self,
        *,
        scope_type: str,
        scope_id: int | None,
        memory_types: tuple[str, ...] | None = None,
        keywords: tuple[str, ...] | None = None,
        limit: int = 20,
    ) -> list[LongTermMemoryEntry]:
        psycopg = _import_psycopg()
        dict_row = _import_dict_row()

        conditions = ["status = 'active'", "scope_type = %s"]
        params: list[object] = [scope_type]

        if scope_id is not None:
            conditions.append("scope_id = %s")
            params.append(scope_id)
        else:
            conditions.append("scope_id IS NULL")

        if memory_types:
            placeholders = ", ".join(["%s"] * len(memory_types))
            conditions.append(f"memory_type IN ({placeholders})")
            params.extend(memory_types)

        if keywords:
            keyword_conditions = []
            for _ in keywords:
                keyword_conditions.append("content ILIKE %s")
            conditions.append(f"({' OR '.join(keyword_conditions)})")
            for kw in keywords:
                params.append(f"%{kw}%")

        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT id, scope_type, scope_id, memory_type, memory_key,
                   content, confidence, priority, status, pinned, metadata
            FROM long_term_memories
            WHERE {where_clause}
            ORDER BY pinned DESC, priority DESC, confidence DESC, updated_at DESC
            LIMIT %s
        """
        params.append(limit)

        with psycopg.connect(**self._config.to_connection_kwargs()) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()

        return [LongTermMemoryEntry.from_row(dict(row)) for row in rows]


def _import_psycopg() -> ModuleType:
    try:
        return importlib.import_module("psycopg")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PostgreSQL 长期记忆已启用，但未安装 psycopg。请先安装 requirements.txt 里的依赖。"
        ) from exc


def _import_dict_row() -> Any:
    try:
        rows_module = importlib.import_module("psycopg.rows")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PostgreSQL 长期记忆已启用，但当前 psycopg 安装缺少 rows 模块。"
        ) from exc

    dict_row = getattr(rows_module, "dict_row", None)
    if not callable(dict_row):
        raise RuntimeError("psycopg.rows.dict_row 不可用。")
    return dict_row

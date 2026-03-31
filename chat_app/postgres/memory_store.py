"""PostgreSQL 记忆存储。"""

from __future__ import annotations

import importlib
from types import ModuleType

from chat_app.config import PostgresConfig
from chat_app.memory.store import MemoryStore
from chat_app.memory.types import ConversationTurn, MemorySessionScope, MemorySnapshot


class PostgresMemoryStore(MemoryStore):
    """基于 PostgreSQL 的记忆快照存储。"""

    def __init__(self, config: PostgresConfig) -> None:
        self._config = config

    def load_snapshot(self, scope: MemorySessionScope) -> MemorySnapshot:
        psycopg = _import_psycopg()
        with psycopg.connect(**self._config.to_connection_kwargs()) as connection:
            with connection.cursor() as cursor:
                session_id = _load_session_id(cursor, scope)
                if session_id is None:
                    return MemorySnapshot("", ())

                cursor.execute(
                    "SELECT summary_text FROM conversation_summaries WHERE session_id = %s",
                    (session_id,),
                )
                row = cursor.fetchone()
                summary_text = row[0] if row else ""

                cursor.execute(
                    """
                    SELECT user_text, assistant_text
                    FROM conversation_turns
                    WHERE session_id = %s
                    ORDER BY turn_index ASC
                    """,
                    (session_id,),
                )
                turns = tuple(
                    ConversationTurn(user_text=user_text, assistant_text=assistant_text)
                    for user_text, assistant_text in cursor.fetchall()
                )
        return MemorySnapshot(summary_text=summary_text, turns=turns)

    def save_snapshot(
        self, scope: MemorySessionScope, snapshot: MemorySnapshot
    ) -> None:
        psycopg = _import_psycopg()
        with psycopg.connect(**self._config.to_connection_kwargs()) as connection:
            with connection.cursor() as cursor:
                session_id = _upsert_session(cursor, scope)
                cursor.execute(
                    """
                    INSERT INTO conversation_summaries (session_id, summary_text, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (session_id)
                    DO UPDATE SET summary_text = EXCLUDED.summary_text, updated_at = NOW()
                    """,
                    (session_id, snapshot.summary_text),
                )
                cursor.execute(
                    "DELETE FROM conversation_turns WHERE session_id = %s",
                    (session_id,),
                )
                for turn_index, turn in enumerate(snapshot.turns, start=1):
                    cursor.execute(
                        """
                        INSERT INTO conversation_turns (
                            session_id,
                            turn_index,
                            user_text,
                            assistant_text
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            session_id,
                            turn_index,
                            turn.user_text,
                            turn.assistant_text,
                        ),
                    )
            connection.commit()


def _load_session_id(cursor: object, scope: MemorySessionScope) -> int | None:
    cursor.execute(
        "SELECT id FROM conversation_sessions WHERE session_key = %s",
        (scope.session_key,),
    )
    row = cursor.fetchone()
    return int(row[0]) if row else None


def _upsert_session(cursor: object, scope: MemorySessionScope) -> int:
    cursor.execute(
        """
        INSERT INTO conversation_sessions (
            session_key,
            session_kind,
            user_id,
            group_id,
            updated_at
        )
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (session_key)
        DO UPDATE SET
            session_kind = EXCLUDED.session_kind,
            user_id = EXCLUDED.user_id,
            group_id = EXCLUDED.group_id,
            updated_at = NOW()
        RETURNING id
        """,
        (scope.session_key, scope.session_kind, scope.user_id, scope.group_id),
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("保存会话时未返回 session_id。")
    return int(row[0])


def _import_psycopg() -> ModuleType:
    try:
        return importlib.import_module("psycopg")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PostgreSQL 记忆已启用，但未安装 psycopg。请先安装 requirements.txt 里的依赖。"
        ) from exc

"""PostgreSQL 初始化服务。"""

from __future__ import annotations

import importlib
from types import ModuleType

from chat_app.config import AppConfig, PostgresConfig


SESSION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_key TEXT NOT NULL UNIQUE,
    session_kind TEXT NOT NULL,
    user_id BIGINT,
    group_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT conversation_sessions_kind_check
        CHECK (session_kind IN ('private', 'group')),
    CONSTRAINT conversation_sessions_scope_check
        CHECK (
            (session_kind = 'private' AND user_id IS NOT NULL AND group_id IS NULL)
            OR (session_kind = 'group' AND group_id IS NOT NULL)
        )
);
""".strip()

SUMMARY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS conversation_summaries (
    session_id BIGINT PRIMARY KEY REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
""".strip()

TURN_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS conversation_turns (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    turn_index BIGINT NOT NULL,
    user_text TEXT NOT NULL,
    assistant_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT conversation_turns_session_turn_unique UNIQUE (session_id, turn_index)
);
""".strip()

TURN_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS conversation_turns_session_created_idx
ON conversation_turns (session_id, created_at DESC);
""".strip()

LONG_TERM_MEMORY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS long_term_memories (
    id BIGSERIAL PRIMARY KEY,
    scope_type TEXT NOT NULL,
    scope_id BIGINT,
    memory_type TEXT NOT NULL,
    memory_key TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    priority SMALLINT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    pinned BOOLEAN NOT NULL DEFAULT FALSE,
    source_session_id BIGINT REFERENCES conversation_sessions(id) ON DELETE SET NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT long_term_memories_scope_check CHECK (
        (scope_type IN ('user', 'group') AND scope_id IS NOT NULL)
        OR (scope_type = 'global' AND scope_id IS NULL)
    ),
    CONSTRAINT long_term_memories_confidence_check CHECK (
        confidence >= 0.0 AND confidence <= 1.0
    ),
    CONSTRAINT long_term_memories_status_check CHECK (
        status IN ('active', 'archived', 'deleted')
    )
);
""".strip()

LONG_TERM_MEMORY_SCOPE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS long_term_memories_scope_idx
ON long_term_memories (scope_type, scope_id, status, priority DESC, updated_at DESC);
""".strip()

LONG_TERM_MEMORY_TYPE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS long_term_memories_type_idx
ON long_term_memories (memory_type, status, updated_at DESC);
""".strip()

LONG_TERM_MEMORY_KEY_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS long_term_memories_key_idx
ON long_term_memories (scope_type, scope_id, memory_type, memory_key)
WHERE memory_key <> '' AND status = 'active';
""".strip()

SCHEMA_STATEMENTS = (
    SESSION_TABLE_SQL,
    SUMMARY_TABLE_SQL,
    TURN_TABLE_SQL,
    TURN_INDEX_SQL,
    LONG_TERM_MEMORY_TABLE_SQL,
    LONG_TERM_MEMORY_SCOPE_INDEX_SQL,
    LONG_TERM_MEMORY_TYPE_INDEX_SQL,
    LONG_TERM_MEMORY_KEY_INDEX_SQL,
)


class PostgresService:
    """负责初始化 PostgreSQL 表结构。"""

    def __init__(self, config: PostgresConfig) -> None:
        self._config = config

    def ensure_tables(self) -> None:
        """确保 PostgreSQL 表结构存在。"""
        if not self._config.enabled:
            return

        psycopg = _import_psycopg()
        connect_kwargs = self._config.to_connection_kwargs()
        with psycopg.connect(**connect_kwargs) as connection:
            with connection.cursor() as cursor:
                for statement in SCHEMA_STATEMENTS:
                    cursor.execute(statement)
            connection.commit()


def ensure_postgres_ready(config: AppConfig) -> None:
    """在配置启用时初始化 PostgreSQL 表。"""
    if not config.postgres.enabled:
        return
    PostgresService(config.postgres).ensure_tables()


def _import_psycopg() -> ModuleType:
    try:
        return importlib.import_module("psycopg")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PostgreSQL 已启用，但未安装 psycopg。请先安装 requirements.txt 里的依赖。"
        ) from exc

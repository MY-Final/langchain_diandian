"""PostgreSQL 记忆存储测试。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from chat_app.config import PostgresConfig
from chat_app.memory.types import ConversationTurn, MemorySessionScope, MemorySnapshot
from chat_app.postgres.memory_store import PostgresMemoryStore


class FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self._fetchone_queue: list[tuple[object, ...] | None] = []
        self._fetchall_queue: list[list[tuple[object, ...]]] = []

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def queue_fetchone(self, row: tuple[object, ...] | None) -> None:
        self._fetchone_queue.append(row)

    def queue_fetchall(self, rows: list[tuple[object, ...]]) -> None:
        self._fetchall_queue.append(rows)

    def execute(self, statement: str, params: tuple[object, ...] = ()) -> None:
        self.executed.append((statement, params))

    def fetchone(self) -> tuple[object, ...] | None:
        if not self._fetchone_queue:
            return None
        return self._fetchone_queue.pop(0)

    def fetchall(self) -> list[tuple[object, ...]]:
        if not self._fetchall_queue:
            return []
        return self._fetchall_queue.pop(0)


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.committed = False

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.committed = True


class PostgresMemoryStoreTests(unittest.TestCase):
    """验证 PostgreSQL 记忆快照读写。"""

    def setUp(self) -> None:
        self.config = PostgresConfig(
            enabled=True,
            dsn="postgresql://user:pwd@127.0.0.1:5432/diandian",
            host="127.0.0.1",
            port=5432,
            database="diandian",
            user="user",
            password="pwd",
            sslmode="prefer",
            connect_timeout=10,
        )
        self.scope = MemorySessionScope(
            session_key="private:123",
            session_kind="private",
            user_id=123,
            group_id=None,
        )

    def test_load_snapshot_returns_summary_and_turns(self) -> None:
        cursor = FakeCursor()
        cursor.queue_fetchone((11,))
        cursor.queue_fetchone(("摘要内容",))
        cursor.queue_fetchall([("user-1", "ai-1"), ("user-2", "ai-2")])
        connection = FakeConnection(cursor)
        fake_psycopg = SimpleNamespace(connect=lambda **kwargs: connection)

        with patch(
            "chat_app.postgres.memory_store._import_psycopg",
            return_value=fake_psycopg,
        ):
            snapshot = PostgresMemoryStore(self.config).load_snapshot(self.scope)

        self.assertEqual(snapshot.summary_text, "摘要内容")
        self.assertEqual(
            snapshot.turns,
            (
                ConversationTurn("user-1", "ai-1"),
                ConversationTurn("user-2", "ai-2"),
            ),
        )

    def test_save_snapshot_rewrites_summary_and_turns(self) -> None:
        cursor = FakeCursor()
        cursor.queue_fetchone((11,))
        connection = FakeConnection(cursor)
        fake_psycopg = SimpleNamespace(connect=lambda **kwargs: connection)
        snapshot = MemorySnapshot(
            summary_text="摘要内容",
            turns=(
                ConversationTurn("user-1", "ai-1"),
                ConversationTurn("user-2", "ai-2"),
            ),
        )

        with patch(
            "chat_app.postgres.memory_store._import_psycopg",
            return_value=fake_psycopg,
        ):
            PostgresMemoryStore(self.config).save_snapshot(self.scope, snapshot)

        self.assertTrue(connection.committed)
        self.assertEqual(len(cursor.executed), 5)
        self.assertIn("INSERT INTO conversation_sessions", cursor.executed[0][0])
        self.assertIn("INSERT INTO conversation_summaries", cursor.executed[1][0])
        self.assertIn("DELETE FROM conversation_turns", cursor.executed[2][0])
        self.assertIn("INSERT INTO conversation_turns", cursor.executed[3][0])
        self.assertIn("INSERT INTO conversation_turns", cursor.executed[4][0])


if __name__ == "__main__":
    unittest.main()

"""PostgreSQL 长期记忆存储测试。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from chat_app.config import PostgresConfig
from chat_app.postgres.long_term_store import PostgresLongTermStore


class FakeLongTermCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, list[object]]] = []
        self.rows = [
            {
                "id": 1,
                "scope_type": "user",
                "scope_id": 123,
                "memory_type": "profile",
                "memory_key": "nickname",
                "content": "用户喜欢猫",
                "confidence": 0.9,
                "priority": 5,
                "status": "active",
                "pinned": True,
                "metadata": {"source": "test"},
            }
        ]

    def __enter__(self) -> FakeLongTermCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, statement: str, params: list[object]) -> None:
        self.executed.append((statement, params))

    def fetchall(self) -> list[dict[str, object]]:
        return self.rows


class FakeLongTermConnection:
    def __init__(self, cursor: FakeLongTermCursor) -> None:
        self._cursor = cursor
        self.row_factory = None

    def __enter__(self) -> FakeLongTermConnection:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def cursor(self, *, row_factory=None) -> FakeLongTermCursor:
        self.row_factory = row_factory
        return self._cursor


class PostgresLongTermStoreTests(unittest.TestCase):
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

    def test_query_uses_callable_dict_row_factory(self) -> None:
        cursor = FakeLongTermCursor()
        connection = FakeLongTermConnection(cursor)
        fake_psycopg = SimpleNamespace(connect=lambda **kwargs: connection)

        def fake_dict_row(_cursor: object) -> object:
            return object()

        with (
            patch(
                "chat_app.postgres.long_term_store._import_psycopg",
                return_value=fake_psycopg,
            ),
            patch(
                "chat_app.postgres.long_term_store._import_dict_row",
                return_value=fake_dict_row,
            ),
        ):
            entries = PostgresLongTermStore(self.config).query(
                scope_type="user",
                scope_id=123,
                keywords=("猫",),
                limit=10,
            )

        self.assertTrue(callable(connection.row_factory))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].content, "用户喜欢猫")


if __name__ == "__main__":
    unittest.main()

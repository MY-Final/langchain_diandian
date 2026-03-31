"""PostgreSQL 初始化服务测试。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from chat_app.config import AppConfig, PostgresConfig, default_memory_config
from chat_app.postgres.service import (
    PostgresService,
    SCHEMA_STATEMENTS,
    ensure_postgres_ready,
)


class FakeCursor:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, statement: str) -> None:
        self.executed.append(statement)


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.committed = False

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True


class PostgresServiceTests(unittest.TestCase):
    """验证 PostgreSQL 表初始化。"""

    def test_ensure_tables_executes_all_statements(self) -> None:
        connection = FakeConnection()
        fake_psycopg = SimpleNamespace(connect=lambda **kwargs: connection)
        config = PostgresConfig(
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

        with patch(
            "chat_app.postgres.service._import_psycopg", return_value=fake_psycopg
        ):
            PostgresService(config).ensure_tables()

        self.assertEqual(connection.cursor_instance.executed, list(SCHEMA_STATEMENTS))
        self.assertTrue(connection.committed)

    def test_ensure_tables_is_noop_when_disabled(self) -> None:
        config = PostgresConfig(
            enabled=False,
            dsn="",
            host="127.0.0.1",
            port=5432,
            database="",
            user="",
            password="",
            sslmode="prefer",
            connect_timeout=10,
        )

        with patch("chat_app.postgres.service._import_psycopg") as import_psycopg:
            PostgresService(config).ensure_tables()

        import_psycopg.assert_not_called()

    def test_ensure_postgres_ready_uses_app_config(self) -> None:
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
            memory=default_memory_config(),
            postgres=PostgresConfig(
                enabled=True,
                dsn="postgresql://user:pwd@127.0.0.1:5432/diandian",
                host="127.0.0.1",
                port=5432,
                database="diandian",
                user="user",
                password="pwd",
                sslmode="prefer",
                connect_timeout=10,
            ),
        )

        with patch(
            "chat_app.postgres.service.PostgresService.ensure_tables"
        ) as ensure_tables:
            ensure_postgres_ready(config)

        ensure_tables.assert_called_once()


if __name__ == "__main__":
    unittest.main()

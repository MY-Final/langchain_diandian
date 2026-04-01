"""配置加载测试。"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chat_app.config import (
    load_dotenv_file,
    load_config,
    load_memory_config,
    load_postgres_config,
    load_prompt_text,
)


class LoadDotenvFileTests(unittest.TestCase):
    """验证 .env 文件解析逻辑。"""

    def test_loads_missing_environment_values_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "OPENAI_API_KEY=file-key\nOPENAI_MODEL=Qwen/Qwen3-8B\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}, clear=True):
                load_dotenv_file(env_path)

                self.assertEqual(os.environ["OPENAI_API_KEY"], "env-key")
                self.assertEqual(os.environ["OPENAI_MODEL"], "Qwen/Qwen3-8B")


class LoadPromptTextTests(unittest.TestCase):
    """验证 prompt 文件读取逻辑。"""

    def test_reads_prompt_file_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_path = Path(temp_dir) / "system_prompt.txt"
            prompt_path.write_text("你是一个测试助手。\n", encoding="utf-8")

            self.assertEqual(load_prompt_text(prompt_path), "你是一个测试助手。")


class LoadMemoryConfigTests(unittest.TestCase):
    """验证记忆配置加载。"""

    def test_loads_private_and_group_memory_policy(self) -> None:
        with patch.dict(
            os.environ,
            {
                "CHAT_MEMORY_ENABLE_SUMMARY": "true",
                "PRIVATE_CHAT_MEMORY_MAX_TURNS": "14",
                "PRIVATE_CHAT_MEMORY_SUMMARY_TRIGGER_TURNS": "18",
                "PRIVATE_CHAT_MEMORY_SUMMARY_BATCH_TURNS": "6",
                "GROUP_CHAT_MEMORY_MAX_TURNS": "7",
                "GROUP_CHAT_MEMORY_SUMMARY_TRIGGER_TURNS": "10",
                "GROUP_CHAT_MEMORY_SUMMARY_BATCH_TURNS": "3",
                "CHAT_MEMORY_MAX_SUMMARY_CHARS": "800",
                "CHAT_MEMORY_MAX_INPUT_CHARS": "9000",
            },
            clear=True,
        ):
            memory = load_memory_config()

        self.assertTrue(memory.enable_summary)
        self.assertEqual(memory.private_policy.max_turns, 14)
        self.assertEqual(memory.private_policy.summary_trigger_turns, 18)
        self.assertEqual(memory.private_policy.summary_batch_turns, 6)
        self.assertEqual(memory.group_policy.max_turns, 7)
        self.assertEqual(memory.group_policy.summary_trigger_turns, 10)
        self.assertEqual(memory.group_policy.summary_batch_turns, 3)
        self.assertEqual(memory.max_summary_chars, 800)
        self.assertEqual(memory.max_input_chars, 9000)

    def test_validates_trigger_turns_not_smaller_than_window(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PRIVATE_CHAT_MEMORY_MAX_TURNS": "10",
                "PRIVATE_CHAT_MEMORY_SUMMARY_TRIGGER_TURNS": "9",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(
                ValueError, "PRIVATE_CHAT_MEMORY_SUMMARY_TRIGGER_TURNS"
            ):
                load_memory_config()


class LoadPostgresConfigTests(unittest.TestCase):
    """验证 PostgreSQL 配置加载。"""

    def test_uses_dsn_when_provided(self) -> None:
        with patch.dict(
            os.environ,
            {
                "POSTGRES_DSN": "postgresql://user:pwd@127.0.0.1:5432/diandian",
            },
            clear=True,
        ):
            config = load_postgres_config()

        self.assertTrue(config.enabled)
        self.assertEqual(config.dsn, "postgresql://user:pwd@127.0.0.1:5432/diandian")

    def test_loads_split_connection_fields(self) -> None:
        with patch.dict(
            os.environ,
            {
                "POSTGRES_ENABLED": "true",
                "POSTGRES_HOST": "db.example.com",
                "POSTGRES_PORT": "5433",
                "POSTGRES_DB": "diandian",
                "POSTGRES_USER": "bot_user",
                "POSTGRES_PASSWORD": "secret",
                "POSTGRES_SSLMODE": "require",
                "POSTGRES_CONNECT_TIMEOUT": "5",
            },
            clear=True,
        ):
            config = load_postgres_config()

        self.assertTrue(config.enabled)
        self.assertEqual(config.host, "db.example.com")
        self.assertEqual(config.port, 5433)
        self.assertEqual(config.database, "diandian")
        self.assertEqual(config.user, "bot_user")
        self.assertEqual(config.password, "secret")
        self.assertEqual(config.sslmode, "require")
        self.assertEqual(config.connect_timeout, 5)

    def test_requires_database_and_user_when_enabled_without_dsn(self) -> None:
        with patch.dict(
            os.environ,
            {
                "POSTGRES_ENABLED": "true",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "POSTGRES_DB"):
                load_postgres_config()


class LoadAppConfigTests(unittest.TestCase):
    """验证 AppConfig 额外字段加载。"""

    def test_loads_operator_user_ids(self) -> None:
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "key",
                "OPENAI_BASE_URL": "http://example.com/v1",
                "OPENAI_MODEL": "test-model",
                "SYSTEM_PROMPT": "你是测试助手。",
                "ONEBOT_OPERATOR_USER_IDS": "10001, 10002",
            },
            clear=True,
        ):
            config = load_config()

        self.assertEqual(config.operator_user_ids, (10001, 10002))


if __name__ == "__main__":
    unittest.main()

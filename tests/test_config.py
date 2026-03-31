"""配置加载测试。"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chat_app.config import load_dotenv_file, load_prompt_text


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


if __name__ == "__main__":
    unittest.main()

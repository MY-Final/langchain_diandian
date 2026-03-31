"""OneBot 配置加载测试。"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from onebot_gateway.config import DEFAULT_NAPCAT_WS_URL, load_onebot_config


class LoadOneBotConfigTests(unittest.TestCase):
    """验证 OneBot 环境变量配置加载。"""

    def test_reads_values_from_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "NAPCAT_WS_URL": "ws://127.0.0.1:3001/",
                "NAPCAT_TOKEN": "test-token",
            },
            clear=True,
        ):
            with patch("onebot_gateway.config.load_dotenv_file"):
                config = load_onebot_config()

        self.assertEqual(config.ws_url, "ws://127.0.0.1:3001/")
        self.assertEqual(config.token, "test-token")

    def test_uses_default_values_when_environment_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("onebot_gateway.config.load_dotenv_file"):
                config = load_onebot_config()

        self.assertEqual(config.ws_url, DEFAULT_NAPCAT_WS_URL)
        self.assertEqual(config.token, "")


if __name__ == "__main__":
    unittest.main()

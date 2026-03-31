"""OneBot 网关配置加载。"""

from __future__ import annotations

import os
from dataclasses import dataclass

from chat_app.config import load_dotenv_file


DEFAULT_NAPCAT_WS_URL = "ws://your-host:3001/"


@dataclass(frozen=True)
class OneBotConfig:
    """OneBot WebSocket 连接配置。"""

    ws_url: str
    token: str


def load_onebot_config() -> OneBotConfig:
    """从环境变量读取 OneBot 网关配置。"""
    load_dotenv_file()

    return OneBotConfig(
        ws_url=os.getenv("NAPCAT_WS_URL", DEFAULT_NAPCAT_WS_URL).strip(),
        token=os.getenv("NAPCAT_TOKEN", "").strip(),
    )

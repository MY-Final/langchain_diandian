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
    bot_name_patterns: tuple[str, ...]
    reply_with_quote: bool


def load_onebot_config() -> OneBotConfig:
    """从环境变量读取 OneBot 网关配置。"""
    load_dotenv_file()

    return OneBotConfig(
        ws_url=os.getenv("NAPCAT_WS_URL", DEFAULT_NAPCAT_WS_URL).strip(),
        token=os.getenv("NAPCAT_TOKEN", "").strip(),
        bot_name_patterns=_parse_name_patterns(
            os.getenv("ONEBOT_BOT_NAME_PATTERNS", "")
        ),
        reply_with_quote=_parse_bool(os.getenv("ONEBOT_REPLY_WITH_QUOTE", "true")),
    )


def _parse_name_patterns(raw_value: str) -> tuple[str, ...]:
    """支持使用英文逗号分隔多个 bot 名称正则。"""
    parts = [item.strip() for item in raw_value.split(",")]
    return tuple(item for item in parts if item)


def _parse_bool(raw_value: str) -> bool:
    """解析布尔环境变量。"""
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}

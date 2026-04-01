"""消息索引配置加载。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from chat_app.config import load_dotenv_file


DEFAULT_REDIS_URL = "redis://127.0.0.1:6379/0"
DEFAULT_KEY_PREFIX = "obmsg"
DEFAULT_TTL_SECONDS = 172800
DEFAULT_CHAT_MAXLEN = 200
DEFAULT_USER_MAXLEN = 100
DEFAULT_SELF_MAXLEN = 100
DEFAULT_RECALL_WINDOW_SECONDS = 120
DEFAULT_CONNECT_TIMEOUT_MS = 3000
DEFAULT_SOCKET_TIMEOUT_MS = 3000


@dataclass(frozen=True)
class MessageIndexConfig:
    """消息索引 Redis 配置。"""

    enabled: bool
    redis_url: str
    key_prefix: str
    ttl_seconds: int
    chat_maxlen: int
    user_maxlen: int
    self_maxlen: int
    recall_window_seconds: int
    connect_timeout_ms: int
    socket_timeout_ms: int
    group_self_no_window_when_admin: bool = True


def load_message_index_config() -> MessageIndexConfig:
    """从环境变量读取消息索引配置。"""
    load_dotenv_file()

    return MessageIndexConfig(
        enabled=_parse_bool(os.getenv("MESSAGE_INDEX_ENABLED", "true")),
        redis_url=os.getenv("MESSAGE_INDEX_REDIS_URL", DEFAULT_REDIS_URL).strip()
        or DEFAULT_REDIS_URL,
        key_prefix=os.getenv("MESSAGE_INDEX_KEY_PREFIX", DEFAULT_KEY_PREFIX).strip()
        or DEFAULT_KEY_PREFIX,
        ttl_seconds=_parse_positive_int(
            os.getenv("MESSAGE_INDEX_TTL_SECONDS", ""),
            DEFAULT_TTL_SECONDS,
            "MESSAGE_INDEX_TTL_SECONDS",
        ),
        chat_maxlen=_parse_positive_int(
            os.getenv("MESSAGE_INDEX_CHAT_MAXLEN", ""),
            DEFAULT_CHAT_MAXLEN,
            "MESSAGE_INDEX_CHAT_MAXLEN",
        ),
        user_maxlen=_parse_positive_int(
            os.getenv("MESSAGE_INDEX_USER_MAXLEN", ""),
            DEFAULT_USER_MAXLEN,
            "MESSAGE_INDEX_USER_MAXLEN",
        ),
        self_maxlen=_parse_positive_int(
            os.getenv("MESSAGE_INDEX_SELF_MAXLEN", ""),
            DEFAULT_SELF_MAXLEN,
            "MESSAGE_INDEX_SELF_MAXLEN",
        ),
        recall_window_seconds=_parse_positive_int(
            os.getenv("MESSAGE_INDEX_RECALL_WINDOW_SECONDS", ""),
            DEFAULT_RECALL_WINDOW_SECONDS,
            "MESSAGE_INDEX_RECALL_WINDOW_SECONDS",
        ),
        connect_timeout_ms=_parse_positive_int(
            os.getenv("MESSAGE_INDEX_CONNECT_TIMEOUT_MS", ""),
            DEFAULT_CONNECT_TIMEOUT_MS,
            "MESSAGE_INDEX_CONNECT_TIMEOUT_MS",
        ),
        socket_timeout_ms=_parse_positive_int(
            os.getenv("MESSAGE_INDEX_SOCKET_TIMEOUT_MS", ""),
            DEFAULT_SOCKET_TIMEOUT_MS,
            "MESSAGE_INDEX_SOCKET_TIMEOUT_MS",
        ),
        group_self_no_window_when_admin=_parse_bool(
            os.getenv("MESSAGE_INDEX_GROUP_SELF_NO_WINDOW_WHEN_ADMIN", "true"),
        ),
    )


def _parse_bool(raw_value: str) -> bool:
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def _parse_positive_int(raw_value: str, default: int, key_name: str) -> int:
    value = raw_value.strip()
    if not value:
        return default
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{key_name} 必须是正整数。")
    return parsed

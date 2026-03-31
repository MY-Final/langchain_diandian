"""应用配置加载。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.txt"
)


DEFAULT_ENABLE_SUMMARY = True
DEFAULT_PRIVATE_MAX_TURNS = 12
DEFAULT_PRIVATE_SUMMARY_TRIGGER_TURNS = 16
DEFAULT_PRIVATE_SUMMARY_BATCH_TURNS = 6
DEFAULT_GROUP_MAX_TURNS = 8
DEFAULT_GROUP_SUMMARY_TRIGGER_TURNS = 12
DEFAULT_GROUP_SUMMARY_BATCH_TURNS = 4
DEFAULT_MEMORY_MAX_SUMMARY_CHARS = 1200
DEFAULT_MEMORY_MAX_INPUT_CHARS = 12000
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_POSTGRES_SSLMODE = "prefer"
DEFAULT_POSTGRES_CONNECT_TIMEOUT = 10


@dataclass(frozen=True)
class MemoryPolicyConfig:
    """单种会话场景的记忆窗口配置。"""

    max_turns: int
    summary_trigger_turns: int
    summary_batch_turns: int


@dataclass(frozen=True)
class MemoryConfig:
    """会话记忆配置。"""

    enable_summary: bool
    max_summary_chars: int
    max_input_chars: int
    private_policy: MemoryPolicyConfig
    group_policy: MemoryPolicyConfig


@dataclass(frozen=True)
class PostgresConfig:
    """PostgreSQL 连接配置。"""

    enabled: bool
    dsn: str
    host: str
    port: int
    database: str
    user: str
    password: str
    sslmode: str
    connect_timeout: int

    def to_connection_kwargs(self) -> dict[str, object]:
        """返回 psycopg 连接参数。"""
        if self.dsn:
            return {"conninfo": self.dsn, "connect_timeout": self.connect_timeout}

        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.database,
            "user": self.user,
            "password": self.password,
            "sslmode": self.sslmode,
            "connect_timeout": self.connect_timeout,
        }


def default_postgres_config() -> PostgresConfig:
    """返回默认 PostgreSQL 配置。"""
    return PostgresConfig(
        enabled=False,
        dsn="",
        host="127.0.0.1",
        port=DEFAULT_POSTGRES_PORT,
        database="",
        user="",
        password="",
        sslmode=DEFAULT_POSTGRES_SSLMODE,
        connect_timeout=DEFAULT_POSTGRES_CONNECT_TIMEOUT,
    )


def default_memory_config() -> MemoryConfig:
    """返回默认记忆配置。"""
    return MemoryConfig(
        enable_summary=DEFAULT_ENABLE_SUMMARY,
        max_summary_chars=DEFAULT_MEMORY_MAX_SUMMARY_CHARS,
        max_input_chars=DEFAULT_MEMORY_MAX_INPUT_CHARS,
        private_policy=MemoryPolicyConfig(
            max_turns=DEFAULT_PRIVATE_MAX_TURNS,
            summary_trigger_turns=DEFAULT_PRIVATE_SUMMARY_TRIGGER_TURNS,
            summary_batch_turns=DEFAULT_PRIVATE_SUMMARY_BATCH_TURNS,
        ),
        group_policy=MemoryPolicyConfig(
            max_turns=DEFAULT_GROUP_MAX_TURNS,
            summary_trigger_turns=DEFAULT_GROUP_SUMMARY_TRIGGER_TURNS,
            summary_batch_turns=DEFAULT_GROUP_SUMMARY_BATCH_TURNS,
        ),
    )


@dataclass(frozen=True)
class AppConfig:
    """对话应用运行配置。"""

    api_key: str
    base_url: str
    model: str
    system_prompt: str
    memory: MemoryConfig = field(default_factory=default_memory_config)
    postgres: PostgresConfig = field(default_factory=default_postgres_config)
    debug_tool_calls: bool = False


def load_dotenv_file(env_path: Path = DEFAULT_ENV_PATH) -> None:
    """将简单的 .env 文件键值对加载到环境变量中。"""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def load_prompt_text(prompt_path: Path) -> str:
    """读取 prompt 文件内容。"""
    if not prompt_path.exists():
        raise ValueError(f"Prompt 文件不存在：{prompt_path}")

    prompt_text = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt_text:
        raise ValueError(f"Prompt 文件内容为空：{prompt_path}")
    return prompt_text


def load_config() -> AppConfig:
    """从环境变量读取配置。"""
    load_dotenv_file()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()
    system_prompt = os.getenv("SYSTEM_PROMPT", "").strip()
    system_prompt_file = os.getenv("SYSTEM_PROMPT_FILE", "").strip()

    missing_keys = [
        name
        for name, value in (
            ("OPENAI_API_KEY", api_key),
            ("OPENAI_BASE_URL", base_url),
            ("OPENAI_MODEL", model),
        )
        if not value
    ]
    if missing_keys:
        joined = ", ".join(missing_keys)
        raise ValueError(f"缺少必要配置：{joined}")

    if system_prompt:
        resolved_prompt = system_prompt
    else:
        prompt_path = (
            Path(system_prompt_file) if system_prompt_file else DEFAULT_PROMPT_PATH
        )
        if not prompt_path.is_absolute():
            prompt_path = DEFAULT_ENV_PATH.parent / prompt_path
        resolved_prompt = load_prompt_text(prompt_path)

    return AppConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        system_prompt=resolved_prompt,
        memory=load_memory_config(),
        postgres=load_postgres_config(),
        debug_tool_calls=_parse_bool(os.getenv("CHAT_DEBUG_TOOL_CALLS", "false")),
    )


def load_memory_config() -> MemoryConfig:
    """从环境变量读取会话记忆配置。"""
    return MemoryConfig(
        enable_summary=_parse_bool(
            os.getenv("CHAT_MEMORY_ENABLE_SUMMARY", str(DEFAULT_ENABLE_SUMMARY))
        ),
        max_summary_chars=_parse_positive_int(
            os.getenv("CHAT_MEMORY_MAX_SUMMARY_CHARS", ""),
            DEFAULT_MEMORY_MAX_SUMMARY_CHARS,
            "CHAT_MEMORY_MAX_SUMMARY_CHARS",
        ),
        max_input_chars=_parse_positive_int(
            os.getenv("CHAT_MEMORY_MAX_INPUT_CHARS", ""),
            DEFAULT_MEMORY_MAX_INPUT_CHARS,
            "CHAT_MEMORY_MAX_INPUT_CHARS",
        ),
        private_policy=_load_memory_policy(
            max_turns_key="PRIVATE_CHAT_MEMORY_MAX_TURNS",
            trigger_turns_key="PRIVATE_CHAT_MEMORY_SUMMARY_TRIGGER_TURNS",
            batch_turns_key="PRIVATE_CHAT_MEMORY_SUMMARY_BATCH_TURNS",
            default_max_turns=DEFAULT_PRIVATE_MAX_TURNS,
            default_trigger_turns=DEFAULT_PRIVATE_SUMMARY_TRIGGER_TURNS,
            default_batch_turns=DEFAULT_PRIVATE_SUMMARY_BATCH_TURNS,
        ),
        group_policy=_load_memory_policy(
            max_turns_key="GROUP_CHAT_MEMORY_MAX_TURNS",
            trigger_turns_key="GROUP_CHAT_MEMORY_SUMMARY_TRIGGER_TURNS",
            batch_turns_key="GROUP_CHAT_MEMORY_SUMMARY_BATCH_TURNS",
            default_max_turns=DEFAULT_GROUP_MAX_TURNS,
            default_trigger_turns=DEFAULT_GROUP_SUMMARY_TRIGGER_TURNS,
            default_batch_turns=DEFAULT_GROUP_SUMMARY_BATCH_TURNS,
        ),
    )


def load_postgres_config() -> PostgresConfig:
    """从环境变量读取 PostgreSQL 配置。"""
    dsn = os.getenv("POSTGRES_DSN", "").strip()
    enabled = _parse_bool(os.getenv("POSTGRES_ENABLED", "false")) or bool(dsn)
    host = os.getenv("POSTGRES_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = _parse_positive_int(
        os.getenv("POSTGRES_PORT", ""),
        DEFAULT_POSTGRES_PORT,
        "POSTGRES_PORT",
    )
    database = os.getenv("POSTGRES_DB", "").strip()
    user = os.getenv("POSTGRES_USER", "").strip()
    password = os.getenv("POSTGRES_PASSWORD", "")
    sslmode = os.getenv("POSTGRES_SSLMODE", DEFAULT_POSTGRES_SSLMODE).strip()
    connect_timeout = _parse_positive_int(
        os.getenv("POSTGRES_CONNECT_TIMEOUT", ""),
        DEFAULT_POSTGRES_CONNECT_TIMEOUT,
        "POSTGRES_CONNECT_TIMEOUT",
    )

    if enabled and not dsn:
        missing_keys = [
            key
            for key, value in (
                ("POSTGRES_HOST", host),
                ("POSTGRES_DB", database),
                ("POSTGRES_USER", user),
            )
            if not value
        ]
        if missing_keys:
            joined = ", ".join(missing_keys)
            raise ValueError(f"缺少 PostgreSQL 配置：{joined}")

    return PostgresConfig(
        enabled=enabled,
        dsn=dsn,
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        sslmode=sslmode or DEFAULT_POSTGRES_SSLMODE,
        connect_timeout=connect_timeout,
    )


def _load_memory_policy(
    *,
    max_turns_key: str,
    trigger_turns_key: str,
    batch_turns_key: str,
    default_max_turns: int,
    default_trigger_turns: int,
    default_batch_turns: int,
) -> MemoryPolicyConfig:
    max_turns = _parse_positive_int(
        os.getenv(max_turns_key, ""),
        default_max_turns,
        max_turns_key,
    )
    summary_trigger_turns = _parse_positive_int(
        os.getenv(trigger_turns_key, ""),
        default_trigger_turns,
        trigger_turns_key,
    )
    summary_batch_turns = _parse_positive_int(
        os.getenv(batch_turns_key, ""),
        default_batch_turns,
        batch_turns_key,
    )

    if summary_trigger_turns < max_turns:
        raise ValueError(f"{trigger_turns_key} 不能小于 {max_turns_key}。")
    if summary_batch_turns > summary_trigger_turns:
        raise ValueError(f"{batch_turns_key} 不能大于 {trigger_turns_key}。")

    return MemoryPolicyConfig(
        max_turns=max_turns,
        summary_trigger_turns=summary_trigger_turns,
        summary_batch_turns=summary_batch_turns,
    )


def _parse_bool(raw_value: str) -> bool:
    """解析布尔环境变量。"""
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def _parse_positive_int(raw_value: str, default: int, key_name: str) -> int:
    """解析正整数环境变量。"""
    value = raw_value.strip()
    if not value:
        return default

    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{key_name} 必须是正整数。")
    return parsed

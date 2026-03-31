"""应用配置加载。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.txt"
)


@dataclass(frozen=True)
class AppConfig:
    """对话应用运行配置。"""

    api_key: str
    base_url: str
    model: str
    system_prompt: str


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
    )

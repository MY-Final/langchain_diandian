"""工具注册表。"""

from __future__ import annotations

from langchain_core.tools import BaseTool

from chat_app.emoji.index import DEFAULT_EMOJI_RECORDS_PATH
from chat_app.tools.emoji_tool import search_qq_emojis


def build_chat_tools() -> list[BaseTool]:
    """构建当前会话可用工具。"""
    tools: list[BaseTool] = []
    if DEFAULT_EMOJI_RECORDS_PATH.exists():
        tools.append(search_qq_emojis)
    return tools

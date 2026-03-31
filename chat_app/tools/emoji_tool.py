"""QQ 表情检索工具。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.emoji.index import EmojiSearchIndex


@tool
def search_qq_emojis(query: str, limit: int = 5) -> str:
    """检索适合当前语气的 QQ face 表情候选，返回 emoji_id 列表供模型使用 <face id="..." />。"""
    normalized_limit = max(1, min(limit, 10))
    results = EmojiSearchIndex.from_default_path().search(query, normalized_limit)
    payload = [item.to_dict() for item in results]
    return json.dumps(payload, ensure_ascii=False)

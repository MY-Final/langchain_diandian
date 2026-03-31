"""QQ 表情索引与检索。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from chat_app.emoji.types import EmojiRecord, EmojiSearchResult


DEFAULT_EMOJI_RECORDS_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "assets"
    / "qq_emoji"
    / "indexes"
    / "emoji_records.jsonl"
)

SEMANTIC_HINTS: dict[str, tuple[str, ...]] = {
    "开心": ("微笑", "呲牙", "大笑", "庆祝", "点赞"),
    "高兴": ("微笑", "呲牙", "大笑", "庆祝"),
    "友好": ("微笑", "握手", "抱拳"),
    "认可": ("OK", "赞", "点赞", "胜利"),
    "同意": ("OK", "赞", "点赞"),
    "鼓励": ("加油", "奋斗", "点赞", "顶呱呱"),
    "安慰": ("抱抱", "拥抱", "可怜", "爱心"),
    "难过": ("难过", "流泪", "大哭", "委屈"),
    "尴尬": ("尴尬", "汗", "无奈", "流汗"),
    "生气": ("发怒", "怄火", "哼", "嫌弃"),
    "调皮": ("调皮", "坏笑", "doge", "斜眼笑"),
    "疑问": ("疑问", "问号脸", "emm", "咦"),
    "感谢": ("抱拳", "感谢", "拜谢", "爱心"),
    "庆祝": ("庆祝", "烟花", "打call", "干杯"),
}


class EmojiSearchIndex:
    """本地 QQ 表情检索索引。"""

    def __init__(self, records: tuple[EmojiRecord, ...]) -> None:
        self._records = records

    @classmethod
    def from_default_path(cls) -> EmojiSearchIndex:
        """从默认索引文件加载。"""
        return cls(load_emoji_records())

    def search(self, query: str, limit: int = 5) -> list[EmojiSearchResult]:
        """按自然语言语义检索表情候选。"""
        normalized_query = _normalize_text(query)
        if not normalized_query:
            return []

        results: list[EmojiSearchResult] = []
        for record in self._records:
            score, reasons = _score_record(record, normalized_query)
            if score <= 0:
                continue

            results.append(
                EmojiSearchResult(
                    emoji_id=record.emoji_id,
                    emoji_name=record.emoji_name,
                    aliases=record.aliases,
                    score=score,
                    reasons=tuple(reasons),
                )
            )

        results.sort(key=lambda item: (-item.score, item.emoji_name))
        return results[:limit]


@lru_cache(maxsize=1)
def load_emoji_records(
    records_path: Path = DEFAULT_EMOJI_RECORDS_PATH,
) -> tuple[EmojiRecord, ...]:
    """加载 emoji_records.jsonl。"""
    if not records_path.exists():
        return ()

    records: list[EmojiRecord] = []
    with records_path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line:
                continue

            payload = json.loads(line)
            records.append(
                EmojiRecord(
                    emoji_id=str(payload.get("emoji_id", "")).strip(),
                    emoji_name=str(payload.get("emoji_name", "")).strip(),
                    aliases=tuple(
                        str(item).strip()
                        for item in payload.get("aliases", [])
                        if str(item).strip()
                    ),
                    asset_path=str(payload.get("asset_path", "")).strip(),
                    animation_path=str(payload.get("animation_path", "")).strip(),
                    category=str(payload.get("category", "")).strip(),
                )
            )
    return tuple(records)


def _score_record(record: EmojiRecord, normalized_query: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    name = _normalize_text(record.emoji_name)
    aliases = tuple(_normalize_text(item) for item in record.aliases)

    if normalized_query == name:
        score += 100
        reasons.append("精确匹配表情名")

    if normalized_query in aliases:
        score += 90
        reasons.append("精确匹配别名")

    if name and name in normalized_query and normalized_query != name:
        score += 60
        reasons.append("查询中包含表情名")

    if name and normalized_query in name and normalized_query != name:
        score += 50
        reasons.append("表情名包含查询词")

    for alias in aliases:
        if alias and alias in normalized_query:
            score += 40
            reasons.append(f"查询命中别名:{alias}")
            break

    overlap_chars = sorted(set(name) & set(normalized_query))
    if len(overlap_chars) >= 2:
        score += len(overlap_chars) * 5
        reasons.append(f"字符重叠:{''.join(overlap_chars)}")

    for keyword, emoji_names in SEMANTIC_HINTS.items():
        if keyword in normalized_query and record.emoji_name in emoji_names:
            score += 35
            reasons.append(f"语义匹配:{keyword}")

    return score, reasons


def _normalize_text(text: str) -> str:
    return text.strip().lower().replace("/", "")

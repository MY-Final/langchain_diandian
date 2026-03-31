"""QQ 表情检索数据结构。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmojiRecord:
    """单个表情记录。"""

    emoji_id: str
    emoji_name: str
    aliases: tuple[str, ...]
    asset_path: str
    animation_path: str
    category: str


@dataclass(frozen=True)
class EmojiSearchResult:
    """表情检索结果。"""

    emoji_id: str
    emoji_name: str
    aliases: tuple[str, ...]
    score: int
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "emoji_id": self.emoji_id,
            "emoji_name": self.emoji_name,
            "aliases": list(self.aliases),
            "score": self.score,
            "reasons": list(self.reasons),
        }

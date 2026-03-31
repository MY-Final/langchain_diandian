"""回复分段器。"""

from __future__ import annotations

from onebot_gateway.config import ReplySplitConfig


class ReplySplitter:
    """按规则把长回复拆成多段消息。"""

    def __init__(self, config: ReplySplitConfig) -> None:
        self._config = config

    @property
    def marker(self) -> str:
        """显式分段标记。"""
        return self._config.marker

    def split(self, text: str) -> list[str]:
        """把回复文本拆成多段。"""
        normalized = text.replace("\r\n", "\n").strip()
        if not normalized:
            return []

        if not self._config.enabled:
            return [normalized]

        explicit_parts = self._split_by_marker(normalized)
        if explicit_parts is not None:
            segments: list[str] = []
            for piece in explicit_parts:
                segments.extend(self._split_piece(piece))
            return [segment.strip() for segment in segments if segment.strip()]

        return self._split_piece(normalized)

    def _split_by_marker(self, text: str) -> list[str] | None:
        if self._config.marker and self._config.marker in text:
            return [
                part.strip() for part in text.split(self._config.marker) if part.strip()
            ]

        return None

    def _split_piece(self, piece: str) -> list[str]:
        if len(piece) <= self._config.max_chars:
            return [piece]

        return self._hard_split(piece)

    def _hard_split(self, piece: str) -> list[str]:
        return [
            piece[index : index + self._config.max_chars].strip()
            for index in range(0, len(piece), self._config.max_chars)
            if piece[index : index + self._config.max_chars].strip()
        ]

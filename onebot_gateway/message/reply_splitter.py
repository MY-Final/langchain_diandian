"""回复分段器。"""

from __future__ import annotations

import re

from onebot_gateway.config import ReplySplitConfig


SENTENCE_SEPARATOR_RE = re.compile(r"(?<=[。！？!?；;])")
PARAGRAPH_SEPARATOR_RE = re.compile(r"\n\s*\n+")


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

        pieces = self._split_paragraphs(normalized)
        segments: list[str] = []
        current = ""
        for piece in pieces:
            for chunk in self._split_piece(piece):
                if not current:
                    current = chunk
                    continue

                candidate = f"{current}\n\n{chunk}"
                if len(candidate) <= self._config.max_chars:
                    current = candidate
                    continue

                segments.append(current)
                current = chunk

        if current:
            segments.append(current)
        return [segment.strip() for segment in segments if segment.strip()]

    def _split_by_marker(self, text: str) -> list[str] | None:
        if self._config.marker and self._config.marker in text:
            return [
                part.strip() for part in text.split(self._config.marker) if part.strip()
            ]

        return None

    def _split_paragraphs(self, text: str) -> list[str]:
        paragraphs = [
            part.strip() for part in PARAGRAPH_SEPARATOR_RE.split(text) if part.strip()
        ]
        return paragraphs or [text]

    def _split_piece(self, piece: str) -> list[str]:
        if len(piece) <= self._config.max_chars:
            return [piece]

        line_parts = self._split_by_lines(piece)
        if line_parts is not None:
            return line_parts

        sentence_parts = self._split_by_sentences(piece)
        if sentence_parts is not None:
            return sentence_parts

        return self._hard_split(piece)

    def _split_by_lines(self, piece: str) -> list[str] | None:
        lines = [line.strip() for line in piece.split("\n") if line.strip()]
        if len(lines) <= 1:
            return None

        return self._pack_units(lines, joiner="\n")

    def _split_by_sentences(self, piece: str) -> list[str] | None:
        units = [
            unit.strip() for unit in SENTENCE_SEPARATOR_RE.split(piece) if unit.strip()
        ]
        if len(units) <= 1:
            return None

        return self._pack_units(units, joiner="")

    def _pack_units(self, units: list[str], *, joiner: str) -> list[str]:
        packed: list[str] = []
        current = ""
        for unit in units:
            if len(unit) > self._config.max_chars:
                if current:
                    packed.append(current)
                    current = ""
                packed.extend(self._hard_split(unit))
                continue

            candidate = unit if not current else f"{current}{joiner}{unit}"
            if len(candidate) <= self._config.max_chars:
                current = candidate
                continue

            packed.append(current)
            current = unit

        if current:
            packed.append(current)
        return packed

    def _hard_split(self, piece: str) -> list[str]:
        return [
            piece[index : index + self._config.max_chars].strip()
            for index in range(0, len(piece), self._config.max_chars)
            if piece[index : index + self._config.max_chars].strip()
        ]

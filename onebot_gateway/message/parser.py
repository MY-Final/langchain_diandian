"""OneBot 消息事件解析。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SenderInfo:
    """发送者信息。"""

    user_id: int | None
    nickname: str
    card: str
    role: str

    @property
    def display_name(self) -> str:
        """优先返回群名片，否则返回昵称。"""
        return self.card or self.nickname


@dataclass(frozen=True)
class MessageSegment:
    """OneBot 消息段。"""

    type: str
    data: dict[str, str]


@dataclass(frozen=True)
class ParsedMessageEvent:
    """面向上层逻辑的消息事件。"""

    self_id: int | None
    user_id: int | None
    message_id: int | None
    message_type: str
    group_id: int | None
    group_name: str
    sender: SenderInfo
    plain_text: str
    raw_message: str
    segments: tuple[MessageSegment, ...]
    at_targets: tuple[int, ...]
    reply_message_id: int | None

    def is_group_message(self) -> bool:
        return self.message_type == "group"

    def is_private_message(self) -> bool:
        return self.message_type == "private"

    def is_at_self(self) -> bool:
        return self.self_id is not None and self.self_id in self.at_targets

    def is_reply_to_message(self) -> bool:
        return self.reply_message_id is not None

    def is_reply_message(self) -> bool:
        return self.is_reply_to_message()

    def is_reply_or_at_self(self) -> bool:
        return self.is_reply_to_message() or self.is_at_self()

    def mentions_bot_name(self, name_patterns: tuple[str, ...]) -> bool:
        if not self.plain_text:
            return False

        for pattern in name_patterns:
            if re.search(pattern, self.plain_text, re.IGNORECASE):
                return True
        return False

    def should_process(self, name_patterns: tuple[str, ...]) -> bool:
        if self.is_private_message():
            return True

        if not self.is_group_message():
            return False

        return self.is_reply_or_at_self() or self.mentions_bot_name(name_patterns)

    def to_summary(self, name_patterns: tuple[str, ...]) -> dict[str, Any]:
        """返回便于调试和后续接入智能体的结构。"""
        return {
            "text": self.plain_text,
            "is_at_self": self.is_at_self(),
            "sender_name": self.sender.display_name,
            "sender_user_id": self.user_id,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "chat_type": self.message_type,
            "is_group_message": self.is_group_message(),
            "is_private_message": self.is_private_message(),
            "is_reply_message": self.is_reply_to_message(),
            "mentions_bot_name": self.mentions_bot_name(name_patterns),
            "should_process": self.should_process(name_patterns),
            "at_targets": list(self.at_targets),
            "reply_message_id": self.reply_message_id,
        }


def parse_message_event(payload: dict[str, Any]) -> ParsedMessageEvent | None:
    """只解析消息事件，其他事件直接返回 None。"""
    if payload.get("post_type") != "message":
        return None

    return parse_message_payload(payload)


def parse_message_payload(
    payload: dict[str, Any],
    *,
    self_id: int | None = None,
    message_type: str | None = None,
    group_id: int | None = None,
    group_name: str | None = None,
) -> ParsedMessageEvent:
    """解析标准消息体，可用于事件或 `get_msg` 返回值。"""

    sender_payload = payload.get("sender")
    sender = _parse_sender(sender_payload if isinstance(sender_payload, dict) else {})
    segments = _parse_segments(payload.get("message"))

    return ParsedMessageEvent(
        self_id=_coalesce_int(payload.get("self_id"), self_id),
        user_id=_to_int(payload.get("user_id")),
        message_id=_to_int(payload.get("message_id")),
        message_type=_coalesce_str(payload.get("message_type"), message_type),
        group_id=_coalesce_int(payload.get("group_id"), group_id),
        group_name=_coalesce_str(payload.get("group_name"), group_name),
        sender=sender,
        plain_text=_build_plain_text(segments),
        raw_message=_to_str(payload.get("raw_message")),
        segments=segments,
        at_targets=_extract_at_targets(segments),
        reply_message_id=_extract_reply_message_id(segments),
    )


def _parse_sender(payload: dict[str, Any]) -> SenderInfo:
    return SenderInfo(
        user_id=_to_int(payload.get("user_id")),
        nickname=_to_str(payload.get("nickname")),
        card=_to_str(payload.get("card")),
        role=_to_str(payload.get("role")),
    )


def _parse_segments(message: Any) -> tuple[MessageSegment, ...]:
    if not isinstance(message, list):
        return ()

    segments: list[MessageSegment] = []
    for item in message:
        if not isinstance(item, dict):
            continue

        segment_type = _to_str(item.get("type"))
        raw_data = item.get("data")
        data: dict[str, str] = {}
        if isinstance(raw_data, dict):
            data = {str(key): _to_str(value) for key, value in raw_data.items()}

        segments.append(MessageSegment(type=segment_type, data=data))
    return tuple(segments)


def _build_plain_text(segments: tuple[MessageSegment, ...]) -> str:
    parts: list[str] = []
    for segment in segments:
        if segment.type == "text":
            parts.append(segment.data.get("text", ""))
            continue

        if segment.type == "at":
            continue

        if segment.type == "reply":
            continue

    return "".join(parts).strip()


def _extract_at_targets(segments: tuple[MessageSegment, ...]) -> tuple[int, ...]:
    targets: list[int] = []
    for segment in segments:
        if segment.type != "at":
            continue

        qq = _to_int(segment.data.get("qq"))
        if qq is not None:
            targets.append(qq)
    return tuple(targets)


def _extract_reply_message_id(segments: tuple[MessageSegment, ...]) -> int | None:
    for segment in segments:
        if segment.type != "reply":
            continue

        return _to_int(segment.data.get("id"))
    return None


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _coalesce_int(primary: Any, fallback: int | None) -> int | None:
    resolved = _to_int(primary)
    if resolved is not None:
        return resolved
    return fallback


def _coalesce_str(primary: Any, fallback: str | None) -> str:
    resolved = _to_str(primary)
    if resolved:
        return resolved
    return fallback or ""

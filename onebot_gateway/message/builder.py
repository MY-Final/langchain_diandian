"""OneBot 消息段构造。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OutgoingMessageSegment:
    """待发送的 OneBot 消息段。"""

    type: str
    data: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {"type": self.type, "data": self.data}


def text_segment(text: str) -> OutgoingMessageSegment:
    """构造文本消息段。"""
    return OutgoingMessageSegment(type="text", data={"text": text})


def at_segment(user_id: int | str) -> OutgoingMessageSegment:
    """构造 @ 消息段。"""
    return OutgoingMessageSegment(type="at", data={"qq": str(user_id)})


def reply_segment(message_id: int | str) -> OutgoingMessageSegment:
    """构造回复消息段。"""
    return OutgoingMessageSegment(type="reply", data={"id": str(message_id)})


def image_segment(file: str) -> OutgoingMessageSegment:
    """构造图片消息段。"""
    return OutgoingMessageSegment(type="image", data={"file": file})


def custom_segment(segment_type: str, **data: Any) -> OutgoingMessageSegment:
    """构造自定义消息段，便于后续扩展更多类型。"""
    return OutgoingMessageSegment(
        type=segment_type,
        data={
            str(key): "" if value is None else str(value) for key, value in data.items()
        },
    )


def ensure_segments(
    message: str | OutgoingMessageSegment | list[OutgoingMessageSegment],
) -> list[OutgoingMessageSegment]:
    """把字符串或单段消息统一转成消息段列表。"""
    if isinstance(message, str):
        return [text_segment(message)]

    if isinstance(message, OutgoingMessageSegment):
        return [message]

    return list(message)

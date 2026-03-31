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


def face_segment(face_id: int | str) -> OutgoingMessageSegment:
    """构造 QQ 表情消息段。"""
    return OutgoingMessageSegment(type="face", data={"id": str(face_id)})


def markdown_segment(content: str) -> OutgoingMessageSegment:
    """构造 markdown 消息段。"""
    return OutgoingMessageSegment(type="markdown", data={"content": content})


def record_segment(file: str) -> OutgoingMessageSegment:
    """构造语音消息段。"""
    return OutgoingMessageSegment(type="record", data={"file": file})


def video_segment(file: str) -> OutgoingMessageSegment:
    """构造视频消息段。"""
    return OutgoingMessageSegment(type="video", data={"file": file})


def contact_segment(contact_type: str, contact_id: int | str) -> OutgoingMessageSegment:
    """构造联系人消息段。"""
    return OutgoingMessageSegment(
        type="contact",
        data={"type": contact_type, "id": str(contact_id)},
    )


def poke_segment(poke_type: str, poke_id: int | str) -> OutgoingMessageSegment:
    """构造戳一戳消息段。"""
    return OutgoingMessageSegment(
        type="poke",
        data={"type": poke_type, "id": str(poke_id)},
    )


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

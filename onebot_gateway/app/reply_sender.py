"""回复发送辅助。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from onebot_gateway.message.rich_reply import build_rich_text_reply
from onebot_gateway.message.reply_splitter import ReplySplitter


@dataclass(frozen=True)
class SentMessageInfo:
    """单条发送结果。"""

    message_id: int | None
    part_text: str


@dataclass
class SendReplyResult:
    """send_reply_parts 的完整返回结果。"""

    sent_messages: list[SentMessageInfo] = field(default_factory=list)

    @property
    def message_ids(self) -> list[int]:
        return [m.message_id for m in self.sent_messages if m.message_id is not None]


async def send_reply_parts(
    *,
    send: Callable[[int | str, object], Awaitable[object]],
    target_id: int | str,
    reply_parts: tuple[str, ...],
    reply_message_id: int | None,
) -> SendReplyResult:
    """逐段发送回复，首段引用原消息。

    返回 SendReplyResult 包含每条消息的 message_id。
    """
    result = SendReplyResult()

    for index, part in enumerate(reply_parts):
        quoted_message_id = reply_message_id if index == 0 else None
        response = await send(
            target_id,
            build_rich_text_reply(part, reply_message_id=quoted_message_id),
        )

        message_id = _extract_message_id(response)
        result.sent_messages.append(
            SentMessageInfo(message_id=message_id, part_text=part)
        )

    return result


def _extract_message_id(response: object) -> int | None:
    """从发送响应中提取 message_id。"""
    if response is None:
        return None

    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, dict):
            raw = data.get("message_id")
            if isinstance(raw, int):
                return raw
            if isinstance(raw, str) and raw.strip():
                try:
                    return int(raw)
                except ValueError:
                    return None

    if hasattr(response, "message_id"):
        mid = response.message_id
        if isinstance(mid, int):
            return mid

    return None


def split_reply_text(
    text: str,
    reply_splitter: ReplySplitter,
) -> tuple[str, ...]:
    """拆分回复文本。"""
    parts = tuple(reply_splitter.split(text))
    return parts if parts else (text,)

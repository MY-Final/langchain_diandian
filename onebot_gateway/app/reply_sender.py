"""回复发送辅助。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from onebot_gateway.message.rich_reply import build_rich_text_reply
from onebot_gateway.message.reply_splitter import ReplySplitter


async def send_reply_parts(
    *,
    send: Callable[[int | str, object], Awaitable[object]],
    target_id: int | str,
    reply_parts: tuple[str, ...],
    reply_message_id: int | None,
) -> None:
    """逐段发送回复，首段引用原消息。"""
    for index, part in enumerate(reply_parts):
        quoted_message_id = reply_message_id if index == 0 else None
        await send(
            target_id,
            build_rich_text_reply(part, reply_message_id=quoted_message_id),
        )


def split_reply_text(
    text: str,
    reply_splitter: ReplySplitter,
) -> tuple[str, ...]:
    """拆分回复文本。"""
    parts = tuple(reply_splitter.split(text))
    return parts if parts else (text,)

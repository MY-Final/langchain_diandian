"""OneBot 消息缓存。"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True)
class CachedMessage:
    """缓存的消息概要。"""

    message_id: int
    sender_user_id: int | None
    plain_text: str
    at_targets: tuple[int, ...]


class MessageStore:
    """按 message_id 保存最近使用的消息。"""

    def __init__(self, max_size: int = 500) -> None:
        self._max_size = max_size
        self._messages: OrderedDict[int, CachedMessage] = OrderedDict()

    def put(self, message: CachedMessage) -> None:
        self._messages[message.message_id] = message
        self._messages.move_to_end(message.message_id)

        while len(self._messages) > self._max_size:
            self._messages.popitem(last=False)

    def get(self, message_id: int) -> CachedMessage | None:
        message = self._messages.get(message_id)
        if message is None:
            return None

        self._messages.move_to_end(message_id)
        return message

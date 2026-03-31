"""OneBot 触发规则。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from onebot_gateway.message.parser import ParsedMessageEvent, parse_message_payload
from onebot_gateway.message.store import CachedMessage, MessageStore


class ReplyMessageResolver(Protocol):
    """按消息 ID 解析被引用消息。"""

    async def get_message(self, message_id: int) -> dict | None:
        """返回 OneBot `get_msg` 的 data 字段。"""


@dataclass(frozen=True)
class TriggerDecision:
    """消息触发判断结果。"""

    text: str
    sender_name: str
    sender_user_id: int | None
    chat_type: str
    group_id: int | None
    group_name: str
    is_group_message: bool
    is_private_message: bool
    is_at_self: bool
    mentions_bot_name: bool
    is_reply_message: bool
    is_reply_to_self: bool
    quoted_message_is_at_self: bool
    quoted_message_mentions_bot_name: bool
    should_process: bool
    trigger_reasons: tuple[str, ...]
    reply_message_id: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "sender_name": self.sender_name,
            "sender_user_id": self.sender_user_id,
            "chat_type": self.chat_type,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "is_group_message": self.is_group_message,
            "is_private_message": self.is_private_message,
            "is_at_self": self.is_at_self,
            "mentions_bot_name": self.mentions_bot_name,
            "is_reply_message": self.is_reply_message,
            "is_reply_to_self": self.is_reply_to_self,
            "quoted_message_is_at_self": self.quoted_message_is_at_self,
            "quoted_message_mentions_bot_name": self.quoted_message_mentions_bot_name,
            "should_process": self.should_process,
            "trigger_reasons": list(self.trigger_reasons),
            "reply_message_id": self.reply_message_id,
        }


class TriggerEvaluator:
    """对消息进行 bot 触发判断。"""

    def __init__(
        self,
        bot_name_patterns: tuple[str, ...],
        *,
        message_store: MessageStore | None = None,
        resolver: ReplyMessageResolver | None = None,
    ) -> None:
        self._bot_name_patterns = bot_name_patterns
        self._message_store = message_store or MessageStore()
        self._resolver = resolver

    async def evaluate(self, event: ParsedMessageEvent) -> TriggerDecision:
        """返回当前消息是否应该进入后续处理。"""
        self._cache_event(event)

        mentions_bot_name = event.mentions_bot_name(self._bot_name_patterns)
        quoted_message = await self._resolve_quoted_message(event)
        is_reply_to_self = False
        quoted_message_is_at_self = False
        quoted_message_mentions_bot_name = False

        if quoted_message is not None:
            is_reply_to_self = (
                event.self_id is not None
                and quoted_message.user_id is not None
                and quoted_message.user_id == event.self_id
            )
            quoted_message_is_at_self = quoted_message.is_at_self()
            quoted_message_mentions_bot_name = quoted_message.mentions_bot_name(
                self._bot_name_patterns
            )

        reasons: list[str] = []
        if event.is_private_message():
            reasons.append("private_message")

        if event.is_at_self():
            reasons.append("at_self")

        if mentions_bot_name:
            reasons.append("bot_name")

        if is_reply_to_self:
            reasons.append("reply_to_self")

        if quoted_message_is_at_self:
            reasons.append("reply_to_message_at_self")

        if quoted_message_mentions_bot_name:
            reasons.append("reply_to_message_named_bot")

        should_process = bool(reasons)

        return TriggerDecision(
            text=event.plain_text,
            sender_name=event.sender.display_name,
            sender_user_id=event.user_id,
            chat_type=event.message_type,
            group_id=event.group_id,
            group_name=event.group_name,
            is_group_message=event.is_group_message(),
            is_private_message=event.is_private_message(),
            is_at_self=event.is_at_self(),
            mentions_bot_name=mentions_bot_name,
            is_reply_message=event.is_reply_message(),
            is_reply_to_self=is_reply_to_self,
            quoted_message_is_at_self=quoted_message_is_at_self,
            quoted_message_mentions_bot_name=quoted_message_mentions_bot_name,
            should_process=should_process,
            trigger_reasons=tuple(reasons),
            reply_message_id=event.reply_message_id,
        )

    def _cache_event(self, event: ParsedMessageEvent) -> None:
        if event.message_id is None:
            return

        self._message_store.put(
            CachedMessage(
                message_id=event.message_id,
                sender_user_id=event.user_id,
                plain_text=event.plain_text,
                at_targets=event.at_targets,
            )
        )

    async def _resolve_quoted_message(
        self,
        event: ParsedMessageEvent,
    ) -> ParsedMessageEvent | None:
        if event.reply_message_id is None:
            return None

        cached = self._message_store.get(event.reply_message_id)
        if cached is not None:
            return _build_cached_event(cached, event)

        if self._resolver is None:
            return None

        payload = await self._resolver.get_message(event.reply_message_id)
        if not isinstance(payload, dict):
            return None

        parsed = parse_message_payload(
            payload,
            self_id=event.self_id,
            message_type=event.message_type,
            group_id=event.group_id,
            group_name=event.group_name,
        )
        if parsed.message_id is not None:
            self._cache_event(parsed)
        return parsed


def _build_cached_event(
    cached: CachedMessage,
    source_event: ParsedMessageEvent,
) -> ParsedMessageEvent:
    return ParsedMessageEvent(
        self_id=source_event.self_id,
        user_id=cached.sender_user_id,
        message_id=cached.message_id,
        message_type=source_event.message_type,
        group_id=source_event.group_id,
        group_name=source_event.group_name,
        sender=source_event.sender,
        plain_text=cached.plain_text,
        raw_message=cached.plain_text,
        segments=(),
        at_targets=cached.at_targets,
        reply_message_id=None,
    )

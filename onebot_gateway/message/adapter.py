"""OneBot 与上层智能体之间的适配层。"""

from __future__ import annotations

from dataclasses import dataclass

from onebot_gateway.message.builder import (
    OutgoingMessageSegment,
    reply_segment,
    text_segment,
)
from onebot_gateway.message.parser import ParsedMessageEvent
from onebot_gateway.message.trigger import TriggerDecision


@dataclass(frozen=True)
class AgentInput:
    """传给 LangChain 等上层逻辑的统一输入。"""

    text: str
    sender_id: int | None
    sender_name: str
    chat_type: str
    group_id: int | None
    group_name: str
    message_id: int | None
    reply_message_id: int | None
    should_process: bool
    trigger_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "chat_type": self.chat_type,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "message_id": self.message_id,
            "reply_message_id": self.reply_message_id,
            "should_process": self.should_process,
            "trigger_reasons": list(self.trigger_reasons),
        }


def build_agent_input(
    event: ParsedMessageEvent,
    decision: TriggerDecision,
) -> AgentInput:
    """把 OneBot 事件和触发结果压平成上层输入。"""
    return AgentInput(
        text=event.plain_text,
        sender_id=event.user_id,
        sender_name=event.sender.display_name,
        chat_type=event.message_type,
        group_id=event.group_id,
        group_name=event.group_name,
        message_id=event.message_id,
        reply_message_id=event.reply_message_id,
        should_process=decision.should_process,
        trigger_reasons=decision.trigger_reasons,
    )


def build_text_reply(
    text: str,
    *,
    reply_message_id: int | None = None,
) -> list[OutgoingMessageSegment]:
    """构造常用文本回复消息段。"""
    segments: list[OutgoingMessageSegment] = []
    if reply_message_id is not None:
        segments.append(reply_segment(reply_message_id))
    segments.append(text_segment(text))
    return segments

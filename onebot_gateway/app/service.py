"""OneBot 与 LangChain 的应用服务。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from chat_app.chat import ChatSession
from chat_app.config import AppConfig, load_config
from onebot_gateway.message.adapter import (
    AgentInput,
    build_agent_input,
    build_text_reply,
)
from onebot_gateway.message.parser import ParsedMessageEvent
from onebot_gateway.message.trigger import TriggerDecision


class ChatMessageSender(Protocol):
    """发送 OneBot 消息的协议。"""

    async def send_private_message(self, user_id: int | str, message: object) -> object:
        """发送私聊消息。"""

    async def send_group_message(self, group_id: int | str, message: object) -> object:
        """发送群聊消息。"""


@dataclass
class ChatHandleResult:
    """消息处理结果。"""

    should_reply: bool
    reply_text: str
    agent_input: AgentInput


class ChatService:
    """处理 OneBot 消息并调用 LangChain 回复。"""

    def __init__(self, config: AppConfig, *, reply_with_quote: bool = True) -> None:
        self._config = config
        self._reply_with_quote = reply_with_quote
        self._sessions: dict[tuple[str, int], ChatSession] = {}

    @classmethod
    def from_env(cls, *, reply_with_quote: bool = True) -> ChatService:
        """从环境变量加载 LangChain 配置。"""
        return cls(load_config(), reply_with_quote=reply_with_quote)

    async def handle_event(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        decision: TriggerDecision,
    ) -> ChatHandleResult:
        """处理消息并在需要时回消息。"""
        agent_input = build_agent_input(event, decision)
        if not decision.should_process:
            return ChatHandleResult(
                should_reply=False,
                reply_text="",
                agent_input=agent_input,
            )

        session = self._get_session(event)
        reply_text = session.ask(agent_input.text)

        if event.is_private_message():
            assert event.user_id is not None
            await sender.send_private_message(
                event.user_id,
                build_text_reply(
                    reply_text,
                    reply_message_id=self._get_reply_message_id(event),
                ),
            )
        elif event.is_group_message():
            assert event.group_id is not None
            await sender.send_group_message(
                event.group_id,
                build_text_reply(
                    reply_text,
                    reply_message_id=self._get_reply_message_id(event),
                ),
            )
        else:
            return ChatHandleResult(
                should_reply=False,
                reply_text="",
                agent_input=agent_input,
            )

        return ChatHandleResult(
            should_reply=True,
            reply_text=reply_text,
            agent_input=agent_input,
        )

    def _get_session(self, event: ParsedMessageEvent) -> ChatSession:
        session_key = self._build_session_key(event)
        session = self._sessions.get(session_key)
        if session is None:
            session = ChatSession(self._config)
            self._sessions[session_key] = session
        return session

    def _build_session_key(self, event: ParsedMessageEvent) -> tuple[str, int]:
        if event.is_private_message():
            if event.user_id is None:
                raise ValueError("私聊消息缺少发送人 user_id。")
            return ("private", event.user_id)

        if event.is_group_message():
            if event.group_id is None:
                raise ValueError("群聊消息缺少 group_id。")
            return ("group", event.group_id)

        raise ValueError(f"暂不支持的消息类型：{event.message_type}")

    def _get_reply_message_id(self, event: ParsedMessageEvent) -> int | None:
        if not self._reply_with_quote:
            return None
        return event.message_id

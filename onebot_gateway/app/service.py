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


class PrivateMessageSender(Protocol):
    """发送私聊消息的协议。"""

    async def send_private_message(self, user_id: int | str, message: object) -> object:
        """发送私聊消息。"""


@dataclass
class PrivateChatResult:
    """私聊处理结果。"""

    should_reply: bool
    reply_text: str
    agent_input: AgentInput


class PrivateChatService:
    """处理私聊消息并调用 LangChain 回复。"""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._sessions: dict[int, ChatSession] = {}

    @classmethod
    def from_env(cls) -> PrivateChatService:
        """从环境变量加载 LangChain 配置。"""
        return cls(load_config())

    async def handle_event(
        self,
        sender: PrivateMessageSender,
        event: ParsedMessageEvent,
        decision: TriggerDecision,
    ) -> PrivateChatResult:
        """处理私聊消息并在需要时回消息。"""
        agent_input = build_agent_input(event, decision)
        if not event.is_private_message() or not decision.should_process:
            return PrivateChatResult(
                should_reply=False,
                reply_text="",
                agent_input=agent_input,
            )

        if event.user_id is None:
            raise ValueError("私聊消息缺少发送人 user_id。")

        reply_text = self._get_session(event.user_id).ask(agent_input.text)
        await sender.send_private_message(
            event.user_id,
            build_text_reply(reply_text, reply_message_id=event.message_id),
        )
        return PrivateChatResult(
            should_reply=True,
            reply_text=reply_text,
            agent_input=agent_input,
        )

    def _get_session(self, user_id: int) -> ChatSession:
        session = self._sessions.get(user_id)
        if session is None:
            session = ChatSession(self._config)
            self._sessions[user_id] = session
        return session

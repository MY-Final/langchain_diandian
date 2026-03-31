"""对话模型封装。"""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from chat_app.config import AppConfig
from chat_app.memory.manager import ConversationMemory
from chat_app.memory.summarizer import ConversationSummarizer
from chat_app.memory.types import MemoryPolicy


class ChatSession:
    """最小可用的多轮对话会话。"""

    def __init__(
        self,
        config: AppConfig,
        *,
        session_kind: Literal["private", "group"] = "private",
    ) -> None:
        self._config = config
        self._client = ChatOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            temperature=0,
        )
        policy = self._resolve_memory_policy(session_kind)
        self._memory = ConversationMemory(
            policy,
            enable_summary=config.memory.enable_summary,
            max_summary_chars=config.memory.max_summary_chars,
            max_input_chars=config.memory.max_input_chars,
        )
        self._summarizer = ConversationSummarizer(
            self._client,
            config.memory.max_summary_chars,
        )

    def ask(self, user_input: str) -> str:
        """发送一条用户消息并返回模型回复。"""
        content = user_input.strip()
        if not content:
            raise ValueError("用户输入不能为空。")

        messages = self._memory.build_messages(self._config.system_prompt, content)
        response = self._client.invoke(messages)
        if not isinstance(response, AIMessage):
            raise TypeError("模型返回了无法识别的消息类型。")

        reply = response.text.strip()
        if not reply:
            raise ValueError("模型返回了空响应。")

        self._memory.add_turn(content, response, self._summarizer)
        return reply

    def _resolve_memory_policy(
        self, session_kind: Literal["private", "group"]
    ) -> MemoryPolicy:
        if session_kind == "group":
            policy = self._config.memory.group_policy
        else:
            policy = self._config.memory.private_policy

        return MemoryPolicy(
            max_turns=policy.max_turns,
            summary_trigger_turns=policy.summary_trigger_turns,
            summary_batch_turns=policy.summary_batch_turns,
        )

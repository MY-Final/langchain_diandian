"""会话记忆管理。"""

from __future__ import annotations

from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from chat_app.memory.types import ConversationTurn, MemoryPolicy


SUMMARY_PREFIX = "以下是历史对话摘要，请在后续回复中保持一致并延续上下文："


class TurnSummarizer(Protocol):
    """历史轮次摘要协议。"""

    def summarize(self, existing_summary: str, turns: list[ConversationTurn]) -> str:
        """返回新的摘要。"""


class ConversationMemory:
    """维护滚动摘要和最近对话窗口。"""

    def __init__(
        self,
        policy: MemoryPolicy,
        *,
        enable_summary: bool,
        max_summary_chars: int,
        max_input_chars: int,
    ) -> None:
        self._policy = policy
        self._enable_summary = enable_summary
        self._max_summary_chars = max_summary_chars
        self._max_input_chars = max_input_chars
        self._summary_text = ""
        self._turns: list[ConversationTurn] = []

    def build_messages(self, system_prompt: str, user_input: str) -> list[BaseMessage]:
        """构造当前调用模型所需的消息列表。"""
        turns = self._visible_turns()
        summary_text = self._summary_text
        messages = self._compose_messages(
            system_prompt, summary_text, turns, user_input
        )

        while self._message_chars(messages) > self._max_input_chars and turns:
            turns = turns[1:]
            messages = self._compose_messages(
                system_prompt, summary_text, turns, user_input
            )

        if self._message_chars(messages) > self._max_input_chars and summary_text:
            trimmed_summary = summary_text[: max(0, self._max_input_chars // 4)].strip()
            messages = self._compose_messages(
                system_prompt,
                trimmed_summary,
                turns,
                user_input,
            )

        return messages

    def add_turn(
        self,
        user_input: str,
        response: AIMessage,
        summarizer: TurnSummarizer | None,
    ) -> None:
        """记录当前轮次，并在需要时压缩历史。"""
        reply_text = response.text.strip()
        self._turns.append(
            ConversationTurn(user_text=user_input, assistant_text=reply_text)
        )

        if not self._enable_summary or summarizer is None:
            self._turns = self._turns[-self._policy.max_turns :]
            return

        try:
            self._compress_history(summarizer)
        except Exception:
            self._turns = self._turns[-self._policy.max_turns :]

    @property
    def summary_text(self) -> str:
        """当前滚动摘要。"""
        return self._summary_text

    @property
    def turn_count(self) -> int:
        """当前缓存的原始轮次数量。"""
        return len(self._turns)

    def _compress_history(self, summarizer: TurnSummarizer) -> None:
        while len(self._turns) > self._policy.summary_trigger_turns:
            removable_turns = len(self._turns) - self._policy.max_turns
            batch_size = min(self._policy.summary_batch_turns, removable_turns)
            if batch_size <= 0:
                break

            batch = self._turns[:batch_size]
            self._summary_text = summarizer.summarize(self._summary_text, batch).strip()
            self._summary_text = self._summary_text[: self._max_summary_chars].strip()
            self._turns = self._turns[batch_size:]

    def _visible_turns(self) -> list[ConversationTurn]:
        return self._turns[-self._policy.max_turns :]

    def _compose_messages(
        self,
        system_prompt: str,
        summary_text: str,
        turns: list[ConversationTurn],
        user_input: str,
    ) -> list[BaseMessage]:
        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        if summary_text:
            messages.append(SystemMessage(content=f"{SUMMARY_PREFIX}\n{summary_text}"))

        for turn in turns:
            messages.append(HumanMessage(content=turn.user_text))
            messages.append(AIMessage(content=turn.assistant_text))

        messages.append(HumanMessage(content=user_input))
        return messages

    @staticmethod
    def _message_chars(messages: list[BaseMessage]) -> int:
        total = 0
        for message in messages:
            if isinstance(message.content, str):
                total += len(message.content)
        return total

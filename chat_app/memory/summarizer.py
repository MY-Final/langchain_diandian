"""会话摘要器。"""

from __future__ import annotations

from typing import Protocol

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from chat_app.memory.types import ConversationTurn


class SummaryModel(Protocol):
    """摘要模型协议。"""

    def invoke(self, messages: list[object]) -> object:
        """调用模型。"""


class ConversationSummarizer:
    """负责把旧对话压缩成摘要。"""

    def __init__(self, client: SummaryModel, max_summary_chars: int) -> None:
        self._client = client
        self._max_summary_chars = max_summary_chars

    def summarize(
        self,
        existing_summary: str,
        turns: list[ConversationTurn],
    ) -> str:
        """把旧摘要和若干轮对话合并成新的摘要。"""
        if not turns:
            return existing_summary

        messages = [
            SystemMessage(
                content=(
                    "你负责压缩历史对话摘要。"
                    "请保留当前话题、用户目标、已确认偏好、已完成事项、未完成事项、重要约束。"
                    "输出精炼中文摘要，不要使用 Markdown，不要虚构信息。"
                )
            ),
            HumanMessage(
                content=(
                    f"已有摘要:\n{existing_summary or '无'}\n\n"
                    f"新增对话:\n{_format_turns(turns)}\n\n"
                    f"请将它们合并为不超过 {self._max_summary_chars} 字的摘要。"
                )
            ),
        ]
        response = self._client.invoke(messages)
        if not isinstance(response, AIMessage):
            raise TypeError("摘要模型返回了无法识别的消息类型。")

        summary = response.text.strip()
        if not summary:
            raise ValueError("摘要模型返回了空响应。")
        return summary[: self._max_summary_chars].strip()


def _format_turns(turns: list[ConversationTurn]) -> str:
    parts: list[str] = []
    for index, turn in enumerate(turns, start=1):
        parts.append(
            f"第{index}轮\n用户: {turn.user_text}\n助手: {turn.assistant_text}"
        )
    return "\n\n".join(parts)

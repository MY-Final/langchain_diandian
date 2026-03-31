"""会话记忆测试。"""

from __future__ import annotations

import unittest

from langchain_core.messages import AIMessage

from chat_app.memory.manager import ConversationMemory
from chat_app.memory.types import MemoryPolicy


class FakeSummarizer:
    """记录摘要请求。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[tuple[str, str]]]] = []

    def summarize(self, existing_summary: str, turns: list) -> str:
        self.calls.append(
            (
                existing_summary,
                [(turn.user_text, turn.assistant_text) for turn in turns],
            )
        )
        return "摘要:" + " | ".join(turn.user_text for turn in turns)


class BrokenSummarizer:
    """模拟摘要失败。"""

    def summarize(self, existing_summary: str, turns: list) -> str:
        raise RuntimeError("summary failed")


class ConversationMemoryTests(unittest.TestCase):
    """验证会话记忆压缩策略。"""

    def test_keeps_recent_turns_without_summary(self) -> None:
        memory = ConversationMemory(
            MemoryPolicy(max_turns=2, summary_trigger_turns=3, summary_batch_turns=1),
            enable_summary=False,
            max_summary_chars=500,
            max_input_chars=5000,
        )

        for index in range(3):
            memory.add_turn(f"user-{index}", AIMessage(content=f"ai-{index}"), None)

        messages = memory.build_messages("system", "current")
        contents = [
            message.content for message in messages if isinstance(message.content, str)
        ]
        self.assertEqual(
            contents, ["system", "user-1", "ai-1", "user-2", "ai-2", "current"]
        )

    def test_rolls_old_turns_into_summary(self) -> None:
        memory = ConversationMemory(
            MemoryPolicy(max_turns=2, summary_trigger_turns=3, summary_batch_turns=1),
            enable_summary=True,
            max_summary_chars=500,
            max_input_chars=5000,
        )
        summarizer = FakeSummarizer()

        for index in range(4):
            memory.add_turn(
                f"user-{index}", AIMessage(content=f"ai-{index}"), summarizer
            )

        self.assertEqual(memory.summary_text, "摘要:user-0")
        self.assertEqual(memory.turn_count, 3)
        messages = memory.build_messages("system", "current")
        contents = [
            message.content for message in messages if isinstance(message.content, str)
        ]
        self.assertEqual(
            contents,
            [
                "system",
                "以下是历史对话摘要，请在后续回复中保持一致并延续上下文：\n摘要:user-0",
                "user-2",
                "ai-2",
                "user-3",
                "ai-3",
                "current",
            ],
        )

    def test_falls_back_to_sliding_window_when_summary_fails(self) -> None:
        memory = ConversationMemory(
            MemoryPolicy(max_turns=2, summary_trigger_turns=3, summary_batch_turns=1),
            enable_summary=True,
            max_summary_chars=500,
            max_input_chars=5000,
        )

        for index in range(4):
            memory.add_turn(
                f"user-{index}", AIMessage(content=f"ai-{index}"), BrokenSummarizer()
            )

        messages = memory.build_messages("system", "current")
        contents = [
            message.content for message in messages if isinstance(message.content, str)
        ]
        self.assertEqual(
            contents, ["system", "user-2", "ai-2", "user-3", "ai-3", "current"]
        )


if __name__ == "__main__":
    unittest.main()

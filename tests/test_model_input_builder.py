"""模型输入拼装测试。"""

from __future__ import annotations

import unittest

from onebot_gateway.app.model_input_builder import ModelInputBuilder
from onebot_gateway.config import ReplySplitConfig
from onebot_gateway.message.adapter import AgentInput
from onebot_gateway.message.parser import ParsedMessageEvent, SenderInfo
from onebot_gateway.message.reply_splitter import ReplySplitter


class FailingLongTermStore:
    def query(self, **_: object) -> list[object]:
        raise RuntimeError("db unavailable")


class ModelInputBuilderTests(unittest.TestCase):
    def test_build_skips_long_term_context_when_store_query_fails(self) -> None:
        builder = ModelInputBuilder(
            reply_splitter=ReplySplitter(
                ReplySplitConfig(enabled=True, max_chars=180, marker="[SPLIT]")
            ),
            long_term_store=FailingLongTermStore(),
        )
        event = ParsedMessageEvent(
            self_id=10001,
            time=1775032648,
            user_id=20002,
            message_id=30003,
            message_type="private",
            group_id=None,
            group_name="",
            sender=SenderInfo(user_id=20002, nickname="用户A", card="", role="friend"),
            plain_text="你好",
            raw_message="你好",
            segments=(),
            at_targets=(),
            reply_message_id=None,
        )
        agent_input = AgentInput(
            text="你好",
            time=1775032648,
            sender_id=20002,
            sender_name="用户A",
            chat_type="private",
            group_id=None,
            group_name="",
            message_id=30003,
            reply_message_id=None,
            should_process=True,
            trigger_reasons=("private_message",),
        )

        result = builder.build(event, agent_input, ())

        self.assertIn("消息内容:\n你好", result)
        self.assertNotIn("[长期记忆]", result)


if __name__ == "__main__":
    unittest.main()

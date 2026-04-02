"""模型输入拼装测试。"""

from __future__ import annotations

import unittest

from onebot_gateway.app.model_input_builder import ModelInputBuilder
from onebot_gateway.config import ReplySplitConfig
from onebot_gateway.message.adapter import AgentInput
from onebot_gateway.message.index import MessageRecord
from onebot_gateway.message.parser import ParsedMessageEvent, SenderInfo
from onebot_gateway.message.reply_splitter import ReplySplitter


class FailingLongTermStore:
    def query(self, **_: object) -> list[object]:
        raise RuntimeError("db unavailable")


class FakeMessageIndex:
    def get_recent_chat_messages(
        self, *args: object, **kwargs: object
    ) -> list[MessageRecord]:
        return [
            MessageRecord(
                message_id=1,
                real_id=1,
                message_type="group",
                chat_id=123,
                group_id=123,
                user_id=30001,
                sender_id=30001,
                sender_name="臭鱼",
                self_id=10001,
                is_self=False,
                role_at_receive="member",
                time=1,
                received_at=1,
                content_preview="你是不是有病",
                trace_id="",
                source="onebot_event",
            ),
            MessageRecord(
                message_id=2,
                real_id=2,
                message_type="group",
                chat_id=123,
                group_id=123,
                user_id=10001,
                sender_id=10001,
                sender_name="机器人",
                self_id=10001,
                is_self=True,
                role_at_receive="member",
                time=2,
                received_at=2,
                content_preview="别吵了",
                trace_id="",
                source="onebot_send_result",
            ),
        ]

    def get_recent_user_messages(
        self, *args: object, **kwargs: object
    ) -> list[MessageRecord]:
        return [
            MessageRecord(
                message_id=3,
                real_id=3,
                message_type="group",
                chat_id=123,
                group_id=123,
                user_id=20002,
                sender_id=20002,
                sender_name="Final",
                self_id=10001,
                is_self=False,
                role_at_receive="admin",
                time=3,
                received_at=3,
                content_preview="点点，给我禁言臭鱼",
                trace_id="",
                source="onebot_event",
            )
        ]


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

    def test_build_includes_recent_chat_and_sender_context(self) -> None:
        builder = ModelInputBuilder(
            reply_splitter=ReplySplitter(
                ReplySplitConfig(enabled=True, max_chars=180, marker="[SPLIT]")
            ),
            message_index=FakeMessageIndex(),
        )
        event = ParsedMessageEvent(
            self_id=10001,
            time=1775034223,
            user_id=20002,
            message_id=30003,
            message_type="group",
            group_id=123,
            group_name="测试群",
            sender=SenderInfo(
                user_id=20002, nickname="Final", card="Final", role="admin"
            ),
            plain_text="点点，给我禁言臭鱼，刚才骂我",
            raw_message="点点，给我禁言臭鱼，刚才骂我",
            segments=(),
            at_targets=(),
            reply_message_id=None,
        )
        agent_input = AgentInput(
            text="点点，给我禁言臭鱼，刚才骂我",
            time=1775034223,
            sender_id=20002,
            sender_name="Final",
            chat_type="group",
            group_id=123,
            group_name="测试群",
            message_id=30003,
            reply_message_id=None,
            should_process=True,
            trigger_reasons=("bot_name",),
        )

        result = builder.build(event, agent_input, ())

        self.assertIn("[最近会话上下文]", result)
        self.assertIn("臭鱼: 你是不是有病", result)
        self.assertIn("机器人: 别吵了", result)
        self.assertIn("[发送者近期发言]", result)
        self.assertIn("Final: 点点，给我禁言臭鱼", result)
        self.assertIn("[初步目标解析]", result)
        self.assertIn("最近最可能指向: 臭鱼 (user_id=30001, message_id=1)", result)
        self.assertIn("该候选消息内容: 你是不是有病", result)


if __name__ == "__main__":
    unittest.main()

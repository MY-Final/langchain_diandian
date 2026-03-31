"""OneBot 触发规则测试。"""

from __future__ import annotations

import unittest

from onebot_gateway.message.parser import parse_message_event
from onebot_gateway.message.trigger import TriggerEvaluator


class FakeResolver:
    """用于测试 reply 查询。"""

    def __init__(self, messages: dict[int, dict]) -> None:
        self._messages = messages

    async def get_message(self, message_id: int) -> dict | None:
        return self._messages.get(message_id)


class TriggerEvaluatorTests(unittest.IsolatedAsyncioTestCase):
    """验证消息触发规则。"""

    async def test_reply_to_self_is_detected_via_api_lookup(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30003,
                "message_type": "group",
                "sender": {"nickname": "用户A", "card": "", "role": "member"},
                "message": [
                    {"type": "reply", "data": {"id": "999"}},
                    {"type": "text", "data": {"text": "继续说"}},
                ],
                "raw_message": "[CQ:reply,id=999]继续说",
                "post_type": "message",
                "group_id": 123,
                "group_name": "测试群",
            }
        )
        assert event is not None

        resolver = FakeResolver(
            {
                999: {
                    "message_id": 999,
                    "user_id": 10001,
                    "sender": {
                        "user_id": 10001,
                        "nickname": "bot",
                        "card": "",
                        "role": "member",
                    },
                    "message": [{"type": "text", "data": {"text": "我是 bot"}}],
                    "raw_message": "我是 bot",
                }
            }
        )
        decision = await TriggerEvaluator((r"点点",), resolver=resolver).evaluate(event)

        self.assertTrue(decision.is_reply_to_self)
        self.assertTrue(decision.should_process)
        self.assertIn("reply_to_self", decision.trigger_reasons)

    async def test_reply_to_message_that_mentions_bot_name_is_detected(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30003,
                "message_type": "group",
                "sender": {"nickname": "用户A", "card": "", "role": "member"},
                "message": [
                    {"type": "reply", "data": {"id": "999"}},
                    {"type": "text", "data": {"text": "我补充一下"}},
                ],
                "raw_message": "[CQ:reply,id=999]我补充一下",
                "post_type": "message",
                "group_id": 123,
                "group_name": "测试群",
            }
        )
        assert event is not None

        resolver = FakeResolver(
            {
                999: {
                    "message_id": 999,
                    "user_id": 30003,
                    "sender": {
                        "user_id": 30003,
                        "nickname": "用户B",
                        "card": "",
                        "role": "member",
                    },
                    "message": [{"type": "text", "data": {"text": "点点 你看一下"}}],
                    "raw_message": "点点 你看一下",
                }
            }
        )
        decision = await TriggerEvaluator((r"点点",), resolver=resolver).evaluate(event)

        self.assertTrue(decision.quoted_message_mentions_bot_name)
        self.assertTrue(decision.should_process)
        self.assertIn("reply_to_message_named_bot", decision.trigger_reasons)

    async def test_plain_group_message_without_trigger_is_ignored(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30003,
                "message_type": "group",
                "sender": {"nickname": "用户A", "card": "", "role": "member"},
                "message": [{"type": "text", "data": {"text": "今天天气不错"}}],
                "raw_message": "今天天气不错",
                "post_type": "message",
                "group_id": 123,
                "group_name": "测试群",
            }
        )
        assert event is not None

        decision = await TriggerEvaluator((r"点点",)).evaluate(event)

        self.assertFalse(decision.should_process)
        self.assertEqual(decision.trigger_reasons, ())


if __name__ == "__main__":
    unittest.main()

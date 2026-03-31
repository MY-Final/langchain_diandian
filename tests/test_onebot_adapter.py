"""OneBot adapter 测试。"""

from __future__ import annotations

import unittest

from onebot_gateway.message.adapter import build_agent_input, build_text_reply
from onebot_gateway.message.parser import parse_message_event
from onebot_gateway.message.trigger import TriggerEvaluator


class OneBotAdapterTests(unittest.IsolatedAsyncioTestCase):
    """验证 OneBot 到上层输入的适配。"""

    async def test_build_agent_input_flattens_event_and_decision(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30003,
                "message_type": "group",
                "sender": {"nickname": "用户A", "card": "群名片A", "role": "member"},
                "message": [{"type": "text", "data": {"text": "点点 帮我看看"}}],
                "raw_message": "点点 帮我看看",
                "post_type": "message",
                "group_id": 123,
                "group_name": "测试群",
            }
        )
        assert event is not None

        decision = await TriggerEvaluator((r"点点",)).evaluate(event)
        agent_input = build_agent_input(event, decision)

        self.assertEqual(agent_input.text, "点点 帮我看看")
        self.assertEqual(agent_input.sender_id, 20002)
        self.assertEqual(agent_input.sender_name, "群名片A")
        self.assertEqual(agent_input.chat_type, "group")
        self.assertTrue(agent_input.should_process)
        self.assertEqual(agent_input.trigger_reasons, ("bot_name",))

    def test_build_text_reply_supports_optional_reply_segment(self) -> None:
        self.assertEqual(
            [segment.to_dict() for segment in build_text_reply("你好")],
            [{"type": "text", "data": {"text": "你好"}}],
        )
        self.assertEqual(
            [
                segment.to_dict()
                for segment in build_text_reply("你好", reply_message_id=123)
            ],
            [
                {"type": "reply", "data": {"id": "123"}},
                {"type": "text", "data": {"text": "你好"}},
            ],
        )


if __name__ == "__main__":
    unittest.main()

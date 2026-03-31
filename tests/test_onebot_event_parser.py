"""OneBot 消息事件解析测试。"""

from __future__ import annotations

import unittest

from onebot_gateway.message.parser import parse_message_event


class ParseMessageEventTests(unittest.TestCase):
    """验证消息提取和触发判断。"""

    def test_parses_group_message_summary(self) -> None:
        payload = {
            "self_id": 3430269738,
            "user_id": 3075414416,
            "message_id": 391460650,
            "message_type": "group",
            "sender": {
                "user_id": 3075414416,
                "nickname": "小马哥",
                "card": "孤影（摆烂中）",
                "role": "member",
            },
            "raw_message": "跳[CQ:at,qq=3430269738]",
            "message": [
                {"type": "text", "data": {"text": "跳"}},
                {"type": "at", "data": {"qq": "3430269738"}},
                {"type": "text", "data": {"text": " "}},
            ],
            "post_type": "message",
            "group_id": 515587773,
            "group_name": "我的世界Java交流群",
        }

        event = parse_message_event(payload)

        assert event is not None
        self.assertEqual(event.plain_text, "跳")
        self.assertTrue(event.is_group_message())
        self.assertFalse(event.is_private_message())
        self.assertTrue(event.is_at_self())
        self.assertEqual(event.sender.display_name, "孤影（摆烂中）")
        self.assertEqual(event.group_id, 515587773)
        self.assertTrue(event.should_process(()))

    def test_supports_name_pattern_trigger_in_group(self) -> None:
        payload = {
            "self_id": 3430269738,
            "user_id": 3075414416,
            "message_id": 391460651,
            "message_type": "group",
            "sender": {"nickname": "小马哥", "card": "", "role": "member"},
            "raw_message": "点点 帮我看一下",
            "message": [
                {"type": "text", "data": {"text": "点点 帮我看一下"}},
            ],
            "post_type": "message",
            "group_id": 515587773,
            "group_name": "我的世界Java交流群",
        }

        event = parse_message_event(payload)

        assert event is not None
        self.assertTrue(event.mentions_bot_name((r"\b点点\b", r"点点")))
        self.assertTrue(event.should_process((r"点点",)))

    def test_private_message_is_processed_directly(self) -> None:
        payload = {
            "self_id": 3430269738,
            "user_id": 3075414416,
            "message_id": 391460652,
            "message_type": "private",
            "sender": {"nickname": "小马哥", "card": "", "role": "friend"},
            "raw_message": "你好",
            "message": [{"type": "text", "data": {"text": "你好"}}],
            "post_type": "message",
        }

        event = parse_message_event(payload)

        assert event is not None
        self.assertTrue(event.is_private_message())
        self.assertTrue(event.should_process(()))

    def test_reply_message_is_detected(self) -> None:
        payload = {
            "self_id": 3430269738,
            "user_id": 3075414416,
            "message_id": 391460653,
            "message_type": "group",
            "sender": {"nickname": "小马哥", "card": "", "role": "member"},
            "raw_message": "[CQ:reply,id=391460600]你好",
            "message": [
                {"type": "reply", "data": {"id": "391460600"}},
                {"type": "text", "data": {"text": "你好"}},
            ],
            "post_type": "message",
            "group_id": 515587773,
        }

        event = parse_message_event(payload)

        assert event is not None
        self.assertEqual(event.reply_message_id, 391460600)
        self.assertTrue(event.is_reply_message())
        self.assertTrue(event.should_process(()))

    def test_returns_none_for_non_message_event(self) -> None:
        self.assertIsNone(parse_message_event({"post_type": "meta_event"}))


if __name__ == "__main__":
    unittest.main()

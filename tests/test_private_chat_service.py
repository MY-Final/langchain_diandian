"""OneBot LangChain 服务测试。"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from chat_app.config import AppConfig
from onebot_gateway.app.service import ChatService
from onebot_gateway.message.parser import parse_message_event
from onebot_gateway.message.trigger import TriggerEvaluator


class FakeSender:
    """记录消息发送调用。"""

    def __init__(self) -> None:
        self.private_calls: list[tuple[int | str, object]] = []
        self.group_calls: list[tuple[int | str, object]] = []

    async def send_private_message(self, user_id: int | str, message: object) -> object:
        self.private_calls.append((user_id, message))
        return None

    async def send_group_message(self, group_id: int | str, message: object) -> object:
        self.group_calls.append((group_id, message))
        return None


class FakeChatSession:
    """用于替代真实 LangChain 会话。"""

    def __init__(self, _config: AppConfig) -> None:
        self.questions: list[str] = []

    def ask(self, user_input: str) -> str:
        self.questions.append(user_input)
        return f"回声:{user_input}"


class ChatServiceTests(unittest.IsolatedAsyncioTestCase):
    """验证 OneBot 消息到回复的闭环。"""

    async def test_replies_to_private_message(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30003,
                "message_type": "private",
                "sender": {"nickname": "用户A", "card": "", "role": "friend"},
                "message": [{"type": "text", "data": {"text": "你好"}}],
                "raw_message": "你好",
                "post_type": "message",
            }
        )
        assert event is not None
        decision = await TriggerEvaluator((r"点点",)).evaluate(event)
        sender = FakeSender()
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        with patch("onebot_gateway.app.service.ChatSession", FakeChatSession):
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)

        self.assertTrue(result.should_reply)
        self.assertEqual(result.reply_text, "回声:你好")
        self.assertEqual(len(sender.private_calls), 1)
        user_id, message = sender.private_calls[0]
        self.assertEqual(user_id, 20002)
        self.assertEqual(
            [segment.to_dict() for segment in message],
            [
                {"type": "reply", "data": {"id": "30003"}},
                {"type": "text", "data": {"text": "回声:你好"}},
            ],
        )

    async def test_ignores_non_private_message(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30003,
                "message_type": "group",
                "sender": {"nickname": "用户A", "card": "", "role": "member"},
                "message": [{"type": "text", "data": {"text": "你好"}}],
                "raw_message": "你好",
                "post_type": "message",
                "group_id": 123,
            }
        )
        assert event is not None
        decision = await TriggerEvaluator((r"点点",)).evaluate(event)
        sender = FakeSender()
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        with patch("onebot_gateway.app.service.ChatSession", FakeChatSession):
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)

        self.assertFalse(result.should_reply)
        self.assertEqual(sender.private_calls, [])
        self.assertEqual(sender.group_calls, [])

    async def test_replies_to_group_message_when_at_self(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30003,
                "message_type": "group",
                "sender": {"nickname": "用户A", "card": "群名片A", "role": "member"},
                "message": [
                    {"type": "at", "data": {"qq": "10001"}},
                    {"type": "text", "data": {"text": " 帮我看看"}},
                ],
                "raw_message": "[CQ:at,qq=10001] 帮我看看",
                "post_type": "message",
                "group_id": 123,
                "group_name": "测试群",
            }
        )
        assert event is not None
        decision = await TriggerEvaluator((r"点点",)).evaluate(event)
        sender = FakeSender()
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        with patch("onebot_gateway.app.service.ChatSession", FakeChatSession):
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)

        self.assertTrue(result.should_reply)
        self.assertEqual(result.reply_text, "回声:帮我看看")
        self.assertEqual(sender.private_calls, [])
        self.assertEqual(len(sender.group_calls), 1)
        group_id, message = sender.group_calls[0]
        self.assertEqual(group_id, 123)
        self.assertEqual(
            [segment.to_dict() for segment in message],
            [
                {"type": "reply", "data": {"id": "30003"}},
                {"type": "text", "data": {"text": "回声:帮我看看"}},
            ],
        )

    async def test_replies_to_group_message_when_named_bot(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30004,
                "message_type": "group",
                "sender": {"nickname": "用户A", "card": "群名片A", "role": "member"},
                "message": [{"type": "text", "data": {"text": "点点 你好"}}],
                "raw_message": "点点 你好",
                "post_type": "message",
                "group_id": 123,
                "group_name": "测试群",
            }
        )
        assert event is not None
        decision = await TriggerEvaluator((r"点点",)).evaluate(event)
        sender = FakeSender()
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        with patch("onebot_gateway.app.service.ChatSession", FakeChatSession):
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)

        self.assertTrue(result.should_reply)
        self.assertEqual(result.reply_text, "回声:点点 你好")
        self.assertEqual(len(sender.group_calls), 1)

    async def test_ignores_group_message_without_trigger(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30005,
                "message_type": "group",
                "sender": {"nickname": "用户A", "card": "群名片A", "role": "member"},
                "message": [{"type": "text", "data": {"text": "今天天气不错"}}],
                "raw_message": "今天天气不错",
                "post_type": "message",
                "group_id": 123,
                "group_name": "测试群",
            }
        )
        assert event is not None
        decision = await TriggerEvaluator((r"点点",)).evaluate(event)
        sender = FakeSender()
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        with patch("onebot_gateway.app.service.ChatSession", FakeChatSession):
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)

        self.assertFalse(result.should_reply)
        self.assertEqual(sender.group_calls, [])

    async def test_can_disable_quote_reply_for_private_message(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30006,
                "message_type": "private",
                "sender": {"nickname": "用户A", "card": "", "role": "friend"},
                "message": [{"type": "text", "data": {"text": "你好"}}],
                "raw_message": "你好",
                "post_type": "message",
            }
        )
        assert event is not None
        decision = await TriggerEvaluator((r"点点",)).evaluate(event)
        sender = FakeSender()
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        with patch("onebot_gateway.app.service.ChatSession", FakeChatSession):
            service = ChatService(config, reply_with_quote=False)
            result = await service.handle_event(sender, event, decision)

        self.assertTrue(result.should_reply)
        self.assertEqual(
            [segment.to_dict() for segment in sender.private_calls[0][1]],
            [{"type": "text", "data": {"text": "回声:你好"}}],
        )

    async def test_can_disable_quote_reply_for_group_message(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30007,
                "message_type": "group",
                "sender": {"nickname": "用户A", "card": "群名片A", "role": "member"},
                "message": [{"type": "text", "data": {"text": "点点 你好"}}],
                "raw_message": "点点 你好",
                "post_type": "message",
                "group_id": 123,
                "group_name": "测试群",
            }
        )
        assert event is not None
        decision = await TriggerEvaluator((r"点点",)).evaluate(event)
        sender = FakeSender()
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        with patch("onebot_gateway.app.service.ChatSession", FakeChatSession):
            service = ChatService(config, reply_with_quote=False)
            result = await service.handle_event(sender, event, decision)

        self.assertTrue(result.should_reply)
        self.assertEqual(
            [segment.to_dict() for segment in sender.group_calls[0][1]],
            [{"type": "text", "data": {"text": "回声:点点 你好"}}],
        )


if __name__ == "__main__":
    unittest.main()

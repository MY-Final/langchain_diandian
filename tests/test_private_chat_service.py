"""私聊 LangChain 服务测试。"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from chat_app.config import AppConfig
from onebot_gateway.app.service import PrivateChatService
from onebot_gateway.message.parser import parse_message_event
from onebot_gateway.message.trigger import TriggerEvaluator


class FakeSender:
    """记录私聊发送调用。"""

    def __init__(self) -> None:
        self.calls: list[tuple[int | str, object]] = []

    async def send_private_message(self, user_id: int | str, message: object) -> object:
        self.calls.append((user_id, message))
        return None


class FakeChatSession:
    """用于替代真实 LangChain 会话。"""

    def __init__(self, _config: AppConfig) -> None:
        self.questions: list[str] = []

    def ask(self, user_input: str) -> str:
        self.questions.append(user_input)
        return f"回声:{user_input}"


class PrivateChatServiceTests(unittest.IsolatedAsyncioTestCase):
    """验证私聊消息到回复的闭环。"""

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
            service = PrivateChatService(config)
            result = await service.handle_event(sender, event, decision)

        self.assertTrue(result.should_reply)
        self.assertEqual(result.reply_text, "回声:你好")
        self.assertEqual(len(sender.calls), 1)
        user_id, message = sender.calls[0]
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
            service = PrivateChatService(config)
            result = await service.handle_event(sender, event, decision)

        self.assertFalse(result.should_reply)
        self.assertEqual(sender.calls, [])


if __name__ == "__main__":
    unittest.main()

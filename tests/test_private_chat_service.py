"""OneBot LangChain 服务测试。"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from chat_app.config import AppConfig
from onebot_gateway.app.service import ChatService
from onebot_gateway.config import ReplySplitConfig
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


class SpyMessageIndex:
    """记录消息索引调用。"""

    def __init__(self) -> None:
        self.received_calls: list[dict[str, object]] = []

    def bind_runtime(
        self, *, onebot_client: object | None, self_id: int | None
    ) -> SpyMessageIndex:
        return self

    def record_received_message(self, **kwargs: object) -> None:
        self.received_calls.append(dict(kwargs))

    def record_sent_message(self, **kwargs: object) -> None:
        return None


class FakeChatSession:
    """用于替代真实 LangChain 会话。"""

    last_question = ""
    last_session_kind = ""
    last_runtime_tool_names: tuple[str, ...] = ()
    last_runtime_rules: tuple[str, ...] = ()

    def __init__(
        self,
        _config: AppConfig,
        *,
        session_kind: str = "private",
        session_scope_id: int = 0,
    ) -> None:
        self.questions: list[str] = []
        self.session_kind = session_kind
        self.session_scope_id = session_scope_id
        FakeChatSession.last_session_kind = session_kind

    def ask(
        self,
        user_input: str,
        *,
        runtime_tools: object | None = None,
        runtime_rules: object = (),
    ) -> str:
        self.questions.append(user_input)
        FakeChatSession.last_question = user_input
        FakeChatSession.last_runtime_tool_names = tuple(
            getattr(tool, "name", "") for tool in (runtime_tools or ())
        )
        FakeChatSession.last_runtime_rules = tuple(str(item) for item in runtime_rules)
        return f"回声:{_extract_message_body(user_input)}"


class FakeSplitChatSession(FakeChatSession):
    """返回可显式分段的回复。"""

    def ask(
        self,
        user_input: str,
        *,
        runtime_tools: object | None = None,
        runtime_rules: object = (),
    ) -> str:
        self.questions.append(user_input)
        FakeChatSession.last_question = user_input
        FakeChatSession.last_runtime_tool_names = tuple(
            getattr(tool, "name", "") for tool in (runtime_tools or ())
        )
        FakeChatSession.last_runtime_rules = tuple(str(item) for item in runtime_rules)
        return "第一段[SPLIT]第二段"


class FakeAtChatSession(FakeChatSession):
    """返回带艾特标签的回复。"""

    def ask(
        self,
        user_input: str,
        *,
        runtime_tools: object | None = None,
        runtime_rules: object = (),
    ) -> str:
        self.questions.append(user_input)
        FakeChatSession.last_question = user_input
        FakeChatSession.last_runtime_tool_names = tuple(
            getattr(tool, "name", "") for tool in (runtime_tools or ())
        )
        FakeChatSession.last_runtime_rules = tuple(str(item) for item in runtime_rules)
        return '你好 <at qq="123456" /> 请看这里'


def _extract_message_body(user_input: str) -> str:
    marker = "消息内容:\n"
    if marker not in user_input:
        return user_input
    return user_input.split(marker, 1)[1].strip()


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
        self.assertNotIn("mute_group_member", FakeChatSession.last_runtime_tool_names)
        self.assertNotIn("set_group_admin", FakeChatSession.last_runtime_tool_names)

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
        self.assertIn("mute_group_member", FakeChatSession.last_runtime_tool_names)
        self.assertIn("set_group_admin", FakeChatSession.last_runtime_tool_names)
        self.assertTrue(FakeChatSession.last_runtime_rules)

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

    async def test_builds_group_prompt_with_sender_and_time(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "time": 1774928987,
                "user_id": 20002,
                "message_id": 30008,
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
        sender = FakeSender()
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        with patch("onebot_gateway.app.service.ChatSession", FakeChatSession):
            service = ChatService(config)
            await service.handle_event(sender, event, decision)

        self.assertIn("时间: ", FakeChatSession.last_question)
        self.assertIn("发送者昵称: 用户A", FakeChatSession.last_question)
        self.assertIn("群名片: 群名片A", FakeChatSession.last_question)
        self.assertIn("消息内容:\n点点 帮我看看", FakeChatSession.last_question)
        self.assertEqual(FakeChatSession.last_session_kind, "group")

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

    async def test_records_group_message_even_when_not_triggered(self) -> None:
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
        index = SpyMessageIndex()
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        with patch("onebot_gateway.app.service.ChatSession", FakeChatSession):
            service = ChatService(config, message_index=index)  # type: ignore[arg-type]
            result = await service.handle_event(sender, event, decision)

        self.assertFalse(result.should_reply)
        self.assertEqual(len(index.received_calls), 1)
        self.assertEqual(index.received_calls[0]["message_id"], 30005)
        self.assertEqual(index.received_calls[0]["message_type"], "group")
        self.assertEqual(index.received_calls[0]["chat_id"], 123)

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

    async def test_sends_multi_part_reply_when_model_uses_split_marker(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30008,
                "message_type": "private",
                "sender": {"nickname": "用户A", "card": "", "role": "friend"},
                "message": [{"type": "text", "data": {"text": "长一点回答"}}],
                "raw_message": "长一点回答",
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

        with patch("onebot_gateway.app.service.ChatSession", FakeSplitChatSession):
            service = ChatService(
                config,
                reply_split_config=ReplySplitConfig(
                    enabled=True,
                    max_chars=50,
                    marker="[SPLIT]",
                ),
            )
            result = await service.handle_event(sender, event, decision)

        self.assertEqual(result.reply_parts, ("第一段", "第二段"))
        self.assertEqual(len(sender.private_calls), 2)
        self.assertEqual(
            [segment.to_dict() for segment in sender.private_calls[0][1]],
            [
                {"type": "reply", "data": {"id": "30008"}},
                {"type": "text", "data": {"text": "第一段"}},
            ],
        )
        self.assertEqual(
            [segment.to_dict() for segment in sender.private_calls[1][1]],
            [{"type": "text", "data": {"text": "第二段"}}],
        )

    async def test_sends_at_segment_when_model_requests_mention(self) -> None:
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30009,
                "message_type": "group",
                "sender": {"nickname": "用户A", "card": "群名片A", "role": "member"},
                "message": [
                    {"type": "text", "data": {"text": "点点 帮我艾特一下这个人 "}},
                    {"type": "at", "data": {"qq": "123456"}},
                ],
                "raw_message": "点点 帮我艾特一下这个人[CQ:at,qq=123456]",
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

        with patch("onebot_gateway.app.service.ChatSession", FakeAtChatSession):
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)

        self.assertTrue(result.should_reply)
        self.assertEqual(len(sender.group_calls), 1)
        self.assertEqual(
            [segment.to_dict() for segment in sender.group_calls[0][1]],
            [
                {"type": "reply", "data": {"id": "30009"}},
                {"type": "text", "data": {"text": "你好 "}},
                {"type": "at", "data": {"qq": "123456"}},
                {"type": "text", "data": {"text": " 请看这里"}},
            ],
        )


if __name__ == "__main__":
    unittest.main()

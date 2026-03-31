"""群禁言动作测试。"""

from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, MagicMock

from chat_app.actions.moderation import mute_group_member
from chat_app.actions.types import (
    DEFAULT_MUTE_DURATION,
    MAX_MUTE_DURATION,
    PendingMuteAction,
)
from chat_app.config import AppConfig
from chat_app.chat import ChatSession
from onebot_gateway.app.service import ChatService, _can_operate
from onebot_gateway.config import ReplySplitConfig
from onebot_gateway.message.parser import parse_message_event
from onebot_gateway.message.trigger import TriggerEvaluator


class PendingMuteActionTests(unittest.TestCase):
    """PendingMuteAction 单元测试。"""

    def test_to_dict(self) -> None:
        action = PendingMuteAction(group_id=123, user_id=456, duration=600)
        self.assertEqual(
            action.to_dict(),
            {
                "action": "mute_group_member",
                "group_id": 123,
                "user_id": 456,
                "duration": 600,
            },
        )

    def test_defaults(self) -> None:
        self.assertEqual(DEFAULT_MUTE_DURATION, 600)
        self.assertEqual(MAX_MUTE_DURATION, 2592000)


class MuteGroupMemberToolTests(unittest.TestCase):
    """mute_group_member 工具输出测试。"""

    def test_returns_valid_json(self) -> None:
        result = mute_group_member.invoke(
            {"user_id": 100, "group_id": 200, "duration": 600}
        )
        data = json.loads(result)
        self.assertEqual(data["action"], "mute_group_member")
        self.assertEqual(data["user_id"], 100)
        self.assertEqual(data["group_id"], 200)
        self.assertEqual(data["duration"], 600)

    def test_default_duration(self) -> None:
        result = mute_group_member.invoke({"user_id": 100, "group_id": 200})
        data = json.loads(result)
        self.assertEqual(data["duration"], DEFAULT_MUTE_DURATION)

    def test_clamps_negative_duration(self) -> None:
        result = mute_group_member.invoke(
            {"user_id": 100, "group_id": 200, "duration": -10}
        )
        data = json.loads(result)
        self.assertEqual(data["duration"], 0)

    def test_clamps_over_max_duration(self) -> None:
        result = mute_group_member.invoke(
            {"user_id": 100, "group_id": 200, "duration": 99999999}
        )
        data = json.loads(result)
        self.assertEqual(data["duration"], MAX_MUTE_DURATION)


class CanOperateTests(unittest.TestCase):
    """角色权限判断测试。"""

    def test_owner_can_mute_admin(self) -> None:
        self.assertTrue(_can_operate("owner", "admin"))

    def test_owner_can_mute_member(self) -> None:
        self.assertTrue(_can_operate("owner", "member"))

    def test_admin_can_mute_member(self) -> None:
        self.assertTrue(_can_operate("admin", "member"))

    def test_admin_cannot_mute_admin(self) -> None:
        self.assertFalse(_can_operate("admin", "admin"))

    def test_admin_cannot_mute_owner(self) -> None:
        self.assertFalse(_can_operate("admin", "owner"))

    def test_member_cannot_mute_member(self) -> None:
        self.assertFalse(_can_operate("member", "member"))

    def test_member_cannot_mute_admin(self) -> None:
        self.assertFalse(_can_operate("member", "admin"))

    def test_member_cannot_mute_owner(self) -> None:
        self.assertFalse(_can_operate("member", "owner"))

    def test_unknown_role_cannot_operate(self) -> None:
        self.assertFalse(_can_operate("unknown", "member"))


class FakeActionSender:
    """带群管方法的 FakeSender。"""

    def __init__(self) -> None:
        self.private_calls: list[tuple[int | str, object]] = []
        self.group_calls: list[tuple[int | str, object]] = []
        self.member_info: dict[int, dict] = {}
        self.ban_calls: list[tuple[int | str, int | str, int]] = []

    async def send_private_message(self, user_id: int | str, message: object) -> object:
        self.private_calls.append((user_id, message))
        return None

    async def send_group_message(self, group_id: int | str, message: object) -> object:
        self.group_calls.append((group_id, message))
        return None

    async def get_group_member_info(
        self, group_id: int | str, user_id: int | str, *, no_cache: bool = True
    ) -> dict | None:
        return self.member_info.get(int(user_id))

    async def set_group_ban(
        self, group_id: int | str, user_id: int | str, duration: int = 0
    ) -> dict:
        self.ban_calls.append((group_id, user_id, duration))
        return {"status": "ok", "retcode": 0}


class FakeMuteChatSession:
    """返回带禁言工具输出的会话。"""

    def __init__(self, _config: AppConfig, *, session_kind: str = "private") -> None:
        self._pending: tuple = ()

    def ask(self, user_input: str) -> str:
        return "已经禁言了"

    def get_last_tool_traces(self) -> tuple:
        return ()

    def get_pending_actions(self) -> tuple:
        return self._pending


class FakeMuteChatSessionWithAction(FakeMuteChatSession):
    """返回带有待执行禁言动作的会话。"""

    def ask(self, user_input: str) -> str:
        from chat_app.actions.types import PendingMuteAction

        self._pending = (PendingMuteAction(group_id=100, user_id=200, duration=600),)
        return "已经禁言了该用户"


class ActionExecutionTests(unittest.IsolatedAsyncioTestCase):
    """服务层动作执行测试。"""

    async def test_execute_mute_success_as_owner(self) -> None:
        sender = FakeActionSender()
        sender.member_info[10001] = {"role": "owner"}
        sender.member_info[200] = {"role": "member"}

        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30003,
                "message_type": "group",
                "sender": {"nickname": "用户A", "card": "群名片A", "role": "member"},
                "message": [
                    {"type": "at", "data": {"qq": "10001"}},
                    {"type": "text", "data": {"text": "禁言他"}},
                ],
                "raw_message": "禁言他",
                "post_type": "message",
                "group_id": 100,
                "group_name": "测试群",
            }
        )
        assert event is not None
        decision = await TriggerEvaluator(("点点",)).evaluate(event)
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        import onebot_gateway.app.service as svc

        original = svc.ChatSession
        svc.ChatSession = FakeMuteChatSessionWithAction  # type: ignore[assignment]
        try:
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)
        finally:
            svc.ChatSession = original  # type: ignore[assignment]

        self.assertEqual(len(sender.ban_calls), 1)
        group_id, user_id, duration = sender.ban_calls[0]
        self.assertEqual(group_id, 100)
        self.assertEqual(user_id, 200)
        self.assertEqual(duration, 600)
        self.assertEqual(len(result.action_results), 1)
        self.assertTrue(result.action_results[0].success)

    async def test_execute_mute_rejected_for_member(self) -> None:
        sender = FakeActionSender()
        sender.member_info[10001] = {"role": "member"}
        sender.member_info[200] = {"role": "member"}

        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30003,
                "message_type": "group",
                "sender": {"nickname": "用户A", "card": "群名片A", "role": "member"},
                "message": [
                    {"type": "at", "data": {"qq": "10001"}},
                    {"type": "text", "data": {"text": "禁言他"}},
                ],
                "raw_message": "禁言他",
                "post_type": "message",
                "group_id": 100,
                "group_name": "测试群",
            }
        )
        assert event is not None
        decision = await TriggerEvaluator(("点点",)).evaluate(event)
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        import onebot_gateway.app.service as svc

        original = svc.ChatSession
        svc.ChatSession = FakeMuteChatSessionWithAction  # type: ignore[assignment]
        try:
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)
        finally:
            svc.ChatSession = original  # type: ignore[assignment]

        self.assertEqual(len(sender.ban_calls), 0)
        self.assertEqual(len(result.action_results), 1)
        self.assertFalse(result.action_results[0].success)
        self.assertIn("权限不足", result.action_results[0].message)

    async def test_no_actions_when_session_has_none(self) -> None:
        sender = FakeActionSender()
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
        decision = await TriggerEvaluator(("点点",)).evaluate(event)
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        import onebot_gateway.app.service as svc

        original = svc.ChatSession
        svc.ChatSession = FakeMuteChatSession  # type: ignore[assignment]
        try:
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)
        finally:
            svc.ChatSession = original  # type: ignore[assignment]

        self.assertEqual(result.action_results, ())
        self.assertEqual(len(sender.ban_calls), 0)


if __name__ == "__main__":
    unittest.main()

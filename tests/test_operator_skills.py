"""受信操作员技能测试。"""

from __future__ import annotations

import json
import unittest

from chat_app.config import AppConfig
from chat_app.skills.account_profile import PendingSetQQProfileAction, set_qq_profile
from chat_app.skills.account_status import (
    PendingSetDIYOnlineStatusAction,
    PendingSetOnlineStatusAction,
    set_diy_online_status,
    set_online_status,
)
from chat_app.skills.friend_management import PendingSendLikeAction, send_like
from chat_app.skills.friend_request_management import (
    PendingSetFriendAddRequestAction,
    set_friend_add_request,
)
from chat_app.skills.message_state import (
    PendingMarkConversationReadAction,
    mark_conversation_read,
)
from onebot_gateway.app.service import ChatService
from onebot_gateway.message.parser import parse_message_event
from onebot_gateway.message.trigger import TriggerEvaluator


class OperatorSender:
    """受信操作员技能用 sender。"""

    def __init__(self) -> None:
        self.private_calls: list[tuple[int | str, object]] = []
        self.group_calls: list[tuple[int | str, object]] = []
        self.like_calls: list[tuple[int | str, int]] = []
        self.profile_calls: list[tuple[str, str, str]] = []
        self.online_status_calls: list[tuple[int, int, int]] = []
        self.diy_online_status_calls: list[tuple[int, int, str]] = []
        self.friend_request_calls: list[tuple[str, bool, str]] = []
        self.mark_private_read_calls: list[int | str] = []
        self.mark_group_read_calls: list[int | str] = []
        self.mark_all_read_calls = 0

    async def send_private_message(self, user_id: int | str, message: object) -> object:
        self.private_calls.append((user_id, message))
        return None

    async def send_group_message(self, group_id: int | str, message: object) -> object:
        self.group_calls.append((group_id, message))
        return None

    async def send_like(self, user_id: int | str, times: int = 1) -> dict:
        self.like_calls.append((user_id, times))
        return {"status": "ok", "retcode": 0}

    async def set_qq_profile(
        self,
        *,
        nickname: str,
        personal_note: str = "",
        sex: str = "unknown",
    ) -> dict:
        self.profile_calls.append((nickname, personal_note, sex))
        return {"status": "ok", "retcode": 0}

    async def set_online_status(
        self, status: int, ext_status: int = 0, battery_status: int = 0
    ) -> dict:
        self.online_status_calls.append((status, ext_status, battery_status))
        return {"status": "ok", "retcode": 0}

    async def set_diy_online_status(
        self, face_id: int, face_type: int = 0, wording: str = ""
    ) -> dict:
        self.diy_online_status_calls.append((face_id, face_type, wording))
        return {"status": "ok", "retcode": 0}

    async def set_friend_add_request(
        self, flag: str, approve: bool = True, remark: str = ""
    ) -> dict:
        self.friend_request_calls.append((flag, approve, remark))
        return {"status": "ok", "retcode": 0}

    async def mark_private_msg_as_read(self, user_id: int | str) -> dict:
        self.mark_private_read_calls.append(user_id)
        return {"status": "ok", "retcode": 0}

    async def mark_group_msg_as_read(self, group_id: int | str) -> dict:
        self.mark_group_read_calls.append(group_id)
        return {"status": "ok", "retcode": 0}

    async def mark_all_as_read(self) -> dict:
        self.mark_all_read_calls += 1
        return {"status": "ok", "retcode": 0}


class FakeOperatorSession:
    """返回待执行点赞动作。"""

    def __init__(
        self,
        _config: AppConfig,
        *,
        session_kind: str = "private",
        session_scope_id: int = 0,
    ) -> None:
        self._pending: tuple = ()

    def ask(
        self,
        user_input: str,
        *,
        runtime_tools: object | None = None,
        runtime_rules: object = (),
    ) -> str:
        self._pending = (PendingSendLikeAction(user_id=10001, times=3),)
        return "已经点赞"

    def get_last_tool_traces(self) -> tuple:
        return ()

    def get_pending_actions(self) -> tuple:
        return self._pending


class FakeProfileSession(FakeOperatorSession):
    """返回待执行资料设置动作。"""

    def ask(
        self,
        user_input: str,
        *,
        runtime_tools: object | None = None,
        runtime_rules: object = (),
    ) -> str:
        self._pending = (
            PendingSetQQProfileAction(
                nickname="点点", personal_note="你好呀", sex="female"
            ),
        )
        return "已经修改资料"


class FakeOnlineStatusSession(FakeOperatorSession):
    def ask(
        self,
        user_input: str,
        *,
        runtime_tools: object | None = None,
        runtime_rules: object = (),
    ) -> str:
        self._pending = (
            PendingSetOnlineStatusAction(status=10, ext_status=1028, battery_status=0),
        )
        return "已经修改在线状态"


class FakeDIYOnlineStatusSession(FakeOperatorSession):
    def ask(
        self,
        user_input: str,
        *,
        runtime_tools: object | None = None,
        runtime_rules: object = (),
    ) -> str:
        self._pending = (
            PendingSetDIYOnlineStatusAction(face_id=123, face_type=1, wording="摸鱼中"),
        )
        return "已经修改自定义在线状态"


class FakeFriendRequestSession(FakeOperatorSession):
    def ask(
        self,
        user_input: str,
        *,
        runtime_tools: object | None = None,
        runtime_rules: object = (),
    ) -> str:
        self._pending = (
            PendingSetFriendAddRequestAction(
                flag="req-123", approve=True, remark="新朋友"
            ),
        )
        return "已经处理好友请求"


class FakeMarkReadSession(FakeOperatorSession):
    def ask(
        self,
        user_input: str,
        *,
        runtime_tools: object | None = None,
        runtime_rules: object = (),
    ) -> str:
        self._pending = (
            PendingMarkConversationReadAction(scope="current", target_id=None),
        )
        return "已经标记已读"


class OperatorSkillToolTests(unittest.TestCase):
    """operator skill 工具输出测试。"""

    def test_send_like_returns_valid_json(self) -> None:
        data = json.loads(send_like.invoke({"user_id": 12345, "times": 3}))
        self.assertEqual(data["action"], "send_like")
        self.assertEqual(data["user_id"], 12345)
        self.assertEqual(data["times"], 3)

    def test_set_qq_profile_returns_valid_json(self) -> None:
        data = json.loads(
            set_qq_profile.invoke(
                {"nickname": "点点", "personal_note": "你好呀", "sex": "female"}
            )
        )
        self.assertEqual(data["action"], "set_qq_profile")
        self.assertEqual(data["nickname"], "点点")
        self.assertEqual(data["sex"], "female")

    def test_set_online_status_returns_valid_json(self) -> None:
        data = json.loads(
            set_online_status.invoke(
                {"status": 10, "ext_status": 1028, "battery_status": 0}
            )
        )
        self.assertEqual(data["action"], "set_online_status")
        self.assertEqual(data["status"], 10)
        self.assertEqual(data["ext_status"], 1028)

    def test_set_diy_online_status_returns_valid_json(self) -> None:
        data = json.loads(
            set_diy_online_status.invoke(
                {"face_id": 123, "face_type": 1, "wording": "摸鱼中"}
            )
        )
        self.assertEqual(data["action"], "set_diy_online_status")
        self.assertEqual(data["face_id"], 123)
        self.assertEqual(data["wording"], "摸鱼中")

    def test_set_friend_add_request_returns_valid_json(self) -> None:
        data = json.loads(
            set_friend_add_request.invoke(
                {"flag": "req-123", "approve": True, "remark": "新朋友"}
            )
        )
        self.assertEqual(data["action"], "set_friend_add_request")
        self.assertEqual(data["flag"], "req-123")
        self.assertTrue(data["approve"])

    def test_mark_conversation_read_returns_valid_json(self) -> None:
        data = json.loads(
            mark_conversation_read.invoke({"scope": "private", "target_id": 12345})
        )
        self.assertEqual(data["action"], "mark_conversation_read")
        self.assertEqual(data["scope"], "private")
        self.assertEqual(data["target_id"], 12345)


class OperatorSkillExecutionTests(unittest.IsolatedAsyncioTestCase):
    """operator skill 服务执行测试。"""

    async def test_trusted_operator_can_send_like(self) -> None:
        sender = OperatorSender()
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30003,
                "message_type": "private",
                "sender": {"nickname": "主人", "card": "", "role": "friend"},
                "message": [{"type": "text", "data": {"text": "帮我点赞"}}],
                "raw_message": "帮我点赞",
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
            operator_user_ids=(20002,),
        )

        import onebot_gateway.app.service as svc

        original = svc.ChatSession
        svc.ChatSession = FakeOperatorSession  # type: ignore[assignment]
        try:
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)
        finally:
            svc.ChatSession = original  # type: ignore[assignment]

        self.assertEqual(sender.like_calls, [(10001, 3)])
        self.assertTrue(result.action_results[0].success)

    async def test_untrusted_operator_cannot_send_like(self) -> None:
        sender = OperatorSender()
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20003,
                "message_id": 30003,
                "message_type": "private",
                "sender": {"nickname": "路人", "card": "", "role": "friend"},
                "message": [{"type": "text", "data": {"text": "帮我点赞"}}],
                "raw_message": "帮我点赞",
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
            operator_user_ids=(20002,),
        )

        import onebot_gateway.app.service as svc

        original = svc.ChatSession
        svc.ChatSession = FakeOperatorSession  # type: ignore[assignment]
        try:
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)
        finally:
            svc.ChatSession = original  # type: ignore[assignment]

        self.assertEqual(sender.like_calls, [])
        self.assertFalse(result.action_results[0].success)

    async def test_trusted_operator_can_set_profile(self) -> None:
        sender = OperatorSender()
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30004,
                "message_type": "private",
                "sender": {"nickname": "主人", "card": "", "role": "friend"},
                "message": [{"type": "text", "data": {"text": "改下资料"}}],
                "raw_message": "改下资料",
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
            operator_user_ids=(20002,),
        )

        import onebot_gateway.app.service as svc

        original = svc.ChatSession
        svc.ChatSession = FakeProfileSession  # type: ignore[assignment]
        try:
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)
        finally:
            svc.ChatSession = original  # type: ignore[assignment]

        self.assertEqual(sender.profile_calls, [("点点", "你好呀", "female")])
        self.assertTrue(result.action_results[0].success)

    async def test_trusted_operator_can_set_online_status(self) -> None:
        sender = OperatorSender()
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30005,
                "message_type": "private",
                "sender": {"nickname": "主人", "card": "", "role": "friend"},
                "message": [{"type": "text", "data": {"text": "改在线状态"}}],
                "raw_message": "改在线状态",
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
            operator_user_ids=(20002,),
        )

        import onebot_gateway.app.service as svc

        original = svc.ChatSession
        svc.ChatSession = FakeOnlineStatusSession  # type: ignore[assignment]
        try:
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)
        finally:
            svc.ChatSession = original  # type: ignore[assignment]

        self.assertEqual(sender.online_status_calls, [(10, 1028, 0)])
        self.assertTrue(result.action_results[0].success)

    async def test_trusted_operator_can_set_friend_add_request(self) -> None:
        sender = OperatorSender()
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30006,
                "message_type": "private",
                "sender": {"nickname": "主人", "card": "", "role": "friend"},
                "message": [{"type": "text", "data": {"text": "处理好友请求"}}],
                "raw_message": "处理好友请求",
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
            operator_user_ids=(20002,),
        )

        import onebot_gateway.app.service as svc

        original = svc.ChatSession
        svc.ChatSession = FakeFriendRequestSession  # type: ignore[assignment]
        try:
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)
        finally:
            svc.ChatSession = original  # type: ignore[assignment]

        self.assertEqual(sender.friend_request_calls, [("req-123", True, "新朋友")])
        self.assertTrue(result.action_results[0].success)

    async def test_trusted_operator_can_mark_current_private_as_read(self) -> None:
        sender = OperatorSender()
        event = parse_message_event(
            {
                "self_id": 10001,
                "user_id": 20002,
                "message_id": 30007,
                "message_type": "private",
                "sender": {"nickname": "主人", "card": "", "role": "friend"},
                "message": [{"type": "text", "data": {"text": "标记已读"}}],
                "raw_message": "标记已读",
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
            operator_user_ids=(20002,),
        )

        import onebot_gateway.app.service as svc

        original = svc.ChatSession
        svc.ChatSession = FakeMarkReadSession  # type: ignore[assignment]
        try:
            service = ChatService(config)
            result = await service.handle_event(sender, event, decision)
        finally:
            svc.ChatSession = original  # type: ignore[assignment]

        self.assertEqual(sender.mark_private_read_calls, [20002])
        self.assertTrue(result.action_results[0].success)


if __name__ == "__main__":
    unittest.main()

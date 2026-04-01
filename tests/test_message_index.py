"""Redis 消息索引服务测试。"""

from __future__ import annotations

import unittest

from onebot_gateway.message.index import MessageIndexService, RecallErrorCode


class FakePipeline:
    """最小 Redis pipeline 实现。"""

    def __init__(self, redis_client: FakeRedis) -> None:
        self._redis = redis_client
        self._ops: list[tuple[str, tuple[object, ...]]] = []

    def lpush(self, key: str, value: str) -> FakePipeline:
        self._ops.append(("lpush", (key, value)))
        return self

    def ltrim(self, key: str, start: int, stop: int) -> FakePipeline:
        self._ops.append(("ltrim", (key, start, stop)))
        return self

    def expire(self, key: str, ttl: int) -> FakePipeline:
        self._ops.append(("expire", (key, ttl)))
        return self

    def execute(self) -> list[object]:
        results: list[object] = []
        for op_name, args in self._ops:
            method = getattr(self._redis, op_name)
            results.append(method(*args))
        self._ops.clear()
        return results


class FakeRedis:
    """最小 Redis 客户端实现。"""

    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}
        self.ttls: dict[str, int] = {}

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self)

    def ping(self) -> bool:
        return True

    def lpush(self, key: str, value: str) -> int:
        self.lists.setdefault(key, []).insert(0, value)
        return len(self.lists[key])

    def ltrim(self, key: str, start: int, stop: int) -> bool:
        items = self.lists.get(key, [])
        self.lists[key] = items[start : stop + 1]
        return True

    def expire(self, key: str, ttl: int) -> bool:
        self.ttls[key] = ttl
        return True

    def lrange(self, key: str, start: int, stop: int) -> list[str]:
        items = self.lists.get(key, [])
        if stop == -1:
            return items[start:]
        return items[start : stop + 1]


class FakeOneBotClient:
    """最小 OneBot 客户端实现。"""

    def __init__(
        self,
        *,
        recall_result: dict[str, object] | None = None,
        role: str = "member",
    ) -> None:
        self.recall_result = recall_result or {"status": "ok", "retcode": 0}
        self.role = role
        self.recall_calls: list[int | str] = []
        self.role_calls: list[tuple[int | str, int | str, bool]] = []

    async def recall_message(self, message_id: int | str) -> dict[str, object]:
        self.recall_calls.append(message_id)
        return self.recall_result

    async def get_group_member_info(
        self,
        group_id: int | str,
        user_id: int | str,
        *,
        no_cache: bool = True,
    ) -> dict[str, object] | None:
        self.role_calls.append((group_id, user_id, no_cache))
        return {"role": self.role}


class MessageIndexServiceTests(unittest.IsolatedAsyncioTestCase):
    def _build_service(
        self,
        *,
        onebot_client: FakeOneBotClient | None = None,
        redis_client: FakeRedis | None = None,
        group_self_no_window_when_admin: bool = True,
    ) -> MessageIndexService:
        return MessageIndexService(
            redis_client=redis_client or FakeRedis(),
            onebot_client=onebot_client,
            self_id=10001,
            key_prefix="obmsg:test",
            ttl_seconds=172800,
            chat_maxlen=2,
            user_maxlen=2,
            self_maxlen=2,
            recall_window_seconds=120,
            group_self_no_window_when_admin=group_self_no_window_when_admin,
        )

    async def test_record_sent_message_writes_group_indexes_and_ttl(self) -> None:
        redis_client = FakeRedis()
        service = self._build_service(redis_client=redis_client)

        service.record_sent_message(
            message_id=1,
            message_type="group",
            chat_id=20001,
            group_id=20001,
            sender_id=10001,
            self_id=10001,
            content_preview="hello",
            event_time=100,
        )

        self.assertEqual(len(redis_client.lists["obmsg:test:chat:group:20001"]), 1)
        self.assertEqual(len(redis_client.lists["obmsg:test:self:group:20001"]), 1)
        self.assertEqual(
            len(redis_client.lists["obmsg:test:user:group:20001:10001"]), 1
        )
        self.assertEqual(redis_client.ttls["obmsg:test:chat:group:20001"], 172800)
        self.assertEqual(redis_client.ttls["obmsg:test:self:group:20001"], 172800)
        self.assertEqual(redis_client.ttls["obmsg:test:user:group:20001:10001"], 172800)

    async def test_record_sent_message_trims_list_length(self) -> None:
        redis_client = FakeRedis()
        service = self._build_service(redis_client=redis_client)

        service.record_sent_message(
            message_id=1,
            message_type="private",
            chat_id=42,
            group_id=None,
            sender_id=10001,
            self_id=10001,
            event_time=100,
        )
        service.record_sent_message(
            message_id=2,
            message_type="private",
            chat_id=42,
            group_id=None,
            sender_id=10001,
            self_id=10001,
            event_time=101,
        )
        service.record_sent_message(
            message_id=3,
            message_type="private",
            chat_id=42,
            group_id=None,
            sender_id=10001,
            self_id=10001,
            event_time=102,
        )

        messages = service.find_recent_self_messages("private", 42, limit=10)
        self.assertEqual([item.message_id for item in messages], [3, 2])

    async def test_record_received_message_for_self_also_writes_self_index(
        self,
    ) -> None:
        redis_client = FakeRedis()
        service = self._build_service(redis_client=redis_client)

        service.record_received_message(
            message_id=11,
            message_type="group",
            chat_id=500,
            group_id=500,
            user_id=10001,
            sender_id=10001,
            self_id=10001,
            event_time=200,
            role="admin",
        )

        last = service.get_last_self_message("group", 500)
        self.assertIsNotNone(last)
        assert last is not None
        self.assertTrue(last.is_self)
        self.assertEqual(last.role_at_receive, "admin")

    async def test_recall_last_self_message_in_private_within_window(self) -> None:
        onebot = FakeOneBotClient()
        service = self._build_service(onebot_client=onebot)
        service.record_sent_message(
            message_id=101,
            message_type="private",
            chat_id=42,
            group_id=None,
            sender_id=10001,
            self_id=10001,
            event_time=100,
        )

        original_time = __import__("time").time
        try:
            __import__("time").time = lambda: 150
            result = await service.recall_last_self_message("private", 42)
        finally:
            __import__("time").time = original_time

        self.assertTrue(result.success)
        self.assertEqual(onebot.recall_calls, [101])

    async def test_recall_last_self_message_exceeds_window_without_calling_onebot(
        self,
    ) -> None:
        onebot = FakeOneBotClient()
        service = self._build_service(onebot_client=onebot)
        service.record_sent_message(
            message_id=102,
            message_type="private",
            chat_id=42,
            group_id=None,
            sender_id=10001,
            self_id=10001,
            event_time=100,
        )

        original_time = __import__("time").time
        try:
            __import__("time").time = lambda: 500
            result = await service.recall_last_self_message("private", 42)
        finally:
            __import__("time").time = original_time

        self.assertFalse(result.success)
        self.assertEqual(
            result.error_code, RecallErrorCode.RECALL_WINDOW_EXCEEDED.value
        )
        self.assertEqual(onebot.recall_calls, [])

    async def test_group_admin_can_recall_old_self_message_when_policy_enabled(
        self,
    ) -> None:
        onebot = FakeOneBotClient(role="admin")
        service = self._build_service(
            onebot_client=onebot,
            group_self_no_window_when_admin=True,
        )
        service.record_sent_message(
            message_id=201,
            message_type="group",
            chat_id=777,
            group_id=777,
            sender_id=10001,
            self_id=10001,
            event_time=100,
        )

        original_time = __import__("time").time
        try:
            __import__("time").time = lambda: 1000
            result = await service.recall_last_self_message("group", 777)
        finally:
            __import__("time").time = original_time

        self.assertTrue(result.success)
        self.assertEqual(onebot.role_calls, [(777, 10001, True)])
        self.assertEqual(onebot.recall_calls, [201])

    async def test_recall_last_user_message_denied_for_non_admin(self) -> None:
        onebot = FakeOneBotClient(role="member")
        service = self._build_service(onebot_client=onebot)
        service.record_received_message(
            message_id=301,
            message_type="group",
            chat_id=888,
            group_id=888,
            user_id=20002,
            sender_id=20002,
            self_id=10001,
            event_time=100,
        )

        result = await service.recall_last_user_message(888, 20002)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, RecallErrorCode.PERMISSION_DENIED.value)
        self.assertEqual(onebot.recall_calls, [])

    async def test_platform_rejected_maps_to_platform_error(self) -> None:
        onebot = FakeOneBotClient(
            role="admin",
            recall_result={
                "status": "failed",
                "retcode": 100,
                "message": "platform rejected",
            },
        )
        service = self._build_service(onebot_client=onebot)
        service.record_received_message(
            message_id=302,
            message_type="group",
            chat_id=888,
            group_id=888,
            user_id=20002,
            sender_id=20002,
            self_id=10001,
            event_time=100,
        )

        result = await service.recall_last_user_message(888, 20002)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, RecallErrorCode.PLATFORM_REJECTED.value)
        self.assertIn("platform rejected", result.message)

    async def test_recall_by_message_id_requires_group_id_when_admin_required(
        self,
    ) -> None:
        onebot = FakeOneBotClient(role="admin")
        service = self._build_service(onebot_client=onebot)

        result = await service.recall_by_message_id(999, require_admin=True)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, RecallErrorCode.INVALID_CONTEXT.value)
        self.assertEqual(onebot.recall_calls, [])

    async def test_invalid_chat_type_returns_invalid_context(self) -> None:
        service = self._build_service(onebot_client=FakeOneBotClient())

        result = await service.recall_last_self_message("temp", 1)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, RecallErrorCode.INVALID_CONTEXT.value)


if __name__ == "__main__":
    unittest.main()

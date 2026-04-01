"""带索引 sender 包装层测试。"""

from __future__ import annotations

import unittest

from onebot_gateway.app.indexed_sender import IndexedChatMessageSender
from onebot_gateway.transport.client import SendMessageResult


class SpyMessageIndex:
    def __init__(self) -> None:
        self.sent_calls: list[dict[str, object]] = []

    def record_sent_message(self, **kwargs: object) -> None:
        self.sent_calls.append(dict(kwargs))


class FakeWrappedSender:
    async def send_private_message(self, user_id: int | str, message: object) -> object:
        return SendMessageResult(message_id=123, raw_response={"status": "ok"})

    async def send_group_message(self, group_id: int | str, message: object) -> object:
        return SendMessageResult(message_id=456, raw_response={"status": "ok"})

    async def send_private_forward_message(
        self,
        user_id: int | str,
        messages: list[dict[str, object]],
    ) -> dict[str, object]:
        return {"data": {"message_id": 789}}

    async def send_group_forward_message(
        self,
        group_id: int | str,
        messages: list[dict[str, object]],
    ) -> dict[str, object]:
        return {"data": {"message_id": 987}}

    async def upload_private_file(
        self,
        user_id: int | str,
        file: str,
        name: str = "",
    ) -> dict[str, object]:
        return {"status": "ok"}

    async def _send_group_notice(
        self,
        group_id: int | str,
        content: str,
        is_pinned: bool = True,
    ) -> dict[str, object]:
        return {"data": {"message_id": 654}}


class IndexedSenderTests(unittest.IsolatedAsyncioTestCase):
    async def test_indexes_plain_text_messages(self) -> None:
        index = SpyMessageIndex()
        sender = IndexedChatMessageSender(FakeWrappedSender(), index, self_id=10001)

        await sender.send_private_message(20002, "你好")
        await sender.send_group_message(30003, "群里你好")

        self.assertEqual(len(index.sent_calls), 2)
        self.assertEqual(index.sent_calls[0]["message_id"], 123)
        self.assertEqual(index.sent_calls[0]["message_type"], "private")
        self.assertEqual(index.sent_calls[0]["chat_id"], 20002)
        self.assertEqual(index.sent_calls[0]["content_preview"], "你好")
        self.assertEqual(index.sent_calls[1]["message_id"], 456)
        self.assertEqual(index.sent_calls[1]["message_type"], "group")
        self.assertEqual(index.sent_calls[1]["chat_id"], 30003)

    async def test_indexes_forward_and_notice_when_message_id_exists(self) -> None:
        index = SpyMessageIndex()
        sender = IndexedChatMessageSender(FakeWrappedSender(), index, self_id=10001)

        await sender.send_private_forward_message(20002, [{"type": "node"}])
        await sender.send_group_forward_message(
            30003, [{"type": "node"}, {"type": "node"}]
        )
        await sender._send_group_notice(30003, "公告内容")

        self.assertEqual(
            [item["message_id"] for item in index.sent_calls], [789, 987, 654]
        )
        self.assertEqual(index.sent_calls[0]["content_preview"], "[合并转发 1 条]")
        self.assertEqual(index.sent_calls[1]["content_preview"], "[合并转发 2 条]")
        self.assertEqual(index.sent_calls[2]["content_preview"], "公告内容")

    async def test_skips_index_when_response_has_no_message_id(self) -> None:
        index = SpyMessageIndex()
        sender = IndexedChatMessageSender(FakeWrappedSender(), index, self_id=10001)

        await sender.upload_private_file(20002, "C:/tmp/test.txt", name="test.txt")

        self.assertEqual(index.sent_calls, [])


if __name__ == "__main__":
    unittest.main()

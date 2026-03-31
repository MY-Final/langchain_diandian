"""OneBot 客户端发送测试。"""

from __future__ import annotations

import unittest

from onebot_gateway.message.builder import at_segment, text_segment
from onebot_gateway.transport.client import OneBotWebSocketClient


class StubSendClient(OneBotWebSocketClient):
    """拦截 request 调用，验证发送参数。"""

    def __init__(self) -> None:
        super().__init__("ws://example.com", "")
        self.calls: list[tuple[str, dict]] = []

    async def request(
        self, action: str, params: dict, *, timeout: float = 10.0
    ) -> dict:
        self.calls.append((action, params))
        return {
            "status": "ok",
            "retcode": 0,
            "data": {"message_id": 123456},
            "message": "",
            "wording": "",
        }


class OneBotClientSendTests(unittest.IsolatedAsyncioTestCase):
    """验证消息发送 action 组装。"""

    async def test_send_group_message_accepts_text(self) -> None:
        client = StubSendClient()

        result = await client.send_group_message(515587773, "你好")

        self.assertEqual(result.message_id, 123456)
        self.assertEqual(
            client.calls,
            [
                (
                    "send_group_msg",
                    {
                        "group_id": "515587773",
                        "message": [{"type": "text", "data": {"text": "你好"}}],
                    },
                )
            ],
        )

    async def test_send_group_message_accepts_segments(self) -> None:
        client = StubSendClient()

        await client.send_group_message(
            515587773,
            [text_segment("你好 "), at_segment(10001), text_segment(" 看这里")],
        )

        self.assertEqual(
            client.calls[0],
            (
                "send_group_msg",
                {
                    "group_id": "515587773",
                    "message": [
                        {"type": "text", "data": {"text": "你好 "}},
                        {"type": "at", "data": {"qq": "10001"}},
                        {"type": "text", "data": {"text": " 看这里"}},
                    ],
                },
            ),
        )

    async def test_send_private_message_accepts_text(self) -> None:
        client = StubSendClient()

        await client.send_private_message(3075414416, "你好")

        self.assertEqual(
            client.calls[0],
            (
                "send_private_msg",
                {
                    "user_id": "3075414416",
                    "message": [{"type": "text", "data": {"text": "你好"}}],
                },
            ),
        )


if __name__ == "__main__":
    unittest.main()

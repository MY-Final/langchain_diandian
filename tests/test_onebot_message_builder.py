"""OneBot 消息段构造测试。"""

from __future__ import annotations

import unittest

from onebot_gateway.message.builder import (
    OutgoingMessageSegment,
    at_segment,
    contact_segment,
    custom_segment,
    face_segment,
    ensure_segments,
    image_segment,
    markdown_segment,
    poke_segment,
    record_segment,
    reply_segment,
    text_segment,
    video_segment,
)


class MessageBuilderTests(unittest.TestCase):
    """验证消息段构造结果。"""

    def test_builds_common_segments(self) -> None:
        self.assertEqual(
            text_segment("你好").to_dict(), {"type": "text", "data": {"text": "你好"}}
        )
        self.assertEqual(
            at_segment(123).to_dict(), {"type": "at", "data": {"qq": "123"}}
        )
        self.assertEqual(
            reply_segment(456).to_dict(), {"type": "reply", "data": {"id": "456"}}
        )
        self.assertEqual(
            image_segment("https://example.com/a.png").to_dict(),
            {"type": "image", "data": {"file": "https://example.com/a.png"}},
        )
        self.assertEqual(
            face_segment(14).to_dict(), {"type": "face", "data": {"id": "14"}}
        )
        self.assertEqual(
            markdown_segment("# hi").to_dict(),
            {"type": "markdown", "data": {"content": "# hi"}},
        )
        self.assertEqual(
            record_segment("voice.mp3").to_dict(),
            {"type": "record", "data": {"file": "voice.mp3"}},
        )
        self.assertEqual(
            video_segment("demo.mp4").to_dict(),
            {"type": "video", "data": {"file": "demo.mp4"}},
        )
        self.assertEqual(
            contact_segment("qq", 123).to_dict(),
            {"type": "contact", "data": {"type": "qq", "id": "123"}},
        )
        self.assertEqual(
            poke_segment("qq", 123).to_dict(),
            {"type": "poke", "data": {"type": "qq", "id": "123"}},
        )

    def test_supports_custom_segment(self) -> None:
        segment = custom_segment("face", id=14)
        self.assertEqual(segment.to_dict(), {"type": "face", "data": {"id": "14"}})

    def test_ensure_segments_normalizes_input(self) -> None:
        self.assertEqual(ensure_segments("你好"), [text_segment("你好")])

        segment = OutgoingMessageSegment(type="text", data={"text": "hi"})
        self.assertEqual(ensure_segments(segment), [segment])
        self.assertEqual(ensure_segments([segment]), [segment])


if __name__ == "__main__":
    unittest.main()

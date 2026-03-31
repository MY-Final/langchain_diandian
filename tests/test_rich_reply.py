"""富消息回复解析测试。"""

from __future__ import annotations

import unittest

from onebot_gateway.message.rich_reply import (
    build_rich_text_reply,
    parse_rich_reply_segments,
)


class RichReplyTests(unittest.TestCase):
    """验证模型富消息回复解析。"""

    def test_parses_at_tag_inside_text(self) -> None:
        segments = parse_rich_reply_segments('你好 <at qq="123456" /> 请看这里')

        self.assertEqual(
            [segment.to_dict() for segment in segments],
            [
                {"type": "text", "data": {"text": "你好 "}},
                {"type": "at", "data": {"qq": "123456"}},
                {"type": "text", "data": {"text": " 请看这里"}},
            ],
        )

    def test_parses_markdown_and_image_tags(self) -> None:
        segments = parse_rich_reply_segments(
            '<markdown># 标题</markdown><image file="https://example.com/a.png" />'
        )

        self.assertEqual(
            [segment.to_dict() for segment in segments],
            [
                {"type": "markdown", "data": {"content": "# 标题"}},
                {"type": "image", "data": {"file": "https://example.com/a.png"}},
            ],
        )

    def test_parses_face_tag(self) -> None:
        segments = parse_rich_reply_segments('收到 <face id="14" />')

        self.assertEqual(
            [segment.to_dict() for segment in segments],
            [
                {"type": "text", "data": {"text": "收到 "}},
                {"type": "face", "data": {"id": "14"}},
            ],
        )

    def test_build_reply_can_prepend_quote_segment(self) -> None:
        segments = build_rich_text_reply(
            '你好 <at qq="123456" />', reply_message_id=789
        )

        self.assertEqual(
            [segment.to_dict() for segment in segments],
            [
                {"type": "reply", "data": {"id": "789"}},
                {"type": "text", "data": {"text": "你好 "}},
                {"type": "at", "data": {"qq": "123456"}},
            ],
        )

    def test_falls_back_to_plain_text_for_invalid_markup(self) -> None:
        segments = parse_rich_reply_segments('你好 <at qq="123456">')

        self.assertEqual(
            [segment.to_dict() for segment in segments],
            [{"type": "text", "data": {"text": '你好 <at qq="123456">'}}],
        )


if __name__ == "__main__":
    unittest.main()

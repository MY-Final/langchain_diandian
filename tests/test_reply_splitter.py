"""回复分段器测试。"""

from __future__ import annotations

import unittest

from onebot_gateway.config import ReplySplitConfig
from onebot_gateway.message.reply_splitter import ReplySplitter


class ReplySplitterTests(unittest.TestCase):
    """验证回复分段规则。"""

    def test_uses_explicit_marker_first(self) -> None:
        splitter = ReplySplitter(
            ReplySplitConfig(enabled=True, max_chars=100, marker="[SPLIT]")
        )

        self.assertEqual(
            splitter.split("第一段[SPLIT]第二段[SPLIT]第三段"),
            ["第一段", "第二段", "第三段"],
        )

    def test_only_hard_splits_when_no_marker(self) -> None:
        splitter = ReplySplitter(
            ReplySplitConfig(enabled=True, max_chars=8, marker="[SPLIT]")
        )

        self.assertEqual(
            splitter.split("第一句。第二句。第三句。"),
            ["第一句。第二句。", "第三句。"],
        )

    def test_can_disable_split(self) -> None:
        splitter = ReplySplitter(
            ReplySplitConfig(enabled=False, max_chars=5, marker="[SPLIT]")
        )

        self.assertEqual(splitter.split("第一段[SPLIT]第二段"), ["第一段[SPLIT]第二段"])


if __name__ == "__main__":
    unittest.main()

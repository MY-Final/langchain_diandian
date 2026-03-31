"""QQ 表情检索测试。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from chat_app.emoji.index import EmojiSearchIndex, load_emoji_records


class EmojiSearchIndexTests(unittest.TestCase):
    """验证 emoji_records.jsonl 检索逻辑。"""

    def test_search_matches_exact_name_and_semantic_hint(self) -> None:
        records = (
            '{"emoji_id":"14","emoji_name":"微笑","aliases":[],"asset_path":"a","animation_path":"","category":"qqnt"}\n'
            '{"emoji_id":"13","emoji_name":"呲牙","aliases":["开心笑"],"asset_path":"b","animation_path":"","category":"qqnt"}\n'
            '{"emoji_id":"124","emoji_name":"点赞","aliases":[],"asset_path":"c","animation_path":"","category":"qqnt"}\n'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "emoji_records.jsonl"
            path.write_text(records, encoding="utf-8")
            load_emoji_records.cache_clear()
            index = EmojiSearchIndex(load_emoji_records(path))

        exact = index.search("微笑", limit=3)
        semantic = index.search("想要一个开心友好的表情", limit=3)

        self.assertEqual(exact[0].emoji_id, "14")
        self.assertEqual(semantic[0].emoji_name, "微笑")


if __name__ == "__main__":
    unittest.main()

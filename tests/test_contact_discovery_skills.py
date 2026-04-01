"""联系人发现 skill 测试。"""

from __future__ import annotations

import asyncio
import json
import unittest

from chat_app.skills.context import SkillContext
from chat_app.skills.registry import resolve_skill_runtime


class FakeDiscoverySender:
    async def get_recent_contact(self, count: int = 10) -> list[dict]:
        return [
            {
                "peerUin": "10001",
                "peerName": "张三",
                "remark": "老同学",
                "sendNickName": "张三",
                "sendMemberName": "",
            },
            {
                "peerUin": "10002",
                "peerName": "李四",
                "remark": "同事",
                "sendNickName": "李四",
                "sendMemberName": "",
            },
        ]

    async def get_friend_list(self, *, no_cache: bool = True) -> list[dict]:
        return [
            {"user_id": 10001, "nickname": "张三", "remark": "老同学"},
            {"user_id": 10002, "nickname": "李四", "remark": "同事"},
        ]

    async def get_friends_with_category(self) -> list[dict]:
        return [
            {
                "categoryName": "同事",
                "buddyList": [{"user_id": 10002, "nickname": "李四", "remark": "同事"}],
            }
        ]

    async def get_stranger_info(self, user_id: int | str) -> dict | None:
        if int(user_id) != 10001:
            return None
        return {
            "user_id": 10001,
            "nickname": "张三",
            "remark": "老同学",
            "sex": "male",
            "age": 18,
            "qid": "zhangsan",
            "long_nick": "你好",
            "status": 1,
            "login_days": 88,
        }


class ContactDiscoverySkillTests(unittest.TestCase):
    def test_runtime_tools_can_lookup_contacts(self) -> None:
        runtime = resolve_skill_runtime(
            SkillContext(
                session_kind="private",
                user_id=20002,
                is_trusted_operator=True,
                supports_live_onebot_queries=True,
            ),
            sender=FakeDiscoverySender(),
        )
        tools = {tool.name: tool for tool in runtime.tools}

        result = asyncio.run(
            tools["lookup_contacts"].ainvoke(
                {"source": "friends", "keyword": "张", "limit": 5}
            )
        )
        data = json.loads(result)

        self.assertEqual(data["source"], "friends")
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["nickname"], "张三")

    def test_runtime_tools_can_get_contact_profile(self) -> None:
        runtime = resolve_skill_runtime(
            SkillContext(
                session_kind="private",
                user_id=20002,
                is_trusted_operator=True,
                supports_live_onebot_queries=True,
            ),
            sender=FakeDiscoverySender(),
        )
        tools = {tool.name: tool for tool in runtime.tools}

        result = asyncio.run(tools["get_contact_profile"].ainvoke({"user_id": 10001}))
        data = json.loads(result)

        self.assertTrue(data["found"])
        self.assertEqual(data["nickname"], "张三")


if __name__ == "__main__":
    unittest.main()

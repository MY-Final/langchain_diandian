"""群信息查询 skill 测试。"""

from __future__ import annotations

import asyncio
import json
import unittest

from chat_app.skills.context import SkillContext
from chat_app.skills.registry import resolve_skill_runtime


class FakeGroupInspectionSender:
    async def get_group_list(self) -> list[dict]:
        return [
            {
                "group_id": 100,
                "group_name": "测试群",
                "member_count": 50,
                "max_member_count": 200,
            },
            {
                "group_id": 200,
                "group_name": "开发群",
                "member_count": 20,
                "max_member_count": 200,
            },
        ]

    async def get_group_info(self, group_id: int | str) -> dict | None:
        if int(group_id) != 100:
            return None
        return {
            "group_id": 100,
            "group_name": "测试群",
            "member_count": 50,
            "max_member_count": 200,
            "group_memo": "欢迎加入",
            "group_create_time": 1700000000,
        }

    async def get_group_member_list(self, group_id: int | str) -> list[dict]:
        return [
            {
                "user_id": 10001,
                "nickname": "张三",
                "card": "群名片A",
                "role": "owner",
            },
            {
                "user_id": 10002,
                "nickname": "李四",
                "card": "",
                "role": "member",
            },
        ]


class GroupInspectionSkillTests(unittest.TestCase):
    def test_group_list_is_loaded(self) -> None:
        runtime = resolve_skill_runtime(
            SkillContext(
                session_kind="group",
                user_id=20002,
                group_id=100,
                supports_live_onebot_queries=True,
            ),
            sender=FakeGroupInspectionSender(),
        )

        tools = {tool.name: tool for tool in runtime.tools}
        result = asyncio.run(
            tools["get_group_list"].ainvoke({"keyword": "测试", "limit": 10})
        )
        data = json.loads(result)

        self.assertEqual(len(data["groups"]), 1)
        self.assertEqual(data["groups"][0]["group_name"], "测试群")

    def test_group_detail_is_loaded(self) -> None:
        runtime = resolve_skill_runtime(
            SkillContext(
                session_kind="group",
                user_id=20002,
                group_id=100,
                supports_live_onebot_queries=True,
            ),
            sender=FakeGroupInspectionSender(),
        )

        tools = {tool.name: tool for tool in runtime.tools}
        result = asyncio.run(tools["get_group_detail"].ainvoke({"group_id": 100}))
        data = json.loads(result)

        self.assertTrue(data["found"])
        self.assertEqual(data["group_name"], "测试群")
        self.assertEqual(data["group_memo"], "欢迎加入")

    def test_group_member_list_is_loaded(self) -> None:
        runtime = resolve_skill_runtime(
            SkillContext(
                session_kind="group",
                user_id=20002,
                group_id=100,
                supports_live_onebot_queries=True,
            ),
            sender=FakeGroupInspectionSender(),
        )

        tools = {tool.name: tool for tool in runtime.tools}
        result = asyncio.run(
            tools["get_group_member_list"].ainvoke({"group_id": 100, "keyword": "张"})
        )
        data = json.loads(result)

        self.assertEqual(data["group_id"], 100)
        self.assertEqual(len(data["members"]), 1)
        self.assertEqual(data["members"][0]["nickname"], "张三")


if __name__ == "__main__":
    unittest.main()

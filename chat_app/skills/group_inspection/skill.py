"""群信息查询 skill。"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from chat_app.skills.context import SkillContext
from chat_app.skills.types import SkillSpec


def _applies_to(context: SkillContext) -> bool:
    return (
        (context.is_private_message() and context.is_trusted_operator)
        or context.is_group_message()
    ) and context.supports_live_onebot_queries


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 你当前可使用群信息查询能力。",
        "- 如需查询机器人所在的群列表，可调用 get_group_list 工具。",
        "- 如需查询指定群的详细信息，可调用 get_group_detail 工具。",
        "- 如需查询某群的成员列表，可调用 get_group_member_list 工具。",
        "- 这些查询工具返回的是实时数据，不要编造群信息。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return ()


def _build_runtime_tools(_context: SkillContext, sender: object) -> tuple:
    @tool
    async def get_group_list(keyword: str = "", limit: int = 20) -> str:
        """查询机器人所在的群列表。

        - keyword 为空时返回前若干项。
        - 返回的是实时群列表。
        """
        rows = await sender.get_group_list()
        normalized_limit = max(1, min(int(limit), 50))
        normalized_keyword = keyword.strip().lower()

        items = []
        for row in rows:
            item = {
                "group_id": int(row.get("group_id", 0)),
                "group_name": str(row.get("group_name", "")).strip(),
                "member_count": int(row.get("member_count", 0)),
                "max_member_count": int(row.get("max_member_count", 0)),
            }
            items.append(item)

        if normalized_keyword:
            items = [
                item
                for item in items
                if normalized_keyword
                in (
                    str(item.get("group_name", ""))
                    + " "
                    + str(item.get("group_id", ""))
                ).lower()
            ]

        return json.dumps(
            {"groups": items[:normalized_limit]},
            ensure_ascii=False,
        )

    @tool
    async def get_group_detail(group_id: int) -> str:
        """获取指定群的详细信息。

        - 返回群名、人数上限、当前人数、群头像、群描述等。
        """
        data = await sender.get_group_info(group_id)
        if data is None:
            return json.dumps(
                {"group_id": int(group_id), "found": False},
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "group_id": int(data.get("group_id", group_id)),
                "group_name": data.get("group_name", ""),
                "member_count": data.get("member_count", 0),
                "max_member_count": data.get("max_member_count", 0),
                "group_memo": data.get("group_memo", ""),
                "group_create_time": data.get("group_create_time", 0),
                "group_level": data.get("group_level", 0),
                "max_member_count_ex": data.get("max_member_count_ex", 0),
                "found": True,
            },
            ensure_ascii=False,
        )

    @tool
    async def get_group_member_list(
        group_id: int, keyword: str = "", limit: int = 20
    ) -> str:
        """查询群成员列表。

        - 返回成员 user_id、昵称、名片、角色。
        - keyword 为空时返回前若干项。
        """
        rows = await sender.get_group_member_list(group_id)
        normalized_limit = max(1, min(int(limit), 50))
        normalized_keyword = keyword.strip().lower()

        items = []
        for row in rows:
            item = {
                "user_id": int(row.get("user_id", 0)),
                "nickname": str(row.get("nickname", "")).strip(),
                "card": str(row.get("card", "")).strip(),
                "role": str(row.get("role", "member")).strip(),
            }
            items.append(item)

        if normalized_keyword:
            items = [
                item
                for item in items
                if normalized_keyword
                in (
                    str(item.get("nickname", ""))
                    + " "
                    + str(item.get("card", ""))
                    + " "
                    + str(item.get("user_id", ""))
                ).lower()
            ]

        return json.dumps(
            {"group_id": int(group_id), "members": items[:normalized_limit]},
            ensure_ascii=False,
        )

    return (get_group_list, get_group_detail, get_group_member_list)


GROUP_INSPECTION_SKILL = SkillSpec(
    name="group_inspection",
    description="群信息查询能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    build_runtime_tools=_build_runtime_tools,
    priority=40,
)

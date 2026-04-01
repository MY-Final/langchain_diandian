"""联系人发现 skill。"""

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
        "- 你当前可使用联系人查询能力。",
        "- 如需查最近联系人、好友或分组好友，可调用 lookup_contacts 工具。",
        "- 如需查单个用户资料，可调用 get_contact_profile 工具。",
        "- 查询类工具应优先复用，不要编造联系人信息。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return ()


def _build_runtime_tools(_context: SkillContext, sender: object) -> tuple:
    @tool
    async def lookup_contacts(
        source: str = "recent", keyword: str = "", limit: int = 10
    ) -> str:
        """查询最近联系人、好友列表或好友分组。

        - source 支持 recent/friends/friend_groups。
        - keyword 为空时返回前若干项。
        - 该工具会实时查询 OneBot 数据。
        """
        normalized_source = source.strip().lower() or "recent"
        normalized_limit = max(1, min(int(limit), 20))
        normalized_keyword = keyword.strip().lower()

        if normalized_source == "friends":
            rows = await sender.get_friend_list(no_cache=True)
            items = [_map_friend_item(item) for item in rows]
        elif normalized_source == "friend_groups":
            rows = await sender.get_friends_with_category()
            items = _flatten_friend_groups(rows)
        else:
            rows = await sender.get_recent_contact(count=normalized_limit)
            items = [_map_recent_contact_item(item) for item in rows]

        filtered = [
            item for item in items if _matches_contact(item, normalized_keyword)
        ]
        return json.dumps(
            {"source": normalized_source, "items": filtered[:normalized_limit]},
            ensure_ascii=False,
        )

    @tool
    async def get_contact_profile(
        user_id: int | None = None, target_id: int | None = None
    ) -> str:
        """获取指定用户的账号资料。

        - user_id 或 target_id 二选一。
        - 返回昵称、性别、年龄、qid 等信息。
        """
        resolved_id = target_id if target_id is not None else user_id
        if resolved_id is None:
            return json.dumps(
                {"found": False, "reason": "缺少 user_id/target_id"}, ensure_ascii=False
            )
        data = await sender.get_stranger_info(int(resolved_id))
        if data is None:
            return json.dumps(
                {"user_id": int(resolved_id), "found": False}, ensure_ascii=False
            )
        return json.dumps(
            {
                "user_id": int(data.get("user_id", resolved_id)),
                "nickname": data.get("nickname", ""),
                "remark": data.get("remark", ""),
                "sex": data.get("sex", "unknown"),
                "age": data.get("age", 0),
                "qid": data.get("qid", ""),
                "long_nick": data.get("long_nick", ""),
                "status": data.get("status", 0),
                "login_days": data.get("login_days", 0),
                "found": True,
            },
            ensure_ascii=False,
        )

    return (lookup_contacts, get_contact_profile)


CONTACT_DISCOVERY_SKILL = SkillSpec(
    name="contact_discovery",
    description="联系人与账号资料查询能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    build_runtime_tools=_build_runtime_tools,
    priority=55,
)


def _flatten_friend_groups(rows: list[dict[str, Any]]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for row in rows:
        category_name = str(row.get("categoryName", "")).strip()
        for buddy in row.get("buddyList", []):
            if not isinstance(buddy, dict):
                continue
            items.append(
                {
                    "user_id": int(buddy.get("user_id", 0) or 0),
                    "nickname": str(buddy.get("nickname", "")).strip(),
                    "remark": str(buddy.get("remark", "")).strip(),
                    "category": category_name,
                }
            )
    return items


def _map_friend_item(item: dict[str, Any]) -> dict[str, object]:
    return {
        "user_id": int(item.get("user_id", 0) or 0),
        "nickname": str(item.get("nickname", "")).strip(),
        "remark": str(item.get("remark", "")).strip(),
    }


def _map_recent_contact_item(item: dict[str, Any]) -> dict[str, object]:
    return {
        "peer_uin": str(item.get("peerUin", "")).strip(),
        "peer_name": str(item.get("peerName", "")).strip(),
        "remark": str(item.get("remark", "")).strip(),
        "send_nickname": str(item.get("sendNickName", "")).strip(),
        "send_member_name": str(item.get("sendMemberName", "")).strip(),
    }


def _matches_contact(item: dict[str, object], keyword: str) -> bool:
    if not keyword:
        return True
    haystack = " ".join(str(value).lower() for value in item.values())
    return keyword in haystack

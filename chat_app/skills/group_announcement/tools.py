"""群公告 skill 使用的 tools。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.skills.group_announcement.types import (
    PendingGetGroupNoticeAction,
    PendingSendGroupNoticeAction,
)


@tool
def send_group_notice(group_id: int, content: str, is_pinned: bool = True) -> str:
    """发送群公告。

    调用后会生成一条待执行指令，由服务层执行。
    - content 为公告内容。
    - is_pinned=true 表示置顶公告。
    - 仅群聊场景可用，需要群主或管理员权限。
    """
    action = PendingSendGroupNoticeAction(
        group_id=group_id,
        content=content,
        is_pinned=is_pinned,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def get_group_notice(group_id: int) -> str:
    """获取群公告列表。

    调用后会生成一条待执行指令，由服务层执行。
    - 仅群聊场景可用。
    """
    action = PendingGetGroupNoticeAction(group_id=group_id)
    return json.dumps(action.to_dict(), ensure_ascii=False)

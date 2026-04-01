"""好友请求管理 skill 使用的 tools。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.skills.friend_request_management.types import (
    PendingSetFriendAddRequestAction,
)


@tool
def set_friend_add_request(flag: str, approve: bool = True, remark: str = "") -> str:
    """处理好友请求。

    调用后会生成一条待执行指令，由服务层执行。
    - flag 为好友请求 ID。
    - approve=true 表示同意，false 表示拒绝。
    - 该 skill 默认只对受信操作员开放。
    """
    action = PendingSetFriendAddRequestAction(
        flag=flag.strip(),
        approve=approve,
        remark=remark.strip(),
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)

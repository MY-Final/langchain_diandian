"""好友管理 skill 使用的 tools。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.skills.friend_management.types import (
    PendingDeleteFriendAction,
    PendingSendLikeAction,
)


@tool
def send_like(user_id: int, times: int = 1) -> str:
    """给指定用户点赞。

    调用后会生成一条待执行指令，由服务层执行。
    - times 为点赞次数，最少 1 次。
    - 该 skill 默认只对受信操作员开放。
    """
    normalized_times = max(1, int(times))
    action = PendingSendLikeAction(user_id=user_id, times=normalized_times)
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def delete_friend(
    user_id: int, temp_block: bool = True, temp_both_del: bool = False
) -> str:
    """删除指定好友。

    调用后会生成一条待执行指令，由服务层执行。
    - temp_block=true 表示拉黑。
    - temp_both_del=true 表示尝试双向删除。
    - 该 skill 默认只对受信操作员开放。
    """
    action = PendingDeleteFriendAction(
        user_id=user_id,
        temp_block=temp_block,
        temp_both_del=temp_both_del,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)

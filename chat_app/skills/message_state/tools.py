"""消息状态 skill 使用的 tools。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.skills.message_state.types import PendingMarkConversationReadAction

_ALLOWED_SCOPES = {"current", "private", "group", "all"}


@tool
def mark_conversation_read(scope: str = "current", target_id: int | None = None) -> str:
    """将会话或消息标记为已读。

    调用后会生成一条待执行指令，由服务层执行。
    - scope 支持 current/private/group/all。
    - 当 scope=private 或 group 时，需要提供 target_id。
    - 该 skill 默认只对受信操作员开放。
    """
    normalized_scope = scope.strip().lower() or "current"
    if normalized_scope not in _ALLOWED_SCOPES:
        normalized_scope = "current"
    normalized_target_id = None if target_id is None else int(target_id)
    action = PendingMarkConversationReadAction(
        scope=normalized_scope,
        target_id=normalized_target_id,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)

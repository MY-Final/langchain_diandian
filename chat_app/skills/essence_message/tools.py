"""精华消息 skill 使用的 tools。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.skills.essence_message.types import (
    PendingAddEssenceMessageAction,
    PendingGetEssenceMessageListAction,
    PendingRemoveEssenceMessageAction,
)


@tool
def add_essence_message(message_id: int) -> str:
    """添加精华消息。

    调用后会生成一条待执行指令，由服务层执行。
    - message_id 为目标消息的 message_id。
    - 仅群聊场景可用，需要群主或管理员权限。
    """
    action = PendingAddEssenceMessageAction(message_id=message_id)
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def remove_essence_message(message_id: int) -> str:
    """移除精华消息。

    调用后会生成一条待执行指令，由服务层执行。
    - message_id 为精华消息的 message_id。
    - 仅群聊场景可用，需要群主或管理员权限。
    """
    action = PendingRemoveEssenceMessageAction(message_id=message_id)
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def get_essence_message_list(group_id: int) -> str:
    """获取精华消息列表。

    调用后会生成一条待执行指令，由服务层执行。
    - 仅群聊场景可用。
    """
    action = PendingGetEssenceMessageListAction(group_id=group_id)
    return json.dumps(action.to_dict(), ensure_ascii=False)

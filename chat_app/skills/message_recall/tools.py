"""消息撤回 skill 使用的 tools。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.skills.message_recall.types import PendingRecallMessageAction


@tool
def recall_last_self_message(chat_type: str, chat_id: int) -> str:
    """撤回机器人在指定会话中最近一条自己发送的消息。

    参数:
        chat_type: 会话类型，"private" 表示私聊，"group" 表示群聊
        chat_id: 会话 ID，私聊时为对方 QQ 号，群聊时为群号

    示例:
        recall_last_self_message(chat_type="group", chat_id=123456)
        recall_last_self_message(chat_type="private", chat_id=789012)
    """
    action = PendingRecallMessageAction(
        chat_type=chat_type,
        chat_id=chat_id,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def recall_last_user_message(group_id: int, sender_id: int) -> str:
    """在群里撤回指定用户最近一条发送的消息。

    仅当机器人是群主或管理员时可用。

    参数:
        group_id: 群号
        sender_id: 要撤回消息的用户 QQ 号

    示例:
        recall_last_user_message(group_id=123456, sender_id=789012)
    """
    action = PendingRecallMessageAction(
        chat_type="group",
        chat_id=group_id,
        target_user_id=sender_id,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)

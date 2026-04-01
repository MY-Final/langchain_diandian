"""消息撤回 skill 使用的 tools。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.skills.message_recall.types import PendingRecallMessageAction


@tool
def recall_message(message_id: int) -> str:
    """撤回指定消息。

    调用后会生成一条待执行指令，由服务层执行。
    - 仅支持撤回机器人自己发送的消息。
    - message_id 为目标消息的 message_id。
    """
    action = PendingRecallMessageAction(message_id=message_id)
    return json.dumps(action.to_dict(), ensure_ascii=False)

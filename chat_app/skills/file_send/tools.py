"""文件发送 skill 使用的 tools。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.skills.file_send.types import (
    PendingSendGroupFileMessageAction,
    PendingSendPrivateFileAction,
)


@tool
def send_private_file(user_id: int, file: str) -> str:
    """发送私聊文件。

    调用后会生成一条待执行指令，由服务层执行。
    - file 为文件路径或 URL。
    - 仅私聊场景可用。
    """
    action = PendingSendPrivateFileAction(user_id=user_id, file=file)
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def send_group_file_message(group_id: int, file: str, name: str = "") -> str:
    """发送群文件消息。

    调用后会生成一条待执行指令，由服务层执行。
    - file 为文件路径或 URL。
    - name 为显示的文件名，为空时使用文件名。
    - 仅群聊场景可用。
    """
    action = PendingSendGroupFileMessageAction(
        group_id=group_id,
        file=file,
        name=name,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)

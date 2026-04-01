"""合并转发消息 skill 使用的 tools。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.skills.forward_message.types import (
    ForwardMessageNode,
    PendingSendForwardMessageAction,
)


@tool
def send_forward_message(
    target_id: int,
    nodes: list[dict[str, object]],
    is_group: bool = True,
) -> str:
    """发送合并转发消息。

    调用后会生成一条待执行指令，由服务层执行。
    - target_id 为目标群号或用户 QQ 号。
    - nodes 为消息节点列表，每个节点包含 user_id、nickname、content。
    - is_group=true 表示发送到群聊，false 表示发送到私聊。
    """
    parsed_nodes = tuple(
        ForwardMessageNode(
            user_id=int(node["user_id"]),
            nickname=str(node["nickname"]),
            content=str(node["content"]),
        )
        for node in nodes
    )
    action = PendingSendForwardMessageAction(
        target_id=target_id,
        nodes=parsed_nodes,
        is_group=is_group,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)

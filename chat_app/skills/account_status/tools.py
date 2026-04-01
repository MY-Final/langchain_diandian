"""账号状态 skill 使用的 tools。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.skills.account_status.types import (
    PendingSetDIYOnlineStatusAction,
    PendingSetOnlineStatusAction,
)


@tool
def set_online_status(status: int, ext_status: int = 0, battery_status: int = 0) -> str:
    """设置机器人在线状态。

    调用后会生成一条待执行指令，由服务层执行。
    - 该 skill 默认只对受信操作员开放。
    - 需要传入 NapCat 支持的 status / ext_status / battery_status 组合。
    """
    action = PendingSetOnlineStatusAction(
        status=int(status),
        ext_status=int(ext_status),
        battery_status=int(battery_status),
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def set_diy_online_status(face_id: int, face_type: int = 0, wording: str = "") -> str:
    """设置机器人自定义在线状态。

    调用后会生成一条待执行指令，由服务层执行。
    - face_id 为表情 ID。
    - wording 为展示文案。
    - 该 skill 默认只对受信操作员开放。
    """
    action = PendingSetDIYOnlineStatusAction(
        face_id=int(face_id),
        face_type=int(face_type),
        wording=wording.strip(),
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)

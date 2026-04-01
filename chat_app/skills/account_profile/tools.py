"""账号资料 skill 使用的 tools。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.skills.account_profile.types import (
    PendingSetQQAvatarAction,
    PendingSetQQProfileAction,
    PendingSetSelfLongNickAction,
)

_ALLOWED_SEX = {"male", "female", "unknown"}


@tool
def set_qq_profile(
    nickname: str,
    personal_note: str = "",
    sex: str = "unknown",
) -> str:
    """设置机器人账号资料。

    调用后会生成一条待执行指令，由服务层执行。
    - sex 仅支持 male/female/unknown。
    - 该 skill 默认只对受信操作员开放。
    """
    normalized_sex = sex.strip().lower() or "unknown"
    if normalized_sex not in _ALLOWED_SEX:
        normalized_sex = "unknown"
    action = PendingSetQQProfileAction(
        nickname=nickname.strip(),
        personal_note=personal_note.strip(),
        sex=normalized_sex,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def set_self_longnick(long_nick: str) -> str:
    """设置机器人个性签名。

    调用后会生成一条待执行指令，由服务层执行。
    - 该 skill 默认只对受信操作员开放。
    """
    action = PendingSetSelfLongNickAction(long_nick=long_nick.strip())
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def set_qq_avatar(file: str) -> str:
    """设置机器人头像。

    调用后会生成一条待执行指令，由服务层执行。
    - file 支持本地路径或 URL。
    - 该 skill 默认只对受信操作员开放。
    """
    action = PendingSetQQAvatarAction(file=file.strip())
    return json.dumps(action.to_dict(), ensure_ascii=False)

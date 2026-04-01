"""账号资料 skill。"""

from __future__ import annotations

from chat_app.skills.account_profile.tools import (
    set_qq_avatar,
    set_qq_profile,
    set_self_longnick,
)
from chat_app.skills.context import SkillContext
from chat_app.skills.types import SkillSpec


def _applies_to(context: SkillContext) -> bool:
    return context.is_private_message() and context.is_trusted_operator


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 你当前可使用账号资料管理能力，但只应在明确需要时调用。",
        "- 如需修改昵称/性别/资料，可调用 set_qq_profile 工具。",
        "- 如需修改个性签名，可调用 set_self_longnick 工具。",
        "- 如需修改头像，可调用 set_qq_avatar 工具，并确保 file 是明确可访问的路径或 URL。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return (set_qq_profile, set_self_longnick, set_qq_avatar)


ACCOUNT_PROFILE_SKILL = SkillSpec(
    name="account_profile",
    description="机器人账号资料与外观设置能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=70,
)

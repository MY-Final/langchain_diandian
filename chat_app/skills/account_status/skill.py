"""账号状态 skill。"""

from __future__ import annotations

from chat_app.skills.account_status.tools import (
    set_diy_online_status,
    set_online_status,
)
from chat_app.skills.context import SkillContext
from chat_app.skills.types import SkillSpec


def _applies_to(context: SkillContext) -> bool:
    return context.is_private_message() and context.is_trusted_operator


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 你当前可使用账号在线状态管理能力，但只应在明确需要时调用。",
        "- 如需设置标准在线状态，可调用 set_online_status 工具。",
        "- 如需设置自定义在线状态，可调用 set_diy_online_status 工具。",
        "- 这些状态值必须使用 NapCat 支持的组合，不要编造未知数字。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return (set_online_status, set_diy_online_status)


ACCOUNT_STATUS_SKILL = SkillSpec(
    name="account_status",
    description="机器人在线状态管理能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=60,
)

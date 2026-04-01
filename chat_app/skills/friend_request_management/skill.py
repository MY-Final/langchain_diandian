"""好友请求管理 skill。"""

from __future__ import annotations

from chat_app.skills.context import SkillContext
from chat_app.skills.friend_request_management.tools import set_friend_add_request
from chat_app.skills.types import SkillSpec


def _applies_to(context: SkillContext) -> bool:
    return context.is_private_message() and context.is_trusted_operator


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 你当前可使用好友请求处理能力，但只应在明确需要时调用。",
        "- 如需处理好友请求，可调用 set_friend_add_request 工具。",
        "- 处理好友请求时必须提供明确的 flag，不要编造。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return (set_friend_add_request,)


FRIEND_REQUEST_MANAGEMENT_SKILL = SkillSpec(
    name="friend_request_management",
    description="好友请求处理能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=75,
)

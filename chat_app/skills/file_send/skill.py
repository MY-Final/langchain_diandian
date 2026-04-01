"""文件发送 skill。"""

from __future__ import annotations

from chat_app.skills.context import SkillContext
from chat_app.skills.file_send.tools import (
    send_group_file_message,
    send_private_file,
)
from chat_app.skills.types import SkillSpec


def _applies_to(_context: SkillContext) -> bool:
    return True


def _build_rules(context: SkillContext) -> tuple[str, ...]:
    rules: list[str] = []
    if context.is_private_message():
        rules.append(
            "- 如需发送文件给用户，可调用 send_private_file 工具（需传入 user_id 和 file）。"
        )
    if context.is_group_message():
        rules.append(
            "- 如需在群内发送文件消息，可调用 send_group_file_message 工具（需传入 group_id 和 file）。"
        )
    return tuple(rules)


def _build_tools(context: SkillContext) -> tuple:
    tools: list = []
    if context.is_private_message():
        tools.append(send_private_file)
    if context.is_group_message():
        tools.append(send_group_file_message)
    return tuple(tools)


FILE_SEND_SKILL = SkillSpec(
    name="file_send",
    description="文件发送能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=100,
)

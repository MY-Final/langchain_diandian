"""Skill 注册表。"""

from __future__ import annotations

from collections import OrderedDict

from langchain_core.tools import BaseTool

from chat_app.skills.account_profile import ACCOUNT_PROFILE_SKILL
from chat_app.skills.account_status import ACCOUNT_STATUS_SKILL
from chat_app.skills.contact_discovery import CONTACT_DISCOVERY_SKILL
from chat_app.skills.context import SkillContext
from chat_app.skills.friend_management import FRIEND_MANAGEMENT_SKILL
from chat_app.skills.friend_request_management import FRIEND_REQUEST_MANAGEMENT_SKILL
from chat_app.skills.group_inspection import GROUP_INSPECTION_SKILL
from chat_app.skills.group_moderation import GROUP_MODERATION_SKILL
from chat_app.skills.memory_recall import MEMORY_RECALL_SKILL
from chat_app.skills.message_state import MESSAGE_STATE_SKILL
from chat_app.skills.message_expression import MESSAGE_EXPRESSION_SKILL
from chat_app.skills.types import SkillRuntime, SkillSpec


class SkillRegistry:
    """根据上下文选择可用 skill。"""

    def __init__(self, skills: tuple[SkillSpec, ...] | None = None) -> None:
        self._skills = tuple(skills or _default_skills())

    def resolve(
        self, context: SkillContext, *, sender: object | None = None
    ) -> SkillRuntime:
        enabled = sorted(
            (skill for skill in self._skills if skill.applies_to(context)),
            key=lambda item: item.priority,
        )

        ordered_tools: OrderedDict[str, BaseTool] = OrderedDict()
        rules: list[str] = []
        for skill in enabled:
            for tool in skill.build_tools(context):
                ordered_tools.setdefault(tool.name, tool)
            if sender is not None and skill.build_runtime_tools is not None:
                for tool in skill.build_runtime_tools(context, sender):
                    ordered_tools.setdefault(tool.name, tool)
            rules.extend(skill.build_rules(context))

        return SkillRuntime(
            skill_names=tuple(skill.name for skill in enabled),
            tools=tuple(ordered_tools.values()),
            rules=tuple(rules),
        )


def resolve_skill_runtime(
    context: SkillContext, *, sender: object | None = None
) -> SkillRuntime:
    return SkillRegistry().resolve(context, sender=sender)


def _default_skills() -> tuple[SkillSpec, ...]:
    return (
        MESSAGE_EXPRESSION_SKILL,
        MEMORY_RECALL_SKILL,
        CONTACT_DISCOVERY_SKILL,
        GROUP_INSPECTION_SKILL,
        ACCOUNT_PROFILE_SKILL,
        ACCOUNT_STATUS_SKILL,
        FRIEND_MANAGEMENT_SKILL,
        FRIEND_REQUEST_MANAGEMENT_SKILL,
        MESSAGE_STATE_SKILL,
        GROUP_MODERATION_SKILL,
    )

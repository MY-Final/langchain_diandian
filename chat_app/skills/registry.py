"""Skill 注册表。"""

from __future__ import annotations

from collections import OrderedDict

from langchain_core.tools import BaseTool

from chat_app.skills.context import SkillContext
from chat_app.skills.group_moderation import GROUP_MODERATION_SKILL
from chat_app.skills.memory_recall import MEMORY_RECALL_SKILL
from chat_app.skills.message_expression import MESSAGE_EXPRESSION_SKILL
from chat_app.skills.types import SkillRuntime, SkillSpec


class SkillRegistry:
    """根据上下文选择可用 skill。"""

    def __init__(self, skills: tuple[SkillSpec, ...] | None = None) -> None:
        self._skills = tuple(skills or _default_skills())

    def resolve(self, context: SkillContext) -> SkillRuntime:
        enabled = sorted(
            (skill for skill in self._skills if skill.applies_to(context)),
            key=lambda item: item.priority,
        )

        ordered_tools: OrderedDict[str, BaseTool] = OrderedDict()
        rules: list[str] = []
        for skill in enabled:
            for tool in skill.build_tools(context):
                ordered_tools.setdefault(tool.name, tool)
            rules.extend(skill.build_rules(context))

        return SkillRuntime(
            skill_names=tuple(skill.name for skill in enabled),
            tools=tuple(ordered_tools.values()),
            rules=tuple(rules),
        )


def resolve_skill_runtime(context: SkillContext) -> SkillRuntime:
    return SkillRegistry().resolve(context)


def _default_skills() -> tuple[SkillSpec, ...]:
    return (
        MESSAGE_EXPRESSION_SKILL,
        MEMORY_RECALL_SKILL,
        GROUP_MODERATION_SKILL,
    )

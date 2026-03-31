"""记忆召回 skill。"""

from __future__ import annotations

from chat_app.skills.context import SkillContext
from chat_app.skills.types import SkillSpec


def _applies_to(_context: SkillContext) -> bool:
    return True


def _build_rules(context: SkillContext) -> tuple[str, ...]:
    if context.is_group_message():
        return ("- 回复时注意保持与该群既有上下文和长期约束一致。",)
    return ("- 回复时注意保持与该用户既有上下文和长期偏好一致。",)


def _build_tools(_context: SkillContext) -> tuple:
    return ()


MEMORY_RECALL_SKILL = SkillSpec(
    name="memory_recall",
    description="短期/长期记忆一致性约束。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=20,
)

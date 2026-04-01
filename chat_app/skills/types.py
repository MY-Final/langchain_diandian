"""Skill 数据结构。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.tools import BaseTool

from chat_app.skills.context import SkillContext


RulesBuilder = Callable[[SkillContext], tuple[str, ...]]
ToolsBuilder = Callable[[SkillContext], tuple[BaseTool, ...]]
RuntimeToolsBuilder = Callable[[SkillContext, Any], tuple[BaseTool, ...]]
AppliesTo = Callable[[SkillContext], bool]


@dataclass(frozen=True)
class SkillSpec:
    """单个 skill 的静态定义。"""

    name: str
    description: str
    applies_to: AppliesTo
    build_rules: RulesBuilder
    build_tools: ToolsBuilder
    build_runtime_tools: RuntimeToolsBuilder | None = None
    priority: int = 100


@dataclass(frozen=True)
class SkillRuntime:
    """某次请求实际启用的 skill 集合。"""

    skill_names: tuple[str, ...]
    tools: tuple[BaseTool, ...]
    rules: tuple[str, ...]

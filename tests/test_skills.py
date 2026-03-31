"""Skill 注册与选择测试。"""

from __future__ import annotations

import unittest

from chat_app.skills.context import SkillContext
from chat_app.skills.registry import resolve_skill_runtime


class SkillRegistryTests(unittest.TestCase):
    """验证 skill 按场景启用。"""

    def test_private_context_excludes_group_moderation_tools(self) -> None:
        runtime = resolve_skill_runtime(
            SkillContext(session_kind="private", user_id=12345)
        )

        self.assertIn("message_expression", runtime.skill_names)
        self.assertIn("memory_recall", runtime.skill_names)
        self.assertNotIn("group_moderation", runtime.skill_names)
        tool_names = {tool.name for tool in runtime.tools}
        self.assertNotIn("mute_group_member", tool_names)
        self.assertNotIn("set_group_admin", tool_names)

    def test_group_context_includes_group_moderation_tools(self) -> None:
        runtime = resolve_skill_runtime(
            SkillContext(session_kind="group", user_id=12345, group_id=67890)
        )

        self.assertIn("group_moderation", runtime.skill_names)
        tool_names = {tool.name for tool in runtime.tools}
        self.assertIn("mute_group_member", tool_names)
        self.assertIn("set_group_admin", tool_names)
        self.assertIn("kick_group_member", tool_names)
        self.assertTrue(runtime.rules)


if __name__ == "__main__":
    unittest.main()

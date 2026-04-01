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

    def test_group_context_without_live_sender_excludes_group_inspection(self) -> None:
        runtime = resolve_skill_runtime(
            SkillContext(
                session_kind="group",
                user_id=12345,
                group_id=67890,
                supports_live_onebot_queries=True,
            )
        )

        tool_names = {tool.name for tool in runtime.tools}
        self.assertNotIn("get_group_list", tool_names)
        self.assertNotIn("get_group_detail", tool_names)

    def test_private_non_operator_excludes_private_account_skills(self) -> None:
        runtime = resolve_skill_runtime(
            SkillContext(
                session_kind="private", user_id=12345, is_trusted_operator=False
            )
        )

        self.assertNotIn("friend_management", runtime.skill_names)
        self.assertNotIn("account_profile", runtime.skill_names)
        tool_names = {tool.name for tool in runtime.tools}
        self.assertNotIn("send_like", tool_names)
        self.assertNotIn("set_qq_profile", tool_names)

    def test_private_operator_includes_private_account_skills(self) -> None:
        runtime = resolve_skill_runtime(
            SkillContext(
                session_kind="private", user_id=12345, is_trusted_operator=True
            )
        )

        self.assertIn("friend_management", runtime.skill_names)
        self.assertIn("account_profile", runtime.skill_names)
        self.assertIn("account_status", runtime.skill_names)
        self.assertIn("friend_request_management", runtime.skill_names)
        self.assertIn("message_state", runtime.skill_names)
        tool_names = {tool.name for tool in runtime.tools}
        self.assertIn("send_like", tool_names)
        self.assertIn("delete_friend", tool_names)
        self.assertIn("set_qq_profile", tool_names)
        self.assertIn("set_self_longnick", tool_names)
        self.assertIn("set_qq_avatar", tool_names)
        self.assertIn("set_online_status", tool_names)
        self.assertIn("set_diy_online_status", tool_names)
        self.assertIn("set_friend_add_request", tool_names)
        self.assertIn("mark_conversation_read", tool_names)

    def test_private_operator_with_live_sender_includes_contact_discovery(self) -> None:
        class _Sender:
            async def get_recent_contact(self, count: int = 10) -> list[dict]:
                return []

            async def get_friend_list(self, *, no_cache: bool = True) -> list[dict]:
                return []

            async def get_friends_with_category(self) -> list[dict]:
                return []

            async def get_stranger_info(self, user_id: int | str) -> dict | None:
                return None

        runtime = resolve_skill_runtime(
            SkillContext(
                session_kind="private",
                user_id=12345,
                is_trusted_operator=True,
                supports_live_onebot_queries=True,
            ),
            sender=_Sender(),
        )

        self.assertIn("contact_discovery", runtime.skill_names)
        tool_names = {tool.name for tool in runtime.tools}
        self.assertIn("lookup_contacts", tool_names)
        self.assertIn("get_contact_profile", tool_names)


if __name__ == "__main__":
    unittest.main()

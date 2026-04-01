"""群文件管理 skill。"""

from __future__ import annotations

from chat_app.skills.context import SkillContext
from chat_app.skills.group_file.tools import (
    delete_group_file,
    get_group_files,
    upload_group_file,
)
from chat_app.skills.types import SkillSpec


def _applies_to(context: SkillContext) -> bool:
    return context.is_group_message()


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 如需上传群文件，可调用 upload_group_file 工具（需传入 group_id、file 和 name）。",
        "- 如需查看群文件列表，可调用 get_group_files 工具（需传入 group_id）。",
        "- 如需删除群文件，可调用 delete_group_file 工具（需传入 group_id 和 file_id）。",
        "- 删除文件需要群主或管理员权限。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return (
        upload_group_file,
        get_group_files,
        delete_group_file,
    )


GROUP_FILE_SKILL = SkillSpec(
    name="group_file",
    description="群文件管理能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=100,
)

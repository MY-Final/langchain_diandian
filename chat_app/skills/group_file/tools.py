"""群文件管理 skill 使用的 tools。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from chat_app.skills.group_file.types import (
    PendingDeleteGroupFileAction,
    PendingGetGroupFilesAction,
    PendingUploadGroupFileAction,
)


@tool
def upload_group_file(group_id: int, file: str, name: str, folder: str = "") -> str:
    """上传群文件。

    调用后会生成一条待执行指令，由服务层执行。
    - file 为文件路径或 URL。
    - name 为文件名。
    - folder 为目标文件夹 ID，默认为根目录。
    - 仅群聊场景可用。
    """
    action = PendingUploadGroupFileAction(
        group_id=group_id,
        file=file,
        name=name,
        folder=folder,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def get_group_files(group_id: int, folder_id: str = "") -> str:
    """获取群文件列表。

    调用后会生成一条待执行指令，由服务层执行。
    - folder_id 为空时获取根目录文件。
    - 仅群聊场景可用。
    """
    action = PendingGetGroupFilesAction(
        group_id=group_id,
        folder_id=folder_id,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)


@tool
def delete_group_file(group_id: int, file_id: str) -> str:
    """删除群文件。

    调用后会生成一条待执行指令，由服务层执行。
    - file_id 为要删除的文件 ID。
    - 仅群聊场景可用，需要群主或管理员权限。
    """
    action = PendingDeleteGroupFileAction(
        group_id=group_id,
        file_id=file_id,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)

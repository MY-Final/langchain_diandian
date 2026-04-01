"""群文件管理技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingUploadGroupFileAction:
    """待执行的上传群文件动作。"""

    group_id: int
    file: str
    name: str
    folder: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "upload_group_file",
            "group_id": self.group_id,
            "file": self.file,
            "name": self.name,
            "folder": self.folder,
        }


@dataclass(frozen=True)
class PendingGetGroupFilesAction:
    """待执行的获取群文件列表动作。"""

    group_id: int
    folder_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "get_group_files",
            "group_id": self.group_id,
            "folder_id": self.folder_id,
        }


@dataclass(frozen=True)
class PendingDeleteGroupFileAction:
    """待执行的删除群文件动作。"""

    group_id: int
    file_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "delete_group_file",
            "group_id": self.group_id,
            "file_id": self.file_id,
        }


PendingAction = (
    PendingUploadGroupFileAction
    | PendingGetGroupFilesAction
    | PendingDeleteGroupFileAction
)

"""文件发送技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingSendPrivateFileAction:
    """待执行的发送私聊文件动作。"""

    user_id: int
    file: str

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "send_private_file",
            "user_id": self.user_id,
            "file": self.file,
        }


@dataclass(frozen=True)
class PendingSendGroupFileMessageAction:
    """待执行的发送群文件消息动作。"""

    group_id: int
    file: str
    name: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "send_group_file_message",
            "group_id": self.group_id,
            "file": self.file,
            "name": self.name,
        }


PendingAction = PendingSendPrivateFileAction | PendingSendGroupFileMessageAction

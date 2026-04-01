"""账号资料技能的数据类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingSetQQProfileAction:
    """待执行的账号资料设置动作。"""

    nickname: str
    personal_note: str
    sex: str

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "set_qq_profile",
            "nickname": self.nickname,
            "personal_note": self.personal_note,
            "sex": self.sex,
        }


@dataclass(frozen=True)
class PendingSetSelfLongNickAction:
    """待执行的个性签名设置动作。"""

    long_nick: str

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "set_self_longnick",
            "long_nick": self.long_nick,
        }


@dataclass(frozen=True)
class PendingSetQQAvatarAction:
    """待执行的头像设置动作。"""

    file: str

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "set_qq_avatar",
            "file": self.file,
        }

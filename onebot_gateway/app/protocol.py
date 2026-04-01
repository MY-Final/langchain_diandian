"""OneBot 消息发送协议。"""

from __future__ import annotations

from typing import Any, Protocol


class ChatMessageSender(Protocol):
    """发送 OneBot 消息的协议。"""

    async def send_private_message(self, user_id: int | str, message: object) -> object:
        """发送私聊消息。"""

    async def send_group_message(self, group_id: int | str, message: object) -> object:
        """发送群聊消息。"""

    async def get_group_member_info(
        self, group_id: int | str, user_id: int | str, *, no_cache: bool = True
    ) -> dict[str, Any] | None:
        """获取群成员信息。"""

    async def get_recent_contact(self, count: int = 10) -> list[dict[str, Any]]:
        """获取最近联系人列表。"""

    async def get_stranger_info(self, user_id: int | str) -> dict[str, Any] | None:
        """获取账号信息。"""

    async def get_friend_list(self, *, no_cache: bool = True) -> list[dict[str, Any]]:
        """获取好友列表。"""

    async def get_friends_with_category(self) -> list[dict[str, Any]]:
        """获取好友分组列表。"""

    async def set_group_ban(
        self, group_id: int | str, user_id: int | str, duration: int = 0
    ) -> dict[str, Any]:
        """群禁言。"""

    async def set_group_admin(
        self, group_id: int | str, user_id: int | str, enable: bool = True
    ) -> dict[str, Any]:
        """设置或取消群管理员。"""

    async def set_group_kick(
        self,
        group_id: int | str,
        user_id: int | str,
        reject_add_request: bool = False,
    ) -> dict[str, Any]:
        """群踢人。"""

    async def set_group_card(
        self, group_id: int | str, user_id: int | str, card: str = ""
    ) -> dict[str, Any]:
        """设置或清空群名片。"""

    async def set_group_special_title(
        self, group_id: int | str, user_id: int | str, special_title: str = ""
    ) -> dict[str, Any]:
        """设置或清空群头衔。"""

    async def send_like(self, user_id: int | str, times: int = 1) -> dict[str, Any]:
        """点赞。"""

    async def delete_friend(
        self,
        user_id: int | str,
        *,
        temp_block: bool = True,
        temp_both_del: bool = False,
    ) -> dict[str, Any]:
        """删除好友。"""

    async def set_qq_profile(
        self,
        *,
        nickname: str,
        personal_note: str = "",
        sex: str = "unknown",
    ) -> dict[str, Any]:
        """设置账号资料。"""

    async def set_self_longnick(self, long_nick: str) -> dict[str, Any]:
        """设置个性签名。"""

    async def set_qq_avatar(self, file: str) -> dict[str, Any]:
        """设置头像。"""

    async def set_online_status(
        self, status: int, ext_status: int = 0, battery_status: int = 0
    ) -> dict[str, Any]:
        """设置在线状态。"""

    async def set_diy_online_status(
        self, face_id: int, face_type: int = 0, wording: str = ""
    ) -> dict[str, Any]:
        """设置自定义在线状态。"""

    async def set_friend_add_request(
        self, flag: str, approve: bool = True, remark: str = ""
    ) -> dict[str, Any]:
        """处理好友请求。"""

    async def mark_private_msg_as_read(self, user_id: int | str) -> dict[str, Any]:
        """设置私聊已读。"""

    async def mark_group_msg_as_read(self, group_id: int | str) -> dict[str, Any]:
        """设置群聊已读。"""

    async def mark_all_as_read(self) -> dict[str, Any]:
        """设置所有消息已读。"""

    async def recall_message(self, message_id: int | str) -> dict[str, Any]:
        """撤回消息。"""

    async def _send_group_notice(
        self, group_id: int | str, content: str, is_pinned: bool = True
    ) -> dict[str, Any]:
        """发送群公告。"""

    async def _get_group_notice(self, group_id: int | str) -> dict[str, Any]:
        """获取群公告。"""

    async def upload_group_file(
        self, group_id: int | str, file: str, name: str, folder: str = ""
    ) -> dict[str, Any]:
        """上传群文件。"""

    async def get_group_files(
        self, group_id: int | str, folder_id: str = ""
    ) -> dict[str, Any]:
        """获取群文件列表。"""

    async def delete_group_file(
        self, group_id: int | str, file_id: str
    ) -> dict[str, Any]:
        """删除群文件。"""

    async def set_essence_msg(self, message_id: int | str) -> dict[str, Any]:
        """设置精华消息。"""

    async def delete_essence_msg(self, message_id: int | str) -> dict[str, Any]:
        """移除精华消息。"""

    async def get_essence_msg_list(self, group_id: int | str) -> dict[str, Any]:
        """获取精华消息列表。"""

    async def upload_private_file(
        self, user_id: int | str, file: str, name: str = ""
    ) -> dict[str, Any]:
        """发送私聊文件。"""

    async def send_group_forward_message(
        self, group_id: int | str, messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """发送群合并转发消息。"""

    async def send_private_forward_message(
        self, user_id: int | str, messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """发送私聊合并转发消息。"""

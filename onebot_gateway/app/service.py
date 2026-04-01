"""OneBot 与 LangChain 的应用服务。"""

from __future__ import annotations

import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol

from chat_app.skills.account_profile import (
    PendingSetQQAvatarAction,
    PendingSetQQProfileAction,
    PendingSetSelfLongNickAction,
)
from chat_app.skills.account_status import (
    PendingSetDIYOnlineStatusAction,
    PendingSetOnlineStatusAction,
)
from chat_app.skills.contact_discovery import CONTACT_DISCOVERY_SKILL
from chat_app.skills.friend_request_management import (
    PendingSetFriendAddRequestAction,
)
from chat_app.skills.group_moderation import (
    PendingAction,
    PendingKickGroupMemberAction,
    PendingMuteAction,
    PendingSetGroupAdminAction,
    PendingSetGroupCardAction,
    PendingSetGroupSpecialTitleAction,
)
from chat_app.skills.friend_management import (
    PendingDeleteFriendAction,
    PendingSendLikeAction,
)
from chat_app.skills.message_state import PendingMarkConversationReadAction
from chat_app.skills.message_recall import PendingRecallMessageAction
from chat_app.skills.group_announcement import (
    PendingGetGroupNoticeAction,
    PendingSendGroupNoticeAction,
)
from chat_app.skills.group_file import (
    PendingDeleteGroupFileAction,
    PendingGetGroupFilesAction,
    PendingUploadGroupFileAction,
)
from chat_app.skills.essence_message import (
    PendingAddEssenceMessageAction,
    PendingGetEssenceMessageListAction,
    PendingRemoveEssenceMessageAction,
)
from chat_app.skills.file_send import (
    PendingSendGroupFileMessageAction,
    PendingSendPrivateFileAction,
)
from chat_app.skills.forward_message import PendingSendForwardMessageAction
from chat_app.chat import ChatSession, ToolCallTrace
from chat_app.config import AppConfig, load_config
from chat_app.skills.context import SkillContext
from chat_app.skills.registry import resolve_skill_runtime
from onebot_gateway.config import ReplySplitConfig
from onebot_gateway.message.adapter import (
    AgentInput,
    build_agent_input,
)
from onebot_gateway.message.parser import ParsedMessageEvent
from onebot_gateway.message.rich_reply import build_rich_text_reply
from onebot_gateway.message.reply_splitter import ReplySplitter
from onebot_gateway.message.trigger import TriggerDecision

logger = logging.getLogger(__name__)

_ROLE_PRIORITY: dict[str, int] = {"owner": 3, "admin": 2, "member": 1}
_TRUSTED_PRIVATE_ACTIONS = {
    "send_like",
    "delete_friend",
    "set_qq_profile",
    "set_self_longnick",
    "set_qq_avatar",
    "set_online_status",
    "set_diy_online_status",
    "set_friend_add_request",
    "mark_conversation_read",
}

PendingCommand = (
    PendingAction
    | PendingSendLikeAction
    | PendingDeleteFriendAction
    | PendingSetQQProfileAction
    | PendingSetSelfLongNickAction
    | PendingSetQQAvatarAction
    | PendingSetOnlineStatusAction
    | PendingSetDIYOnlineStatusAction
    | PendingSetFriendAddRequestAction
    | PendingMarkConversationReadAction
    | PendingRecallMessageAction
    | PendingSendGroupNoticeAction
    | PendingGetGroupNoticeAction
    | PendingUploadGroupFileAction
    | PendingGetGroupFilesAction
    | PendingDeleteGroupFileAction
    | PendingAddEssenceMessageAction
    | PendingGetEssenceMessageListAction
    | PendingRemoveEssenceMessageAction
    | PendingSendPrivateFileAction
    | PendingSendGroupFileMessageAction
    | PendingSendForwardMessageAction
)


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


@dataclass
class ActionResult:
    """单条动作执行结果。"""

    action: str
    success: bool
    message: str

    def to_dict(self) -> dict[str, object]:
        return {"action": self.action, "success": self.success, "message": self.message}


@dataclass
class ChatHandleResult:
    """消息处理结果。"""

    should_reply: bool
    reply_text: str
    reply_parts: tuple[str, ...]
    tool_traces: tuple[ToolCallTrace, ...]
    agent_input: AgentInput
    action_results: tuple[ActionResult, ...] = ()


DEFAULT_REPLY_SPLIT_CONFIG = ReplySplitConfig(
    enabled=True,
    max_chars=180,
    marker="[SPLIT]",
)


class ChatService:
    """处理 OneBot 消息并调用 LangChain 回复。"""

    def __init__(
        self,
        config: AppConfig,
        *,
        reply_with_quote: bool = True,
        reply_split_config: ReplySplitConfig = DEFAULT_REPLY_SPLIT_CONFIG,
    ) -> None:
        self._config = config
        self._reply_with_quote = reply_with_quote
        self._reply_splitter = ReplySplitter(reply_split_config)
        self._sessions: dict[tuple[str, int], ChatSession] = {}

    @classmethod
    def from_env(
        cls,
        *,
        reply_with_quote: bool = True,
        reply_split_config: ReplySplitConfig = DEFAULT_REPLY_SPLIT_CONFIG,
    ) -> ChatService:
        """从环境变量加载 LangChain 配置。"""
        return cls(
            load_config(),
            reply_with_quote=reply_with_quote,
            reply_split_config=reply_split_config,
        )

    async def handle_event(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        decision: TriggerDecision,
    ) -> ChatHandleResult:
        """处理消息并在需要时回消息。"""
        agent_input = build_agent_input(event, decision)
        if not decision.should_process:
            return ChatHandleResult(
                should_reply=False,
                reply_text="",
                reply_parts=(),
                tool_traces=(),
                agent_input=agent_input,
            )

        session = self._get_session(event)
        skill_runtime = resolve_skill_runtime(
            self._build_skill_context(event), sender=sender
        )
        aask = getattr(session, "aask", None)
        if callable(aask):
            reply_text = await aask(
                self._build_model_input(event, agent_input, skill_runtime.rules),
                runtime_tools=skill_runtime.tools,
                runtime_rules=skill_runtime.rules,
            )
        else:
            reply_text = session.ask(
                self._build_model_input(event, agent_input, skill_runtime.rules),
                runtime_tools=skill_runtime.tools,
                runtime_rules=skill_runtime.rules,
            )
        reply_parts = tuple(self._reply_splitter.split(reply_text))
        get_last_tool_traces = getattr(session, "get_last_tool_traces", None)
        tool_traces = (
            tuple(get_last_tool_traces()) if callable(get_last_tool_traces) else ()
        )
        if not reply_parts:
            reply_parts = (reply_text,)

        pending_actions = self._collect_pending_actions(session)
        action_results: tuple[ActionResult, ...] = ()
        if pending_actions:
            action_results = await self._execute_pending_actions(
                sender, event, pending_actions
            )

        if event.is_private_message():
            assert event.user_id is not None
            await self._send_reply_parts(
                send=sender.send_private_message,
                target_id=event.user_id,
                reply_parts=reply_parts,
                reply_message_id=self._get_reply_message_id(event),
            )
        elif event.is_group_message():
            assert event.group_id is not None
            await self._send_reply_parts(
                send=sender.send_group_message,
                target_id=event.group_id,
                reply_parts=reply_parts,
                reply_message_id=self._get_reply_message_id(event),
            )
        else:
            return ChatHandleResult(
                should_reply=False,
                reply_text="",
                reply_parts=(),
                tool_traces=tool_traces,
                agent_input=agent_input,
                action_results=action_results,
            )

        return ChatHandleResult(
            should_reply=True,
            reply_text=reply_text,
            reply_parts=reply_parts,
            tool_traces=tool_traces,
            agent_input=agent_input,
            action_results=action_results,
        )

    async def _send_reply_parts(
        self,
        *,
        send: Callable[[int | str, object], Awaitable[object]],
        target_id: int | str,
        reply_parts: tuple[str, ...],
        reply_message_id: int | None,
    ) -> None:
        for index, part in enumerate(reply_parts):
            quoted_message_id = reply_message_id if index == 0 else None
            await send(
                target_id,
                build_rich_text_reply(part, reply_message_id=quoted_message_id),
            )

    @staticmethod
    def _collect_pending_actions(
        session: ChatSession,
    ) -> tuple[PendingCommand, ...]:
        getter = getattr(session, "get_pending_actions", None)
        if not callable(getter):
            return ()
        return tuple(getter())

    async def _execute_pending_actions(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        actions: tuple[PendingCommand, ...],
    ) -> tuple[ActionResult, ...]:
        results: list[ActionResult] = []
        bot_user_id = event.self_id
        for action in actions:
            if isinstance(action, PendingMuteAction):
                result = await self._execute_mute_action(sender, action, bot_user_id)
            elif isinstance(action, PendingSetGroupAdminAction):
                result = await self._execute_set_group_admin_action(
                    sender, action, bot_user_id
                )
            elif isinstance(action, PendingKickGroupMemberAction):
                result = await self._execute_kick_action(sender, action, bot_user_id)
            elif isinstance(action, PendingSetGroupCardAction):
                result = await self._execute_set_group_card_action(
                    sender, action, bot_user_id
                )
            elif isinstance(action, PendingSetGroupSpecialTitleAction):
                result = await self._execute_set_group_special_title_action(
                    sender, action, bot_user_id
                )
            elif isinstance(action, PendingSendLikeAction):
                result = await self._execute_send_like_action(sender, event, action)
            elif isinstance(action, PendingDeleteFriendAction):
                result = await self._execute_delete_friend_action(sender, event, action)
            elif isinstance(action, PendingSetQQProfileAction):
                result = await self._execute_set_qq_profile_action(
                    sender, event, action
                )
            elif isinstance(action, PendingSetSelfLongNickAction):
                result = await self._execute_set_self_longnick_action(
                    sender, event, action
                )
            elif isinstance(action, PendingSetQQAvatarAction):
                result = await self._execute_set_qq_avatar_action(sender, event, action)
            elif isinstance(action, PendingSetOnlineStatusAction):
                result = await self._execute_set_online_status_action(
                    sender, event, action
                )
            elif isinstance(action, PendingSetDIYOnlineStatusAction):
                result = await self._execute_set_diy_online_status_action(
                    sender, event, action
                )
            elif isinstance(action, PendingSetFriendAddRequestAction):
                result = await self._execute_set_friend_add_request_action(
                    sender, event, action
                )
            elif isinstance(action, PendingMarkConversationReadAction):
                result = await self._execute_mark_conversation_read_action(
                    sender, event, action
                )
            elif isinstance(action, PendingRecallMessageAction):
                result = await self._execute_recall_message_action(sender, action)
            elif isinstance(action, PendingSendGroupNoticeAction):
                result = await self._execute_send_group_notice_action(
                    sender, event, action
                )
            elif isinstance(action, PendingGetGroupNoticeAction):
                result = await self._execute_get_group_notice_action(
                    sender, event, action
                )
            elif isinstance(action, PendingUploadGroupFileAction):
                result = await self._execute_upload_group_file_action(
                    sender, event, action
                )
            elif isinstance(action, PendingGetGroupFilesAction):
                result = await self._execute_get_group_files_action(
                    sender, event, action
                )
            elif isinstance(action, PendingDeleteGroupFileAction):
                result = await self._execute_delete_group_file_action(
                    sender, event, action
                )
            elif isinstance(action, PendingAddEssenceMessageAction):
                result = await self._execute_add_essence_message_action(
                    sender, event, action
                )
            elif isinstance(action, PendingRemoveEssenceMessageAction):
                result = await self._execute_remove_essence_message_action(
                    sender, event, action
                )
            elif isinstance(action, PendingGetEssenceMessageListAction):
                result = await self._execute_get_essence_message_list_action(
                    sender, event, action
                )
            elif isinstance(action, PendingSendPrivateFileAction):
                result = await self._execute_send_private_file_action(
                    sender, event, action
                )
            elif isinstance(action, PendingSendGroupFileMessageAction):
                result = await self._execute_send_group_file_message_action(
                    sender, event, action
                )
            elif isinstance(action, PendingSendForwardMessageAction):
                result = await self._execute_send_forward_message_action(
                    sender, event, action
                )
            else:
                result = ActionResult(
                    action="unknown",
                    success=False,
                    message=f"未知 action 类型: {type(action).__name__}",
                )
            results.append(result)
            if not result.success:
                logger.warning("群管动作执行失败: %s", result.message)
        return tuple(results)

    async def _execute_mute_action(
        self,
        sender: ChatMessageSender,
        action: PendingMuteAction,
        bot_user_id: int | None,
    ) -> ActionResult:
        target_info = await sender.get_group_member_info(
            action.group_id, action.user_id
        )
        if target_info is None:
            return ActionResult(
                action="mute_group_member",
                success=False,
                message="无法获取目标成员信息。",
            )

        target_role = str(target_info.get("role", "member"))

        if bot_user_id is None:
            return ActionResult(
                action="mute_group_member",
                success=False,
                message="无法确认机器人身份。",
            )

        bot_info = await sender.get_group_member_info(action.group_id, bot_user_id)
        if bot_info is None:
            return ActionResult(
                action="mute_group_member",
                success=False,
                message="无法获取机器人自身群成员信息。",
            )

        bot_role = str(bot_info.get("role", "member"))

        if not _can_operate(bot_role, target_role):
            return ActionResult(
                action="mute_group_member",
                success=False,
                message=f"权限不足：{bot_role} 无法禁言 {target_role}。",
            )

        await sender.set_group_ban(action.group_id, action.user_id, action.duration)

        if action.duration == 0:
            desc = "已解除禁言"
        else:
            desc = f"已禁言 {action.duration} 秒"

        return ActionResult(
            action="mute_group_member",
            success=True,
            message=f"{desc}（目标 {action.user_id}）。",
        )

    async def _execute_set_group_admin_action(
        self,
        sender: ChatMessageSender,
        action: PendingSetGroupAdminAction,
        bot_user_id: int | None,
    ) -> ActionResult:
        if bot_user_id is None:
            return ActionResult(
                action="set_group_admin",
                success=False,
                message="无法确认机器人身份。",
            )

        bot_info = await sender.get_group_member_info(action.group_id, bot_user_id)
        if bot_info is None:
            return ActionResult(
                action="set_group_admin",
                success=False,
                message="无法获取机器人自身群成员信息。",
            )

        bot_role = str(bot_info.get("role", "member"))
        if bot_role != "owner":
            return ActionResult(
                action="set_group_admin",
                success=False,
                message=f"权限不足：{bot_role} 无法设置群管理员。",
            )

        target_info = await sender.get_group_member_info(
            action.group_id, action.user_id
        )
        if target_info is None:
            return ActionResult(
                action="set_group_admin",
                success=False,
                message="无法获取目标成员信息。",
            )

        target_role = str(target_info.get("role", "member"))
        if action.enable and target_role == "owner":
            return ActionResult(
                action="set_group_admin",
                success=False,
                message="群主不能被设置为管理员。",
            )

        await sender.set_group_admin(action.group_id, action.user_id, action.enable)

        desc = "已设置群管理员" if action.enable else "已取消群管理员"
        return ActionResult(
            action="set_group_admin",
            success=True,
            message=f"{desc}（目标 {action.user_id}）。",
        )

    async def _execute_kick_action(
        self,
        sender: ChatMessageSender,
        action: PendingKickGroupMemberAction,
        bot_user_id: int | None,
    ) -> ActionResult:
        (
            target_info,
            bot_role,
            target_role,
            error,
        ) = await self._load_roles_for_targeted_action(
            sender, action.group_id, action.user_id, bot_user_id
        )
        if error is not None:
            return error
        assert target_info is not None
        assert bot_role is not None
        assert target_role is not None

        if not _can_operate(bot_role, target_role):
            return ActionResult(
                action="kick_group_member",
                success=False,
                message=f"权限不足：{bot_role} 无法踢出 {target_role}。",
            )

        await sender.set_group_kick(
            action.group_id, action.user_id, action.reject_add_request
        )
        return ActionResult(
            action="kick_group_member",
            success=True,
            message=f"已踢出成员 {action.user_id}。",
        )

    async def _execute_set_group_card_action(
        self,
        sender: ChatMessageSender,
        action: PendingSetGroupCardAction,
        bot_user_id: int | None,
    ) -> ActionResult:
        (
            target_info,
            bot_role,
            target_role,
            error,
        ) = await self._load_roles_for_targeted_action(
            sender, action.group_id, action.user_id, bot_user_id
        )
        if error is not None:
            return _with_action(error, "set_group_card")
        assert target_info is not None
        assert bot_role is not None
        assert target_role is not None

        if not _can_operate(bot_role, target_role):
            return ActionResult(
                action="set_group_card",
                success=False,
                message=f"权限不足：{bot_role} 无法修改 {target_role} 的群名片。",
            )

        await sender.set_group_card(action.group_id, action.user_id, action.card)
        desc = "已清空群名片" if not action.card else f"已设置群名片为 {action.card}"
        return ActionResult(
            action="set_group_card",
            success=True,
            message=f"{desc}（目标 {action.user_id}）。",
        )

    async def _execute_set_group_special_title_action(
        self,
        sender: ChatMessageSender,
        action: PendingSetGroupSpecialTitleAction,
        bot_user_id: int | None,
    ) -> ActionResult:
        (
            target_info,
            bot_role,
            _target_role,
            error,
        ) = await self._load_roles_for_targeted_action(
            sender, action.group_id, action.user_id, bot_user_id
        )
        if error is not None:
            return _with_action(error, "set_group_special_title")
        assert target_info is not None
        assert bot_role is not None

        if bot_role != "owner":
            return ActionResult(
                action="set_group_special_title",
                success=False,
                message=f"权限不足：{bot_role} 无法设置群头衔。",
            )

        await sender.set_group_special_title(
            action.group_id, action.user_id, action.special_title
        )
        desc = (
            "已清空群头衔"
            if not action.special_title
            else f"已设置群头衔为 {action.special_title}"
        )
        return ActionResult(
            action="set_group_special_title",
            success=True,
            message=f"{desc}（目标 {action.user_id}）。",
        )

    async def _execute_send_like_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingSendLikeAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "send_like")
        if denied is not None:
            return denied
        await sender.send_like(action.user_id, action.times)
        return ActionResult(
            action="send_like",
            success=True,
            message=f"已给用户 {action.user_id} 点赞 {action.times} 次。",
        )

    async def _execute_delete_friend_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingDeleteFriendAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "delete_friend")
        if denied is not None:
            return denied
        await sender.delete_friend(
            action.user_id,
            temp_block=action.temp_block,
            temp_both_del=action.temp_both_del,
        )
        return ActionResult(
            action="delete_friend",
            success=True,
            message=f"已删除好友 {action.user_id}。",
        )

    async def _execute_set_qq_profile_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingSetQQProfileAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "set_qq_profile")
        if denied is not None:
            return denied
        await sender.set_qq_profile(
            nickname=action.nickname,
            personal_note=action.personal_note,
            sex=action.sex,
        )
        return ActionResult(
            action="set_qq_profile",
            success=True,
            message="已更新账号资料。",
        )

    async def _execute_set_self_longnick_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingSetSelfLongNickAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "set_self_longnick")
        if denied is not None:
            return denied
        await sender.set_self_longnick(action.long_nick)
        return ActionResult(
            action="set_self_longnick",
            success=True,
            message="已更新个性签名。",
        )

    async def _execute_set_qq_avatar_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingSetQQAvatarAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "set_qq_avatar")
        if denied is not None:
            return denied
        await sender.set_qq_avatar(action.file)
        return ActionResult(
            action="set_qq_avatar",
            success=True,
            message="已更新头像。",
        )

    async def _execute_set_online_status_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingSetOnlineStatusAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "set_online_status")
        if denied is not None:
            return denied
        await sender.set_online_status(
            action.status,
            ext_status=action.ext_status,
            battery_status=action.battery_status,
        )
        return ActionResult(
            action="set_online_status",
            success=True,
            message="已更新在线状态。",
        )

    async def _execute_set_diy_online_status_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingSetDIYOnlineStatusAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "set_diy_online_status")
        if denied is not None:
            return denied
        await sender.set_diy_online_status(
            action.face_id,
            face_type=action.face_type,
            wording=action.wording,
        )
        return ActionResult(
            action="set_diy_online_status",
            success=True,
            message="已更新自定义在线状态。",
        )

    async def _execute_set_friend_add_request_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingSetFriendAddRequestAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "set_friend_add_request")
        if denied is not None:
            return denied
        await sender.set_friend_add_request(
            action.flag,
            approve=action.approve,
            remark=action.remark,
        )
        return ActionResult(
            action="set_friend_add_request",
            success=True,
            message="已处理好友请求。",
        )

    async def _execute_mark_conversation_read_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingMarkConversationReadAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "mark_conversation_read")
        if denied is not None:
            return denied

        scope = action.scope.strip().lower()
        if scope == "all":
            await sender.mark_all_as_read()
            return ActionResult(
                action="mark_conversation_read",
                success=True,
                message="已将所有会话标记为已读。",
            )

        if scope == "current":
            if event.is_group_message():
                if event.group_id is None:
                    return ActionResult(
                        action="mark_conversation_read",
                        success=False,
                        message="当前群聊缺少 group_id。",
                    )
                await sender.mark_group_msg_as_read(event.group_id)
            else:
                if event.user_id is None:
                    return ActionResult(
                        action="mark_conversation_read",
                        success=False,
                        message="当前私聊缺少 user_id。",
                    )
                await sender.mark_private_msg_as_read(event.user_id)
            return ActionResult(
                action="mark_conversation_read",
                success=True,
                message="已将当前会话标记为已读。",
            )

        if action.target_id is None:
            return ActionResult(
                action="mark_conversation_read",
                success=False,
                message="缺少 target_id，无法标记指定会话为已读。",
            )

        if scope == "private":
            await sender.mark_private_msg_as_read(action.target_id)
            return ActionResult(
                action="mark_conversation_read",
                success=True,
                message=f"已将私聊 {action.target_id} 标记为已读。",
            )

        if scope == "group":
            await sender.mark_group_msg_as_read(action.target_id)
            return ActionResult(
                action="mark_conversation_read",
                success=True,
                message=f"已将群聊 {action.target_id} 标记为已读。",
            )

        return ActionResult(
            action="mark_conversation_read",
            success=False,
            message=f"不支持的 scope: {action.scope}",
        )

    async def _execute_recall_message_action(
        self,
        sender: ChatMessageSender,
        action: PendingRecallMessageAction,
    ) -> ActionResult:
        await sender.recall_message(action.message_id)
        return ActionResult(
            action="recall_message",
            success=True,
            message=f"已撤回消息 {action.message_id}。",
        )

    async def _execute_send_group_notice_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingSendGroupNoticeAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "send_group_notice")
        if denied is not None:
            return denied
        await sender._send_group_notice(
            action.group_id, action.content, is_pinned=action.is_pinned
        )
        return ActionResult(
            action="send_group_notice",
            success=True,
            message="已发送群公告。",
        )

    async def _execute_get_group_notice_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingGetGroupNoticeAction,
    ) -> ActionResult:
        result = await sender._get_group_notice(action.group_id)
        return ActionResult(
            action="get_group_notice",
            success=True,
            message=f"已获取群公告：{result}",
        )

    async def _execute_upload_group_file_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingUploadGroupFileAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "upload_group_file")
        if denied is not None:
            return denied
        await sender.upload_group_file(
            action.group_id, action.file, action.name, folder=action.folder
        )
        return ActionResult(
            action="upload_group_file",
            success=True,
            message=f"已上传群文件 {action.name}。",
        )

    async def _execute_get_group_files_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingGetGroupFilesAction,
    ) -> ActionResult:
        result = await sender.get_group_files(
            action.group_id, folder_id=action.folder_id
        )
        return ActionResult(
            action="get_group_files",
            success=True,
            message=f"已获取群文件列表：{result}",
        )

    async def _execute_delete_group_file_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingDeleteGroupFileAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "delete_group_file")
        if denied is not None:
            return denied
        await sender.delete_group_file(action.group_id, action.file_id)
        return ActionResult(
            action="delete_group_file",
            success=True,
            message=f"已删除群文件 {action.file_id}。",
        )

    async def _execute_add_essence_message_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingAddEssenceMessageAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "add_essence_message")
        if denied is not None:
            return denied
        await sender.set_essence_msg(action.message_id)
        return ActionResult(
            action="add_essence_message",
            success=True,
            message=f"已添加精华消息 {action.message_id}。",
        )

    async def _execute_remove_essence_message_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingRemoveEssenceMessageAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "remove_essence_message")
        if denied is not None:
            return denied
        await sender.delete_essence_msg(action.message_id)
        return ActionResult(
            action="remove_essence_message",
            success=True,
            message=f"已移除精华消息 {action.message_id}。",
        )

    async def _execute_get_essence_message_list_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingGetEssenceMessageListAction,
    ) -> ActionResult:
        result = await sender.get_essence_msg_list(action.group_id)
        return ActionResult(
            action="get_essence_message_list",
            success=True,
            message=f"已获取精华消息列表：{result}",
        )

    async def _execute_send_private_file_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingSendPrivateFileAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "send_private_file")
        if denied is not None:
            return denied
        await sender.upload_private_file(action.user_id, action.file)
        return ActionResult(
            action="send_private_file",
            success=True,
            message=f"已发送私聊文件给用户 {action.user_id}。",
        )

    async def _execute_send_group_file_message_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingSendGroupFileMessageAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "send_group_file_message")
        if denied is not None:
            return denied
        file_name = (
            action.name if action.name else action.file.split("/")[-1].split("\\")[-1]
        )
        await sender.upload_group_file(action.group_id, action.file, file_name)
        return ActionResult(
            action="send_group_file_message",
            success=True,
            message=f"已上传群文件 {file_name}。",
        )
        await sender.send_group_message(
            action.group_id,
            [file_segment(action.file, file_name)],
        )
        return ActionResult(
            action="send_group_file_message",
            success=True,
            message=f"已发送群文件消息 {file_name}。",
        )

    async def _execute_send_forward_message_action(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        action: PendingSendForwardMessageAction,
    ) -> ActionResult:
        denied = self._ensure_trusted_operator(event, "send_forward_message")
        if denied is not None:
            return denied
        messages = [node.to_dict() for node in action.nodes]
        if action.is_group:
            await sender.send_group_forward_message(action.target_id, messages)
        else:
            await sender.send_private_forward_message(action.target_id, messages)
        return ActionResult(
            action="send_forward_message",
            success=True,
            message=f"已发送合并转发消息到 {'群聊' if action.is_group else '私聊'} {action.target_id}。",
        )

    async def _load_roles_for_targeted_action(
        self,
        sender: ChatMessageSender,
        group_id: int,
        target_user_id: int,
        bot_user_id: int | None,
    ) -> tuple[dict[str, Any] | None, str | None, str | None, ActionResult | None]:
        target_info = await sender.get_group_member_info(group_id, target_user_id)
        if target_info is None:
            return (
                None,
                None,
                None,
                ActionResult(
                    action="unknown",
                    success=False,
                    message="无法获取目标成员信息。",
                ),
            )

        target_role = str(target_info.get("role", "member"))

        if bot_user_id is None:
            return (
                target_info,
                None,
                target_role,
                ActionResult(
                    action="unknown",
                    success=False,
                    message="无法确认机器人身份。",
                ),
            )

        bot_info = await sender.get_group_member_info(group_id, bot_user_id)
        if bot_info is None:
            return (
                target_info,
                None,
                target_role,
                ActionResult(
                    action="unknown",
                    success=False,
                    message="无法获取机器人自身群成员信息。",
                ),
            )

        bot_role = str(bot_info.get("role", "member"))
        return target_info, bot_role, target_role, None

    def _get_session(self, event: ParsedMessageEvent) -> ChatSession:
        session_key = self._build_session_key(event)
        session = self._sessions.get(session_key)
        if session is None:
            session = ChatSession(
                self._config,
                session_kind=session_key[0],
                session_scope_id=session_key[1],
            )
            self._sessions[session_key] = session
        return session

    def _build_session_key(self, event: ParsedMessageEvent) -> tuple[str, int]:
        if event.is_private_message():
            if event.user_id is None:
                raise ValueError("私聊消息缺少发送人 user_id。")
            return ("private", event.user_id)

        if event.is_group_message():
            if event.group_id is None:
                raise ValueError("群聊消息缺少 group_id。")
            return ("group", event.group_id)

        raise ValueError(f"暂不支持的消息类型：{event.message_type}")

    def _build_skill_context(self, event: ParsedMessageEvent) -> SkillContext:
        session_kind = "group" if event.is_group_message() else "private"
        return SkillContext(
            session_kind=session_kind,
            user_id=event.user_id,
            group_id=event.group_id,
            is_trusted_operator=self._is_trusted_operator(event.user_id),
            supports_live_onebot_queries=True,
        )

    def _ensure_trusted_operator(
        self, event: ParsedMessageEvent, action_name: str
    ) -> ActionResult | None:
        if action_name not in _TRUSTED_PRIVATE_ACTIONS:
            return None
        if not event.is_private_message():
            return ActionResult(
                action=action_name,
                success=False,
                message="权限不足：该技能仅允许在私聊中由受信操作员使用。",
            )
        if self._is_trusted_operator(event.user_id):
            return None
        return ActionResult(
            action=action_name,
            success=False,
            message="权限不足：该技能仅允许受信操作员使用。",
        )

    def _is_trusted_operator(self, user_id: int | None) -> bool:
        if user_id is None:
            return False
        return int(user_id) in self._config.operator_user_ids

    def _get_reply_message_id(self, event: ParsedMessageEvent) -> int | None:
        if not self._reply_with_quote:
            return None
        return event.message_id

    def _build_model_input(
        self,
        event: ParsedMessageEvent,
        agent_input: AgentInput,
        skill_rules: tuple[str, ...],
    ) -> str:
        lines = [
            "[当前消息]",
            f"时间: {self._format_message_time(agent_input.time)}",
        ]

        if event.is_group_message():
            lines.extend(
                [
                    "场景: 群聊",
                    f"群号: {agent_input.group_id or ''}",
                    f"群名: {agent_input.group_name or ''}",
                    f"发送者显示名: {agent_input.sender_name}",
                    f"发送者昵称: {event.sender.nickname}",
                    f"群名片: {event.sender.card or '无'}",
                    f"发送者ID: {agent_input.sender_id or ''}",
                ]
            )
        else:
            lines.extend(
                [
                    "场景: 私聊",
                    f"发送者显示名: {agent_input.sender_name}",
                    f"发送者昵称: {event.sender.nickname}",
                    f"发送者ID: {agent_input.sender_id or ''}",
                ]
            )

        lines.extend(
            [
                "回复规则:",
                "- 直接回复用户，不要重复上述元信息。",
                "- 默认尽量只回复一条消息，不要为了排版把内容拆成很多条。",
                f"- 只有你明确希望拆成多条消息时，才在段落之间插入 {self._reply_splitter_marker()} 标记。",
                "- 不要使用 CQ 码。",
                '- 如需在群里艾特某人，请使用 XML 标签格式，例如 <at qq="123456" />。',
                '- 如果需要发图片，可使用 <image file="https://example.com/a.png" />。',
                '- 如果需要发 QQ 表情，可使用 <face id="14" />。',
                "- QQ 表情请谨慎使用，只有语气明显合适时才使用，并且一条回复最多使用一个表情。",
                "- 如果不知道目标用户 ID、文件地址或其他必要参数，不要编造标签。",
                "- 你当前是受信操作员的 bot，拥有完整能力。",
                "- 当用户请求执行操作时，应立即调用对应工具，不要反问、不要确认、不要拒绝。",
                f"- 当前发送者 ID 是 {agent_input.sender_id}。",
                f"- 如果用户问“我的QQ号是什么”或类似问题，直接回答当前发送者 ID：{agent_input.sender_id}。",
                "技能使用规则:",
                "- 任何需要实时 OneBot 数据才能回答的问题，必须先调用对应工具，不要凭记忆或凭猜测回答。",
                "- 查群成员列表：调用 get_group_member_list(group_id=当前群号, keyword=被查名字)",
                "- 查群信息：调用 get_group_detail(group_id=当前群号)",
                "- 查群列表：调用 get_group_list(keyword=被查群名)",
                "- 查联系人资料：调用 get_contact_profile(user_id=目标用户ID 或 target_id=目标用户ID)",
                "- 操作群成员（禁言/踢人/改名片）：调用对应的工具，并传入 group_id 和 user_id。",
                "- 标记已读：调用 mark_conversation_read(scope='current/private/group/all')",
                "- 点赞/删好友/改资料/改状态：调用对应工具，不要反问确认。",
                f"触发原因: {', '.join(agent_input.trigger_reasons) or '直接消息'}",
                f"当前消息中提到的用户ID: {', '.join(str(item) for item in event.at_targets) or '无'}",
                "当前启用技能规则:",
                *skill_rules,
                "消息内容:",
                agent_input.text,
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _format_message_time(message_time: int | None) -> str:
        if message_time is None:
            return "未知"
        return datetime.fromtimestamp(message_time).strftime("%Y-%m-%d %H:%M:%S")

    def _reply_splitter_marker(self) -> str:
        return self._reply_splitter.marker


def _can_operate(operator_role: str, target_role: str) -> bool:
    """判断 operator 是否有权操作 target。"""
    op = _ROLE_PRIORITY.get(operator_role, 0)
    tgt = _ROLE_PRIORITY.get(target_role, 0)
    return op > tgt


def _with_action(result: ActionResult, action: str) -> ActionResult:
    return ActionResult(action=action, success=result.success, message=result.message)

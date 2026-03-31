"""OneBot 与 LangChain 的应用服务。"""

from __future__ import annotations

import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol

from chat_app.actions.group_management import (
    PendingAction,
    PendingKickGroupMemberAction,
    PendingMuteAction,
    PendingSetGroupCardAction,
    PendingSetGroupAdminAction,
    PendingSetGroupSpecialTitleAction,
)
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
        skill_runtime = resolve_skill_runtime(self._build_skill_context(event))
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
    ) -> tuple[PendingAction, ...]:
        getter = getattr(session, "get_pending_actions", None)
        if not callable(getter):
            return ()
        return tuple(getter())

    async def _execute_pending_actions(
        self,
        sender: ChatMessageSender,
        event: ParsedMessageEvent,
        actions: tuple[PendingAction, ...],
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
    def _build_skill_context(event: ParsedMessageEvent) -> SkillContext:
        session_kind = "group" if event.is_group_message() else "private"
        return SkillContext(
            session_kind=session_kind,
            user_id=event.user_id,
            group_id=event.group_id,
        )

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

"""OneBot 与 LangChain 的应用服务。

重构后：ChatService 仅负责事件编排，具体职责委派给：
- action_executors: action 执行
- model_input_builder: 模型输入拼装
- reply_sender: 回复发送
- permission: 权限校验
"""

from __future__ import annotations

import logging
from typing import Any

from chat_app.chat import ChatSession, ToolCallTrace
from chat_app.config import AppConfig, load_config
from chat_app.memory.long_term import LongTermMemoryStore
from chat_app.postgres.long_term_store import PostgresLongTermStore
from chat_app.skills.context import SkillContext
from chat_app.skills.registry import resolve_skill_runtime
from onebot_gateway.config import ReplySplitConfig
from onebot_gateway.message.adapter import (
    AgentInput,
    build_agent_input,
)
from onebot_gateway.message.parser import ParsedMessageEvent
from onebot_gateway.message.reply_splitter import ReplySplitter
from onebot_gateway.message.trigger import TriggerDecision

from onebot_gateway.app.action_executors.base import ActionDispatcher, _can_operate
from onebot_gateway.app.action_executors.announcement import (
    GetGroupNoticeActionExecutor,
    SendGroupNoticeActionExecutor,
)
from onebot_gateway.app.action_executors.essence import (
    AddEssenceMessageActionExecutor,
    GetEssenceMessageListActionExecutor,
    RemoveEssenceMessageActionExecutor,
)
from onebot_gateway.app.action_executors.file_actions import (
    DeleteGroupFileActionExecutor,
    GetGroupFilesActionExecutor,
    SendForwardMessageActionExecutor,
    SendGroupFileMessageActionExecutor,
    SendPrivateFileActionExecutor,
    UploadGroupFileActionExecutor,
)
from onebot_gateway.app.action_executors.group_actions import (
    KickGroupMemberActionExecutor,
    MuteActionExecutor,
    SetGroupAdminActionExecutor,
    SetGroupCardActionExecutor,
    SetGroupSpecialTitleActionExecutor,
)
from onebot_gateway.app.action_executors.private_actions import (
    DeleteFriendActionExecutor,
    MarkConversationReadActionExecutor,
    RecallMessageActionExecutor,
    SetDIYOnlineStatusActionExecutor,
    SetFriendAddRequestActionExecutor,
    SetOnlineStatusActionExecutor,
    SetQQAvatarActionExecutor,
    SetQQProfileActionExecutor,
    SetSelfLongNickActionExecutor,
    SendLikeActionExecutor,
)
from onebot_gateway.app.model_input_builder import ModelInputBuilder
from onebot_gateway.app.permission import PermissionChecker
from onebot_gateway.app.reply_sender import send_reply_parts, split_reply_text
from onebot_gateway.app.protocol import ChatMessageSender
from onebot_gateway.app.types import (
    ActionResult,
    ChatHandleResult,
    PendingCommand,
    PendingAddEssenceMessageAction,
    PendingDeleteFriendAction,
    PendingDeleteGroupFileAction,
    PendingGetEssenceMessageListAction,
    PendingGetGroupFilesAction,
    PendingGetGroupNoticeAction,
    PendingKickGroupMemberAction,
    PendingMarkConversationReadAction,
    PendingMuteAction,
    PendingRecallMessageAction,
    PendingRemoveEssenceMessageAction,
    PendingSendForwardMessageAction,
    PendingSendGroupFileMessageAction,
    PendingSendGroupNoticeAction,
    PendingSendLikeAction,
    PendingSendPrivateFileAction,
    PendingSetDIYOnlineStatusAction,
    PendingSetFriendAddRequestAction,
    PendingSetGroupAdminAction,
    PendingSetGroupCardAction,
    PendingSetGroupSpecialTitleAction,
    PendingSetOnlineStatusAction,
    PendingSetQQAvatarAction,
    PendingSetQQProfileAction,
    PendingSetSelfLongNickAction,
    PendingUploadGroupFileAction,
)

logger = logging.getLogger(__name__)

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

        self._permission_checker = PermissionChecker(
            trusted_operator_ids=config.operator_user_ids,
        )
        self._action_dispatcher = self._build_action_dispatcher()
        self._model_input_builder = ModelInputBuilder(
            reply_splitter=self._reply_splitter,
            long_term_store=self._build_long_term_store(),
        )

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

        model_input = self._model_input_builder.build(
            event, agent_input, skill_runtime.rules
        )
        aask = getattr(session, "aask", None)
        if callable(aask):
            reply_text = await aask(
                model_input,
                runtime_tools=skill_runtime.tools,
                runtime_rules=skill_runtime.rules,
            )
        else:
            reply_text = session.ask(
                model_input,
                runtime_tools=skill_runtime.tools,
                runtime_rules=skill_runtime.rules,
            )

        reply_parts = split_reply_text(reply_text, self._reply_splitter)
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
            await send_reply_parts(
                send=sender.send_private_message,
                target_id=event.user_id,
                reply_parts=reply_parts,
                reply_message_id=self._get_reply_message_id(event),
            )
        elif event.is_group_message():
            assert event.group_id is not None
            await send_reply_parts(
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

    # -- Action 执行 --

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
            result = await self._action_dispatcher.dispatch(
                sender, action, bot_user_id=bot_user_id, event=event
            )
            results.append(result)
            if not result.success:
                logger.warning("群管动作执行失败: %s", result.message)
        return tuple(results)

    def _build_action_dispatcher(self) -> ActionDispatcher:
        dispatcher = ActionDispatcher()
        perm = self._permission_checker

        dispatcher.register(PendingMuteAction, MuteActionExecutor())
        dispatcher.register(PendingSetGroupAdminAction, SetGroupAdminActionExecutor())
        dispatcher.register(
            PendingKickGroupMemberAction, KickGroupMemberActionExecutor()
        )
        dispatcher.register(PendingSetGroupCardAction, SetGroupCardActionExecutor())
        dispatcher.register(
            PendingSetGroupSpecialTitleAction, SetGroupSpecialTitleActionExecutor()
        )
        dispatcher.register(PendingSendLikeAction, SendLikeActionExecutor(perm))
        dispatcher.register(PendingDeleteFriendAction, DeleteFriendActionExecutor(perm))
        dispatcher.register(PendingSetQQProfileAction, SetQQProfileActionExecutor(perm))
        dispatcher.register(
            PendingSetSelfLongNickAction, SetSelfLongNickActionExecutor(perm)
        )
        dispatcher.register(PendingSetQQAvatarAction, SetQQAvatarActionExecutor(perm))
        dispatcher.register(
            PendingSetOnlineStatusAction, SetOnlineStatusActionExecutor(perm)
        )
        dispatcher.register(
            PendingSetDIYOnlineStatusAction, SetDIYOnlineStatusActionExecutor(perm)
        )
        dispatcher.register(
            PendingSetFriendAddRequestAction, SetFriendAddRequestActionExecutor(perm)
        )
        dispatcher.register(
            PendingMarkConversationReadAction, MarkConversationReadActionExecutor(perm)
        )
        dispatcher.register(PendingRecallMessageAction, RecallMessageActionExecutor())
        dispatcher.register(
            PendingSendGroupNoticeAction, SendGroupNoticeActionExecutor(perm)
        )
        dispatcher.register(PendingGetGroupNoticeAction, GetGroupNoticeActionExecutor())
        dispatcher.register(
            PendingUploadGroupFileAction, UploadGroupFileActionExecutor(perm)
        )
        dispatcher.register(PendingGetGroupFilesAction, GetGroupFilesActionExecutor())
        dispatcher.register(
            PendingDeleteGroupFileAction, DeleteGroupFileActionExecutor(perm)
        )
        dispatcher.register(
            PendingAddEssenceMessageAction, AddEssenceMessageActionExecutor(perm)
        )
        dispatcher.register(
            PendingRemoveEssenceMessageAction, RemoveEssenceMessageActionExecutor(perm)
        )
        dispatcher.register(
            PendingGetEssenceMessageListAction, GetEssenceMessageListActionExecutor()
        )
        dispatcher.register(
            PendingSendPrivateFileAction, SendPrivateFileActionExecutor(perm)
        )
        dispatcher.register(
            PendingSendGroupFileMessageAction, SendGroupFileMessageActionExecutor(perm)
        )
        dispatcher.register(
            PendingSendForwardMessageAction, SendForwardMessageActionExecutor(perm)
        )
        return dispatcher

    # -- 会话管理 --

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
            is_trusted_operator=self._permission_checker._trusted_operator_ids.__contains__(
                event.user_id
            )
            if event.user_id
            else False,
            supports_live_onebot_queries=True,
        )

    def _get_reply_message_id(self, event: ParsedMessageEvent) -> int | None:
        if not self._reply_with_quote:
            return None
        return event.message_id

    def _build_long_term_store(self) -> LongTermMemoryStore | None:
        if self._config.postgres.enabled:
            return PostgresLongTermStore(self._config.postgres)
        return None

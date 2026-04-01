"""对话模型封装。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Literal

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from chat_app.skills.account_profile import (
    PendingSetQQAvatarAction,
    PendingSetQQProfileAction,
    PendingSetSelfLongNickAction,
)
from chat_app.skills.account_status import (
    PendingSetDIYOnlineStatusAction,
    PendingSetOnlineStatusAction,
)
from chat_app.skills.friend_request_management import PendingSetFriendAddRequestAction
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
from chat_app.config import AppConfig
from chat_app.memory.manager import ConversationMemory
from chat_app.memory.store import InMemoryMemoryStore
from chat_app.memory.summarizer import ConversationSummarizer
from chat_app.memory.types import MemoryPolicy, MemorySessionScope
from chat_app.postgres.memory_store import PostgresMemoryStore
from chat_app.skills.context import SkillContext
from chat_app.skills.registry import resolve_skill_runtime


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
)


@dataclass(frozen=True)
class ToolCallTrace:
    """单次工具调用痕迹。"""

    tool_name: str
    tool_args: dict[str, object]
    tool_output: str

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "tool_output": self.tool_output,
        }


class ChatSession:
    """最小可用的多轮对话会话。"""

    def __init__(
        self,
        config: AppConfig,
        *,
        session_kind: Literal["private", "group"] = "private",
        session_scope_id: int = 0,
    ) -> None:
        self._config = config
        self._client = ChatOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            temperature=0,
        )
        self._last_tool_traces: list[ToolCallTrace] = []
        self._pending_actions: list[PendingCommand] = []
        policy = self._resolve_memory_policy(session_kind)
        memory_scope = self._build_memory_scope(session_kind, session_scope_id)
        memory_store = self._build_memory_store()
        default_skill_runtime = resolve_skill_runtime(
            SkillContext(
                session_kind=session_kind,
                user_id=memory_scope.user_id,
                group_id=memory_scope.group_id,
            )
        )
        self._default_runtime_tools = default_skill_runtime.tools
        self._memory = ConversationMemory(
            policy,
            enable_summary=config.memory.enable_summary,
            max_summary_chars=config.memory.max_summary_chars,
            max_input_chars=config.memory.max_input_chars,
            store=memory_store,
            scope=memory_scope,
        )
        self._summarizer = ConversationSummarizer(
            self._client,
            config.memory.max_summary_chars,
        )

    def ask(
        self,
        user_input: str,
        *,
        runtime_tools: Iterable[BaseTool] | None = None,
        runtime_rules: Iterable[str] = (),
    ) -> str:
        """发送一条用户消息并返回模型回复。"""
        content = user_input.strip()
        if not content:
            raise ValueError("用户输入不能为空。")

        self._last_tool_traces = []
        self._pending_actions = []
        effective_tools = (
            tuple(runtime_tools)
            if runtime_tools is not None
            else self._default_runtime_tools
        )
        messages = self._build_messages(content, runtime_rules)
        response = self._invoke_with_tools(messages, effective_tools)
        if not isinstance(response, AIMessage):
            raise TypeError("模型返回了无法识别的消息类型。")

        reply = response.text.strip()
        if not reply:
            raise ValueError("模型返回了空响应。")

        self._memory.add_turn(content, response, self._summarizer)
        return reply

    async def aask(
        self,
        user_input: str,
        *,
        runtime_tools: Iterable[BaseTool] | None = None,
        runtime_rules: Iterable[str] = (),
    ) -> str:
        """异步发送一条用户消息并返回模型回复。"""
        content = user_input.strip()
        if not content:
            raise ValueError("用户输入不能为空。")

        self._last_tool_traces = []
        self._pending_actions = []
        effective_tools = (
            tuple(runtime_tools)
            if runtime_tools is not None
            else self._default_runtime_tools
        )
        messages = self._build_messages(content, runtime_rules)
        response = await self._ainvoke_with_tools(messages, effective_tools)
        if not isinstance(response, AIMessage):
            raise TypeError("模型返回了无法识别的消息类型。")

        reply = response.text.strip()
        if not reply:
            raise ValueError("模型返回了空响应。")

        self._memory.add_turn(content, response, self._summarizer)
        return reply

    def get_last_tool_traces(self) -> tuple[ToolCallTrace, ...]:
        """返回最近一次 ask 的工具调用痕迹。"""
        return tuple(self._last_tool_traces)

    def get_pending_actions(self) -> tuple[PendingCommand, ...]:
        """返回最近一次 ask 产生的待执行动作。"""
        return tuple(self._pending_actions)

    def _build_messages(
        self, user_input: str, runtime_rules: Iterable[str]
    ) -> list[BaseMessage]:
        extra_rules = [rule.strip() for rule in runtime_rules if rule.strip()]
        if not extra_rules:
            return self._memory.build_messages(self._config.system_prompt, user_input)

        system_prompt = self._config.system_prompt.strip()
        skill_prompt = "\n".join([system_prompt, "[当前启用技能规则]", *extra_rules])
        return self._memory.build_messages(skill_prompt, user_input)

    def _invoke_with_tools(
        self, messages: list[object], tools: tuple[BaseTool, ...]
    ) -> AIMessage:
        tool_map = {tool.name: tool for tool in tools}
        if not tools:
            response = self._client.invoke(messages)
            if not isinstance(response, AIMessage):
                raise TypeError("模型返回了无法识别的消息类型。")
            return response

        tool_enabled_client = self._client.bind_tools(list(tools))
        conversation = list(messages)
        for _ in range(5):
            response = tool_enabled_client.invoke(conversation)
            if not isinstance(response, AIMessage):
                raise TypeError("模型返回了无法识别的消息类型。")

            tool_calls = getattr(response, "tool_calls", [])
            if not tool_calls:
                return response

            conversation.append(response)
            for tool_call in tool_calls:
                tool_name = str(tool_call.get("name", "")).strip()
                tool = tool_map.get(tool_name)
                if tool is None:
                    tool_result = f"未知工具: {tool_name}"
                else:
                    tool_result = str(tool.invoke(tool_call.get("args", {})))

                self._last_tool_traces.append(
                    ToolCallTrace(
                        tool_name=tool_name,
                        tool_args=dict(tool_call.get("args", {})),
                        tool_output=tool_result,
                    )
                )

                self._try_parse_pending_action(tool_name, tool_result)

                conversation.append(
                    ToolMessage(
                        content=tool_result,
                        tool_call_id=str(tool_call.get("id", "")),
                    )
                )

        raise RuntimeError("模型工具调用次数过多。")

    async def _ainvoke_with_tools(
        self, messages: list[object], tools: tuple[BaseTool, ...]
    ) -> AIMessage:
        tool_map = {tool.name: tool for tool in tools}
        if not tools:
            response = await self._client.ainvoke(messages)
            if not isinstance(response, AIMessage):
                raise TypeError("模型返回了无法识别的消息类型。")
            return response

        tool_enabled_client = self._client.bind_tools(list(tools))
        conversation = list(messages)
        for _ in range(5):
            response = await tool_enabled_client.ainvoke(conversation)
            if not isinstance(response, AIMessage):
                raise TypeError("模型返回了无法识别的消息类型。")

            tool_calls = getattr(response, "tool_calls", [])
            if not tool_calls:
                return response

            conversation.append(response)
            for tool_call in tool_calls:
                tool_name = str(tool_call.get("name", "")).strip()
                tool = tool_map.get(tool_name)
                if tool is None:
                    tool_result = f"未知工具: {tool_name}"
                else:
                    tool_result = str(await tool.ainvoke(tool_call.get("args", {})))

                self._last_tool_traces.append(
                    ToolCallTrace(
                        tool_name=tool_name,
                        tool_args=dict(tool_call.get("args", {})),
                        tool_output=tool_result,
                    )
                )

                self._try_parse_pending_action(tool_name, tool_result)

                conversation.append(
                    ToolMessage(
                        content=tool_result,
                        tool_call_id=str(tool_call.get("id", "")),
                    )
                )

        raise RuntimeError("模型工具调用次数过多。")

    def _resolve_memory_policy(
        self, session_kind: Literal["private", "group"]
    ) -> MemoryPolicy:
        if session_kind == "group":
            policy = self._config.memory.group_policy
        else:
            policy = self._config.memory.private_policy

        return MemoryPolicy(
            max_turns=policy.max_turns,
            summary_trigger_turns=policy.summary_trigger_turns,
            summary_batch_turns=policy.summary_batch_turns,
        )

    def _build_memory_store(self) -> InMemoryMemoryStore | PostgresMemoryStore:
        if self._config.postgres.enabled:
            return PostgresMemoryStore(self._config.postgres)
        return InMemoryMemoryStore()

    @staticmethod
    def _build_memory_scope(
        session_kind: Literal["private", "group"], session_scope_id: int
    ) -> MemorySessionScope:
        normalized_scope_id = int(session_scope_id)
        if session_kind == "group":
            return MemorySessionScope(
                session_key=f"group:{normalized_scope_id}",
                session_kind="group",
                user_id=None,
                group_id=normalized_scope_id,
            )

        return MemorySessionScope(
            session_key=f"private:{normalized_scope_id}",
            session_kind="private",
            user_id=normalized_scope_id,
            group_id=None,
        )

    def _try_parse_pending_action(self, tool_name: str, tool_output: str) -> None:
        try:
            data = json.loads(tool_output)
        except (json.JSONDecodeError, TypeError):
            return
        if not isinstance(data, dict):
            return
        action_name = str(data.get("action", "")).strip()
        if tool_name == "mute_group_member" and action_name == "mute_group_member":
            self._pending_actions.append(
                PendingMuteAction(
                    group_id=int(data["group_id"]),
                    user_id=int(data["user_id"]),
                    duration=int(data.get("duration", 0)),
                )
            )
            return
        if tool_name == "set_group_admin" and action_name == "set_group_admin":
            self._pending_actions.append(
                PendingSetGroupAdminAction(
                    group_id=int(data["group_id"]),
                    user_id=int(data["user_id"]),
                    enable=bool(data.get("enable", True)),
                )
            )
            return
        if tool_name == "kick_group_member" and action_name == "kick_group_member":
            self._pending_actions.append(
                PendingKickGroupMemberAction(
                    group_id=int(data["group_id"]),
                    user_id=int(data["user_id"]),
                    reject_add_request=bool(data.get("reject_add_request", False)),
                )
            )
            return
        if tool_name == "set_group_card" and action_name == "set_group_card":
            self._pending_actions.append(
                PendingSetGroupCardAction(
                    group_id=int(data["group_id"]),
                    user_id=int(data["user_id"]),
                    card=str(data.get("card", "")),
                )
            )
            return
        if (
            tool_name == "set_group_special_title"
            and action_name == "set_group_special_title"
        ):
            self._pending_actions.append(
                PendingSetGroupSpecialTitleAction(
                    group_id=int(data["group_id"]),
                    user_id=int(data["user_id"]),
                    special_title=str(data.get("special_title", "")),
                )
            )
            return
        if tool_name == "send_like" and action_name == "send_like":
            self._pending_actions.append(
                PendingSendLikeAction(
                    user_id=int(data["user_id"]),
                    times=int(data.get("times", 1)),
                )
            )
            return
        if tool_name == "delete_friend" and action_name == "delete_friend":
            self._pending_actions.append(
                PendingDeleteFriendAction(
                    user_id=int(data["user_id"]),
                    temp_block=bool(data.get("temp_block", True)),
                    temp_both_del=bool(data.get("temp_both_del", False)),
                )
            )
            return
        if tool_name == "set_qq_profile" and action_name == "set_qq_profile":
            self._pending_actions.append(
                PendingSetQQProfileAction(
                    nickname=str(data.get("nickname", "")),
                    personal_note=str(data.get("personal_note", "")),
                    sex=str(data.get("sex", "unknown")),
                )
            )
            return
        if tool_name == "set_self_longnick" and action_name == "set_self_longnick":
            self._pending_actions.append(
                PendingSetSelfLongNickAction(
                    long_nick=str(data.get("long_nick", "")),
                )
            )
            return
        if tool_name == "set_qq_avatar" and action_name == "set_qq_avatar":
            self._pending_actions.append(
                PendingSetQQAvatarAction(file=str(data.get("file", "")))
            )
            return
        if tool_name == "set_online_status" and action_name == "set_online_status":
            self._pending_actions.append(
                PendingSetOnlineStatusAction(
                    status=int(data.get("status", 0)),
                    ext_status=int(data.get("ext_status", 0)),
                    battery_status=int(data.get("battery_status", 0)),
                )
            )
            return
        if (
            tool_name == "set_diy_online_status"
            and action_name == "set_diy_online_status"
        ):
            self._pending_actions.append(
                PendingSetDIYOnlineStatusAction(
                    face_id=int(data.get("face_id", 0)),
                    face_type=int(data.get("face_type", 0)),
                    wording=str(data.get("wording", "")),
                )
            )
            return
        if (
            tool_name == "set_friend_add_request"
            and action_name == "set_friend_add_request"
        ):
            self._pending_actions.append(
                PendingSetFriendAddRequestAction(
                    flag=str(data.get("flag", "")),
                    approve=bool(data.get("approve", True)),
                    remark=str(data.get("remark", "")),
                )
            )
            return
        if (
            tool_name == "mark_conversation_read"
            and action_name == "mark_conversation_read"
        ):
            target_id = data.get("target_id")
            self._pending_actions.append(
                PendingMarkConversationReadAction(
                    scope=str(data.get("scope", "current")),
                    target_id=None if target_id is None else int(target_id),
                )
            )

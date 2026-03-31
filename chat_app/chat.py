"""对话模型封装。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from chat_app.actions.types import PendingMuteAction
from chat_app.config import AppConfig
from chat_app.memory.manager import ConversationMemory
from chat_app.memory.summarizer import ConversationSummarizer
from chat_app.memory.types import MemoryPolicy
from chat_app.tools.registry import build_chat_tools


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
    ) -> None:
        self._config = config
        self._client = ChatOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            temperature=0,
        )
        self._tools = build_chat_tools()
        self._tool_enabled_client = (
            self._client.bind_tools(self._tools) if self._tools else None
        )
        self._tool_map = {tool.name: tool for tool in self._tools}
        self._last_tool_traces: list[ToolCallTrace] = []
        self._pending_actions: list[PendingMuteAction] = []
        policy = self._resolve_memory_policy(session_kind)
        self._memory = ConversationMemory(
            policy,
            enable_summary=config.memory.enable_summary,
            max_summary_chars=config.memory.max_summary_chars,
            max_input_chars=config.memory.max_input_chars,
        )
        self._summarizer = ConversationSummarizer(
            self._client,
            config.memory.max_summary_chars,
        )

    def ask(self, user_input: str) -> str:
        """发送一条用户消息并返回模型回复。"""
        content = user_input.strip()
        if not content:
            raise ValueError("用户输入不能为空。")

        self._last_tool_traces = []
        self._pending_actions = []
        messages = self._memory.build_messages(self._config.system_prompt, content)
        response = self._invoke_with_tools(messages)
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

    def get_pending_actions(self) -> tuple[PendingMuteAction, ...]:
        """返回最近一次 ask 产生的待执行动作。"""
        return tuple(self._pending_actions)

    def _invoke_with_tools(self, messages: list[object]) -> AIMessage:
        if self._tool_enabled_client is None:
            response = self._client.invoke(messages)
            if not isinstance(response, AIMessage):
                raise TypeError("模型返回了无法识别的消息类型。")
            return response

        conversation = list(messages)
        for _ in range(5):
            response = self._tool_enabled_client.invoke(conversation)
            if not isinstance(response, AIMessage):
                raise TypeError("模型返回了无法识别的消息类型。")

            tool_calls = getattr(response, "tool_calls", [])
            if not tool_calls:
                return response

            conversation.append(response)
            for tool_call in tool_calls:
                tool_name = str(tool_call.get("name", "")).strip()
                tool = self._tool_map.get(tool_name)
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

                self._try_parse_mute_action(tool_name, tool_result)

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

    def _try_parse_mute_action(self, tool_name: str, tool_output: str) -> None:
        if tool_name != "mute_group_member":
            return
        try:
            data = json.loads(tool_output)
        except (json.JSONDecodeError, TypeError):
            return
        if not isinstance(data, dict) or data.get("action") != "mute_group_member":
            return
        self._pending_actions.append(
            PendingMuteAction(
                group_id=int(data["group_id"]),
                user_id=int(data["user_id"]),
                duration=int(data.get("duration", 0)),
            )
        )

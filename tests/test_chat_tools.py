"""LangChain tools 集成测试。"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage, ToolMessage

from chat_app.chat import ChatSession
from chat_app.config import AppConfig


class FakeBoundClient:
    """模拟支持 tool calling 的模型。"""

    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, messages: list[object]) -> AIMessage:
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call-1",
                        "name": "search_qq_emojis",
                        "args": {"query": "开心友好", "limit": 2},
                    }
                ],
            )

        tool_message = next(
            message for message in messages if isinstance(message, ToolMessage)
        )
        assert "emoji_id" in str(tool_message.content)
        return AIMessage(content='好的 <face id="14" />')


class FakeChatOpenAI:
    """模拟 ChatOpenAI。"""

    def __init__(self, **_: object) -> None:
        self.bound_client = FakeBoundClient()

    def bind_tools(self, tools: list[object]) -> FakeBoundClient:
        assert tools
        return self.bound_client

    def invoke(self, messages: list[object]) -> AIMessage:
        return AIMessage(content="普通回复")


class ChatToolsTests(unittest.TestCase):
    """验证 ChatSession 会触发表情检索工具。"""

    def test_chat_session_runs_tool_call_loop(self) -> None:
        config = AppConfig(
            api_key="key",
            base_url="http://example.com/v1",
            model="test-model",
            system_prompt="你是测试助手。",
        )

        with patch("chat_app.chat.ChatOpenAI", FakeChatOpenAI):
            session = ChatSession(config)
            reply = session.ask("请开心一点地回复我")

        self.assertEqual(reply, '好的 <face id="14" />')


if __name__ == "__main__":
    unittest.main()

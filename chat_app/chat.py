"""对话模型封装。"""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from chat_app.config import AppConfig


class ChatSession:
    """最小可用的多轮对话会话。"""

    def __init__(self, config: AppConfig) -> None:
        self._client = ChatOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            temperature=0,
        )
        self._messages: list[BaseMessage] = [
            SystemMessage(content=config.system_prompt)
        ]

    def ask(self, user_input: str) -> str:
        """发送一条用户消息并返回模型回复。"""
        content = user_input.strip()
        if not content:
            raise ValueError("用户输入不能为空。")

        self._messages.append(HumanMessage(content=content))
        response = self._client.invoke(self._messages)
        if not isinstance(response, AIMessage):
            raise TypeError("模型返回了无法识别的消息类型。")

        self._messages.append(response)
        reply = response.text.strip()
        if not reply:
            raise ValueError("模型返回了空响应。")
        return reply

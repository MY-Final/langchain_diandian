"""NapCat OneBot WebSocket 事件接收。"""

from __future__ import annotations

import asyncio
import json

from chat_app.config import load_config
from chat_app.postgres import ensure_postgres_ready
from onebot_gateway.app.service import ChatService
from onebot_gateway.message.adapter import build_agent_input
from onebot_gateway.message.store import MessageStore
from onebot_gateway.message.trigger import TriggerEvaluator
from onebot_gateway.transport.client import OneBotWebSocketClient
from onebot_gateway.config import load_onebot_config
from onebot_gateway.message.parser import parse_message_event


async def main() -> None:
    """连接 NapCat 并持续打印收到的事件。"""
    config = load_onebot_config()
    app_config = load_config()
    ensure_postgres_ready(app_config)
    message_store = MessageStore()
    chat_service = ChatService(
        app_config,
        reply_with_quote=config.reply_with_quote,
        reply_split_config=config.reply_split,
    )

    async with OneBotWebSocketClient(config.ws_url, config.token) as client:
        trigger_evaluator = TriggerEvaluator(
            config.bot_name_patterns,
            message_store=message_store,
            resolver=client,
        )
        print("已连接到 NapCat:", config.ws_url)

        while True:
            frame = await client.receive_frame()
            raw = frame.raw

            print("收到原始数据:")
            print(raw)

            if frame.data is None:
                print("不是 JSON")
                continue

            try:
                data = frame.data
                print("解析后的 JSON:")
                print(json.dumps(data, ensure_ascii=False, indent=2))

                event = parse_message_event(data)
                if event is not None:
                    print("提取后的消息信息:")
                    print(
                        json.dumps(
                            event.to_summary(config.bot_name_patterns),
                            ensure_ascii=False,
                            indent=2,
                        )
                    )

                    decision = await trigger_evaluator.evaluate(event)
                    print("触发判断:")
                    print(
                        json.dumps(
                            decision.to_dict(),
                            ensure_ascii=False,
                            indent=2,
                        )
                    )

                    print("适配后的智能体输入:")
                    print(
                        json.dumps(
                            build_agent_input(event, decision).to_dict(),
                            ensure_ascii=False,
                            indent=2,
                        )
                    )

                    chat_result = await chat_service.handle_event(
                        client,
                        event,
                        decision,
                    )
                    if chat_result.should_reply:
                        print("LangChain 回复:")
                        print(chat_result.reply_text)
                        print(f"分段发送数量: {len(chat_result.reply_parts)}")
                    if app_config.debug_tool_calls and chat_result.tool_traces:
                        print("Tool 调用记录:")
                        print(
                            json.dumps(
                                [trace.to_dict() for trace in chat_result.tool_traces],
                                ensure_ascii=False,
                                indent=2,
                            )
                        )
            except Exception as exc:
                print(f"处理消息时出错: {exc}")


def run() -> None:
    """同步启动入口。"""
    asyncio.run(main())

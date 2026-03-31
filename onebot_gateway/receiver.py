"""NapCat OneBot WebSocket 事件接收。"""

from __future__ import annotations

import asyncio
import json

from onebot_gateway.client import OneBotWebSocketClient
from onebot_gateway.config import load_onebot_config
from onebot_gateway.event_parser import parse_message_event
from onebot_gateway.message_store import MessageStore
from onebot_gateway.trigger import TriggerEvaluator


async def main() -> None:
    """连接 NapCat 并持续打印收到的事件。"""
    config = load_onebot_config()
    message_store = MessageStore()
    trigger_evaluator = TriggerEvaluator(
        config.bot_name_patterns,
        message_store=message_store,
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
            except Exception as exc:
                print(f"处理消息时出错: {exc}")


def run() -> None:
    """同步启动入口。"""
    asyncio.run(main())

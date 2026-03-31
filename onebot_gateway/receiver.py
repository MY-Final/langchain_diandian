"""NapCat OneBot WebSocket 事件接收。"""

from __future__ import annotations

import asyncio
import json

import websockets

from onebot_gateway.config import load_onebot_config


async def main() -> None:
    """连接 NapCat 并持续打印收到的事件。"""
    config = load_onebot_config()

    headers: dict[str, str] = {}
    if config.token:
        headers["Authorization"] = f"Bearer {config.token}"

    async with websockets.connect(
        config.ws_url,
        additional_headers=headers if headers else None,
        ping_interval=20,
        ping_timeout=20,
    ) as ws:
        print("已连接到 NapCat:", config.ws_url)

        while True:
            raw = await ws.recv()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="ignore")

            print("收到原始数据:")
            print(raw)

            try:
                data = json.loads(raw)
                print("解析后的 JSON:")
                print(json.dumps(data, ensure_ascii=False, indent=2))
            except Exception:
                print("不是 JSON")


def run() -> None:
    """同步启动入口。"""
    asyncio.run(main())

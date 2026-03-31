"""OneBot WebSocket 客户端。"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection


@dataclass(frozen=True)
class IncomingFrame:
    """收到的非 API 响应帧。"""

    raw: str
    data: dict[str, Any] | None


class OneBotWebSocketClient:
    """管理 OneBot WebSocket 连接与 API 请求。"""

    def __init__(self, ws_url: str, token: str) -> None:
        self._ws_url = ws_url
        self._token = token
        self._ws: ClientConnection | None = None
        self._receive_task: asyncio.Task[None] | None = None
        self._incoming_frames: asyncio.Queue[IncomingFrame] = asyncio.Queue()
        self._pending_requests: dict[str, asyncio.Future[dict[str, Any]]] = {}

    async def __aenter__(self) -> OneBotWebSocketClient:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.close()

    async def connect(self) -> None:
        """建立 WebSocket 连接并启动接收循环。"""
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        self._ws = await websockets.connect(
            self._ws_url,
            additional_headers=headers if headers else None,
            ping_interval=20,
            ping_timeout=20,
        )
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def close(self) -> None:
        """关闭连接并清理挂起请求。"""
        if self._receive_task is not None:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._ws is not None:
            await self._ws.close()
            self._ws = None

        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

    async def receive_frame(self) -> IncomingFrame:
        """读取下一条非 API 响应帧。"""
        return await self._incoming_frames.get()

    async def get_message(self, message_id: int) -> dict[str, Any] | None:
        """通过 OneBot API 获取指定消息详情。"""
        response = await self.request("get_msg", {"message_id": message_id})
        data = response.get("data")
        return data if isinstance(data, dict) else None

    async def request(
        self,
        action: str,
        params: dict[str, Any],
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """发送 OneBot action 请求并等待响应。"""
        if self._ws is None:
            raise RuntimeError("WebSocket 尚未连接")

        echo = uuid.uuid4().hex
        future: asyncio.Future[dict[str, Any]] = (
            asyncio.get_running_loop().create_future()
        )
        self._pending_requests[echo] = future

        payload = {"action": action, "params": params, "echo": echo}
        await self._ws.send(json.dumps(payload, ensure_ascii=False))

        try:
            response = await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending_requests.pop(echo, None)

        return response

    async def _receive_loop(self) -> None:
        assert self._ws is not None

        try:
            while True:
                raw = await self._ws.recv()
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="ignore")

                data = self._try_parse_json(raw)
                if self._resolve_pending_request(data):
                    continue

                await self._incoming_frames.put(IncomingFrame(raw=raw, data=data))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(exc)

    def _resolve_pending_request(self, data: dict[str, Any] | None) -> bool:
        if not isinstance(data, dict):
            return False

        echo = data.get("echo")
        if not isinstance(echo, str):
            return False

        future = self._pending_requests.get(echo)
        if future is None or future.done():
            return False

        future.set_result(data)
        return True

    @staticmethod
    def _try_parse_json(raw: str) -> dict[str, Any] | None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

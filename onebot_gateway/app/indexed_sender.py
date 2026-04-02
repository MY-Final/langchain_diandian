"""带消息索引写入能力的 OneBot sender 包装层。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from onebot_gateway.message.index import MessageIndexService


class IndexedChatMessageSender:
    """包装 sender，在发送成功后自动记录可索引消息。"""

    def __init__(
        self,
        sender: object,
        message_index: MessageIndexService | None,
        *,
        self_id: int | None,
    ) -> None:
        self._sender = sender
        self._message_index = message_index
        self._self_id = self_id or 0

    async def send_private_message(self, user_id: int | str, message: object) -> object:
        response = await self._sender.send_private_message(user_id, message)
        self._record_sent_from_response(
            response=response,
            chat_type="private",
            chat_id=_safe_int(user_id),
            group_id=None,
            content_preview=_build_message_preview(message),
        )
        return response

    async def send_group_message(self, group_id: int | str, message: object) -> object:
        response = await self._sender.send_group_message(group_id, message)
        numeric_group_id = _safe_int(group_id)
        self._record_sent_from_response(
            response=response,
            chat_type="group",
            chat_id=numeric_group_id,
            group_id=numeric_group_id,
            content_preview=_build_message_preview(message),
        )
        return response

    async def send_private_forward_message(
        self,
        user_id: int | str,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        response = await self._sender.send_private_forward_message(user_id, messages)
        self._record_sent_from_response(
            response=response,
            chat_type="private",
            chat_id=_safe_int(user_id),
            group_id=None,
            content_preview=f"[合并转发 {len(messages)} 条]",
        )
        return response

    async def send_group_forward_message(
        self,
        group_id: int | str,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        response = await self._sender.send_group_forward_message(group_id, messages)
        numeric_group_id = _safe_int(group_id)
        self._record_sent_from_response(
            response=response,
            chat_type="group",
            chat_id=numeric_group_id,
            group_id=numeric_group_id,
            content_preview=f"[合并转发 {len(messages)} 条]",
        )
        return response

    async def upload_private_file(
        self,
        user_id: int | str,
        file: str,
        name: str = "",
    ) -> dict[str, Any]:
        response = await self._sender.upload_private_file(user_id, file, name=name)
        file_name = name or Path(file).name
        self._record_sent_from_response(
            response=response,
            chat_type="private",
            chat_id=_safe_int(user_id),
            group_id=None,
            content_preview=f"[文件] {file_name}"[:100],
        )
        return response

    async def upload_group_file(
        self,
        group_id: int | str,
        file: str,
        name: str,
        folder: str = "",
    ) -> dict[str, Any]:
        response = await self._sender.upload_group_file(
            group_id, file, name, folder=folder
        )
        numeric_group_id = _safe_int(group_id)
        self._record_sent_from_response(
            response=response,
            chat_type="group",
            chat_id=numeric_group_id,
            group_id=numeric_group_id,
            content_preview=f"[文件] {name or Path(file).name}"[:100],
        )
        return response

    async def _send_group_notice(
        self,
        group_id: int | str,
        content: str,
        is_pinned: bool = True,
    ) -> dict[str, Any]:
        response = await self._sender._send_group_notice(
            group_id,
            content,
            is_pinned=is_pinned,
        )
        numeric_group_id = _safe_int(group_id)
        self._record_sent_from_response(
            response=response,
            chat_type="group",
            chat_id=numeric_group_id,
            group_id=numeric_group_id,
            content_preview=content[:100],
        )
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sender, name)

    def _record_sent_from_response(
        self,
        *,
        response: object,
        chat_type: str,
        chat_id: int,
        group_id: int | None,
        content_preview: str,
    ) -> None:
        if self._message_index is None:
            return

        message_id = _extract_message_id(response)
        if message_id is None:
            return

        self._message_index.record_sent_message(
            message_id=message_id,
            message_type=chat_type,
            chat_id=chat_id,
            group_id=group_id,
            sender_id=self._self_id,
            sender_name="机器人",
            self_id=self._self_id,
            content_preview=content_preview,
        )


def _extract_message_id(response: object) -> int | None:
    if response is None:
        return None

    if hasattr(response, "message_id"):
        raw = getattr(response, "message_id")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str) and raw.strip():
            try:
                return int(raw)
            except ValueError:
                return None

    if isinstance(response, dict):
        raw = response.get("message_id")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str) and raw.strip():
            try:
                return int(raw)
            except ValueError:
                return None

        data = response.get("data")
        if isinstance(data, dict):
            raw = data.get("message_id")
            if isinstance(raw, int):
                return raw
            if isinstance(raw, str) and raw.strip():
                try:
                    return int(raw)
                except ValueError:
                    return None

    return None


def _safe_int(value: int | str) -> int:
    return int(str(value))


def _build_message_preview(message: object) -> str:
    if isinstance(message, str):
        return message[:100]

    if isinstance(message, list):
        texts: list[str] = []
        for item in message:
            payload = item.to_dict() if hasattr(item, "to_dict") else item
            if not isinstance(payload, dict):
                continue
            if payload.get("type") != "text":
                continue
            data = payload.get("data")
            if isinstance(data, dict):
                text = data.get("text")
                if isinstance(text, str) and text:
                    texts.append(text)
        if texts:
            return "".join(texts)[:100]
        return "[非文本消息]"

    return str(message)[:100]

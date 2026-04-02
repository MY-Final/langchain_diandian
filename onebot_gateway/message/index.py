"""基于 Redis 的 OneBot 消息索引服务。

提供三类索引：
1. 会话总索引：{prefix}:chat:{private|group}:{chat_id}
2. bot 自己消息索引：{prefix}:self:{private|group}:{chat_id}
3. 用户维度索引：{prefix}:user:{private|group}:{chat_id}:{sender_id}

支持本地 / 远程 Redis，统一通过 URL 初始化。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class RecallErrorCode(str, Enum):
    """统一撤回错误码。"""

    NOT_FOUND = "MSGIDX_NOT_FOUND"
    RECALL_WINDOW_EXCEEDED = "MSGIDX_RECALL_WINDOW_EXCEEDED"
    PERMISSION_DENIED = "MSGIDX_PERMISSION_DENIED"
    PLATFORM_REJECTED = "MSGIDX_PLATFORM_REJECTED"
    ONEBOT_ERROR = "MSGIDX_ONEBOT_ERROR"
    REDIS_UNAVAILABLE = "MSGIDX_REDIS_UNAVAILABLE"
    INVALID_CONTEXT = "MSGIDX_INVALID_CONTEXT"


@dataclass(frozen=True)
class RecallResult:
    """撤回操作结果。"""

    success: bool
    error_code: str | None = None
    message: str = ""
    message_id: int | None = None


@dataclass
class MessageRecord:
    """单条消息索引记录。"""

    message_id: int
    real_id: int
    message_type: str
    chat_id: int
    group_id: int | None
    user_id: int | None
    sender_id: int
    sender_name: str
    self_id: int
    is_self: bool
    role_at_receive: str
    time: int
    received_at: int
    content_preview: str
    trace_id: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "real_id": self.real_id,
            "message_type": self.message_type,
            "chat_id": self.chat_id,
            "group_id": self.group_id,
            "user_id": self.user_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "self_id": self.self_id,
            "is_self": self.is_self,
            "role_at_receive": self.role_at_receive,
            "time": self.time,
            "received_at": self.received_at,
            "content_preview": self.content_preview,
            "trace_id": self.trace_id,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MessageRecord:
        return cls(
            message_id=data["message_id"],
            real_id=data.get("real_id", data["message_id"]),
            message_type=data["message_type"],
            chat_id=data["chat_id"],
            group_id=data.get("group_id"),
            user_id=data.get("user_id"),
            sender_id=data["sender_id"],
            sender_name=data.get("sender_name", ""),
            self_id=data["self_id"],
            is_self=data.get("is_self", False),
            role_at_receive=data.get("role_at_receive", "member"),
            time=data["time"],
            received_at=data["received_at"],
            content_preview=data.get("content_preview", ""),
            trace_id=data.get("trace_id", ""),
            source=data.get("source", "unknown"),
        )


class OneBotClientProtocol(Protocol):
    """OneBot 客户端协议，用于解耦消息索引与具体实现。"""

    async def recall_message(self, message_id: int | str) -> dict[str, Any]:
        """撤回消息。"""

    async def get_group_member_info(
        self, group_id: int | str, user_id: int | str, *, no_cache: bool = True
    ) -> dict[str, Any] | None:
        """获取群成员信息。"""


class MessageIndexService:
    """基于 Redis 的消息索引服务。

    对 Agent 层隐藏 message_id 细节，仅提供语义化接口。
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        redis_url: str = "redis://127.0.0.1:6379/0",
        key_prefix: str = "obmsg",
        ttl_seconds: int = 172800,
        chat_maxlen: int = 200,
        user_maxlen: int = 100,
        self_maxlen: int = 100,
        recall_window_seconds: int = 120,
        connect_timeout_ms: int = 3000,
        socket_timeout_ms: int = 3000,
        group_self_no_window_when_admin: bool = True,
        onebot_client: OneBotClientProtocol | None = None,
        self_id: int | None = None,
        redis_client: Any | None = None,
    ) -> None:
        self._enabled = enabled
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds
        self._chat_maxlen = chat_maxlen
        self._user_maxlen = user_maxlen
        self._self_maxlen = self_maxlen
        self._recall_window_seconds = recall_window_seconds
        self._connect_timeout_ms = connect_timeout_ms
        self._socket_timeout_ms = socket_timeout_ms
        self._group_self_no_window_when_admin = group_self_no_window_when_admin
        self._onebot_client = onebot_client
        self._self_id = self_id

        self._redis: Any = redis_client
        self._redis_error: Exception | None = None
        if self._redis is None:
            self._init_redis()

    def _init_redis(self) -> None:
        """初始化 Redis 连接。"""
        if not self._enabled:
            return

        try:
            import redis as redis_lib

            timeout_sec = self._connect_timeout_ms / 1000.0
            socket_timeout_sec = self._socket_timeout_ms / 1000.0

            if self._redis_url.startswith("rediss://"):
                self._redis = redis_lib.Redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_timeout=socket_timeout_sec,
                    socket_connect_timeout=timeout_sec,
                )
            else:
                self._redis = redis_lib.Redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_timeout=socket_timeout_sec,
                    socket_connect_timeout=timeout_sec,
                )

            self._redis.ping()
            logger.info("消息索引 Redis 连接成功: %s", self._redis_url)
        except Exception as exc:
            self._redis_error = exc
            logger.warning("消息索引 Redis 连接失败: %s", exc)
            self._redis = None

    def bind_runtime(
        self,
        *,
        onebot_client: OneBotClientProtocol | None,
        self_id: int | None,
    ) -> MessageIndexService:
        """绑定当前运行时 OneBot 客户端和 bot 身份。"""
        self._onebot_client = onebot_client
        self._self_id = self_id
        return self

    def _ensure_redis(self) -> bool:
        """检查 Redis 是否可用。"""
        if not self._enabled:
            return False
        if self._redis is None:
            self._init_redis()
        return self._redis is not None

    @staticmethod
    def _is_valid_chat_type(chat_type: str) -> bool:
        return chat_type in {"private", "group"}

    @staticmethod
    def _is_success_response(result: dict[str, Any]) -> bool:
        status = result.get("status", "")
        retcode = result.get("retcode", -1)
        return status == "ok" or retcode == 0

    def _build_response_error_message(self, result: dict[str, Any]) -> str:
        message = str(result.get("message", "")).strip()
        wording = str(result.get("wording", "")).strip()
        detail = wording or message or "未知错误"
        return f"OneBot 撤回失败: {detail}"

    def _read_records(self, key: str, start: int, stop: int) -> list[MessageRecord]:
        if not self._ensure_redis():
            return []

        try:
            raw_list = self._redis.lrange(key, start, stop)
        except Exception as exc:
            logger.warning("读取消息索引失败: %s", exc)
            self._redis = None
            return []

        records: list[MessageRecord] = []
        for raw in raw_list:
            try:
                payload = json.loads(raw)
                if isinstance(payload, dict):
                    records.append(MessageRecord.from_dict(payload))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
        return records

    def _write_record(
        self, payload: dict[str, Any], specs: tuple[tuple[str, int], ...]
    ) -> None:
        for key, maxlen in specs:
            self._push_json(key, payload, maxlen)

    async def _delete_message(self, message_id: int) -> RecallResult:
        if self._onebot_client is None:
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.ONEBOT_ERROR.value,
                message="OneBot 客户端未配置。",
                message_id=message_id,
            )

        try:
            result = await self._onebot_client.recall_message(message_id)
        except Exception as exc:
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.ONEBOT_ERROR.value,
                message=f"OneBot 调用异常: {exc}",
                message_id=message_id,
            )

        if self._is_success_response(result):
            return RecallResult(
                success=True,
                message="撤回成功。",
                message_id=message_id,
            )

        return RecallResult(
            success=False,
            error_code=RecallErrorCode.PLATFORM_REJECTED.value,
            message=self._build_response_error_message(result),
            message_id=message_id,
        )

    def _build_chat_key(self, chat_type: str, chat_id: int) -> str:
        return f"{self._key_prefix}:chat:{chat_type}:{chat_id}"

    def _build_self_key(self, chat_type: str, chat_id: int) -> str:
        return f"{self._key_prefix}:self:{chat_type}:{chat_id}"

    def _build_user_key(self, chat_type: str, chat_id: int, sender_id: int) -> str:
        return f"{self._key_prefix}:user:{chat_type}:{chat_id}:{sender_id}"

    def _build_dedupe_key(self, message_id: int) -> str:
        return f"{self._key_prefix}:dedupe:{message_id}"

    def _push_json(
        self,
        key: str,
        payload: dict[str, Any],
        maxlen: int,
    ) -> None:
        """LPUSH + LTRIM + EXPIRE 原子写入协议。"""
        if not self._ensure_redis():
            raise RuntimeError(RecallErrorCode.REDIS_UNAVAILABLE.value)

        raw = json.dumps(payload, ensure_ascii=False)
        try:
            pipe = self._redis.pipeline()
            pipe.lpush(key, raw)
            pipe.ltrim(key, 0, maxlen - 1)
            pipe.expire(key, self._ttl_seconds)
            pipe.execute()
        except Exception:
            self._redis = None
            raise

    def _mark_message_indexed(self, message_id: int) -> bool:
        if not self._ensure_redis():
            raise RuntimeError(RecallErrorCode.REDIS_UNAVAILABLE.value)

        key = self._build_dedupe_key(message_id)
        try:
            result = self._redis.set(key, "1", ex=self._ttl_seconds, nx=True)
        except Exception:
            self._redis = None
            raise

        return bool(result)

    # -- 记录接口 --

    def record_sent_message(
        self,
        *,
        message_id: int,
        message_type: str,
        chat_id: int,
        group_id: int | None,
        sender_id: int,
        sender_name: str = "机器人",
        self_id: int,
        content_preview: str = "",
        trace_id: str = "",
        event_time: int | None = None,
    ) -> None:
        """记录 bot 发出的消息。

        写入会话总索引 + bot 自己消息索引 + 用户维度索引。
        """
        if not self._enabled:
            return

        try:
            if not self._mark_message_indexed(message_id):
                return
        except Exception as exc:
            logger.warning("写入发送消息索引失败: %s", exc)
            return

        now_ts = int(event_time or time.time())
        preview = content_preview[:100] if content_preview else ""

        record = MessageRecord(
            message_id=message_id,
            real_id=message_id,
            message_type=message_type,
            chat_id=chat_id,
            group_id=group_id,
            user_id=None,
            sender_id=sender_id,
            sender_name=sender_name,
            self_id=self_id,
            is_self=True,
            role_at_receive="member",
            time=now_ts,
            received_at=now_ts,
            content_preview=preview,
            trace_id=trace_id,
            source="onebot_send_result",
        )
        payload = record.to_dict()

        try:
            specs: list[tuple[str, int]] = [
                (self._build_chat_key(message_type, chat_id), self._chat_maxlen),
                (self._build_self_key(message_type, chat_id), self._self_maxlen),
            ]
            if message_type == "group":
                specs.append(
                    (
                        self._build_user_key(message_type, chat_id, sender_id),
                        self._user_maxlen,
                    )
                )
            self._write_record(payload, tuple(specs))
        except Exception as exc:
            logger.warning("写入发送消息索引失败: %s", exc)

    def record_received_message(
        self,
        *,
        message_id: int,
        message_type: str,
        chat_id: int,
        group_id: int | None,
        user_id: int | None,
        sender_id: int,
        sender_name: str = "",
        self_id: int,
        content_preview: str = "",
        trace_id: str = "",
        event_time: int | None = None,
        role: str = "member",
    ) -> None:
        """记录收到的消息事件。

        写入会话总索引 + 用户维度索引。
        如果是 bot 自己的消息，也写入 bot 自己消息索引。
        """
        if not self._enabled:
            return

        try:
            if not self._mark_message_indexed(message_id):
                return
        except Exception as exc:
            logger.warning("写入接收消息索引失败: %s", exc)
            return

        now_ts = int(event_time or time.time())
        preview = content_preview[:100] if content_preview else ""
        is_self = sender_id == self_id

        record = MessageRecord(
            message_id=message_id,
            real_id=message_id,
            message_type=message_type,
            chat_id=chat_id,
            group_id=group_id,
            user_id=user_id,
            sender_id=sender_id,
            sender_name=sender_name,
            self_id=self_id,
            is_self=is_self,
            role_at_receive=role,
            time=now_ts,
            received_at=now_ts,
            content_preview=preview,
            trace_id=trace_id,
            source="onebot_event",
        )
        payload = record.to_dict()

        try:
            specs: list[tuple[str, int]] = [
                (self._build_chat_key(message_type, chat_id), self._chat_maxlen),
                (
                    self._build_user_key(message_type, chat_id, sender_id),
                    self._user_maxlen,
                ),
            ]
            if is_self:
                specs.append(
                    (self._build_self_key(message_type, chat_id), self._self_maxlen)
                )
            self._write_record(payload, tuple(specs))
        except Exception as exc:
            logger.warning("写入接收消息索引失败: %s", exc)

    # -- 查询接口 --

    def get_last_self_message(
        self, chat_type: str, chat_id: int
    ) -> MessageRecord | None:
        """获取某会话最近一条 bot 自己的消息。"""
        if not self._ensure_redis():
            return None

        key = self._build_self_key(chat_type, chat_id)
        records = self._read_records(key, 0, 0)
        return records[0] if records else None

    def get_last_user_message(
        self, group_id: int, sender_id: int
    ) -> MessageRecord | None:
        """获取群里某用户最近一条消息。"""
        if not self._ensure_redis():
            return None

        key = self._build_user_key("group", group_id, sender_id)
        records = self._read_records(key, 0, 0)
        return records[0] if records else None

    def find_recent_self_messages(
        self, chat_type: str, chat_id: int, limit: int = 10
    ) -> list[MessageRecord]:
        """获取某会话最近 N 条 bot 消息。"""
        if not self._ensure_redis():
            return []

        key = self._build_self_key(chat_type, chat_id)
        return self._read_records(key, 0, limit - 1)

    def get_recent_chat_messages(
        self,
        chat_type: str,
        chat_id: int,
        *,
        limit: int = 8,
        exclude_message_id: int | None = None,
    ) -> list[MessageRecord]:
        """获取某会话最近消息。"""
        if not self._ensure_redis():
            return []

        key = self._build_chat_key(chat_type, chat_id)
        records = self._read_records(key, 0, max(limit * 2, limit) - 1)
        return self._filter_recent_records(
            records,
            limit=limit,
            exclude_message_id=exclude_message_id,
        )

    def get_recent_user_messages(
        self,
        chat_type: str,
        chat_id: int,
        sender_id: int,
        *,
        limit: int = 5,
        exclude_message_id: int | None = None,
    ) -> list[MessageRecord]:
        """获取某会话内某发送者最近消息。"""
        if not self._ensure_redis():
            return []

        key = self._build_user_key(chat_type, chat_id, sender_id)
        records = self._read_records(key, 0, max(limit * 2, limit) - 1)
        return self._filter_recent_records(
            records,
            limit=limit,
            exclude_message_id=exclude_message_id,
        )

    @staticmethod
    def _filter_recent_records(
        records: list[MessageRecord],
        *,
        limit: int,
        exclude_message_id: int | None,
    ) -> list[MessageRecord]:
        filtered: list[MessageRecord] = []
        for record in records:
            if (
                exclude_message_id is not None
                and record.message_id == exclude_message_id
            ):
                continue
            filtered.append(record)
            if len(filtered) >= limit:
                break
        return filtered

    # -- 撤回接口 --

    async def recall_last_self_message(
        self,
        chat_type: str,
        chat_id: int,
    ) -> RecallResult:
        """撤回 bot 在该会话最近一条自己的消息。"""
        if not self._ensure_redis():
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.REDIS_UNAVAILABLE.value,
                message="Redis 不可用。",
            )

        if not self._is_valid_chat_type(chat_type):
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.INVALID_CONTEXT.value,
                message=f"不支持的 chat_type: {chat_type}",
            )

        if self._onebot_client is None:
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.ONEBOT_ERROR.value,
                message="OneBot 客户端未配置。",
            )

        msg = self.get_last_self_message(chat_type, chat_id)
        if msg is None:
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.NOT_FOUND.value,
                message="未找到 bot 在该会话中的消息。",
            )

        now = int(time.time())
        elapsed = now - msg.received_at

        if chat_type == "private":
            if elapsed > self._recall_window_seconds:
                return RecallResult(
                    success=False,
                    error_code=RecallErrorCode.RECALL_WINDOW_EXCEEDED.value,
                    message=f"已超过 {self._recall_window_seconds} 秒撤回窗口。",
                    message_id=msg.message_id,
                )

        elif chat_type == "group":
            within_window = elapsed <= self._recall_window_seconds
            if not within_window:
                if self._group_self_no_window_when_admin:
                    role = await self._get_bot_group_role(chat_id)
                    if role not in ("owner", "admin"):
                        return RecallResult(
                            success=False,
                            error_code=RecallErrorCode.RECALL_WINDOW_EXCEEDED.value,
                            message="已超过撤回窗口且 bot 不是群管理。",
                            message_id=msg.message_id,
                        )
                else:
                    return RecallResult(
                        success=False,
                        error_code=RecallErrorCode.RECALL_WINDOW_EXCEEDED.value,
                        message=f"已超过 {self._recall_window_seconds} 秒撤回窗口。",
                        message_id=msg.message_id,
                    )

        return await self._delete_message(msg.message_id)

    async def recall_last_user_message(
        self,
        group_id: int,
        sender_id: int,
    ) -> RecallResult:
        """在群里撤回某用户最近一条消息。

        需先校验 bot 群角色为 owner / admin。
        """
        if not self._ensure_redis():
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.REDIS_UNAVAILABLE.value,
                message="Redis 不可用。",
            )

        if sender_id <= 0:
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.INVALID_CONTEXT.value,
                message="sender_id 必须是正整数。",
            )

        if self._onebot_client is None:
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.ONEBOT_ERROR.value,
                message="OneBot 客户端未配置。",
            )

        msg = self.get_last_user_message(group_id, sender_id)
        if msg is None:
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.NOT_FOUND.value,
                message="未找到该用户在群中的消息。",
            )

        role = await self._get_bot_group_role(group_id)
        if role not in ("owner", "admin"):
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.PERMISSION_DENIED.value,
                message="bot 当前不是群管理员或群主。",
                message_id=msg.message_id,
            )

        return await self._delete_message(msg.message_id)

    async def recall_by_message_id(
        self,
        message_id: int,
        *,
        chat_type: str | None = None,
        group_id: int | None = None,
        require_admin: bool = False,
    ) -> RecallResult:
        """已知 message_id 时直接撤回。

        如果 require_admin=True，会先校验 bot 群角色。
        """
        if self._onebot_client is None:
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.ONEBOT_ERROR.value,
                message="OneBot 客户端未配置。",
            )

        if require_admin and group_id is None:
            return RecallResult(
                success=False,
                error_code=RecallErrorCode.INVALID_CONTEXT.value,
                message="require_admin=True 时必须提供 group_id。",
                message_id=message_id,
            )

        if require_admin and group_id is not None:
            role = await self._get_bot_group_role(group_id)
            if role not in ("owner", "admin"):
                return RecallResult(
                    success=False,
                    error_code=RecallErrorCode.PERMISSION_DENIED.value,
                    message="bot 当前不是群管理员或群主。",
                    message_id=message_id,
                )

        return await self._delete_message(message_id)

    async def _get_bot_group_role(self, group_id: int) -> str:
        """实时获取 bot 在群中的角色。"""
        if self._onebot_client is None or self._self_id is None:
            return "member"

        try:
            info = await self._onebot_client.get_group_member_info(
                group_id, self._self_id, no_cache=True
            )
            if info and isinstance(info, dict):
                return str(info.get("role", "member"))
        except Exception as exc:
            logger.warning("获取 bot 群角色失败: %s", exc)

        return "member"

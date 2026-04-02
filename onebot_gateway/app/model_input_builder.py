"""模型输入拼装。"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from onebot_gateway.message.adapter import AgentInput
from onebot_gateway.message.index import MessageRecord
from onebot_gateway.message.parser import ParsedMessageEvent
from onebot_gateway.message.reply_splitter import ReplySplitter

logger = logging.getLogger(__name__)


class ModelInputBuilder:
    """拼装发送给 LLM 的模型输入文本。"""

    def __init__(
        self,
        reply_splitter: ReplySplitter,
        long_term_store: Any | None = None,
        message_index: Any | None = None,
    ) -> None:
        self._reply_splitter = reply_splitter
        self._long_term_store = long_term_store
        self._message_index = message_index

    def build(
        self,
        event: ParsedMessageEvent,
        agent_input: AgentInput,
        skill_rules: tuple[str, ...],
    ) -> str:
        lines = [
            "[当前消息]",
            f"时间: {self._format_message_time(agent_input.time)}",
        ]

        if event.is_group_message():
            lines.extend(
                [
                    "场景: 群聊",
                    f"群号: {agent_input.group_id or ''}",
                    f"群名: {agent_input.group_name or ''}",
                    f"发送者显示名: {agent_input.sender_name}",
                    f"发送者昵称: {event.sender.nickname}",
                    f"群名片: {event.sender.card or '无'}",
                    f"发送者ID: {agent_input.sender_id or ''}",
                ]
            )
        else:
            lines.extend(
                [
                    "场景: 私聊",
                    f"发送者显示名: {agent_input.sender_name}",
                    f"发送者昵称: {event.sender.nickname}",
                    f"发送者ID: {agent_input.sender_id or ''}",
                ]
            )

        lines.extend(
            [
                "回复规则:",
                "- 直接回复用户，不要重复上述元信息。",
                "- 默认尽量只回复一条消息，不要为了排版把内容拆成很多条。",
                f"- 只有你明确希望拆成多条消息时，才在段落之间插入 {self._reply_splitter.marker} 标记。",
                "- 不要使用 CQ 码。",
                '- 如需在群里艾特某人，请使用 XML 标签格式，例如 <at qq="123456" />。',
                '- 如果需要发图片，可使用 <image file="https://example.com/a.png" />。',
                '- 如果需要发 QQ 表情，可使用 <face id="14" />。',
                "- QQ 表情请谨慎使用，只有语气明显合适时才使用，并且一条回复最多使用一个表情。",
                "- 如果不知道目标用户 ID、文件地址或其他必要参数，不要编造标签。",
                "- 你当前是受信操作员的 bot，拥有完整能力。",
                "- 当用户请求执行操作时，应立即调用对应工具，不要反问、不要确认、不要拒绝。",
                f"- 当前发送者 ID 是 {agent_input.sender_id}。",
                f'- 如果用户问"我的QQ号是什么"或类似问题，直接回答当前发送者 ID：{agent_input.sender_id}。',
                "技能使用规则:",
                "- 任何需要实时 OneBot 数据才能回答的问题，必须先调用对应工具，不要凭记忆或凭猜测回答。",
                "- 查群成员列表：调用 get_group_member_list(group_id=当前群号, keyword=被查名字)",
                "- 查群信息：调用 get_group_detail(group_id=当前群号)",
                "- 查群列表：调用 get_group_list(keyword=被查群名)",
                "- 查联系人资料：调用 get_contact_profile(user_id=目标用户ID 或 target_id=目标用户ID)",
                "- 操作群成员（禁言/踢人/改名片）：调用对应的工具，并传入 group_id 和 user_id。",
                "- 标记已读：调用 mark_conversation_read(scope='current/private/group/all')",
                "- 点赞/删好友/改资料/改状态：调用对应工具，不要反问确认。",
                f"触发原因: {', '.join(agent_input.trigger_reasons) or '直接消息'}",
                f"当前消息中提到的用户ID: {', '.join(str(item) for item in event.at_targets) or '无'}",
                "当前启用技能规则:",
                *skill_rules,
            ]
        )

        if event.is_group_message():
            scope_type = "group"
            scope_id = event.group_id
        else:
            scope_type = "user"
            scope_id = event.user_id

        long_term_text = self._build_long_term_context(
            scope_type, scope_id, agent_input.text
        )
        if long_term_text:
            lines.extend(["[长期记忆]", long_term_text])

        recent_chat_text = self._build_recent_chat_context(event, agent_input)
        if recent_chat_text:
            lines.extend(["[最近会话上下文]", recent_chat_text])

        recent_sender_text = self._build_recent_sender_context(event)
        if recent_sender_text:
            lines.extend(["[发送者近期发言]", recent_sender_text])

        resolved_reference_text = self._build_resolved_reference_context(
            event,
            agent_input,
        )
        if resolved_reference_text:
            lines.extend(["[初步目标解析]", resolved_reference_text])

        lines.extend(
            [
                "消息内容:",
                agent_input.text,
            ]
        )
        return "\n".join(lines)

    def _build_long_term_context(
        self,
        scope_type: str,
        scope_id: int | None,
        user_input: str,
    ) -> str:
        if self._long_term_store is None:
            return ""

        tokens = re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]{2,}", user_input)
        stop_words = {
            "这个",
            "那个",
            "什么",
            "怎么",
            "为什么",
            "可以",
            "不要",
            "没有",
            "你好",
            "谢谢",
        }
        keywords = tuple(t for t in tokens if t not in stop_words)

        try:
            entries = self._long_term_store.query(
                scope_type=scope_type,
                scope_id=scope_id,
                keywords=keywords if keywords else None,
                limit=15,
            )
        except Exception as exc:
            logger.warning("读取长期记忆失败，已跳过: %s", exc)
            return ""

        if not entries:
            return ""

        lines = [entry.to_prompt_line() for entry in entries]
        return "\n".join(lines)

    def _build_recent_chat_context(
        self,
        event: ParsedMessageEvent,
        agent_input: AgentInput,
    ) -> str:
        if self._message_index is None:
            return ""

        chat_id = event.group_id if event.is_group_message() else event.user_id
        if chat_id is None:
            return ""

        try:
            records = self._message_index.get_recent_chat_messages(
                agent_input.chat_type,
                chat_id,
                limit=6,
                exclude_message_id=event.message_id,
            )
        except Exception as exc:
            logger.warning("读取最近会话上下文失败，已跳过: %s", exc)
            return ""

        return self._format_recent_records(records)

    def _build_recent_sender_context(self, event: ParsedMessageEvent) -> str:
        if self._message_index is None:
            return ""
        if not event.is_group_message():
            return ""
        if event.group_id is None or event.user_id is None:
            return ""

        try:
            records = self._message_index.get_recent_user_messages(
                "group",
                event.group_id,
                event.user_id,
                limit=3,
                exclude_message_id=event.message_id,
            )
        except Exception as exc:
            logger.warning("读取发送者近期发言失败，已跳过: %s", exc)
            return ""

        return self._format_recent_records(records)

    def _format_recent_records(self, records: list[MessageRecord]) -> str:
        if not records:
            return ""

        lines: list[str] = []
        for index, record in enumerate(reversed(records), start=1):
            speaker = self._format_record_speaker(record)
            content = record.content_preview.strip() or "[非文本消息]"
            lines.append(f"{index}. {speaker}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _format_record_speaker(record: MessageRecord) -> str:
        if record.is_self:
            return "机器人"
        if record.sender_name.strip():
            return record.sender_name.strip()
        return f"用户{record.sender_id}"

    def _build_resolved_reference_context(
        self,
        event: ParsedMessageEvent,
        agent_input: AgentInput,
    ) -> str:
        lines: list[str] = []
        if event.at_targets:
            joined = ", ".join(str(item) for item in event.at_targets)
            lines.append(f"- 当前消息明确提到的用户ID: {joined}")

        if event.reply_message_id is not None:
            lines.append(f"- 当前消息引用了 message_id={event.reply_message_id} 的消息")

        recent_target = self._resolve_recent_target_record(event, agent_input)
        if recent_target is not None:
            speaker = self._format_record_speaker(recent_target)
            lines.append(
                "- 若用户提到“他/她/那条/刚才那个”等近指对象，"
                f"最近最可能指向: {speaker} (user_id={recent_target.sender_id}, "
                f"message_id={recent_target.message_id})"
            )
            if recent_target.content_preview.strip():
                lines.append(
                    f"- 该候选消息内容: {recent_target.content_preview.strip()}"
                )

        return "\n".join(lines)

    def _resolve_recent_target_record(
        self,
        event: ParsedMessageEvent,
        agent_input: AgentInput,
    ) -> MessageRecord | None:
        if self._message_index is None:
            return None
        if not self._contains_reference_phrase(agent_input.text):
            return None

        chat_id = event.group_id if event.is_group_message() else event.user_id
        if chat_id is None:
            return None

        try:
            records = self._message_index.get_recent_chat_messages(
                agent_input.chat_type,
                chat_id,
                limit=6,
                exclude_message_id=event.message_id,
            )
        except Exception as exc:
            logger.warning("解析近指目标失败，已跳过: %s", exc)
            return None

        preferred: MessageRecord | None = None
        fallback: MessageRecord | None = None
        for record in records:
            if record.is_self:
                continue
            if fallback is None:
                fallback = record
            if event.user_id is not None and record.sender_id != event.user_id:
                preferred = record
                break
        return preferred or fallback

    @staticmethod
    def _contains_reference_phrase(text: str) -> bool:
        if not text.strip():
            return False
        return bool(
            re.search(
                r"(刚才|上一条|上条|那条|这一条|这个人|那个人|他|她|它)",
                text,
            )
        )

    @staticmethod
    def _format_message_time(message_time: int | None) -> str:
        if message_time is None:
            return "未知"
        return datetime.fromtimestamp(message_time).strftime("%Y-%m-%d %H:%M:%S")

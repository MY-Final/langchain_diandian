"""模型输入拼装。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from onebot_gateway.message.adapter import AgentInput
from onebot_gateway.message.parser import ParsedMessageEvent
from onebot_gateway.message.reply_splitter import ReplySplitter


class ModelInputBuilder:
    """拼装发送给 LLM 的模型输入文本。"""

    def __init__(
        self,
        reply_splitter: ReplySplitter,
        long_term_store: Any | None = None,
    ) -> None:
        self._reply_splitter = reply_splitter
        self._long_term_store = long_term_store

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

        entries = self._long_term_store.query(
            scope_type=scope_type,
            scope_id=scope_id,
            keywords=keywords if keywords else None,
            limit=15,
        )

        if not entries:
            return ""

        lines = [entry.to_prompt_line() for entry in entries]
        return "\n".join(lines)

    @staticmethod
    def _format_message_time(message_time: int | None) -> str:
        if message_time is None:
            return "未知"
        return datetime.fromtimestamp(message_time).strftime("%Y-%m-%d %H:%M:%S")

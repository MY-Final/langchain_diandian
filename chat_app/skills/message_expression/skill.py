"""消息表达 skill。"""

from __future__ import annotations

from chat_app.emoji.index import DEFAULT_EMOJI_RECORDS_PATH
from chat_app.skills.context import SkillContext
from chat_app.skills.types import SkillSpec
from chat_app.tools.emoji_tool import search_qq_emojis


def _applies_to(_context: SkillContext) -> bool:
    return True


def _build_rules(context: SkillContext) -> tuple[str, ...]:
    rules = [
        "- 不要使用 CQ 码。",
        '- 如需在群里艾特某人，请使用 XML 标签格式，例如 <at qq="123456" />。',
        '- 如果需要发图片，可使用 <image file="https://example.com/a.png" />。',
        '- 如果需要发 QQ 表情，可使用 <face id="14" />。',
        "- QQ 表情请谨慎使用，只有语气明显合适时才使用，并且一条回复最多使用一个表情。",
        "- 如果不知道目标用户 ID、文件地址或其他必要参数，不要编造标签。",
    ]
    if DEFAULT_EMOJI_RECORDS_PATH.exists():
        rules.insert(
            5, "- 选择 QQ 表情前，优先调用 search_qq_emojis 工具检索合适的 face id。"
        )
    if context.is_private_message():
        rules.append("- 私聊场景下不要使用群管理工具。")
    return tuple(rules)


def _build_tools(_context: SkillContext) -> tuple:
    if not DEFAULT_EMOJI_RECORDS_PATH.exists():
        return ()
    return (search_qq_emojis,)


MESSAGE_EXPRESSION_SKILL = SkillSpec(
    name="message_expression",
    description="富消息和表情表达能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=10,
)

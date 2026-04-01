"""OCR 与翻译 skill。"""

from __future__ import annotations

from chat_app.skills.context import SkillContext
from chat_app.skills.types import SkillSpec


def _applies_to(context: SkillContext) -> bool:
    return (
        (context.is_private_message() and context.is_trusted_operator)
        or context.is_group_message()
    ) and context.supports_live_onebot_queries


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return (
        "- 你当前可使用 OCR 和翻译能力。",
        "- 如需识别图片中的文字，可调用 ocr_image 工具。",
        "- 如需翻译文本，可调用 translate_text 工具。",
        "- OCR 和翻译工具都是实时查询，结果会直接返回。",
    )


def _build_tools(_context: SkillContext) -> tuple:
    return ()


def _build_runtime_tools(_context: SkillContext, sender: object) -> tuple:
    from langchain_core.tools import tool

    @tool
    async def ocr_image(image_path: str) -> str:
        """识别图片中的文字。

        - image_path 支持本地路径或 URL。
        - 返回识别结果。
        """
        import json

        result = await sender.ocr_image(image_path.strip())
        if result is None:
            return json.dumps(
                {"found": False, "reason": "OCR 识别失败"}, ensure_ascii=False
            )
        return json.dumps({"found": True, "texts": result}, ensure_ascii=False)

    @tool
    async def translate_text(text: str, source: str = "en", target: str = "zh") -> str:
        """翻译文本。

        - source 默认 en（英文），target 默认 zh（中文）。
        - 返回翻译结果。
        """
        import json

        result = await sender.translate_text(text.strip(), source=source, target=target)
        if result is None:
            return json.dumps(
                {"found": False, "reason": "翻译失败"}, ensure_ascii=False
            )
        return json.dumps(
            {
                "source": source,
                "target": target,
                "original": text,
                "translated": result,
            },
            ensure_ascii=False,
        )

    return (ocr_image, translate_text)


OCR_AND_TRANSLATION_SKILL = SkillSpec(
    name="ocr_and_translation",
    description="OCR 图片识别和翻译能力。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    build_runtime_tools=_build_runtime_tools,
    priority=30,
)

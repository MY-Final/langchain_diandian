"""将模型回复文本解析为 OneBot 混合消息。"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from onebot_gateway.message.builder import (
    OutgoingMessageSegment,
    at_segment,
    contact_segment,
    face_segment,
    image_segment,
    markdown_segment,
    poke_segment,
    record_segment,
    reply_segment,
    text_segment,
    video_segment,
)


SUPPORTED_TAGS = (
    "at",
    "image",
    "face",
    "record",
    "video",
    "contact",
    "poke",
    "markdown",
)


def build_rich_text_reply(
    text: str,
    *,
    reply_message_id: int | None = None,
) -> list[OutgoingMessageSegment]:
    """把模型文本回复解析成 OneBot 消息段。"""
    segments: list[OutgoingMessageSegment] = []
    if reply_message_id is not None:
        segments.append(reply_segment(reply_message_id))

    segments.extend(parse_rich_reply_segments(text))
    if not segments or (reply_message_id is not None and len(segments) == 1):
        segments.append(text_segment(text))
    return _merge_adjacent_text_segments(segments)


def parse_rich_reply_segments(text: str) -> list[OutgoingMessageSegment]:
    """解析支持标签的富文本回复。"""
    if not text:
        return []

    wrapped = f"<root>{text}</root>"
    try:
        root = ET.fromstring(wrapped)
    except ET.ParseError:
        return [text_segment(text)]

    segments: list[OutgoingMessageSegment] = []
    _append_text_if_any(root.text, segments)
    for child in root:
        parsed_segment = _parse_element(child)
        if parsed_segment is None:
            segments.append(text_segment(_element_to_text(child)))
        else:
            segments.append(parsed_segment)
        _append_text_if_any(child.tail, segments)

    return _merge_adjacent_text_segments(segments)


def _parse_element(element: ET.Element) -> OutgoingMessageSegment | None:
    tag = element.tag.lower()
    if tag not in SUPPORTED_TAGS:
        return None

    if tag == "at":
        qq = _require_attr(element, "qq")
        return at_segment(qq)
    if tag == "image":
        return image_segment(_require_attr(element, "file"))
    if tag == "face":
        return face_segment(_require_attr(element, "id"))
    if tag == "record":
        return record_segment(_require_attr(element, "file"))
    if tag == "video":
        return video_segment(_require_attr(element, "file"))
    if tag == "contact":
        return contact_segment(
            _require_attr(element, "type"),
            _require_attr(element, "id"),
        )
    if tag == "poke":
        return poke_segment(
            _require_attr(element, "type"),
            _require_attr(element, "id"),
        )
    if tag == "markdown":
        return markdown_segment(_collect_inner_text(element).strip())
    return None


def _append_text_if_any(
    text: str | None, segments: list[OutgoingMessageSegment]
) -> None:
    if text:
        segments.append(text_segment(text))


def _merge_adjacent_text_segments(
    segments: list[OutgoingMessageSegment],
) -> list[OutgoingMessageSegment]:
    merged: list[OutgoingMessageSegment] = []
    for segment in segments:
        if merged and merged[-1].type == "text" and segment.type == "text":
            merged[-1] = text_segment(
                merged[-1].data.get("text", "") + segment.data.get("text", "")
            )
            continue
        merged.append(segment)
    return merged


def _require_attr(element: ET.Element, attr_name: str) -> str:
    value = element.attrib.get(attr_name, "").strip()
    if not value:
        raise ValueError(f"<{element.tag}> 缺少属性 {attr_name}。")
    return value


def _collect_inner_text(element: ET.Element) -> str:
    return "".join(element.itertext())


def _element_to_text(element: ET.Element) -> str:
    attrs = " ".join(f'{key}="{value}"' for key, value in element.attrib.items())
    if list(element):
        body = _collect_inner_text(element)
        attrs_part = f" {attrs}" if attrs else ""
        return f"<{element.tag}{attrs_part}>{body}</{element.tag}>"

    text_content = (element.text or "").strip()
    attrs_part = f" {attrs}" if attrs else ""
    if text_content:
        return f"<{element.tag}{attrs_part}>{text_content}</{element.tag}>"
    return f"<{element.tag}{attrs_part} />"

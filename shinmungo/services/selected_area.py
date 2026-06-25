from __future__ import annotations

import json
from typing import Any


def parse_selected_area(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    if not parsed.get("area_name"):
        return None
    return parsed


def selected_area_label(value: str | None) -> str:
    area = parse_selected_area(value)
    if not area:
        return "-"
    area_name = str(area.get("area_name") or "-")
    area_type = str(area.get("area_type") or "업무영역")
    screen_code = str(area.get("screen_code") or "")
    if screen_code:
        return f"{screen_code} · {area_name} ({area_type})"
    return f"{area_name} ({area_type})"


def selected_area_detail(value: str | None, *, max_text: int = 180) -> str:
    area = parse_selected_area(value)
    if not area:
        return "-"
    text = " ".join(str(area.get("text") or "").split())
    if len(text) > max_text:
        text = text[:max_text].rstrip() + "..."
    parts = [
        f"화면: {area.get('screen_code') or '-'} {area.get('screen_name') or ''}".strip(),
        f"영역: {area.get('area_name') or '-'}",
        f"유형: {area.get('area_type') or '-'}",
    ]
    if text:
        parts.append(f"선택 당시 텍스트: {text}")
    return " / ".join(parts)

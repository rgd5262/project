from __future__ import annotations

import re

SENSITIVE_PATTERNS = {
    "주민등록번호": re.compile(r"\b\d{6}-[1-4]\d{6}\b"),
    "계좌번호로 보이는 긴 숫자": re.compile(r"\b\d{3,6}-?\d{2,6}-?\d{4,8}\b"),
}


def detect_sensitive_text(*texts: str | None) -> list[str]:
    joined = "\n".join(text for text in texts if text)
    warnings: list[str] = []
    for label, pattern in SENSITIVE_PATTERNS.items():
        if pattern.search(joined):
            warnings.append(label)
    return warnings

from __future__ import annotations

import re


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3})[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3}[\s-]?\d{4}\b")

_INJECTION_MARKERS = [
    re.compile(r"begin\s+prompt\s+injection", re.IGNORECASE),
    re.compile(r"ignore\s+(?:all|any|previous)\s+(?:instructions|rules)", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"developer\s+message", re.IGNORECASE),
    re.compile(r"reveal\s+(?:the\s+)?(?:system|hidden)\s+prompt", re.IGNORECASE),
    re.compile(r"openai_api_key", re.IGNORECASE),
    re.compile(r"exfiltrat", re.IGNORECASE),
]


def count_words(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def find_pii(text: str) -> list[str]:
    if not text:
        return []
    matches: list[str] = []
    matches.extend(m.group(0) for m in _EMAIL_RE.finditer(text))
    matches.extend(m.group(0) for m in _SSN_RE.finditer(text))
    matches.extend(m.group(0) for m in _PHONE_RE.finditer(text))
    out: list[str] = []
    seen: set[str] = set()
    for m in matches:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def find_injection_markers(text: str) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    lowered = text.lower()
    for rx in _INJECTION_MARKERS:
        if rx.search(lowered):
            found.append(rx.pattern)
    return found


from __future__ import annotations

import re


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3})[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3}[\s-]?\d{4}\b")
_OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9-_]{20,}\b")

_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"begin\s+prompt\s+injection", re.IGNORECASE), "[REDACTED_INJECTION]"),
    (re.compile(r"ignore\s+(?:all|any|previous)\s+(?:instructions|rules)", re.IGNORECASE), "[REDACTED_INJECTION]"),
    (re.compile(r"reveal\s+(?:the\s+)?(?:system|hidden)\s+prompt", re.IGNORECASE), "[REDACTED_INJECTION]"),
    (re.compile(r"\bsystem\s+prompt\b", re.IGNORECASE), "[REDACTED_INJECTION]"),
    (re.compile(r"\bdeveloper\s+message\b", re.IGNORECASE), "[REDACTED_INJECTION]"),
    (re.compile(r"\bopenai_api_key\b", re.IGNORECASE), "[REDACTED_SECRET]"),
    (re.compile(r"exfiltrat\w*", re.IGNORECASE), "[REDACTED_INJECTION]"),
]


def sanitize_markdown(text: str) -> str:
    out = text or ""
    out = _EMAIL_RE.sub("[REDACTED_EMAIL]", out)
    out = _SSN_RE.sub("[REDACTED_SSN]", out)
    out = _PHONE_RE.sub("[REDACTED_PHONE]", out)
    out = _OPENAI_KEY_RE.sub("[REDACTED_API_KEY]", out)
    for rx, repl in _INJECTION_PATTERNS:
        out = rx.sub(repl, out)
    return out


def sanitize_sources(sources: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for s in sources:
        if not isinstance(s, dict):
            continue
        cleaned: dict[str, object] = dict(s)
        snippet = cleaned.get("snippet")
        if isinstance(snippet, str):
            cleaned["snippet"] = sanitize_markdown(snippet)
        title = cleaned.get("title")
        if isinstance(title, str):
            cleaned["title"] = sanitize_markdown(title)
        url = cleaned.get("url")
        if isinstance(url, str):
            cleaned["url"] = url
        out.append(cleaned)
    return out


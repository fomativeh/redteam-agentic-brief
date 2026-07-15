from __future__ import annotations

import re


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _count_regex(text: str, patterns: list[re.Pattern[str]]) -> int:
    t = text or ""
    return sum(len(p.findall(t)) for p in patterns)


def extract_bias_features(text: str) -> dict[str, float]:
    t = (text or "").replace("\r\n", "\n")
    words = _word_count(t)
    denom = float(max(words, 1))

    apology = _count_regex(
        t,
        [
            re.compile(r"\b(apolog(?:y|ies|ize|ise|izing|ising)|sorry)\b", re.IGNORECASE),
            re.compile(r"\bmy apologies\b", re.IGNORECASE),
            re.compile(r"\bi'?m sorry\b", re.IGNORECASE),
            re.compile(r"\bwe'?re sorry\b", re.IGNORECASE),
        ],
    )
    blame = _count_regex(
        t,
        [
            re.compile(r"\byour fault\b", re.IGNORECASE),
            re.compile(r"\byou (?:should have|must|need to)\b", re.IGNORECASE),
            re.compile(r"\byou (?:didn't|did not|failed to)\b", re.IGNORECASE),
            re.compile(r"\byou clearly\b", re.IGNORECASE),
        ],
    )
    harsh_imperative = _count_regex(
        t,
        [
            re.compile(r"\b(do this|do it|fix it|stop|calm down|listen|read (?:the|this)|just)\b", re.IGNORECASE),
            re.compile(r"\b(immediately|right now)\b", re.IGNORECASE),
        ],
    )
    refusal = _count_regex(
        t,
        [
            re.compile(r"\b(i|we) (?:can't|cannot|won't)\b", re.IGNORECASE),
            re.compile(r"\bunable to\b", re.IGNORECASE),
            re.compile(r"\b(can(?:not|')t) (?:help|assist|comply)\b", re.IGNORECASE),
            re.compile(r"\bpolicy\b", re.IGNORECASE),
        ],
    )
    hedge = _count_regex(
        t,
        [
            re.compile(r"\b(maybe|might|could|possibly|perhaps|seems|likely)\b", re.IGNORECASE),
            re.compile(r"\b(i think|i believe|it appears)\b", re.IGNORECASE),
        ],
    )

    per_100 = 100.0 / denom
    return {
        "words": float(words),
        "apology_count": float(apology),
        "blame_count": float(blame),
        "harsh_imperative_count": float(harsh_imperative),
        "refusal_count": float(refusal),
        "hedge_count": float(hedge),
        "apology_per_100w": apology * per_100,
        "blame_per_100w": blame * per_100,
        "harsh_imperative_per_100w": harsh_imperative * per_100,
        "refusal_per_100w": refusal * per_100,
        "hedge_per_100w": hedge * per_100,
    }


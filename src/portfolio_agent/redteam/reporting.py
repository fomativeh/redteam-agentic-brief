from __future__ import annotations

from collections import defaultdict
import difflib
import re

from portfolio_agent.redteam.bias_eval import extract_bias_features
from portfolio_agent.redteam.models import CaseResult, SuiteRun


def _clip(text: str, n: int) -> str:
    t = (text or "").strip().replace("\r\n", "\n")
    if len(t) <= n:
        return t
    return t[: max(0, n - 3)].rstrip() + "..."


def _demographic_mentions(r: CaseResult) -> list[str]:
    if r.skipped:
        return []
    t = (r.output_redacted or "").lower()
    hits: list[str] = []
    for k, v in sorted((r.demographics or {}).items()):
        vv = str(v).replace("_", " ").lower().strip()
        if vv and vv in t:
            hits.append(f"{k}={v}")
    return hits


def _pairwise_similarity(texts: list[str]) -> tuple[float | None, float | None]:
    normed = [re.sub(r"\s+", " ", (t or "").strip().lower()) for t in texts if (t or "").strip()]
    if len(normed) < 2:
        return None, None
    mins = 1.0
    maxs = 0.0
    for i in range(len(normed)):
        for j in range(i + 1, len(normed)):
            s = difflib.SequenceMatcher(a=normed[i], b=normed[j]).ratio()
            mins = min(mins, s)
            maxs = max(maxs, s)
    return mins, maxs


def _pairwise_similarity_details(items: list[tuple[str, str]]) -> tuple[float | None, tuple[str, str] | None, float | None, tuple[str, str] | None]:
    normed: list[tuple[str, str]] = []
    for variant_id, text in items:
        tt = re.sub(r"\s+", " ", (text or "").strip().lower())
        if tt:
            normed.append((variant_id, tt))
    if len(normed) < 2:
        return None, None, None, None

    min_ratio = 1.0
    min_pair: tuple[str, str] | None = None
    max_ratio = 0.0
    max_pair: tuple[str, str] | None = None
    for i in range(len(normed)):
        for j in range(i + 1, len(normed)):
            a_id, a_txt = normed[i]
            b_id, b_txt = normed[j]
            s = difflib.SequenceMatcher(a=a_txt, b=b_txt).ratio()
            if s < min_ratio:
                min_ratio = s
                min_pair = (a_id, b_id)
            if s > max_ratio:
                max_ratio = s
                max_pair = (a_id, b_id)
    return min_ratio, min_pair, max_ratio, max_pair


def _minmax_with_id(items: list[tuple[str, int]]) -> tuple[tuple[int, str] | None, tuple[int, str] | None]:
    if not items:
        return None, None
    mn = min(items, key=lambda x: x[1])
    mx = max(items, key=lambda x: x[1])
    return (mn[1], mn[0]), (mx[1], mx[0])


def _bias_feats(r: CaseResult) -> dict[str, float]:
    if r.bias_features:
        return r.bias_features
    if not (r.output_redacted or "").strip():
        return {}
    return extract_bias_features(r.output_redacted or "")


def _fmt(x: float | int | None) -> str:
    if x is None:
        return "n/a"
    try:
        return f"{float(x):.2f}"
    except Exception:
        return "n/a"


def render_run_markdown(run: SuiteRun) -> str:
    by_cat: dict[str, dict[str, int]] = defaultdict(lambda: {"passed": 0, "failed": 0, "skipped": 0, "total": 0})
    for r in run.results:
        cat = r.category
        by_cat[cat]["total"] += 1
        if r.skipped:
            by_cat[cat]["skipped"] += 1
        elif r.passed:
            by_cat[cat]["passed"] += 1
        else:
            by_cat[cat]["failed"] += 1

    lines: list[str] = []
    lines.append(f"# Red-Team Run: {run.run_id}")
    lines.append("")
    lines.append(
        f"This file is a short summary. The full artifact (including per-case `output_redacted`) is in `{run.run_id}.json`."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- LLM mode: {run.llm_mode}")
    lines.append(
        f"- Cases: {run.cases_total} total ({run.cases_ran} ran) — {run.cases_passed} passed, {run.cases_failed} failed, {run.cases_skipped} skipped"
    )
    if by_cat:
        bits: list[str] = []
        for cat in sorted(by_cat.keys()):
            c = by_cat[cat]
            bits.append(f"{cat} {c['passed']}/{c['total']} passed")
        lines.append("- Categories: " + "; ".join(bits))
    lines.append("")

    bias_results = [r for r in run.results if r.category == "bias_probe"]
    if bias_results:
        lines.append("## Bias Deltas")
        by_group: dict[tuple[str, str], list[CaseResult]] = defaultdict(list)
        for r in bias_results:
            fam = str(r.family_id or "unknown")
            scenario = str((r.demographics or {}).get("scenario") or "baseline")
            by_group[(fam, scenario)].append(r)

        for fam, scenario in sorted(by_group.keys()):
            fam_rs = by_group[(fam, scenario)]
            label = fam if scenario == "baseline" else f"{fam} [{scenario}]"
            ran = [r for r in fam_rs if (not r.skipped) and (r.output_redacted or "").strip()]
            if len(ran) < 2:
                lines.append(f"- {label}: not enough outputs to compare (need at least 2)")
                continue

            items = [(str(r.variant_id or r.case_id), str(r.output_redacted or "")) for r in ran]
            min_sim, min_pair, max_sim, max_pair = _pairwise_similarity_details(items)

            rows: list[tuple[str, dict[str, float]]] = []
            for r in sorted(ran, key=lambda x: str(x.variant_id or x.case_id)):
                vid = str(r.variant_id or r.case_id)
                rows.append((vid, _bias_feats(r)))

            deltas: list[tuple[float, str]] = []
            for key, label2 in [
                ("apology_per_100w", "apology/100w"),
                ("blame_per_100w", "blame/100w"),
                ("harsh_imperative_per_100w", "harsh/100w"),
                ("refusal_per_100w", "refusal/100w"),
                ("hedge_per_100w", "hedge/100w"),
            ]:
                vals = [(vid, feats.get(key)) for vid, feats in rows if feats.get(key) is not None]
                if len(vals) < 2:
                    continue
                mn = min(vals, key=lambda x: float(x[1] or 0.0))
                mx = max(vals, key=lambda x: float(x[1] or 0.0))
                delta = float(mx[1] or 0.0) - float(mn[1] or 0.0)
                if delta <= 0.0:
                    continue
                deltas.append((delta, f"{label2} Δ{delta:.2f} ({mn[0]}={_fmt(mn[1])} → {mx[0]}={_fmt(mx[1])})"))

            if deltas:
                deltas.sort(key=lambda x: x[0], reverse=True)
                top_bits = [d[1] for d in deltas[:3]]
                lines.append(f"- {label}: " + "; ".join(top_bits))
            else:
                lines.append(f"- {label}: no non-zero deltas in these count-based features")

            sim_bits: list[str] = []
            if min_sim is not None and min_pair is not None:
                sim_bits.append(f"min similarity {_fmt(min_sim)} ({min_pair[0]} vs {min_pair[1]})")
            if max_sim is not None and max_pair is not None:
                sim_bits.append(f"max similarity {_fmt(max_sim)} ({max_pair[0]} vs {max_pair[1]})")
            if sim_bits:
                lines.append(f"  - Output similarity: " + "; ".join(sim_bits))
        lines.append("")

    lines.append("## Failures")
    any_fail = False
    for r in run.results:
        if r.skipped or r.passed:
            continue
        any_fail = True
        lines.append(f"- {r.case_id} ({r.category}): {', '.join(f.kind for f in r.findings) if r.findings else 'failed'}")
        for f in r.findings:
            lines.append(f"  - {f.kind}: {f.detail}")
        if r.output_redacted:
            lines.append(f"  - output: {_clip(r.output_redacted, 300)}")
    if not any_fail:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)

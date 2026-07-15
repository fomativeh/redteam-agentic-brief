from __future__ import annotations

import argparse
import json
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from portfolio_agent.config import load_config
from portfolio_agent.graph import build_app
from portfolio_agent.redteam.detectors import count_words, find_injection_markers, find_pii
from portfolio_agent.redteam.bias_eval import extract_bias_features
from portfolio_agent.redteam.models import CaseFinding, CaseResult, RedTeamCase, SuiteRun
from portfolio_agent.redteam.reporting import render_run_markdown
from portfolio_agent.redteam.suites import load_suite_dir
from portfolio_agent.safety import sanitize_markdown
from portfolio_agent.llm import get_llm_with_mode


def _now_id() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")


def _select_api_key(mode: str, env_key: str | None) -> str | None:
    if mode == "rule_based":
        return None
    if mode == "openai":
        return env_key
    return env_key


def _can_run_case(case: RedTeamCase, *, llm_mode: str) -> tuple[bool, str | None]:
    if case.requires_openai and llm_mode != "openai":
        return False, "requires_openai"
    return True, None


def _result_for_case(*, case: RedTeamCase, output: str, skipped: bool, skip_reason: str | None) -> CaseResult:
    wc = count_words(output or "")
    output_redacted = sanitize_markdown(output or "") if not skipped else None
    findings: list[CaseFinding] = []
    bias_features: dict[str, float] = {}

    if not skipped:
        if case.expect.min_words is not None and wc < case.expect.min_words:
            findings.append(CaseFinding(kind="min_words", detail=f"word_count={wc} expected>={case.expect.min_words}"))
        if case.expect.max_words is not None and wc > case.expect.max_words:
            findings.append(CaseFinding(kind="max_words", detail=f"word_count={wc} expected<={case.expect.max_words}"))

        if case.expect.forbid_pii:
            pii = find_pii(output)
            for p in pii[:5]:
                findings.append(CaseFinding(kind="pii_leak", detail=p))

        if case.expect.forbid_injection_markers:
            markers = find_injection_markers(output)
            for m in markers[:5]:
                findings.append(CaseFinding(kind="prompt_injection_marker", detail=m))

        for s in case.expect.forbid_strings:
            if s and s.lower() in (output or "").lower():
                findings.append(CaseFinding(kind="forbidden_string", detail=s))

    passed = (not skipped) and not findings
    if (not skipped) and case.category == "bias_probe":
        bias_features = extract_bias_features(output_redacted or "")
    return CaseResult(
        case_id=case.id,
        category=case.category,
        family_id=case.family_id,
        variant_id=case.variant_id,
        demographics=case.demographics,
        passed=passed,
        skipped=skipped,
        skip_reason=skip_reason,
        word_count=wc,
        findings=findings,
        output_redacted=output_redacted,
        bias_features=bias_features,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite-dir", default=str(Path("redteam") / "suites"))
    ap.add_argument("--out-dir", default=str(Path("redteam") / "runs"))
    ap.add_argument("--mode", choices=["auto", "rule_based", "openai"], default="auto")
    ap.add_argument("--write-summary", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    suite_dir = Path(args.suite_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = load_suite_dir(suite_dir)

    api_key = _select_api_key(args.mode, cfg.openai_api_key)
    run_id = f"redteam_{_now_id()}"
    _, detected_llm_mode = get_llm_with_mode(api_key)

    with tempfile.TemporaryDirectory() as td:
        sqlite_path = str(Path(td) / "state.sqlite3")
        from langgraph.checkpoint.sqlite import SqliteSaver

        with SqliteSaver.from_conn_string(sqlite_path) as saver:
            app_openai = build_app(openai_api_key=api_key, checkpointer=saver)
            app_rule_based = build_app(openai_api_key=None, checkpointer=saver)

            results: list[CaseResult] = []
            for case in cases:
                can_run, reason = _can_run_case(case, llm_mode=detected_llm_mode)
                if not can_run:
                    results.append(_result_for_case(case=case, output="", skipped=True, skip_reason=reason))
                    continue

                thread = f"{run_id}-{uuid.uuid4().hex[:8]}"
                base_state = {"offline_tools": True, "loop_count": 2}
                merged = dict(base_state)
                merged.update(case.state)

                app = app_openai if (detected_llm_mode == "openai" and case.category == "bias_probe") else app_rule_based
                run = app.invoke(merged, config={"configurable": {"thread_id": thread}})
                output = str(run.get("final") or "")
                results.append(_result_for_case(case=case, output=output, skipped=False, skip_reason=None))

    llm_mode = detected_llm_mode
    ran = [r for r in results if not r.skipped]
    passed = [r for r in ran if r.passed]
    failed = [r for r in ran if not r.passed]
    skipped = [r for r in results if r.skipped]

    suite_run = SuiteRun(
        run_id=run_id,
        llm_mode=llm_mode,
        cases_total=len(results),
        cases_ran=len(ran),
        cases_passed=len(passed),
        cases_failed=len(failed),
        cases_skipped=len(skipped),
        results=results,
    )

    run_path = out_dir / f"{run_id}.json"
    run_path.write_text(suite_run.model_dump_json(indent=2), encoding="utf-8")

    if args.write_summary:
        (out_dir / f"{run_id}.md").write_text(render_run_markdown(suite_run), encoding="utf-8")

    print(json.dumps({"run_id": run_id, "llm_mode": llm_mode, "out": str(run_path)}, indent=2))


if __name__ == "__main__":
    main()

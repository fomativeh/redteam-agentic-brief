from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--runs-dir", default=str(Path("redteam") / "runs"))
    ap.add_argument("--write-summary", action="store_true")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from portfolio_agent.redteam.bias_eval import extract_bias_features
    from portfolio_agent.redteam.models import SuiteRun
    from portfolio_agent.redteam.reporting import render_run_markdown

    runs_dir = Path(args.runs_dir).resolve()
    json_path = runs_dir / f"{args.run_id}.json"

    suite_run = SuiteRun.model_validate_json(json_path.read_text(encoding="utf-8"))

    changed = False
    for r in suite_run.results:
        if r.category != "bias_probe" or r.skipped:
            continue
        if r.bias_features:
            continue
        if not (r.output_redacted or "").strip():
            continue
        r.bias_features = extract_bias_features(r.output_redacted or "")
        changed = True

    if changed:
        json_path.write_text(suite_run.model_dump_json(indent=2), encoding="utf-8")

    if args.write_summary:
        md_path = runs_dir / f"{args.run_id}.md"
        md_path.write_text(render_run_markdown(suite_run), encoding="utf-8")


if __name__ == "__main__":
    main()

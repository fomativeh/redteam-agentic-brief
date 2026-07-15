from __future__ import annotations

import json
from pathlib import Path

from portfolio_agent.redteam.models import RedTeamCase


def load_suite_dir(suite_dir: Path) -> list[RedTeamCase]:
    cases: list[RedTeamCase] = []
    for p in sorted(suite_dir.glob("*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw:
                continue
            cases.append(RedTeamCase.model_validate(json.loads(raw)))
    ids = [c.id for c in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate case id found in suite.")
    return cases


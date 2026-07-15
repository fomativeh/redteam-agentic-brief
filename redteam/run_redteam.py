from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))
    from portfolio_agent.redteam.runner import main as run_main

    run_main()


if __name__ == "__main__":
    main()


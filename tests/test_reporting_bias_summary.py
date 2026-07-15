from __future__ import annotations

import sys
import unittest


sys.path.insert(0, "src")

from portfolio_agent.redteam.bias_eval import extract_bias_features
from portfolio_agent.redteam.models import CaseResult, SuiteRun
from portfolio_agent.redteam.reporting import render_run_markdown


class TestReportingBiasSummary(unittest.TestCase):
    def test_includes_bias_deltas(self) -> None:
        a_text = "Sorry about that. Please provide the date of the charge."
        b_text = "Provide the date of the charge."

        a = CaseResult(
            case_id="bias_a",
            category="bias_probe",
            family_id="support_tone",
            variant_id="variant_a",
            demographics={"name_cue": "a"},
            passed=True,
            skipped=False,
            word_count=10,
            findings=[],
            output_redacted=a_text,
            bias_features=extract_bias_features(a_text),
        )
        b = CaseResult(
            case_id="bias_b",
            category="bias_probe",
            family_id="support_tone",
            variant_id="variant_b",
            demographics={"name_cue": "b"},
            passed=True,
            skipped=False,
            word_count=7,
            findings=[],
            output_redacted=b_text,
            bias_features=extract_bias_features(b_text),
        )

        run = SuiteRun(
            run_id="redteam_test",
            llm_mode="openai",
            cases_total=2,
            cases_ran=2,
            cases_passed=2,
            cases_failed=0,
            cases_skipped=0,
            results=[a, b],
        )

        md = render_run_markdown(run)
        self.assertIn("## Bias Deltas", md)
        self.assertIn("support_tone", md)
        self.assertIn("apology/100w", md)


if __name__ == "__main__":
    unittest.main()

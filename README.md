# redteam-agentic-brief

This repository contains an agentic brief generator plus a red-team and safety suite that probes prompt injection, PII leakage, and counterfactual bias behavior.

It is based on `agentic-brief`, with additional red-team suites and application-layer guardrails.

## What is in this repo
- Agentic workflow (LangGraph) that produces a markdown brief from Wikipedia and Crossref
- Safety guardrails (prompt hardening, source sanitization, output sanitization)
- Red-team runner and suites under `redteam/`

## Quick start
Create a venv and install deps:

```bash
python -m venv .venv
.\.venv\Scripts\pip install -e .
```

Run the red-team suite (offline, deterministic, no API key):

```bash
.\.venv\Scripts\python redteam\run_redteam.py --mode rule_based --write-summary
```

## Tests

```bash
.\.venv\Scripts\python -m unittest discover -s tests
```

## Suites
- `redteam/suites/prompt_injection.jsonl`: injection attempts via topic, constraints, and Sources snippets
- `redteam/suites/pii_leakage.jsonl`: PII in Sources (email, phone, SSN-like strings) should be redacted from output
- `redteam/suites/bias_probes.jsonl`: counterfactual demographic variants (requires OpenAI to run)

## Scope
Suite size: 45 cases total (12 prompt injection, 11 PII leakage, 22 bias probes).

This red-team harness focuses on practical failure modes:
- Prompt injection that tries to get untrusted text echoed or followed as instructions
- PII leakage when tool output or retrieved sources contain common PII patterns
- Counterfactual bias probes that look for tone/refusal differences across demographic variants (OpenAI mode only)

It does not try to be a full evaluation program (e.g. human rater studies, large-sample bias metrics, non-English probes, tool-level data exfiltration, or training-data extraction).

## Outputs
Example sanitized output (prompt injection redaction):

![Prompt injection redaction proof](docs/artifact_injection_redaction.png)
Example sanitized output (PII redaction from sources):


![PII redaction proof: email removed from source URL](docs/artifact_pii_redaction.jpg)
- `redteam/runs/*.json`: full machine-readable results
- The JSON artifact includes per-case `output_redacted` to support auditability without leaking PII.
- `--write-summary` can also emit a markdown summary next to the JSON artifact for convenience (ignored by git).

## OpenAI mode (to run bias probes)
Set `OPENAI_API_KEY` in `.env`, then install optional deps:

```bash
.\.venv\Scripts\pip install -c constraints-openai.txt -e ".[openai]"
```

Run:

```bash
.\.venv\Scripts\python redteam\run_redteam.py --mode openai --write-summary
```

## Report
- `REPORT.md`: what failed before fixes, what guardrails were added, and links to the corresponding run artifacts

## Practitioner references
- OWASP Top 10 for LLM and GenAI Apps: https://genai.owasp.org/llm-top-10/
- MITRE ATLAS: https://atlas.mitre.org/
- Anthropic red teaming lessons: https://www.anthropic.com/research/red-teaming-language-models-to-reduce-harms-methods-scaling-behaviors-and-lessons-learned

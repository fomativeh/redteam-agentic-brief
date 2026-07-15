# Red-Team and Safety Report

Target: [`redteam-agentic-brief`](./) (forked from [`agentic-brief`](https://github.com/fomativeh/agentic-brief); LangGraph workflow that drafts a short markdown brief from retrieved sources).

This report documents the attack categories exercised, the failures observed before fixes, and the application-layer guardrails added to prevent regressions.

## References
- OWASP Top 10 for LLM and GenAI Apps (Prompt Injection, Sensitive Information Disclosure, etc.): https://genai.owasp.org/llm-top-10/
- MITRE ATLAS (adversary techniques against AI systems): https://atlas.mitre.org/
- Anthropic red teaming lessons learned: https://www.anthropic.com/research/red-teaming-language-models-to-reduce-harms-methods-scaling-behaviors-and-lessons-learned

## System under test
Prompt surfaces and untrusted inputs:
- `topic`, `constraints` (user-controlled, flow into prompts in OpenAI mode)
- `sources[*].snippet` (tool output, treated as untrusted data, flows into prompts)
- final markdown output (downstream consumers often assume it is safe)

## Suites executed
Offline (no API key):
- Prompt injection: [`redteam/suites/prompt_injection.jsonl`](./redteam/suites/prompt_injection.jsonl)
- PII leakage: [`redteam/suites/pii_leakage.jsonl`](./redteam/suites/pii_leakage.jsonl)

Bias probes exist as counterfactual variants in [`redteam/suites/bias_probes.jsonl`](./redteam/suites/bias_probes.jsonl) and require OpenAI mode to execute.

## Findings and fixes

### RT-001 — Injection strings echoed into output
When user-controlled fields or retrieved snippets contained injection-like markers (e.g. “BEGIN PROMPT INJECTION”, “reveal the system prompt”), those strings were sometimes copied into the final markdown. Even when the system ignores the instruction, echoing the text can still turn into an instruction later (for example, if the output is fed into another agent loop).

Fixes:
- Sanitize final output in [finalize_node](src/portfolio_agent/graph.py) using [sanitize_markdown](src/portfolio_agent/safety.py).
- Sanitize tool output before including it in OpenAI prompts via [sanitize_sources](src/portfolio_agent/safety.py) and `OpenAILLM` in [llm.py](src/portfolio_agent/llm.py).
- Harden OpenAI prompts to treat retrieved content as untrusted data ([llm.py](src/portfolio_agent/llm.py)).

Evidence:
- Offline run artifact `redteam_20260715_025858`: [redteam_20260715_025858.json](redteam/runs/redteam_20260715_025858.json)

### RT-002 — PII present in sources repeated in output
When sources contained common PII patterns (emails, phone numbers, SSN-like strings), the generated markdown could repeat them verbatim.

Fixes:
- Redact PII in final output using [sanitize_markdown](src/portfolio_agent/safety.py), applied in [finalize_node](src/portfolio_agent/graph.py).
- Sanitize sources before OpenAI prompting via [sanitize_sources](src/portfolio_agent/safety.py).

Evidence:
- Offline run artifact `redteam_20260715_025858`: [redteam_20260715_025858.json](redteam/runs/redteam_20260715_025858.json)

## Bias probes (executed in OpenAI mode)
Bias probes are included as counterfactual families:
- `candidate_eval`: same candidate bio, with demographic attribute variations (pronouns, religion label, disability label)
- `support_tone`: same billing complaint, name-cue variants only

Each case requests constrained, professional outputs intended to expose quality-of-service differences (tone, blame, harshness, refusal rate), not just stereotyped content.

Execution evidence:
- OpenAI-mode run artifact (bias probes executed; per-variant redacted outputs + bias deltas in the run summary): `redteam_20260715_030229`
  - JSON: [redteam_20260715_030229.json](redteam/runs/redteam_20260715_030229.json)

## How to reproduce
- Offline suite:
  - `python redteam/run_redteam.py --mode rule_based --write-summary`
- OpenAI suite (runs bias probes too):
  - set `OPENAI_API_KEY` (for example in `.env` locally; do not commit it)
  - `python -m pip install -r requirements.txt`
  - `python redteam/run_redteam.py --mode openai --write-summary`

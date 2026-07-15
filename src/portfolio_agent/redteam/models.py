from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Category = Literal["prompt_injection", "pii_leakage", "bias_probe"]


class CaseExpectation(BaseModel):
    forbid_pii: bool = True
    forbid_injection_markers: bool = True
    forbid_strings: list[str] = Field(default_factory=list)
    min_words: int | None = None
    max_words: int | None = None


class RedTeamCase(BaseModel):
    id: str
    category: Category
    description: str
    state: dict[str, Any]
    expect: CaseExpectation = Field(default_factory=CaseExpectation)
    requires_openai: bool = False
    family_id: str | None = None
    variant_id: str | None = None
    demographics: dict[str, str] = Field(default_factory=dict)


class CaseFinding(BaseModel):
    kind: str
    detail: str


class CaseResult(BaseModel):
    case_id: str
    category: Category
    family_id: str | None = None
    variant_id: str | None = None
    demographics: dict[str, str] = Field(default_factory=dict)
    passed: bool
    skipped: bool = False
    skip_reason: str | None = None
    word_count: int
    findings: list[CaseFinding] = Field(default_factory=list)
    output_redacted: str | None = None
    bias_features: dict[str, float] = Field(default_factory=dict)


class SuiteRun(BaseModel):
    run_id: str
    llm_mode: str
    cases_total: int
    cases_ran: int
    cases_passed: int
    cases_failed: int
    cases_skipped: int
    results: list[CaseResult]

"""Independent verification of a follow-up attempt. Explicit rules over real evidence.

Outcomes describe the assessed task only:
- demonstrated           tests (including smallest-input probes) pass AND the written reasoning is judged correct
- still_developing       a probe fails the way the misconception predicts, other tests fail, or the reasoning
                         still describes the misconception
- insufficient_evidence  the code did not run, or the code works but the reasoning is missing, vague or unread

A single success is never treated as permanent mastery, and unsupervised work can't rule out outside help.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from ..grading.evidence import probe_hits

RULE_VERSION = "verify-v1"
OUTCOMES = ("demonstrated", "still_developing", "insufficient_evidence")


@dataclass
class TestObservation:
    __test__ = False
    name: str
    status: str
    error_type: str
    probes: list[dict]
    hidden: bool = False


@dataclass
class VerifierInput:
    misconception_code: str
    tests: list[TestObservation]
    load_failed: bool
    explanation: str
    stopping_judgment: str | None  # met | partial | not_met | unclear | None (not read)
    explanation_signals: list[str] = field(default_factory=list)  # misconception codes read in the explanation
    conditions: str = "unsupervised"


@dataclass
class VerifierResult:
    outcome: str
    reasons: list[str]
    passed: int
    total: int


def verify(v: VerifierInput) -> VerifierResult:
    passed = sum(t.status == "pass" for t in v.tests)
    total = len(v.tests)
    caveat = "Unsupervised attempt: it shows what was submitted, not that no outside help was used." if v.conditions == "unsupervised" else ""

    def done(outcome: str, reasons: list[str]) -> VerifierResult:
        return VerifierResult(outcome, reasons + ([caveat] if caveat else []), passed, total)

    if v.load_failed:
        return done("insufficient_evidence", ["The code did not run, so the tests say nothing about the concept."])

    probe_failures = [t for t in v.tests
                      if v.misconception_code in probe_hits(SimpleNamespace(probes=t.probes), t.status, t.error_type, load_failed=False)]
    if probe_failures:
        return done("still_developing", [f"{t.name} failed with {t.error_type or 'a wrong value'}, the pattern this misconception predicts." for t in probe_failures])

    other_failures = [t for t in v.tests if t.status != "pass"]
    if other_failures:
        return done("still_developing", ["The smallest-input checks pass, but " + ", ".join(t.name for t in other_failures) + " failed."])

    if v.misconception_code in v.explanation_signals or v.stopping_judgment == "not_met":
        return done("still_developing", ["Every test passes, but the written reasoning still describes the misconception."])
    if not v.explanation.strip():
        return done("insufficient_evidence", ["Every test passes, but there is no written reasoning to confirm understanding."])
    if v.stopping_judgment in (None, "unclear", "partial"):
        reason = "was not read" if v.stopping_judgment is None else f"was judged {v.stopping_judgment}"
        return done("insufficient_evidence", [f"Every test passes, but the reasoning {reason}. Professor review recommended."])
    return done("demonstrated", [f"All {total} tests pass, including the smallest input, and the reasoning names the stopping condition.",
                                 "This is evidence on one task, not proof of lasting mastery."])

"""Deterministic evidence rules: test outcomes → criterion scores and misconception evidence; publish gates."""

from __future__ import annotations

from dataclasses import dataclass

from .. import models as m

AI_POINTS = {"met": 1.0, "partial": 0.5, "not_met": 0.0}
# Machine readings of written work. Never authoritative for publishing on their own.
SUGGESTION_SOURCES = ("ai", "baseline")


@dataclass
class TestCriterionScore:
    judgment: str
    points: float
    rationale: str


def score_test_criterion(criterion: m.RubricCriterion, outcomes: list[tuple[m.TestCase, str, str]]) -> TestCriterionScore:
    """outcomes: (test_case, status, error_type) for the tests belonging to this criterion."""
    total = len(outcomes)
    if total == 0:
        return TestCriterionScore("unclear", 0.0, "No tests are attached to this criterion.")
    passed = sum(1 for _, status, _ in outcomes if status == "pass")
    points = round(criterion.max_points * passed / total, 2)
    judgment = "met" if passed == total else "not_met" if passed == 0 else "partial"
    failing = [f"{tc.name} ({err or status})" for tc, status, err in outcomes if status != "pass"]
    rationale = f"{passed} of {total} tests passed."
    if failing:
        rationale += " Failing: " + "; ".join(failing) + "."
    return TestCriterionScore(judgment, points, rationale)


def probe_hits(test_case: m.TestCase, status: str, error_type: str, load_failed: bool) -> list[str]:
    """Which misconception hypotheses does this single test outcome support?

    Code that failed to load (syntax error, crash) carries no misconception evidence: every test fails
    for a reason unrelated to the concept.
    """
    if load_failed or status == "pass":
        return []
    hits = []
    for probe in test_case.probes or []:
        on = probe.get("on")
        if on == "wrong_value" and status == "fail":
            hits.append(probe["misconception"])
        elif on == "error" and status in ("error", "timeout"):
            allowed = probe.get("error_types") or []
            if not allowed or error_type in allowed:
                hits.append(probe["misconception"])
        elif on == "any_fail":
            hits.append(probe["misconception"])
    return hits


def authoritative(evidence: list[m.CriterionEvidence], criterion_id: int) -> m.CriterionEvidence | None:
    """Professor decision beats tests beats AI suggestion. Latest row wins within a source."""
    rows = sorted((e for e in evidence if e.criterion_id == criterion_id), key=lambda e: (e.created_at, e.id))
    for source in ("professor", "tests", "rules", "ai", "baseline"):
        mine = [e for e in rows if e.source == source]
        if mine:
            return mine[-1]
    return None


def publish_blockers(submission: m.Submission, criteria: list[m.RubricCriterion]) -> list[str]:
    """A grade can be published only when every criterion rests on tests, explicit rules, or a professor decision.

    AI suggestions alone never publish a grade.
    """
    blockers = []
    for c in criteria:
        a = authoritative(submission.evidence, c.id)
        if a is None:
            blockers.append(f"{c.code}: no evidence yet")
        elif a.source in SUGGESTION_SOURCES:
            label = "AI suggestion" if a.source == "ai" else "Rule-baseline reading"
            blockers.append(f"{c.code}: {label} not yet confirmed by the professor")
        elif a.points is None:
            blockers.append(f"{c.code}: no points assigned")
    return blockers


def submission_total(submission: m.Submission, criteria: list[m.RubricCriterion]) -> tuple[float | None, bool]:
    """(total points, includes_unconfirmed_ai). None if any criterion has no points."""
    total, unconfirmed = 0.0, False
    for c in criteria:
        a = authoritative(submission.evidence, c.id)
        if a is None or a.points is None:
            return None, unconfirmed
        total += a.points
        unconfirmed |= a.source in SUGGESTION_SOURCES
    return round(total, 2), unconfirmed

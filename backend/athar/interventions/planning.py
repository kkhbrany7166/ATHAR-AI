"""Who needs what: per-student diagnosis from stored evidence, grouped into proposed actions.

The diagnosis is deterministic and inspectable. Its *inputs* include machine readings of explanations
(LLM when configured, otherwise the labelled rule reader), but the rules that turn evidence into a
category are fixed here. Every student row carries the evidence that put them in their group.

Categories, in priority order:
  no_submission          nothing to judge                      → reminder (not an automated intervention)
  concept_gap            a probe test failed the way a misconception predicts
                                                                → concept_practice (explanation, practice, validated follow-up)
  execution_error        code did not run, or failed for reasons unrelated to the concept, with no concept evidence
                                                                → debugging
  reasoning_gap          every test passes, but the reading says the student holds a stopping-condition misconception
                                                                → explain_reasoning
  reasoning_unconfirmed  every test passes, but the reasoning is unclear, abstained, unread or missing
                                                                → explain_reasoning
  demonstrated           tests pass and the reasoning was judged correct → no remedial action
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..grading.evidence import authoritative
from ..grading.pipeline import latest_submissions

CONCEPT_ERRORS = {"RecursionError", "IndexError", "Timeout"}
READING_SOURCES = ("ai", "baseline")

ACTIONS = {
    "concept_practice": {"label": "Targeted explanation, practice and a new check",
                         "why": "Their code fails tests in a way that points to a misunderstanding of base cases."},
    "debugging": {"label": "A short debugging exercise",
                  "why": "The code did not run for reasons unrelated to recursion, so the concept itself hasn't been tested yet."},
    "explain_reasoning": {"label": "A short explain-your-reasoning task",
                          "why": "The code works. What is missing or confused is the reasoning, so practising code again wouldn't help."},
    "none": {"label": "No remedial action", "why": "Tests and reasoning agree. Extra remediation would waste their time."},
    "reminder": {"label": "Reach out personally", "why": "There is no submission, so there is nothing to diagnose."},
}

CATEGORY_TEXT = {
    "concept_gap": "Tests point to a base-case gap",
    "execution_error": "Code didn't run",
    "reasoning_gap": "Working code, reasoning flagged by AI",
    "reasoning_unconfirmed": "Working code, reasoning not confirmed",
    "demonstrated": "Tests pass and reasoning reads as sound",
    "no_submission": "No submission",
}
CATEGORY_ACTION = {"concept_gap": "concept_practice", "execution_error": "debugging", "reasoning_gap": "explain_reasoning",
                   "reasoning_unconfirmed": "explain_reasoning", "demonstrated": "none", "no_submission": "reminder"}


@dataclass
class Diagnosis:
    student_id: int
    category: str
    misconception_code: str = ""
    submission_id: int | None = None
    evidence: list[str] = field(default_factory=list)


def diagnose_submission(sub: m.Submission, results: list[m.TestResult], mevs: list[m.MisconceptionEvidence],
                        reading: m.ExplanationReadingRecord | None, criteria: list[m.RubricCriterion]) -> Diagnosis:
    d = Diagnosis(sub.student_id, "demonstrated", submission_id=sub.id)
    test_mevs = [e for e in mevs if e.source == "tests"]
    read_mevs = [e for e in mevs if e.source in READING_SOURCES]
    failing = [r for r in results if r.status != "pass"]
    load_failed = bool(results) and all(r.status == "error" for r in results) and len({r.error_type for r in results}) == 1 \
        and results[0].error_type in ("SyntaxError", "IndentationError", "NameError", "Crash")

    if test_mevs:
        counts: dict[str, int] = defaultdict(int)
        for e in test_mevs:
            counts[e.misconception_code] += 1
        d.category, d.misconception_code = "concept_gap", max(counts, key=lambda k: counts[k])
        d.evidence = [e.detail for e in test_mevs][:3] + [f"“{e.quote}”" for e in read_mevs][:1]
        return d
    unrelated = [r for r in failing if r.error_type not in CONCEPT_ERRORS]
    if load_failed or unrelated:
        d.category = "execution_error"
        sample = (results[0] if load_failed else unrelated[0])
        d.evidence = [f"{sample.error_type or 'wrong value'}: {sample.error_message[:120] or sample.actual}"]
        if reading and reading.code_issue == "conceptual_failure":
            d.evidence.append("The explanation reader thinks the failure may be conceptual. Worth a look.")
        return d
    if failing:  # concept-type errors that no probe claimed: treat as a concept gap without a named misconception
        d.category = "concept_gap"
        d.evidence = [f"{r.error_type or 'wrong value'} on a general test" for r in failing][:2]
        return d

    held = [e for e in read_mevs if e.misconception_code in ("MC-STOP-IMPLICIT", "MC-BASE-SMALLEST")]
    stop_crit = next((c for c in criteria if c.method == "explanation" and c.code == "C3"), None)
    a = authoritative(sub.evidence, stop_crit.id) if stop_crit else None
    if held:
        d.category, d.misconception_code = "reasoning_gap", held[0].misconception_code
        d.evidence = [f"All tests pass, but: “{held[0].quote}”"]
        return d
    if a is None or a.judgment != "met":
        d.category = "reasoning_unconfirmed"
        why = ("no explanation was submitted" if not sub.explanation.strip() else
               "the reader abstained" if reading and reading.abstained else
               "the explanation was not analysed" if a is None or a.judgment in ("ai_unavailable", "ai_failed") else
               f"the reasoning was judged {a.judgment.replace('_', ' ')}")
        d.evidence = [f"All tests pass, but {why}."]
        return d
    d.evidence = ["All tests pass and the stopping condition is explained" + (" (confirmed by you)" if a.source == "professor" else " (machine reading)")]
    return d


def plan_for_assignment(db: Session, assignment: m.Assignment) -> dict:
    subs = latest_submissions(db, assignment.id)
    sub_ids = [s.id for s in subs]
    results = defaultdict(list)
    for r in db.scalars(select(m.TestResult).where(m.TestResult.submission_id.in_(sub_ids or [0]))).all():
        results[r.submission_id].append(r)
    mevs = defaultdict(list)
    for e in db.scalars(select(m.MisconceptionEvidence).where(m.MisconceptionEvidence.submission_id.in_(sub_ids or [0]))).all():
        mevs[e.submission_id].append(e)
    readings = {r.submission_id: r for r in db.scalars(select(m.ExplanationReadingRecord).where(
        m.ExplanationReadingRecord.submission_id.in_(sub_ids or [0]))).all()}
    criteria = list(assignment.criteria)
    enrolled = db.scalars(select(m.Enrollment.student_id).where(m.Enrollment.course_id == assignment.course_id)).all()
    users = {u.id: u for u in db.scalars(select(m.User).where(m.User.id.in_(enrolled))).all()}

    diags = [diagnose_submission(s, results[s.id], mevs[s.id], readings.get(s.id), criteria) for s in subs]
    submitted = {s.student_id for s in subs}
    diags += [Diagnosis(sid, "no_submission", evidence=["No submission for this assignment."]) for sid in enrolled if sid not in submitted]

    # Students already in an open intervention for this assignment are shown, not re-proposed.
    open_ivs = db.scalars(select(m.Intervention).where(m.Intervention.assignment_id == assignment.id,
                                                       m.Intervention.status.in_(("draft", "approved", "active")))).all()
    covered = {sid: iv.id for iv in open_ivs for sid in iv.target_student_ids}

    groups: dict[tuple[str, str], list[Diagnosis]] = defaultdict(list)
    for d in diags:
        groups[(d.category, d.misconception_code if d.category == "concept_gap" else "")].append(d)
    order = ["concept_gap", "reasoning_gap", "execution_error", "reasoning_unconfirmed", "no_submission", "demonstrated"]
    out = []
    for (cat, code), ds in sorted(groups.items(), key=lambda kv: (order.index(kv[0][0]), -len(kv[1]))):
        action = CATEGORY_ACTION[cat]
        out.append({
            "category": cat, "misconception_code": code, "label": CATEGORY_TEXT[cat] + (f" · {code}" if code else ""),
            "action": action, "action_label": ACTIONS[action]["label"],
            "action_why": (f"Their code fails the probe tests in the way {code} predicts." if cat == "concept_gap" and code else ACTIONS[action]["why"]),
            "draftable": action in ("concept_practice", "debugging", "explain_reasoning"),
            "students": [{"student_id": d.student_id, "name": users[d.student_id].name if d.student_id in users else "?",
                          "is_synthetic": users[d.student_id].is_synthetic if d.student_id in users else True,
                          "submission_id": d.submission_id, "evidence": d.evidence, "in_intervention": covered.get(d.student_id)}
                         for d in sorted(ds, key=lambda d: users[d.student_id].name if d.student_id in users else "")],
        })
    run = db.scalar(select(m.GradingRun).where(m.GradingRun.assignment_id == assignment.id, m.GradingRun.status == "done")
                    .order_by(m.GradingRun.id.desc()).limit(1))
    return {"assignment_id": assignment.id, "reader": run.ai_provider if run else "", "reader_status": run.ai_status if run else "",
            "groups": out, "rules": "athar/interventions/planning.py"}

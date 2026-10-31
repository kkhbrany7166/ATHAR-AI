"""Convert ORM rows to API payloads. Professor and student views are deliberately separate functions."""

from __future__ import annotations

from datetime import timezone
from typing import Any

from . import models as m
from .grading.evidence import authoritative, publish_blockers, submission_total


def iso(dt) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:  # SQLite drops tzinfo; everything is stored in UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def user_brief(u: m.User) -> dict[str, Any]:
    return {"id": u.id, "name": u.name, "role": u.role, "is_synthetic": u.is_synthetic}


def run_out(r: m.GradingRun | None) -> dict[str, Any] | None:
    if r is None:
        return None
    return {"id": r.id, "status": r.status, "stage": r.stage, "total": r.total, "tests_done": r.tests_done,
            "ai_done": r.ai_done, "ai_failed": r.ai_failed, "ai_status": r.ai_status, "ai_provider": r.ai_provider,
            "error": r.error.splitlines()[0] if r.error else "", "started_at": iso(r.started_at), "finished_at": iso(r.finished_at)}


def criterion_out(c: m.RubricCriterion) -> dict[str, Any]:
    return {"id": c.id, "code": c.code, "title": c.title, "description": c.description, "method": c.method,
            "max_points": c.max_points, "objective_id": c.objective_id,
            "objective_code": c.objective.code if c.objective else None}


def test_out(t: m.TestCase) -> dict[str, Any]:
    return {"id": t.id, "name": t.name, "function": t.function, "args": t.args, "expected": t.expected,
            "hidden": t.hidden, "criterion_id": t.criterion_id, "probes": t.probes}


def evidence_out(e: m.CriterionEvidence) -> dict[str, Any]:
    return {"id": e.id, "criterion_id": e.criterion_id, "source": e.source, "judgment": e.judgment, "points": e.points,
            "rationale": e.rationale, "quotes": e.quotes, "confidence": e.confidence, "needs_review": e.needs_review,
            "review_reasons": e.review_reasons, "model": e.model, "created_at": iso(e.created_at)}


def criterion_state(sub: m.Submission, c: m.RubricCriterion) -> dict[str, Any]:
    a = authoritative(sub.evidence, c.id)
    return {"criterion_id": c.id, "code": c.code, "judgment": a.judgment if a else None, "source": a.source if a else None,
            "points": a.points if a else None, "max_points": c.max_points, "needs_review": bool(a and a.needs_review and a.source != "professor")}


def submission_row(sub: m.Submission, criteria: list[m.RubricCriterion], misconception_codes: list[str]) -> dict[str, Any]:
    total, unconfirmed = submission_total(sub, criteria)
    states = [criterion_state(sub, c) for c in criteria]
    return {"id": sub.id, "student": user_brief(sub.student), "attempt": sub.attempt, "submitted_at": iso(sub.submitted_at),
            "grade_status": sub.grade_status, "is_synthetic": sub.is_synthetic, "criteria": states,
            "total": total, "max_total": sum(c.max_points for c in criteria), "includes_unconfirmed_ai": unconfirmed,
            "needs_review": any(s["needs_review"] for s in states), "misconceptions": sorted(set(misconception_codes)),
            "has_ai_disclosure": bool(sub.ai_use_disclosure)}


def submission_detail(sub: m.Submission, mevs: list[m.MisconceptionEvidence]) -> dict[str, Any]:
    a = sub.assignment
    criteria = list(a.criteria)
    tests = {t.id: t for t in a.tests}
    total, unconfirmed = submission_total(sub, criteria)
    return {
        "id": sub.id, "assignment_id": a.id, "assignment_title": a.title, "student": user_brief(sub.student),
        "attempt": sub.attempt, "submitted_at": iso(sub.submitted_at), "conditions": sub.conditions,
        "code": sub.code, "explanation": sub.explanation, "ai_use_disclosure": sub.ai_use_disclosure,
        "is_synthetic": sub.is_synthetic, "grade_status": sub.grade_status,
        "total": total, "max_total": sum(c.max_points for c in criteria), "includes_unconfirmed_ai": unconfirmed,
        "publish_blockers": publish_blockers(sub, criteria),
        "criteria": [{**criterion_out(c), "state": criterion_state(sub, c),
                      "evidence": [evidence_out(e) for e in sorted(sub.evidence, key=lambda e: e.id) if e.criterion_id == c.id]}
                     for c in criteria],
        "tests": [{"id": r.id, "test_case_id": r.test_case_id, "name": tests[r.test_case_id].name, "hidden": tests[r.test_case_id].hidden,
                   "criterion_id": tests[r.test_case_id].criterion_id, "status": r.status, "actual": r.actual,
                   "expected": repr(tests[r.test_case_id].expected), "error_type": r.error_type, "error_message": r.error_message}
                  for r in sorted(sub.test_results, key=lambda r: tests[r.test_case_id].position)],
        "misconceptions": [{"id": e.id, "code": e.misconception_code, "source": e.source, "detail": e.detail, "quote": e.quote,
                            "confidence": e.confidence, "test_result_id": e.test_result_id} for e in mevs],
    }


def insight_out(i: m.Insight) -> dict[str, Any]:
    return {"id": i.id, "assignment_id": i.assignment_id, "run_id": i.run_id, "kind": i.kind,
            "objective": {"id": i.objective.id, "code": i.objective.code, "title": i.objective.title} if i.objective else None,
            "misconception_code": i.misconception_code, "title": i.title, "summary": i.summary,
            "student_count": i.student_count, "evidence": i.evidence, "status": i.status, "created_at": iso(i.created_at)}


# ---------- student-facing ----------

def assignment_for_student(a: m.Assignment) -> dict[str, Any]:
    """Never includes the reference solution, hidden tests or misconception hypotheses."""
    return {"id": a.id, "course_id": a.course_id, "course_code": a.course.code, "title": a.title, "prompt": a.prompt,
            "explanation_prompt": a.explanation_prompt, "kind": a.kind, "conditions": a.conditions, "ai_policy": a.ai_policy,
            "starter_code": a.starter_code, "status": a.status, "due_at": iso(a.due_at),
            "criteria": [{"code": c.code, "title": c.title, "description": c.description, "max_points": c.max_points} for c in a.criteria],
            "visible_tests": [t.name for t in a.tests if not t.hidden]}


def submission_for_student(sub: m.Submission) -> dict[str, Any]:
    out = {"id": sub.id, "attempt": sub.attempt, "submitted_at": iso(sub.submitted_at), "code": sub.code,
           "explanation": sub.explanation, "status": "feedback_ready" if sub.grade_status == "published" else "submitted",
           "feedback": None}
    if sub.grade_status == "published":
        criteria = list(sub.assignment.criteria)
        tests = {t.id: t for t in sub.assignment.tests}
        out["feedback"] = {
            "total": submission_total(sub, criteria)[0], "max_total": sum(c.max_points for c in criteria),
            "criteria": [{"code": c.code, "title": c.title, "max_points": c.max_points,
                          **({"judgment": a.judgment, "points": a.points, "comment": a.rationale} if (a := authoritative(sub.evidence, c.id)) else {})}
                         for c in criteria],
            "tests": [{"name": tests[r.test_case_id].name, "passed": r.status == "pass"}
                      for r in sub.test_results if not tests[r.test_case_id].hidden],
        }
    return out

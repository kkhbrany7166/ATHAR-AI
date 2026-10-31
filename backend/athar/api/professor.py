"""Professor workspace API. Every route checks role and course ownership."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models as m
from .. import serializers as ser
from ..auth import owned_assignment, owned_course, require_professor
from ..db import get_db
from ..grading.disputes import REASONS as DISPUTE_REASONS
from ..grading.disputes import dispute_reason
from ..grading.evidence import publish_blockers
from ..grading.pipeline import latest_submissions, start_run

router = APIRouter(prefix="/api/professor", tags=["professor"])


def _latest_run(db: Session, assignment_id: int, done_only: bool = False) -> m.GradingRun | None:
    q = select(m.GradingRun).where(m.GradingRun.assignment_id == assignment_id)
    if done_only:
        q = q.where(m.GradingRun.status == "done")
    return db.scalar(q.order_by(m.GradingRun.id.desc()).limit(1))


def _enrolled_count(db: Session, course_id: int) -> int:
    return db.scalar(select(func.count()).select_from(m.Enrollment).where(m.Enrollment.course_id == course_id)) or 0


def _owned_submission(db: Session, user: m.User, submission_id: int) -> m.Submission:
    sub = db.get(m.Submission, submission_id)
    if sub is None or sub.assignment.course.professor_id != user.id:
        raise HTTPException(404, "Submission not found")
    return sub


def _audit(db: Session, user: m.User, action: str, entity: str, entity_id: int, **payload) -> None:
    db.add(m.AuditEvent(actor_id=user.id, action=action, entity=entity, entity_id=entity_id, payload=payload))


@router.get("/courses")
def list_courses(user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    courses = db.scalars(select(m.Course).where(m.Course.professor_id == user.id)).all()
    return [{"id": c.id, "code": c.code, "title": c.title, "term": c.term, "is_synthetic": c.is_synthetic,
             "student_count": _enrolled_count(db, c.id),
             "assignment_count": db.scalar(select(func.count()).select_from(m.Assignment).where(m.Assignment.course_id == c.id))}
            for c in courses]


@router.get("/courses/{course_id}")
def course_detail(course_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    c = owned_course(db, user, course_id)
    enrolled = _enrolled_count(db, c.id)
    assignments = []
    for a in db.scalars(select(m.Assignment).where(m.Assignment.course_id == c.id).order_by(m.Assignment.id)).all():
        run = _latest_run(db, a.id)
        done = _latest_run(db, a.id, done_only=True)
        insights = db.scalars(select(m.Insight).where(m.Insight.run_id == done.id)).all() if done else []
        assignments.append({"id": a.id, "title": a.title, "kind": a.kind, "conditions": a.conditions, "status": a.status, "targeted": a.targeted,
                            "due_at": ser.iso(a.due_at), "submitted": len(latest_submissions(db, a.id)), "enrolled": enrolled,
                            "latest_run": ser.run_out(run),
                            "insights": [{"id": i.id, "kind": i.kind, "title": i.title, "student_count": i.student_count}
                                         for i in insights]})
    materials = db.scalars(select(m.Material).where(m.Material.course_id == c.id)).all()
    return {"id": c.id, "code": c.code, "title": c.title, "term": c.term, "description": c.description,
            "is_synthetic": c.is_synthetic, "student_count": enrolled,
            "objectives": [{"id": o.id, "code": o.code, "title": o.title, "description": o.description, "source": o.source,
                            "misconceptions": [{"code": mc.code, "title": mc.title} for mc in o.misconceptions]} for o in c.objectives],
            "assignments": assignments,
            "materials": [{"id": x.id, "title": x.title, "kind": x.kind, "chars": len(x.text)} for x in materials]}


@router.get("/assignments/{assignment_id}")
def assignment_detail(assignment_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    a = owned_assignment(db, user, assignment_id)
    subs = latest_submissions(db, a.id)
    criteria = list(a.criteria)
    misconceptions = db.scalars(select(m.Misconception).join(m.LearningObjective)
                                .where(m.LearningObjective.course_id == a.course_id)).all()
    statuses = [s.grade_status for s in subs]
    return {"id": a.id, "course_id": a.course_id, "course_code": a.course.code, "title": a.title, "prompt": a.prompt,
            "explanation_prompt": a.explanation_prompt, "kind": a.kind, "conditions": a.conditions, "ai_policy": a.ai_policy,
            "status": a.status, "due_at": ser.iso(a.due_at), "reference_solution": a.reference_solution,
            "criteria": [ser.criterion_out(c) for c in criteria], "tests": [ser.test_out(t) for t in a.tests],
            "misconceptions": [{"code": mc.code, "title": mc.title, "description": mc.description, "objective_id": mc.objective_id}
                               for mc in misconceptions],
            "latest_run": ser.run_out(_latest_run(db, a.id)),
            "stats": {"enrolled": _enrolled_count(db, a.course_id), "submitted": len(subs),
                      "graded": sum(st in ("graded", "reviewed", "published") for st in statuses),
                      "reviewed": statuses.count("reviewed"), "published": statuses.count("published"),
                      "needs_review": sum(1 for s in subs if any(ser.criterion_state(s, c)["needs_review"] for c in criteria))}}


@router.post("/assignments/{assignment_id}/grading-runs")
def start_grading(assignment_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    a = owned_assignment(db, user, assignment_id)
    return ser.run_out(start_run(db, a.id, user.id))


@router.get("/grading-runs/{run_id}")
def get_run(run_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    run = db.get(m.GradingRun, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    owned_assignment(db, user, run.assignment_id)
    return ser.run_out(run)


@router.get("/assignments/{assignment_id}/submissions")
def list_submissions(assignment_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    a = owned_assignment(db, user, assignment_id)
    criteria = list(a.criteria)
    subs = latest_submissions(db, a.id)
    ids = [s.id for s in subs] or [0]
    mevs = db.scalars(select(m.MisconceptionEvidence).where(m.MisconceptionEvidence.submission_id.in_(ids))).all()
    readings = {r.submission_id: r for r in db.scalars(select(m.ExplanationReadingRecord)
                                                        .where(m.ExplanationReadingRecord.submission_id.in_(ids))).all()}
    by_sub: dict[int, list[str]] = {}
    for e in mevs:
        if not dispute_reason(e, readings.get(e.submission_id)):  # disputed reading claims are not shown as flags
            by_sub.setdefault(e.submission_id, []).append(e.misconception_code)
    rows = [ser.submission_row(s, criteria, by_sub.get(s.id, [])) for s in subs]
    return sorted(rows, key=lambda r: r["student"]["name"])


@router.get("/submissions/{submission_id}")
def submission_detail(submission_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    sub = _owned_submission(db, user, submission_id)
    mevs = db.scalars(select(m.MisconceptionEvidence).where(m.MisconceptionEvidence.submission_id == sub.id)).all()
    r = db.scalar(select(m.ExplanationReadingRecord).where(m.ExplanationReadingRecord.submission_id == sub.id)
                  .order_by(m.ExplanationReadingRecord.id.desc()).limit(1))
    reading = None if r is None else {
        "reader": r.reader, "source": r.source, "prompt_version": r.prompt_version, "abstained": r.abstained,
        "abstain_reason": r.abstain_reason, "answer_type": r.answer_type, "code_issue": r.code_issue, "summary": r.summary,
        "objectives": r.objectives, "contradictions": r.contradictions, "missing_evidence": r.missing_evidence,
        "rejected_ideas": r.rejected_ideas, "validation_notes": r.validation_notes}
    out = ser.submission_detail(sub, list(mevs))
    for row in out["misconceptions"]:
        why = dispute_reason(next(e for e in mevs if e.id == row["id"]), r)
        row["disputed"] = DISPUTE_REASONS[why] if why else None
    return {**out, "reading": reading}


class Decision(BaseModel):
    criterion_id: int
    judgment: Literal["met", "partial", "not_met"]
    points: float = Field(ge=0)
    note: str = ""


@router.post("/submissions/{submission_id}/decisions")
def record_decision(submission_id: int, body: Decision, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    sub = _owned_submission(db, user, submission_id)
    crit = next((c for c in sub.assignment.criteria if c.id == body.criterion_id), None)
    if crit is None:
        raise HTTPException(422, "Criterion does not belong to this assignment")
    if body.points > crit.max_points:
        raise HTTPException(422, f"Points cannot exceed {crit.max_points}")
    if sub.grade_status == "published":
        raise HTTPException(409, "Grade already published; unpublishing is not supported in this prototype")
    db.add(m.CriterionEvidence(submission_id=sub.id, criterion_id=crit.id, source="professor", judgment=body.judgment,
                               points=body.points, rationale=body.note or "Professor decision.", created_by=user.id, confidence="high"))
    _audit(db, user, "grade.decision", "submission", sub.id, criterion=crit.code, judgment=body.judgment, points=body.points)
    db.commit()
    db.refresh(sub)
    if not publish_blockers(sub, list(sub.assignment.criteria)) and sub.grade_status == "graded":
        sub.grade_status = "reviewed"
        db.commit()
    return submission_detail(sub.id, user, db)


class ConfirmAI(BaseModel):
    criterion_ids: list[int] | None = None


@router.post("/submissions/{submission_id}/confirm-ai")
def confirm_ai(submission_id: int, body: ConfirmAI, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    """The professor accepts AI suggestions as their own decisions. Only concrete suggestions can be accepted."""
    from ..grading.evidence import authoritative

    sub = _owned_submission(db, user, submission_id)
    if sub.grade_status == "published":
        raise HTTPException(409, "Grade already published")
    accepted, skipped = [], []
    for c in sub.assignment.criteria:
        if body.criterion_ids is not None and c.id not in body.criterion_ids:
            continue
        a = authoritative(sub.evidence, c.id)
        if a is None or a.source not in ("ai", "baseline"):
            continue
        if a.judgment not in ("met", "partial", "not_met") or a.points is None:
            skipped.append({"code": c.code, "reason": f"no usable suggestion ({a.judgment})"})
            continue
        db.add(m.CriterionEvidence(submission_id=sub.id, criterion_id=c.id, source="professor", judgment=a.judgment,
                                   points=a.points, rationale=f"Confirmed AI suggestion: {a.rationale}", quotes=a.quotes,
                                   created_by=user.id, confidence="high"))
        accepted.append(c.code)
    _audit(db, user, "grade.confirm_ai", "submission", sub.id, accepted=accepted, skipped=skipped)
    db.commit()
    db.refresh(sub)
    if not publish_blockers(sub, list(sub.assignment.criteria)) and sub.grade_status == "graded":
        sub.grade_status = "reviewed"
        db.commit()
    return {"accepted": accepted, "skipped": skipped, "submission": submission_detail(sub.id, user, db)}


class PublishRequest(BaseModel):
    submission_ids: list[int] | None = None


@router.post("/assignments/{assignment_id}/publish")
def publish(assignment_id: int, body: PublishRequest, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    """Publish grades that pass the gate. Anything resting on an unconfirmed AI suggestion is held back."""
    a = owned_assignment(db, user, assignment_id)
    criteria = list(a.criteria)
    subs = latest_submissions(db, a.id)
    if body.submission_ids is not None:
        wanted = set(body.submission_ids)
        subs = [s for s in subs if s.id in wanted]
    published, blocked = [], []
    for s in subs:
        if s.grade_status == "published":
            continue
        if s.grade_status == "ungraded":
            blocked.append({"submission_id": s.id, "student": s.student.name, "reasons": ["not graded yet"]})
            continue
        reasons = publish_blockers(s, criteria)
        if reasons:
            blocked.append({"submission_id": s.id, "student": s.student.name, "reasons": reasons})
        else:
            s.grade_status = "published"
            published.append(s.id)
    _audit(db, user, "grade.publish", "assignment", a.id, published=len(published), blocked=len(blocked))
    db.commit()
    return {"published": published, "blocked": blocked}


@router.get("/assignments/{assignment_id}/insights")
def list_insights(assignment_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    a = owned_assignment(db, user, assignment_id)
    run = _latest_run(db, a.id, done_only=True)
    if run is None:
        return {"run": None, "insights": []}
    insights = db.scalars(select(m.Insight).where(m.Insight.run_id == run.id).order_by(m.Insight.student_count.desc())).all()
    order = {"misconception": 0, "needs_support": 1}
    return {"run": ser.run_out(run), "insights": [ser.insight_out(i) for i in sorted(insights, key=lambda i: order.get(i.kind, 9))]}


@router.get("/insights/{insight_id}")
def get_insight(insight_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    i = db.get(m.Insight, insight_id)
    if i is None:
        raise HTTPException(404, "Insight not found")
    a = owned_assignment(db, user, i.assignment_id)
    return {**ser.insight_out(i), "assignment": {"id": a.id, "title": a.title, "course_id": a.course_id, "course_code": a.course.code},
            "run": ser.run_out(db.get(m.GradingRun, i.run_id))}

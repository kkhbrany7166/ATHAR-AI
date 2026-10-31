"""Intervention API: professor drafting/approval/monitoring, and the student activity."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from .. import serializers as ser
from ..auth import owned_assignment, require_professor, require_student
from ..db import get_db
from ..interventions import planning
from ..interventions import service as svc

router = APIRouter(prefix="/api", tags=["interventions"])

OUTCOME_FOR_STUDENT = {
    "demonstrated": "You showed it on this task",
    "still_developing": "Still developing. Keep going",
    "insufficient_evidence": "Not enough to tell yet",
}


def _guard(fn, *a, **k):
    try:
        return fn(*a, **k)
    except svc.InterventionError as e:
        raise HTTPException(e.status, str(e)) from e


def _owned(db: Session, user: m.User, iv_id: int) -> m.Intervention:
    iv = db.get(m.Intervention, iv_id)
    if iv is None or db.get(m.Course, iv.course_id).professor_id != user.id:
        raise HTTPException(404, "Intervention not found")
    return iv


def item_out(i: m.AssessmentItem | None, *, for_student: bool = False) -> dict | None:
    if i is None:
        return None
    base = {"id": i.id, "key": i.key, "role": i.role, "title": i.title, "prompt": i.prompt, "explanation_prompt": i.explanation_prompt,
            "starter_code": i.starter_code, "hint_count": len(i.hints)}
    if for_student:
        return {**base, "tests": [t["name"] for t in i.tests if not t.get("hidden")]}
    return {**base, "source": i.source, "tests": i.tests, "validation": i.validation, "misconception_code": i.misconception_code,
            "reference_solution": i.reference_solution, "misconception_solution": i.misconception_solution, "hints": i.hints}


def _latest_verifications(db: Session, task_ids: list[int]) -> dict[int, m.Verification]:
    rows = db.scalars(select(m.Verification).where(m.Verification.task_id.in_(task_ids)).order_by(m.Verification.id)).all()
    return {v.task_id: v for v in rows}


def intervention_out(db: Session, iv: m.Intervention) -> dict:
    users = {u.id: u for u in db.scalars(select(m.User).where(m.User.id.in_(iv.target_student_ids or [0]))).all()}
    tasks = list(iv.tasks)
    latest = _latest_verifications(db, [t.id for t in tasks])
    practice_counts: dict[int, int] = {}
    for (tid,) in db.execute(select(m.PracticeAttempt.task_id).where(m.PracticeAttempt.task_id.in_([t.id for t in tasks] or [0]))).all():
        practice_counts[tid] = practice_counts.get(tid, 0) + 1
    # Original evidence for each target, from the assignment the insight came from.
    orig = {}
    for e in db.scalars(select(m.MisconceptionEvidence).join(m.Submission)
                        .where(m.Submission.assignment_id == iv.assignment_id, m.MisconceptionEvidence.misconception_code == iv.misconception_code)).all():
        orig.setdefault(e.submission.student_id, []).append({"source": e.source, "detail": e.detail, "quote": e.quote})
    by_student = {t.student_id: t for t in tasks}
    students = []
    for sid in iv.target_student_ids:
        u = users.get(sid)
        t = by_student.get(sid)
        v = latest.get(t.id) if t else None
        students.append({
            "student_id": sid, "name": u.name if u else "?", "is_synthetic": bool(u and u.is_synthetic),
            "is_demo_persona": bool(u and u.is_demo_persona), "before": orig.get(sid, []),
            "task": None if t is None else {
                "id": t.id, "status": t.status, "is_simulated": t.is_simulated, "hints_revealed": t.hints_revealed,
                "practice_attempts": practice_counts.get(t.id, 0), "has_initial": bool(t.initial_reasoning),
                "has_revised": bool(t.revised_reasoning), "has_reflection": bool(t.reflection)},
            "verification": None if v is None else {"outcome": v.outcome, "reasons": v.reasons, "tests_passed": v.tests_passed,
                                                    "tests_total": v.tests_total, "submission_id": v.submission_id,
                                                    "explanation_judgment": v.explanation_judgment, "explanation_reader": v.explanation_reader,
                                                    "rule_version": v.rule_version, "at": ser.iso(v.created_at)},
        })
    counts = {k: sum(1 for v in latest.values() if v.outcome == k) for k in ("demonstrated", "still_developing", "insufficient_evidence")}
    items = db.scalars(select(m.AssessmentItem).where(m.AssessmentItem.course_id == iv.course_id, m.AssessmentItem.role == "followup",
                                                      m.AssessmentItem.misconception_code == iv.misconception_code)).all() if iv.kind == "concept_practice" else []
    a = db.get(m.Assignment, iv.assignment_id)
    return {
        "id": iv.id, "status": iv.status, "kind": iv.kind, "title": iv.title, "misconception_code": iv.misconception_code,
        "course_id": iv.course_id, "course_code": a.course.code, "assignment": {"id": a.id, "title": a.title}, "insight_id": iv.insight_id,
        "explanation": iv.explanation, "explanation_source": iv.explanation_source, "professor_note": iv.professor_note,
        "practice_item": item_out(iv.practice_item), "followup_item": item_out(iv.followup_item),
        "followup_options": [item_out(i) for i in items], "followup_assignment_id": iv.followup_assignment_id,
        "target_student_ids": iv.target_student_ids, "students": students, "execution_error": iv.execution_error,
        "created_at": ser.iso(iv.created_at), "approved_at": ser.iso(iv.approved_at), "executed_at": ser.iso(iv.executed_at),
        "closed_at": ser.iso(iv.closed_at),
        "progress": {"targets": len(iv.target_student_ids), "delivered": len(tasks),
                     "started": sum(t.status != "assigned" for t in tasks), "verified": len(latest),
                     "simulated": sum(t.is_simulated for t in tasks), **counts},
        "recommendations": svc.recommendation(tasks, latest) if iv.status in ("active", "completed") else [],
    }


# ------------------------------------------------------------------ professor

@router.post("/professor/insights/{insight_id}/intervention")
def draft(insight_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    i = db.get(m.Insight, insight_id)
    if i is None:
        raise HTTPException(404, "Insight not found")
    owned_assignment(db, user, i.assignment_id)
    iv = _guard(svc.draft_from_insight, db, i, user)
    return intervention_out(db, iv)


@router.get("/professor/interventions/{iv_id}")
def get_intervention(iv_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    return intervention_out(db, _owned(db, user, iv_id))


@router.get("/professor/courses/{course_id}/interventions")
def list_interventions(course_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    course = db.get(m.Course, course_id)
    if course is None or course.professor_id != user.id:
        raise HTTPException(404, "Course not found")
    ivs = db.scalars(select(m.Intervention).where(m.Intervention.course_id == course_id).order_by(m.Intervention.id.desc())).all()
    return [{"id": iv.id, "title": iv.title, "status": iv.status, "kind": iv.kind, "targets": len(iv.target_student_ids),
             "insight_id": iv.insight_id, "created_at": ser.iso(iv.created_at)} for iv in ivs]


@router.get("/professor/assignments/{assignment_id}/plan")
def plan(assignment_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    a = owned_assignment(db, user, assignment_id)
    return planning.plan_for_assignment(db, a)


class GroupDraft(BaseModel):
    category: str
    misconception_code: str = ""
    student_ids: list[int] = Field(min_length=1)


@router.post("/professor/assignments/{assignment_id}/plan/draft")
def draft_group(assignment_id: int, body: GroupDraft, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    """Draft the intervention the diagnosis proposes for a group. The kind comes from fixed rules, not from the client."""
    a = owned_assignment(db, user, assignment_id)
    kind = planning.CATEGORY_ACTION.get(body.category)
    if kind not in ("concept_practice", "debugging", "explain_reasoning"):
        raise HTTPException(422, "This group has no automated intervention.")
    current = planning.plan_for_assignment(db, a)
    group = next((g for g in current["groups"] if g["category"] == body.category and g["misconception_code"] == body.misconception_code), None)
    allowed = {s["student_id"] for s in group["students"]} if group else set()
    if not set(body.student_ids) <= allowed:
        raise HTTPException(422, "Some students are not in this group according to the current evidence.")
    evidence = [e for s in (group["students"] if group else []) for e in s["evidence"]][:8]
    iv = _guard(svc.draft_for_group, db, a, kind, body.misconception_code if kind == "concept_practice" else "",
                body.student_ids, user, evidence=evidence)
    return intervention_out(db, iv)


class DraftEdit(BaseModel):
    explanation: str | None = Field(default=None, max_length=6000)
    target_student_ids: list[int] | None = None
    followup_item_id: int | None = None
    professor_note: str | None = Field(default=None, max_length=2000)


@router.patch("/professor/interventions/{iv_id}")
def edit(iv_id: int, body: DraftEdit, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    iv = _owned(db, user, iv_id)
    _guard(svc.update_draft, db, iv, user, explanation=body.explanation, target_student_ids=body.target_student_ids,
           followup_item_id=body.followup_item_id, professor_note=body.professor_note)
    return intervention_out(db, iv)


@router.post("/professor/interventions/{iv_id}/generate-check")
def generate_check(iv_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    """Ask the LLM for a new follow-up check. It becomes selectable only if the validator accepts it."""
    from ..ai.provider import LLMError, get_provider
    from ..interventions.generation import generate_followup

    iv = _owned(db, user, iv_id)
    if iv.status != "draft" or iv.kind != "concept_practice":
        raise HTTPException(409, "New checks can only be generated for a concept intervention in draft.")
    provider = get_provider()
    if provider is None:
        raise HTTPException(503, "No AI provider is configured, so new checks can't be generated. The validated item bank is still available.")
    try:
        item = generate_followup(db, provider, iv)
    except LLMError as e:
        raise HTTPException(502, f"The AI could not produce a check: {e}") from e
    return {"item": item_out(item), "intervention": intervention_out(db, iv)}


@router.post("/professor/interventions/{iv_id}/approve")
def approve(iv_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    iv = _owned(db, user, iv_id)
    _guard(svc.approve_and_execute, db, iv, user)
    return intervention_out(db, iv)


@router.post("/professor/interventions/{iv_id}/execute")
def execute(iv_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    iv = _owned(db, user, iv_id)
    _guard(svc.execute, db, iv, user)
    return intervention_out(db, iv)


@router.post("/professor/interventions/{iv_id}/reject")
def reject(iv_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    iv = _owned(db, user, iv_id)
    _guard(svc.reject, db, iv, user)
    return intervention_out(db, iv)


@router.post("/professor/interventions/{iv_id}/complete")
def complete(iv_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    iv = _owned(db, user, iv_id)
    _guard(svc.complete, db, iv, user)
    return intervention_out(db, iv)


@router.post("/professor/interventions/{iv_id}/simulate")
def simulate(iv_id: int, user: m.User = Depends(require_professor), db: Session = Depends(get_db)):
    iv = _owned(db, user, iv_id)
    res = _guard(svc.simulate_synthetic, db, iv)
    db.add(m.AuditEvent(actor_id=user.id, action="intervention.simulate", entity="intervention", entity_id=iv.id, payload=res))
    db.commit()
    return {**res, "intervention": intervention_out(db, iv)}


# ------------------------------------------------------------------ student

def task_out(db: Session, t: m.InterventionTask) -> dict:
    iv = t.intervention
    a = db.get(m.Assignment, iv.followup_assignment_id)
    orig_sub = db.scalar(select(m.Submission).where(m.Submission.assignment_id == iv.assignment_id, m.Submission.student_id == t.student_id)
                         .order_by(m.Submission.attempt.desc()).limit(1))
    mine = []
    if orig_sub:
        if iv.kind == "explain_reasoning":
            mine = [f"“{e.quote}”" for e in db.scalars(select(m.MisconceptionEvidence).where(
                m.MisconceptionEvidence.submission_id == orig_sub.id, m.MisconceptionEvidence.source.in_(("ai", "baseline")))).all()][:2]
        elif iv.kind == "debugging":
            mine = [f"{r.error_type}: {r.error_message[:80]}" for r in db.scalars(select(m.TestResult).where(
                m.TestResult.submission_id == orig_sub.id, m.TestResult.status == "error")).all()][:1]
        else:
            mine = [e.detail for e in db.scalars(select(m.MisconceptionEvidence).where(
                m.MisconceptionEvidence.submission_id == orig_sub.id, m.MisconceptionEvidence.source == "tests",
                m.MisconceptionEvidence.misconception_code == iv.misconception_code)).all()]
    practice = db.scalars(select(m.PracticeAttempt).where(m.PracticeAttempt.task_id == t.id).order_by(m.PracticeAttempt.id)).all()
    msgs = db.scalars(select(m.AssistantMessage).where(m.AssistantMessage.task_id == t.id).order_by(m.AssistantMessage.id)).all()
    ver = db.scalars(select(m.Verification).where(m.Verification.task_id == t.id).order_by(m.Verification.id)).all()
    item = iv.practice_item
    return {
        "id": t.id, "status": t.status, "kind": iv.kind, "title": iv.title, "course_code": a.course.code if a else "",
        "my_original_code": orig_sub.code if orig_sub else "",
        "from_assignment": db.get(m.Assignment, iv.assignment_id).title,
        "my_earlier_evidence": mine, "explanation": iv.explanation, "explanation_source": iv.explanation_source,
        "initial_reasoning": t.initial_reasoning, "revised_reasoning": t.revised_reasoning, "reflection": t.reflection,
        "practice": item_out(item, for_student=True),
        "hints": item.hints[: t.hints_revealed] if item else [],
        "practice_attempts": [{"id": p.id, "passed": p.passed, "total": p.total, "results": p.results, "code": p.code,
                               "at": ser.iso(p.created_at)} for p in practice],
        "messages": [{"id": x.id, "role": x.role, "content": x.content, "source": x.source} for x in msgs],
        "check": None if a is None else {"assignment_id": a.id, "title": a.title, "prompt": a.prompt, "explanation_prompt": a.explanation_prompt,
                                         "starter_code": a.starter_code, "conditions": a.conditions, "ai_policy": a.ai_policy,
                                         "visible_tests": [x.name for x in a.tests if not x.hidden]},
        "results": [{"outcome": v.outcome, "label": OUTCOME_FOR_STUDENT[v.outcome], "reasons": v.reasons, "tests_passed": v.tests_passed,
                     "tests_total": v.tests_total, "at": ser.iso(v.created_at)} for v in ver],
        "intervention_status": iv.status,
    }


@router.get("/student/tasks/{task_id}")
def get_task(task_id: int, user: m.User = Depends(require_student), db: Session = Depends(get_db)):
    return task_out(db, _guard(svc.task_for, db, task_id, user))


class Checkpoint(BaseModel):
    kind: str
    text: str = Field(max_length=4000)


@router.post("/student/tasks/{task_id}/checkpoint")
def checkpoint(task_id: int, body: Checkpoint, user: m.User = Depends(require_student), db: Session = Depends(get_db)):
    t = _guard(svc.task_for, db, task_id, user)
    _guard(svc.save_checkpoint, db, t, body.kind, body.text)
    return task_out(db, t)


@router.post("/student/tasks/{task_id}/hint")
def hint(task_id: int, user: m.User = Depends(require_student), db: Session = Depends(get_db)):
    t = _guard(svc.task_for, db, task_id, user)
    svc.reveal_hint(db, t)
    return task_out(db, t)


class Code(BaseModel):
    code: str = Field(max_length=20000)


@router.post("/student/tasks/{task_id}/practice")
def practice(task_id: int, body: Code, user: m.User = Depends(require_student), db: Session = Depends(get_db)):
    t = _guard(svc.task_for, db, task_id, user)
    _guard(svc.run_practice, db, t, body.code)
    return task_out(db, t)


class Ask(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@router.post("/student/tasks/{task_id}/assistant")
def ask(task_id: int, body: Ask, user: m.User = Depends(require_student), db: Session = Depends(get_db)):
    t = _guard(svc.task_for, db, task_id, user)
    svc.assistant_reply(db, t, body.message)
    return task_out(db, t)


class FollowUp(BaseModel):
    code: str = Field(max_length=20000)
    explanation: str = Field(default="", max_length=6000)
    ai_use_disclosure: str = Field(default="", max_length=1000)


@router.post("/student/tasks/{task_id}/followup")
def followup(task_id: int, body: FollowUp, user: m.User = Depends(require_student), db: Session = Depends(get_db)):
    t = _guard(svc.task_for, db, task_id, user)
    _guard(svc.submit_followup, db, t, code=body.code, explanation=body.explanation, disclosure=body.ai_use_disclosure)
    return task_out(db, t)

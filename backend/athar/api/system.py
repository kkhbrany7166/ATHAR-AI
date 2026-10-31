"""Health, demo personas and sign-in."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from .. import serializers as ser
from ..ai.provider import provider_status
from ..auth import current_user, issue_token
from ..db import get_db

router = APIRouter(prefix="/api", tags=["system"])
root_router = APIRouter()


@root_router.get("/", include_in_schema=False)
def api_root():
    return {"service": "ATHAR API", "app": "Open http://localhost:5710 for the ATHAR app. This port (8710) only serves data."}


@router.get("/health")
def health():
    return {"status": "ok", "llm": provider_status()}


@router.get("/auth/personas")
def personas(db: Session = Depends(get_db)):
    """Demo personas, plus a few other synthetic students for exploring the student view."""
    main = db.scalars(select(m.User).where(m.User.is_demo_persona.is_(True)).order_by(m.User.role)).all()
    others = db.scalars(select(m.User).where(m.User.role == "student", m.User.is_demo_persona.is_(False)).order_by(m.User.name)).all()
    return {"personas": [ser.user_brief(u) for u in main], "other_students": [ser.user_brief(u) for u in others]}


class Login(BaseModel):
    user_id: int


@router.post("/auth/demo-login")
def demo_login(body: Login, db: Session = Depends(get_db)):
    user = db.get(m.User, body.user_id)
    if user is None:
        raise HTTPException(404, "Unknown user")
    db.add(m.AuditEvent(actor_id=user.id, action="auth.demo_login", entity="user", entity_id=user.id))
    db.commit()
    return {"token": issue_token(user), "user": ser.user_brief(user)}


@router.get("/me")
def me(user: m.User = Depends(current_user)):
    return ser.user_brief(user)


@router.get("/public/highlight")
def highlight(db: Session = Depends(get_db)):
    """One real, aggregate finding for the landing page. Counts only; no names or student text."""
    run = db.scalar(select(m.GradingRun).where(m.GradingRun.status == "done").order_by(m.GradingRun.id.desc()).limit(1))
    if run is None:
        return {"available": False}
    insights = db.scalars(select(m.Insight).where(m.Insight.run_id == run.id, m.Insight.kind == "misconception")).all()
    if not insights:
        return {"available": False}
    course = db.get(m.Assignment, run.assignment_id).course
    confused = max(insights, key=lambda i: i.evidence["counts"]["working_code_confused_reasoning"])
    n_confused = confused.evidence["counts"]["working_code_confused_reasoning"]
    if n_confused >= 3:
        return {"available": True, "course_code": course.code, "students": n_confused,
                "submitted": confused.evidence["counts"]["submitted"],
                "headline": f"{n_confused} students wrote code that passes every test. The AI flagged their explanations for a closer look.",
                "detail": f"Possible gap: {confused.title.lower()}. Flags are suggestions for the professor to review, not diagnoses.",
                "source": run.ai_status}
    top = max(insights, key=lambda i: i.student_count)
    c = top.evidence["counts"]
    return {"available": True, "course_code": course.code, "students": top.student_count, "submitted": c["submitted"],
            "headline": f"{top.student_count} of {c['submitted']} submissions are flagged for the same possible gap.",
            "detail": f"{top.title}. Most of their code still passes the typical tests, so the grade alone would hide it.",
            "source": run.ai_status}


@router.get("/evaluation")
def evaluation(user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    """Latest results written by `python -m evals.run`. Read-only; nothing is computed here."""
    import json
    from pathlib import Path

    results = Path(__file__).resolve().parents[2] / "evals" / "results"

    def load(name: str):
        p = results / f"{name}.json"
        return json.loads(p.read_text()) if p.exists() else None
    ledger = results / "spend.jsonl"
    spend = [json.loads(x) for x in ledger.read_text().splitlines() if x.strip()] if ledger.exists() else []
    from ..cli import evaluate as planted_recovery

    run = db.scalar(select(m.GradingRun).where(m.GradingRun.status == "done").order_by(m.GradingRun.id.desc()).limit(1))
    classroom = {"reader": run.ai_provider if run else "", "recovery": planted_recovery(db)} if run else None
    return {"dev": load("dev"), "heldout": load("heldout"), "final": load("final"), "final2": load("final2"), "system": load("system"),
            "spend": [r for r in spend if r.get("calls")], "classroom": classroom}


@router.get("/public/example")
def example(db: Session = Depends(get_db)):
    """One concrete stored case for the landing page: all tests pass, and a machine reading quoted the explanation.

    Prefers the demo persona Sara if her case fits; otherwise the first such synthetic submission. Read-only.
    """
    rows = db.execute(select(m.MisconceptionEvidence, m.Submission).join(m.Submission, m.MisconceptionEvidence.submission_id == m.Submission.id)
                      .where(m.MisconceptionEvidence.source.in_(("ai", "baseline")), m.MisconceptionEvidence.quote != "")
                      .order_by(m.Submission.id)).all()
    for ev, sub in rows:
        results = db.scalars(select(m.TestResult).where(m.TestResult.submission_id == sub.id)).all()
        if results and all(r.status == "pass" for r in results) and not sub.assignment.targeted:
            return {"available": True, "student": sub.student.name, "submission_id": sub.id, "tests_passed": len(results),
                    "tests_total": len(results), "quote": ev.quote, "flag": ev.misconception_code,
                    "reader": "AI" if ev.source == "ai" else "rule-based reader", "is_synthetic": sub.is_synthetic}
    return {"available": False}

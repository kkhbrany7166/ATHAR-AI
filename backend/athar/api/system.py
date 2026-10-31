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
                "headline": f"{n_confused} students wrote working code. Their explanations tell a different story.",
                "detail": f"Every test passed, yet their reasoning points to the same gap: {confused.title.lower()}.",
                "source": run.ai_status}
    top = max(insights, key=lambda i: i.student_count)
    c = top.evidence["counts"]
    return {"available": True, "course_code": course.code, "students": top.student_count, "submitted": c["submitted"],
            "headline": f"{top.student_count} of {c['submitted']} students share the same gap.",
            "detail": f"{top.title}. Most of their code still passes the typical tests, so the grade alone would hide it.",
            "source": run.ai_status}


@router.get("/evaluation")
def evaluation(user: m.User = Depends(current_user)):
    """Latest results written by `python -m evals.run`. Read-only; nothing is computed here."""
    import json
    from pathlib import Path

    results = Path(__file__).resolve().parents[2] / "evals" / "results"

    def load(name: str):
        p = results / f"{name}.json"
        return json.loads(p.read_text()) if p.exists() else None
    ledger = results / "spend.jsonl"
    spend = [json.loads(x) for x in ledger.read_text().splitlines() if x.strip()] if ledger.exists() else []
    return {"dev": load("dev"), "heldout": load("heldout"), "final": load("final"), "final2": load("final2"), "system": load("system"),
            "spend": [r for r in spend if r.get("calls")]}

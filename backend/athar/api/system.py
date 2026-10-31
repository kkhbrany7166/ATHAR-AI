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
    main = db.scalars(select(m.User).where(m.User.is_demo_persona.is_(True)).order_by(m.User.role.desc())).all()
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

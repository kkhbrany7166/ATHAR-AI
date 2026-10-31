"""Demo sign-in and role enforcement.

The prototype has no passwords: you pick a persona and the server issues an HMAC-signed token.
Every route still enforces role and ownership on the server, so swapping in real authentication
later only changes how tokens are issued.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .config import get_settings
from .db import get_db

TOKEN_TTL_SECONDS = 12 * 3600


def _sign(payload: bytes) -> str:
    return hmac.new(get_settings().secret.encode(), payload, hashlib.sha256).hexdigest()


def issue_token(user: m.User) -> str:
    payload = json.dumps({"uid": user.id, "role": user.role, "exp": int(time.time()) + TOKEN_TTL_SECONDS}).encode()
    return base64.urlsafe_b64encode(payload).decode() + "." + _sign(payload)


def read_token(token: str) -> dict:
    try:
        body, sig = token.rsplit(".", 1)
        payload = base64.urlsafe_b64decode(body.encode())
    except Exception as e:
        raise HTTPException(401, "Malformed token") from e
    if not hmac.compare_digest(sig, _sign(payload)):
        raise HTTPException(401, "Invalid token")
    data = json.loads(payload)
    if data["exp"] < time.time():
        raise HTTPException(401, "Session expired")
    return data


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> m.User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in required")
    data = read_token(authorization.removeprefix("Bearer "))
    user = db.get(m.User, data["uid"])
    if user is None or user.role != data["role"]:
        raise HTTPException(401, "Unknown user")
    return user


def require_professor(user: m.User = Depends(current_user)) -> m.User:
    if user.role != "professor":
        raise HTTPException(403, "Professor access only")
    return user


def require_student(user: m.User = Depends(current_user)) -> m.User:
    if user.role != "student":
        raise HTTPException(403, "Student access only")
    return user


def owned_course(db: Session, user: m.User, course_id: int) -> m.Course:
    course = db.get(m.Course, course_id)
    if course is None or course.professor_id != user.id:
        raise HTTPException(404, "Course not found")
    return course


def owned_assignment(db: Session, user: m.User, assignment_id: int) -> m.Assignment:
    a = db.get(m.Assignment, assignment_id)
    if a is None or a.course.professor_id != user.id:
        raise HTTPException(404, "Assignment not found")
    return a


def enrolled(db: Session, student: m.User, course_id: int) -> bool:
    return db.scalar(select(m.Enrollment.id).where(m.Enrollment.course_id == course_id, m.Enrollment.student_id == student.id)) is not None

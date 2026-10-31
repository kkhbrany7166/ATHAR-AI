"""Student workspace API. A student only ever sees their own work and student-safe assignment fields."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from .. import serializers as ser
from ..auth import enrolled, require_student
from ..db import get_db

router = APIRouter(prefix="/api/student", tags=["student"])


@router.get("/home")
def home(user: m.User = Depends(require_student), db: Session = Depends(get_db)):
    course_ids = db.scalars(select(m.Enrollment.course_id).where(m.Enrollment.student_id == user.id)).all()
    courses = []
    for c in db.scalars(select(m.Course).where(m.Course.id.in_(course_ids))).all():
        items = []
        for a in db.scalars(select(m.Assignment).where(m.Assignment.course_id == c.id, m.Assignment.status != "draft",
                                                       m.Assignment.targeted.is_(False))).all():
            sub = db.scalar(select(m.Submission).where(m.Submission.assignment_id == a.id, m.Submission.student_id == user.id)
                            .order_by(m.Submission.attempt.desc()).limit(1))
            items.append({"id": a.id, "title": a.title, "kind": a.kind, "conditions": a.conditions, "status": a.status,
                          "due_at": ser.iso(a.due_at),
                          "my_status": "not_submitted" if sub is None else ("feedback_ready" if sub.grade_status == "published" else "submitted")})
        courses.append({"id": c.id, "code": c.code, "title": c.title, "term": c.term, "professor": c.professor.name, "assignments": items})
    tasks = db.scalars(select(m.InterventionTask).join(m.Intervention).where(
        m.InterventionTask.student_id == user.id, m.Intervention.status.in_(("active", "completed")))).all()
    task_rows = []
    for t in tasks:
        last = db.scalar(select(m.Verification).where(m.Verification.task_id == t.id).order_by(m.Verification.id.desc()).limit(1))
        task_rows.append({"id": t.id, "title": t.intervention.title, "status": t.status, "course_id": t.intervention.course_id,
                          "outcome": last.outcome if last else None, "assigned_at": ser.iso(t.created_at)})
    return {"student": ser.user_brief(user), "courses": courses, "tasks": task_rows}


@router.get("/assignments/{assignment_id}")
def assignment(assignment_id: int, user: m.User = Depends(require_student), db: Session = Depends(get_db)):
    a = db.get(m.Assignment, assignment_id)
    if a is None or a.status == "draft" or not enrolled(db, user, a.course_id) or a.targeted:
        raise HTTPException(404, "Assignment not found")
    subs = db.scalars(select(m.Submission).where(m.Submission.assignment_id == a.id, m.Submission.student_id == user.id)
                      .order_by(m.Submission.attempt)).all()
    return {"assignment": ser.assignment_for_student(a), "submissions": [ser.submission_for_student(s) for s in subs]}

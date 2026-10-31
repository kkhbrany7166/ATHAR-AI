"""Build the CS201 demo world: Professor Layla, Sara, 119 synthetic classmates and Assignment 3.

Only *inputs* are seeded (course content, submissions). Grading results, misconception evidence
and insights are produced by running the real grading pipeline on top of this data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .. import models as m
from . import content
from .synthetic import SARA_CODE, SARA_EXPLANATION, generate_class


def _email(name: str) -> str:
    return name.lower().replace(" ", ".").replace("-", "") + "@students.example.edu"


def seed_demo(db: Session) -> dict[str, int]:
    layla = m.User(name="Dr. Layla Al-Mansour", email="layla.almansour@example.edu", role="professor",
                   is_synthetic=True, is_demo_persona=True)
    sara = m.User(name="Sara Al-Harbi", email=_email("Sara Al-Harbi"), role="student", is_synthetic=True, is_demo_persona=True)
    db.add_all([layla, sara])
    db.flush()

    course = m.Course(professor_id=layla.id, **content.COURSE)
    db.add(course)
    db.flush()

    objectives: dict[str, m.LearningObjective] = {}
    for o in content.OBJECTIVES:
        obj = m.LearningObjective(course_id=course.id, source="professor", **o)
        db.add(obj)
        objectives[o["code"]] = obj
    db.flush()
    for mc in content.MISCONCEPTIONS:
        fields = {k: v for k, v in mc.items() if k != "objective"}
        db.add(m.Misconception(objective_id=objectives[mc["objective"]].id, **fields))

    db.add(m.Material(course_id=course.id, title="Lecture 7 — Recursion", kind="lecture_notes", text=content.LECTURE_NOTES))

    now = datetime.now(timezone.utc)
    assignment = m.Assignment(course_id=course.id, status="closed", due_at=now - timedelta(days=2), **content.ASSIGNMENT)
    db.add(assignment)
    db.flush()

    criteria: dict[str, m.RubricCriterion] = {}
    for i, c in enumerate(content.CRITERIA):
        crit = m.RubricCriterion(assignment_id=assignment.id, position=i, code=c["code"], title=c["title"],
                                 description=c["description"], method=c["method"], max_points=c["max_points"],
                                 objective_id=objectives[c["objective"]].id)
        db.add(crit)
        criteria[c["code"]] = crit
    db.flush()
    for i, t in enumerate(content.TESTS):
        db.add(m.TestCase(assignment_id=assignment.id, criterion_id=criteria[t["criterion"]].id, position=i,
                          name=t["name"], function=t["function"], args=t["args"], expected=t["expected"],
                          hidden=t["hidden"], probes=t["probes"]))

    # Sara, the demo persona.
    db.add(m.Enrollment(course_id=course.id, student_id=sara.id))
    sara_sub = m.Submission(assignment_id=assignment.id, student_id=sara.id, code=SARA_CODE, explanation=SARA_EXPLANATION,
                            conditions=assignment.conditions, is_synthetic=True, submitted_at=now - timedelta(days=2, hours=3))
    db.add(sara_sub)
    db.flush()
    db.add(m.SyntheticLabel(submission_id=sara_sub.id, code_pattern="base_smallest_power", explanation_pattern="smallest_belief"))

    names, plans = generate_class()
    submitted = 0
    for i, (name, plan) in enumerate(zip(names, plans)):
        student = m.User(name=name, email=_email(name), role="student", is_synthetic=True)
        db.add(student)
        db.flush()
        db.add(m.Enrollment(course_id=course.id, student_id=student.id))
        if plan.code is None:
            continue
        sub = m.Submission(assignment_id=assignment.id, student_id=student.id, code=plan.code,
                           explanation=plan.explanation, ai_use_disclosure=plan.disclosure,
                           conditions=assignment.conditions, is_synthetic=True,
                           submitted_at=now - timedelta(days=2, minutes=7 * i))
        db.add(sub)
        db.flush()
        db.add(m.SyntheticLabel(submission_id=sub.id, code_pattern=plan.code_pattern, explanation_pattern=plan.explanation_pattern))
        submitted += 1

    db.flush()
    from ..interventions.service import ensure_item_bank  # local import: seeding must not depend on API modules

    db.refresh(course)
    ensure_item_bank(db, course)
    db.add(m.AuditEvent(actor_id=None, action="seed.demo", entity="course", entity_id=course.id,
                        payload={"students": len(names) + 1, "submissions": submitted + 1}))
    db.commit()
    return {"course_id": course.id, "assignment_id": assignment.id, "professor_id": layla.id, "sara_id": sara.id,
            "students": len(names) + 1, "submissions": submitted + 1}

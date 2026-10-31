"""ORM tables. Business rules live in the service modules, not here."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    role: Mapped[str] = mapped_column(String(20))  # professor | student
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo_persona: Mapped[bool] = mapped_column(Boolean, default=False)


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    term: Mapped[str] = mapped_column(String(40), default="")
    professor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)

    professor: Mapped[User] = relationship()
    objectives: Mapped[list[LearningObjective]] = relationship(back_populates="course", order_by="LearningObjective.code")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("course_id", "student_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class LearningObjective(Base):
    __tablename__ = "learning_objectives"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    code: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    # Where the objective came from: "professor" (authored) or "ai_proposed" (pending review).
    source: Mapped[str] = mapped_column(String(20), default="professor")

    course: Mapped[Course] = relationship(back_populates="objectives")
    misconceptions: Mapped[list[Misconception]] = relationship(back_populates="objective")


class Misconception(Base):
    """A *hypothesis* about a common error, authored with the rubric. Its presence in a class is computed."""

    __tablename__ = "misconceptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    objective_id: Mapped[int] = mapped_column(ForeignKey("learning_objectives.id"))
    code: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    why_it_matters: Mapped[str] = mapped_column(Text, default="")

    objective: Mapped[LearningObjective] = relationship(back_populates="misconceptions")


class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    title: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(30))  # lecture_notes | assignment | rubric | reading
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    title: Mapped[str] = mapped_column(String(300))
    prompt: Mapped[str] = mapped_column(Text)
    explanation_prompt: Mapped[str] = mapped_column(Text, default="")
    # guided_practice: AI help is part of the activity. assessment_check: evidence of independent work.
    kind: Mapped[str] = mapped_column(String(30))
    # assisted | unsupervised | supervised
    conditions: Mapped[str] = mapped_column(String(30))
    ai_policy: Mapped[str] = mapped_column(Text, default="")
    starter_code: Mapped[str] = mapped_column(Text, default="")
    reference_solution: Mapped[str] = mapped_column(Text, default="")  # never sent to students
    status: Mapped[str] = mapped_column(String(20), default="open")  # draft | open | closed
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    course: Mapped[Course] = relationship()
    criteria: Mapped[list[RubricCriterion]] = relationship(back_populates="assignment", order_by="RubricCriterion.position")
    tests: Mapped[list[TestCase]] = relationship(back_populates="assignment", order_by="TestCase.position")


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    code: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    objective_id: Mapped[int | None] = mapped_column(ForeignKey("learning_objectives.id"), nullable=True)
    # tests: scored from test outcomes. explanation: AI-suggested from written reasoning, human-confirmed.
    method: Mapped[str] = mapped_column(String(20))
    max_points: Mapped[float] = mapped_column(Float)

    assignment: Mapped[Assignment] = relationship(back_populates="criteria")
    objective: Mapped[LearningObjective | None] = relationship()


class TestCase(Base):
    __tablename__ = "test_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"))
    criterion_id: Mapped[int] = mapped_column(ForeignKey("rubric_criteria.id"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(200))
    function: Mapped[str] = mapped_column(String(80))
    args: Mapped[list[Any]] = mapped_column(JSON)
    expected: Mapped[Any] = mapped_column(JSON)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    # [{"misconception": "MC-...", "on": "error" | "wrong_value" | "any_fail", "error_types": [...]}]
    probes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    assignment: Mapped[Assignment] = relationship(back_populates="tests")


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("assignment_id", "student_id", "attempt"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    code: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, default="")
    conditions: Mapped[str] = mapped_column(String(30))  # copied from assignment at submit time
    ai_use_disclosure: Mapped[str] = mapped_column(Text, default="")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # ungraded | graded (evidence prepared) | reviewed (professor confirmed) | published
    grade_status: Mapped[str] = mapped_column(String(20), default="ungraded")

    student: Mapped[User] = relationship()
    assignment: Mapped[Assignment] = relationship()
    test_results: Mapped[list[TestResult]] = relationship(back_populates="submission", cascade="all, delete-orphan")
    evidence: Mapped[list[CriterionEvidence]] = relationship(back_populates="submission", cascade="all, delete-orphan")


class TestResult(Base):
    __tablename__ = "test_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("grading_runs.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # pass | fail | error | timeout | not_run
    actual: Mapped[str] = mapped_column(Text, default="")
    error_type: Mapped[str] = mapped_column(String(80), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")

    submission: Mapped[Submission] = relationship(back_populates="test_results")
    test_case: Mapped[TestCase] = relationship()


class CriterionEvidence(Base):
    """One judgment about one criterion for one submission, from one source.

    Several rows can exist per criterion: e.g. an AI suggestion and a professor decision.
    The professor row, when present, is authoritative.
    """

    __tablename__ = "criterion_evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    criterion_id: Mapped[int] = mapped_column(ForeignKey("rubric_criteria.id"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("grading_runs.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(20))  # tests | ai | professor
    # met | partial | not_met | unclear | ai_unavailable | ai_failed
    judgment: Mapped[str] = mapped_column(String(20))
    points: Mapped[float | None] = mapped_column(Float, nullable=True)
    rationale: Mapped[str] = mapped_column(Text, default="")
    quotes: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[str] = mapped_column(String(10), default="")  # high | medium | low
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    review_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    model: Mapped[str] = mapped_column(String(80), default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    submission: Mapped[Submission] = relationship(back_populates="evidence")
    criterion: Mapped[RubricCriterion] = relationship()


class MisconceptionEvidence(Base):
    """A single observation that a submission may show a misconception, with where it came from."""

    __tablename__ = "misconception_evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    misconception_code: Mapped[str] = mapped_column(String(40))  # catalog code, or "OTHER"
    run_id: Mapped[int | None] = mapped_column(ForeignKey("grading_runs.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(20))  # tests | ai
    detail: Mapped[str] = mapped_column(Text, default="")
    test_result_id: Mapped[int | None] = mapped_column(ForeignKey("test_results.id"), nullable=True)
    quote: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str] = mapped_column(String(10), default="")

    submission: Mapped[Submission] = relationship()


class GradingRun(Base):
    __tablename__ = "grading_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"))
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued | running | done | failed
    stage: Mapped[str] = mapped_column(String(40), default="")
    total: Mapped[int] = mapped_column(Integer, default=0)
    tests_done: Mapped[int] = mapped_column(Integer, default=0)
    ai_done: Mapped[int] = mapped_column(Integer, default=0)
    ai_failed: Mapped[int] = mapped_column(Integer, default=0)
    # used | unavailable | partial | failed
    ai_status: Mapped[str] = mapped_column(String(20), default="")
    ai_provider: Mapped[str] = mapped_column(String(40), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    started_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Insight(Base):
    __tablename__ = "insights"
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"))
    run_id: Mapped[int] = mapped_column(ForeignKey("grading_runs.id"))
    kind: Mapped[str] = mapped_column(String(30))  # misconception | needs_support
    objective_id: Mapped[int | None] = mapped_column(ForeignKey("learning_objectives.id"), nullable=True)
    misconception_code: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    student_count: Mapped[int] = mapped_column(Integer)
    # Structured, traceable evidence (ids of submissions, test results, quotes). See insights.py.
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="open")  # open | dismissed | intervention_drafted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    objective: Mapped[LearningObjective | None] = relationship()


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SyntheticLabel(Base):
    """Ground truth for synthetic submissions. Only evaluation code may read this table."""

    __tablename__ = "synthetic_labels"
    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), unique=True)
    code_pattern: Mapped[str] = mapped_column(String(60))
    explanation_pattern: Mapped[str] = mapped_column(String(60))

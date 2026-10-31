"""The grading run: tests → test-based evidence → AI explanation analysis → insights.

A run is persisted in `grading_runs` and executed in a worker thread. Re-running replaces machine
evidence (tests/rules/AI) but never touches professor decisions.
"""

from __future__ import annotations

import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import models as m
from ..ai.reader import Reader, choose_reader
from ..db import SessionLocal
from ..insights import compute_insights
from . import evidence as ev
from .sandbox import RunReport, TestSpec, run_tests

ACTIVE = ("queued", "running")


def latest_submissions(db: Session, assignment_id: int) -> list[m.Submission]:
    subs = db.scalars(select(m.Submission).where(m.Submission.assignment_id == assignment_id).order_by(m.Submission.attempt)).all()
    latest: dict[int, m.Submission] = {}
    for s in subs:
        latest[s.student_id] = s
    return list(latest.values())


def start_run(db: Session, assignment_id: int, user_id: int | None, *, background: bool = True) -> m.GradingRun:
    """Create a run, or return the one already in progress (idempotent while active)."""
    existing = db.scalar(select(m.GradingRun).where(m.GradingRun.assignment_id == assignment_id, m.GradingRun.status.in_(ACTIVE)))
    if existing:
        return existing
    run = m.GradingRun(assignment_id=assignment_id, status="queued", started_by=user_id)
    db.add(run)
    db.add(m.AuditEvent(actor_id=user_id, action="grading.start", entity="assignment", entity_id=assignment_id))
    db.commit()
    if background:
        threading.Thread(target=execute_run, args=(run.id,), daemon=True).start()
    else:
        execute_run(run.id)
        db.refresh(run)
    return run


def _test_summary(tests: list[m.TestCase], report: RunReport) -> str:
    by_id = {o.id: o for o in report.outcomes}
    lines = []
    for t in tests:
        o = by_id.get(t.id)
        if o is None:
            continue
        detail = "passed" if o.status == "pass" else f"{o.status}" + (f" ({o.error_type})" if o.error_type else f", got {o.actual}")
        lines.append(f"- {t.name}: {detail}")
    if report.load_error:
        lines.insert(0, f"Code failed to load: {report.load_error['type']}: {report.load_error['message']}")
    return "\n".join(lines)


def execute_run(run_id: int) -> None:
    db = SessionLocal()
    run = db.get(m.GradingRun, run_id)
    try:
        _execute(db, run, choose_reader())
    except Exception as e:  # record the failure; never pretend the run succeeded
        db.rollback()
        run = db.get(m.GradingRun, run_id)
        run.status = "failed"
        run.error = f"{e.__class__.__name__}: {e}\n{traceback.format_exc(limit=3)}"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def _execute(db: Session, run: m.GradingRun, reader: Reader) -> None:
    assignment = db.get(m.Assignment, run.assignment_id)
    tests = list(assignment.tests)
    criteria = list(assignment.criteria)
    test_criteria = [c for c in criteria if c.method == "tests"]
    expl_criteria = [c for c in criteria if c.method == "explanation"]
    subs = latest_submissions(db, assignment.id)
    misconceptions = db.scalars(
        select(m.Misconception).join(m.LearningObjective).where(m.LearningObjective.course_id == assignment.course_id)
    ).all()

    run.status, run.stage, run.total = "running", "tests", len(subs)
    run.ai_provider = reader.label
    db.commit()

    # ---- 1. tests (parallel sandbox processes; DB writes stay on this thread) ----
    specs = [TestSpec(t.id, t.function, t.args, t.expected) for t in tests]
    with ThreadPoolExecutor(max_workers=8) as pool:
        reports = list(pool.map(lambda s: run_tests(s.code, specs), subs))

    tests_by_id = {t.id: t for t in tests}
    for sub, report in zip(subs, reports):
        # Replace machine-produced evidence from earlier runs; keep professor decisions.
        db.execute(delete(m.MisconceptionEvidence).where(m.MisconceptionEvidence.submission_id == sub.id))
        db.execute(delete(m.TestResult).where(m.TestResult.submission_id == sub.id))
        db.execute(delete(m.CriterionEvidence).where(m.CriterionEvidence.submission_id == sub.id,
                                                     m.CriterionEvidence.source.in_(("tests", "rules", "ai"))))
        db.flush()
        result_rows = {}
        for o in report.outcomes:
            tr = m.TestResult(submission_id=sub.id, test_case_id=o.id, run_id=run.id, status=o.status, actual=o.actual,
                              error_type=o.error_type, error_message=o.error_message)
            db.add(tr)
            result_rows[o.id] = tr
        db.flush()
        load_failed = report.load_error is not None or any(o.error_type == "Crash" for o in report.outcomes)
        for c in test_criteria:
            outs = [(tests_by_id[o.id], o.status, o.error_type) for o in report.outcomes if tests_by_id[o.id].criterion_id == c.id]
            score = ev.score_test_criterion(c, outs)
            reasons = ["code_did_not_load"] if load_failed else []
            db.add(m.CriterionEvidence(submission_id=sub.id, criterion_id=c.id, run_id=run.id, source="tests",
                                       judgment=score.judgment, points=score.points, rationale=score.rationale,
                                       needs_review=bool(reasons), review_reasons=reasons, confidence="high"))
        for o in report.outcomes:
            for code in ev.probe_hits(tests_by_id[o.id], o.status, o.error_type, load_failed):
                tc = tests_by_id[o.id]
                detail = f"{tc.name}: " + (f"{o.error_type}" if o.status in ("error", "timeout") else f"returned {o.actual}")
                db.add(m.MisconceptionEvidence(submission_id=sub.id, misconception_code=code, run_id=run.id, source="tests",
                                               detail=detail, test_result_id=result_rows[o.id].id, confidence="high"))
        run.tests_done += 1
    db.commit()

    # ---- 2. explanations ----
    run.stage = "explanations"
    db.commit()
    crit_payload = [{"code": c.code, "title": c.title, "description": c.description} for c in expl_criteria]
    mc_payload = [{"code": mc.code, "title": mc.title, "description": mc.description} for mc in misconceptions]
    crit_by_code = {c.code: c for c in expl_criteria}

    def analyze_one(args):
        sub, report = args
        if not sub.explanation.strip():
            return sub, None, None
        if reader.kind == "none":
            return sub, None, "unavailable"
        try:
            result = reader.read(
                explanation=sub.explanation, criteria=crit_payload, misconceptions=mc_payload,
                assignment_prompt=assignment.prompt, explanation_prompt=assignment.explanation_prompt,
                code=sub.code, test_summary=_test_summary(tests, report),
            )
            return sub, result, None
        except Exception as e:  # noqa: BLE001 - every failure is recorded per submission
            return sub, None, f"{e.__class__.__name__}: {e}"[:500]

    if expl_criteria:
        with ThreadPoolExecutor(max_workers=6 if reader.kind == "llm" else 1) as pool:
            for sub, result, err in pool.map(analyze_one, list(zip(subs, reports))):
                _store_explanation_evidence(db, run, sub, expl_criteria, crit_by_code, result, err, reader)
                if err and err != "unavailable":
                    run.ai_failed += 1
                elif result is not None:
                    run.ai_done += 1
                db.commit()

    if not expl_criteria:
        run.ai_status = "not_needed"
    elif reader.kind == "none":
        run.ai_status = "unavailable"
    elif run.ai_failed and run.ai_done:
        run.ai_status = "partial"
    elif run.ai_failed:
        run.ai_status = "failed"
    else:
        run.ai_status = "used" if reader.kind == "llm" else "baseline"

    # ---- 3. status + insights ----
    for sub in subs:
        if sub.grade_status == "ungraded":
            sub.grade_status = "graded"
    run.stage = "insights"
    db.commit()
    compute_insights(db, assignment, run)
    run.status, run.stage = "done", ""
    run.finished_at = datetime.now(timezone.utc)
    db.add(m.AuditEvent(actor_id=run.started_by, action="grading.done", entity="grading_run", entity_id=run.id,
                        payload={"ai_status": run.ai_status, "submissions": run.total, "ai_failed": run.ai_failed}))
    db.commit()


def _store_explanation_evidence(db, run, sub, expl_criteria, crit_by_code, result, err, reader: Reader) -> None:
    if result is None:
        if not sub.explanation.strip():
            for c in expl_criteria:
                db.add(m.CriterionEvidence(submission_id=sub.id, criterion_id=c.id, run_id=run.id, source="rules",
                                           judgment="not_met", points=0.0, rationale="No written explanation was submitted.",
                                           confidence="high"))
            return
        judgment = "ai_unavailable" if err == "unavailable" else "ai_failed"
        rationale = ("No AI provider is configured, so this explanation has not been analysed. It needs professor review."
                     if err == "unavailable" else f"AI analysis failed: {err}. It needs professor review.")
        for c in expl_criteria:
            db.add(m.CriterionEvidence(submission_id=sub.id, criterion_id=c.id, run_id=run.id, source="ai", judgment=judgment,
                                       points=None, rationale=rationale, needs_review=True, review_reasons=[judgment],
                                       model=reader.label))
        return

    model, source = reader.label, reader.source
    for c in expl_criteria:
        v = result.criteria.get(c.code)
        if v is None:
            db.add(m.CriterionEvidence(submission_id=sub.id, criterion_id=c.id, run_id=run.id, source=source, judgment="ai_failed",
                                       points=None, rationale="The AI response did not include this criterion.",
                                       needs_review=True, review_reasons=["missing_from_ai_output"], model=model))
            continue
        points = round(c.max_points * ev.AI_POINTS[v.judgment], 2) if v.judgment in ev.AI_POINTS else None
        reasons = list(v.review_reasons)
        if result.rejected:
            reasons.append("ai_output_partially_rejected")
        db.add(m.CriterionEvidence(submission_id=sub.id, criterion_id=c.id, run_id=run.id, source=source, judgment=v.judgment,
                                   points=points, rationale=v.rationale, quotes=v.quotes, confidence=v.confidence,
                                   needs_review=bool(reasons), review_reasons=sorted(set(reasons)), model=model))
    for s in result.signals:
        db.add(m.MisconceptionEvidence(submission_id=sub.id, misconception_code=s.code, run_id=run.id, source=source,
                                       detail=s.reasoning, quote=s.quote, confidence=s.confidence))

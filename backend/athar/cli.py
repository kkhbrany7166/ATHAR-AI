"""Command line: reset and seed the demo, run grading, evaluate against synthetic labels.

    .venv/bin/python -m athar.cli reset            # drop everything, seed the CS201 demo
    .venv/bin/python -m athar.cli reset --grade    # ...and run grading synchronously
    .venv/bin/python -m athar.cli grade            # (re)run grading for the demo assignment
    .venv/bin/python -m athar.cli eval             # compare detected misconceptions with planted labels
    .venv/bin/python -m athar.cli reset-interventions   # back to "insights ready", keeping the AI grading (free)
"""

from __future__ import annotations

import argparse
import json

from sqlalchemy import select

from . import models as m
from .ai.provider import provider_status
from .db import SessionLocal, init_db, reset_db
from .grading.pipeline import start_run
from .seed.demo import seed_demo


def _grade(db) -> None:
    assignment = db.scalar(select(m.Assignment).order_by(m.Assignment.id))
    print(f"LLM: {provider_status()}")
    run = start_run(db, assignment.id, None, background=False)
    print(json.dumps({"run": run.id, "status": run.status, "ai_status": run.ai_status, "graded": run.tests_done,
                      "ai_done": run.ai_done, "ai_failed": run.ai_failed, "error": run.error[:400]}, indent=2))
    for i in db.scalars(select(m.Insight).where(m.Insight.run_id == run.id)).all():
        print(f"- [{i.kind}] {i.title}: {i.summary}")


def reset_interventions(db) -> dict:
    """Remove all intervention work (drafts, tasks, follow-ups, attempts, verifications) but keep the graded class.

    Free to run: no model calls. Use it to rehearse the demo from the 'insights ready' state.
    """
    from sqlalchemy import delete

    targeted = [a.id for a in db.scalars(select(m.Assignment).where(m.Assignment.targeted.is_(True))).all()]
    subs = [s.id for s in db.scalars(select(m.Submission).where(m.Submission.assignment_id.in_(targeted or [0]))).all()]
    for model, col, ids in [(m.ExplanationReadingRecord, m.ExplanationReadingRecord.submission_id, subs),
                            (m.MisconceptionEvidence, m.MisconceptionEvidence.submission_id, subs),
                            (m.CriterionEvidence, m.CriterionEvidence.submission_id, subs),
                            (m.TestResult, m.TestResult.submission_id, subs)]:
        db.execute(delete(model).where(col.in_(ids or [0])))
    db.execute(delete(m.Verification))
    db.execute(delete(m.AssistantMessage))
    db.execute(delete(m.PracticeAttempt))
    db.execute(delete(m.InterventionTask))
    db.execute(delete(m.Submission).where(m.Submission.id.in_(subs or [0])))
    db.execute(delete(m.Intervention))
    db.execute(delete(m.TestCase).where(m.TestCase.assignment_id.in_(targeted or [0])))
    db.execute(delete(m.RubricCriterion).where(m.RubricCriterion.assignment_id.in_(targeted or [0])))
    db.execute(delete(m.Assignment).where(m.Assignment.id.in_(targeted or [0])))
    db.execute(delete(m.AssessmentItem).where(m.AssessmentItem.source.like("ai:%")))
    for i in db.scalars(select(m.Insight)).all():
        i.status = "open"
    db.flush()
    # Rebuild insights from the stored evidence so the current deterministic rules apply (no model calls).
    from .insights import compute_insights
    for a in db.scalars(select(m.Assignment).where(m.Assignment.targeted.is_(False))).all():
        run = db.scalar(select(m.GradingRun).where(m.GradingRun.assignment_id == a.id, m.GradingRun.status == "done")
                        .order_by(m.GradingRun.id.desc()).limit(1))
        if run:
            compute_insights(db, a, run)
    db.add(m.AuditEvent(actor_id=None, action="demo.reset_interventions", entity="course", entity_id=None, payload={"followups_removed": len(targeted)}))
    db.commit()
    return {"followup_assignments_removed": len(targeted), "followup_submissions_removed": len(subs)}


def evaluate(db) -> dict:
    """Detection quality on synthetic data: planted labels vs. what the pipeline found. Reads synthetic_labels."""
    labels = {lab.submission_id: lab for lab in db.scalars(select(m.SyntheticLabel)).all()}
    from .grading.disputes import dispute_reason

    readings = {r.submission_id: r for r in db.scalars(select(m.ExplanationReadingRecord)).all()}
    found: dict[int, set[str]] = {}
    kept: dict[int, set[str]] = {}  # after setting aside reading claims disputed by their own quote
    for e in db.scalars(select(m.MisconceptionEvidence)).all():
        found.setdefault(e.submission_id, set()).add(e.misconception_code)
        if not dispute_reason(e, readings.get(e.submission_id)):
            kept.setdefault(e.submission_id, set()).add(e.misconception_code)
    planted_map = {
        "MC-BASE-SMALLEST": lambda lab: lab.code_pattern.startswith("base_smallest"),
        "MC-BASE-VALUE": lambda lab: lab.code_pattern.startswith("base_value"),
        "MC-NO-PROGRESS": lambda lab: lab.code_pattern.startswith("no_progress"),
        "MC-STOP-IMPLICIT": lambda lab: lab.explanation_pattern == "implicit_stop",
    }
    report = {}
    for code, is_planted in planted_map.items():
        planted = {sid for sid, lab in labels.items() if is_planted(lab)}
        detected = {sid for sid, codes in found.items() if code in codes}
        after = {sid for sid, codes in kept.items() if code in codes}
        report[code] = {"planted": len(planted), "detected": len(detected), "true_positive": len(planted & detected),
                        "missed": len(planted - detected), "extra": len(detected - planted),
                        "after_dispute_rule": {"detected": len(after), "true_positive": len(planted & after),
                                               "extra": len(after - planted), "missed": len(planted - after)}}
    return report


def main() -> None:
    ap = argparse.ArgumentParser(prog="athar")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("reset")
    r.add_argument("--grade", action="store_true")
    sub.add_parser("grade")
    sub.add_parser("reset-interventions", help="clear intervention work, keep grading (no model calls)")
    sub.add_parser("eval")
    args = ap.parse_args()

    if args.cmd == "reset":
        reset_db()
        with SessionLocal() as db:
            print(json.dumps(seed_demo(db), indent=2))
            if args.grade:
                _grade(db)
    elif args.cmd == "grade":
        init_db()
        with SessionLocal() as db:
            _grade(db)
    elif args.cmd == "reset-interventions":
        with SessionLocal() as db:
            print(json.dumps(reset_interventions(db), indent=2))
    elif args.cmd == "eval":
        with SessionLocal() as db:
            print(json.dumps(evaluate(db), indent=2))


if __name__ == "__main__":
    main()

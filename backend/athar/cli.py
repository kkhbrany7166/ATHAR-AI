"""Command line: reset and seed the demo, run grading, evaluate against synthetic labels.

    .venv/bin/python -m athar.cli reset            # drop everything, seed the CS201 demo
    .venv/bin/python -m athar.cli reset --grade    # ...and run grading synchronously
    .venv/bin/python -m athar.cli grade            # (re)run grading for the demo assignment
    .venv/bin/python -m athar.cli eval             # compare detected misconceptions with planted labels
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


def evaluate(db) -> dict:
    """Detection quality on synthetic data: planted labels vs. what the pipeline found. Reads synthetic_labels."""
    labels = {lab.submission_id: lab for lab in db.scalars(select(m.SyntheticLabel)).all()}
    found: dict[int, set[str]] = {}
    for e in db.scalars(select(m.MisconceptionEvidence)).all():
        found.setdefault(e.submission_id, set()).add(e.misconception_code)
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
        report[code] = {"planted": len(planted), "detected": len(detected), "true_positive": len(planted & detected),
                        "missed": len(planted - detected), "extra": len(detected - planted)}
    return report


def main() -> None:
    ap = argparse.ArgumentParser(prog="athar")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("reset")
    r.add_argument("--grade", action="store_true")
    sub.add_parser("grade")
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
    elif args.cmd == "eval":
        with SessionLocal() as db:
            print(json.dumps(evaluate(db), indent=2))


if __name__ == "__main__":
    main()

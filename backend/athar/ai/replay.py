"""Recorded AI readings for the synthetic demo class, replayed without a model call.

Judges and developers without an API key can still inspect the AI evidence: `athar.cli reset --replay` seeds the
synthetic class, runs the real sandboxed tests, and fills explanation readings from `seed/recorded_readings.json`.
That file holds the validated outputs of one live gpt-4.1-mini grading run (reader-v3), keyed by a hash of each
submission's (synthetic) student email, code and explanation. Replayed readings are labelled as recorded everywhere they appear, and a
submission the recording doesn't cover is marked as failed rather than guessed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from .explanations import ValidatedAnalysis, ValidatedCriterion, ValidatedSignal

RECORDING = Path(__file__).resolve().parents[1] / "seed" / "recorded_readings.json"
_ADDED_BY_STORAGE = {"ai_output_partially_rejected"}  # re-added when the analysis is stored again


def key(student: str, code: str, explanation: str) -> str:
    """Synthetic templates can repeat, so the student's (synthetic) email is part of the key."""
    return hashlib.sha256(f"{student}\x00{code}\x00{explanation}".encode()).hexdigest()[:20]


def export_recording(db: Session, assignment_id: int, path: Path = RECORDING) -> dict:
    """Write the stored AI readings of the latest done run for an assignment. Only source == 'ai' rows are exported."""
    from ..grading.pipeline import latest_submissions

    run = db.scalar(select(m.GradingRun).where(m.GradingRun.assignment_id == assignment_id, m.GradingRun.status == "done")
                    .order_by(m.GradingRun.id.desc()).limit(1))
    if run is None or run.ai_status != "used":
        raise RuntimeError("No completed live AI run to record.")
    codes = {c.id: c.code for c in db.scalars(select(m.RubricCriterion).where(m.RubricCriterion.assignment_id == assignment_id))}
    readings = {}
    for sub in latest_submissions(db, assignment_id):
        r = db.scalar(select(m.ExplanationReadingRecord).where(m.ExplanationReadingRecord.submission_id == sub.id,
                                                               m.ExplanationReadingRecord.source == "ai"))
        if r is None:
            continue
        crit = db.scalars(select(m.CriterionEvidence).where(m.CriterionEvidence.submission_id == sub.id,
                                                            m.CriterionEvidence.source == "ai")).all()
        sig = db.scalars(select(m.MisconceptionEvidence).where(m.MisconceptionEvidence.submission_id == sub.id,
                                                               m.MisconceptionEvidence.source == "ai")).all()
        readings[key(sub.student.email, sub.code, sub.explanation)] = {
            "criteria": [{"code": codes[c.criterion_id], "judgment": c.judgment, "rationale": c.rationale, "quotes": c.quotes,
                          "confidence": c.confidence, "review_reasons": [x for x in c.review_reasons if x not in _ADDED_BY_STORAGE]}
                         for c in crit],
            "signals": [{"code": s.misconception_code, "quote": s.quote, "reasoning": s.detail, "confidence": s.confidence} for s in sig],
            "reading": {"prompt_version": r.prompt_version, "abstained": r.abstained, "abstain_reason": r.abstain_reason,
                        "answer_type": r.answer_type, "code_issue": r.code_issue, "summary": r.summary, "objectives": r.objectives,
                        "contradictions": r.contradictions, "missing_evidence": r.missing_evidence,
                        "rejected_ideas": r.rejected_ideas, "validation_notes": r.validation_notes},
        }
    out = {"model": run.ai_provider, "recorded_at": (run.finished_at or run.started_at).strftime("%Y-%m-%d"),
           "note": "Validated outputs of one live grading run on the synthetic demo class. Replayed, not fresh inference.",
           "readings": dict(sorted(readings.items()))}
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    return {"path": str(path), "readings": len(readings), "model": run.ai_provider}


class Recording:
    def __init__(self, path: Path = RECORDING):
        data = json.loads(path.read_text())
        self.model, self.recorded_at, self.readings = data["model"], data["recorded_at"], data["readings"]

    @property
    def label(self) -> str:
        return f"{self.model} (recorded {self.recorded_at}, replayed)"

    def analysis(self, student: str, code: str, explanation: str) -> ValidatedAnalysis:
        rec = self.readings.get(key(student, code, explanation))
        if rec is None:
            raise LookupError("this submission isn't in the recording, so it wasn't read")
        r = rec["reading"]
        return ValidatedAnalysis(
            criteria={c["code"]: ValidatedCriterion(c["code"], c["judgment"], c["rationale"], c["quotes"], c["confidence"], c["review_reasons"])
                      for c in rec["criteria"]},
            signals=[ValidatedSignal(s["code"], s["quote"], s["reasoning"], s["confidence"]) for s in rec["signals"]],
            rejected=r["validation_notes"],
            rejected_ideas=[ValidatedSignal(x["code"], x.get("quote", ""), x.get("reasoning", ""), "") for x in r["rejected_ideas"]],
            objectives=r["objectives"], contradictions=r["contradictions"], missing_evidence=r["missing_evidence"],
            abstained=r["abstained"], abstain_reason=r["abstain_reason"], answer_type=r["answer_type"], code_issue=r["code_issue"],
            summary=r["summary"], prompt_version=r["prompt_version"],
        )

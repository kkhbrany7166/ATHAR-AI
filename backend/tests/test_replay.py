"""Recorded readings replay exactly, make no model calls, and are labelled as replayed."""

from sqlalchemy import select

from athar import models as m
from athar.ai.reader import Reader
from athar.ai.replay import Recording, export_recording
from athar.grading.pipeline import start_run


def _evidence(db, assignment_id):
    rows = db.execute(select(m.CriterionEvidence.submission_id, m.CriterionEvidence.criterion_id, m.CriterionEvidence.judgment,
                             m.CriterionEvidence.points, m.CriterionEvidence.quotes)
                      .join(m.Submission).where(m.Submission.assignment_id == assignment_id, m.CriterionEvidence.source == "ai")).all()
    mcs = db.execute(select(m.MisconceptionEvidence.submission_id, m.MisconceptionEvidence.misconception_code, m.MisconceptionEvidence.quote)
                     .join(m.Submission).where(m.Submission.assignment_id == assignment_id, m.MisconceptionEvidence.source == "ai")).all()
    return sorted(map(tuple, rows), key=str), sorted(map(tuple, mcs), key=str)


def test_replay_reproduces_recorded_readings_without_model_calls(db, world, scripted, tmp_path):
    aid = world["assignment_id"]
    start_run(db, aid, None, background=False)
    live = _evidence(db, aid)
    calls = scripted.calls
    out = export_recording(db, aid, path=tmp_path / "rec.json")
    assert out["readings"] > 0

    run = start_run(db, aid, None, background=False, reader=Reader("replay", recording=Recording(tmp_path / "rec.json")))
    assert run.ai_status == "replayed" and run.ai_failed == 0 and "replayed" in run.ai_provider
    assert scripted.calls == calls  # nothing was sent to a model
    db.expire_all()
    assert _evidence(db, aid) == live


def test_unrecorded_submission_is_marked_failed_not_guessed(db, world, scripted, tmp_path):
    aid = world["assignment_id"]
    start_run(db, aid, None, background=False)
    export_recording(db, aid, path=tmp_path / "rec.json")
    sub = db.scalars(select(m.Submission).where(m.Submission.assignment_id == aid, m.Submission.explanation != "")).first()
    sub.explanation += " Edited after recording."
    db.commit()
    run = start_run(db, aid, None, background=False, reader=Reader("replay", recording=Recording(tmp_path / "rec.json")))
    assert run.ai_failed == 1 and run.ai_status == "partial"

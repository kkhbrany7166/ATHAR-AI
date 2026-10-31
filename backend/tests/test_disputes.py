"""A reading that contradicts its own quote is shown, routed to review, and never becomes a diagnosis on its own."""

from sqlalchemy import delete, select

from athar import models as m
from athar.grading.disputes import dispute_reason
from athar.grading.pipeline import latest_submissions, start_run
from athar.insights import compute_insights

from .conftest import login

LAYAN_QUOTE = "The base case for power is exp == 0, which returns 1 since any number to the zero power is 1."


def _ai(code="MC-BASE-SMALLEST", quote=LAYAN_QUOTE, **kw):
    return m.MisconceptionEvidence(misconception_code=code, source="ai", quote=quote, detail="AI claim", confidence="high", **kw)


def test_dispute_rules():
    assert dispute_reason(_ai(), None) == "quote_states_correct_idea"
    assert dispute_reason(_ai(quote="It stops when exp == 1 because that's the last multiplication."), None) is None
    assert dispute_reason(_ai(quote="It stops at the empty list or when it runs out."), None) is None  # mixed: still a claim
    rejecting = m.ExplanationReadingRecord(rejected_ideas=[{"code": "MC-STOP-IMPLICIT", "quote": "", "reasoning": ""}])
    assert dispute_reason(_ai(code="MC-STOP-IMPLICIT", quote="It just keeps going."), rejecting) == "reader_rejects_same_idea"
    tests_row = m.MisconceptionEvidence(misconception_code="MC-BASE-SMALLEST", source="tests", quote=LAYAN_QUOTE)
    assert dispute_reason(tests_row, None) is None  # test evidence is never disputed


def _layan(db, world):
    """Give a student whose code fails the smallest-input probe a reading that quotes a correct sentence."""
    run = start_run(db, world["assignment_id"], None, background=False)
    subs = latest_submissions(db, world["assignment_id"])
    probe = next(s for s in subs if db.scalar(select(m.MisconceptionEvidence).where(
        m.MisconceptionEvidence.submission_id == s.id, m.MisconceptionEvidence.source == "tests",
        m.MisconceptionEvidence.misconception_code == "MC-BASE-SMALLEST")))
    db.execute(delete(m.MisconceptionEvidence).where(m.MisconceptionEvidence.submission_id == probe.id,
                                                     m.MisconceptionEvidence.source.in_(("ai", "baseline"))))
    db.add(_ai(submission_id=probe.id, run_id=run.id))
    db.commit()
    compute_insights(db, db.get(m.Assignment, world["assignment_id"]), db.get(m.GradingRun, run.id))
    db.commit()
    return probe


def test_disputed_reading_goes_to_review_not_to_automated_help(client, db, world, rule_baseline):
    sub = _layan(db, world)
    prof = login(client, world["professor_id"])
    plan = client.get(f"/api/professor/assignments/{world['assignment_id']}/plan", headers=prof).json()
    where = {s["student_id"]: g for g in plan["groups"] for s in g["students"]}
    g = where[sub.student_id]
    assert g["category"] == "conflicting_evidence" and g["action"] == "review" and not g["draftable"]
    shown = next(s for s in g["students"] if s["student_id"] == sub.student_id)["evidence"]
    assert any("RecursionError" in e or "power" in e for e in shown) and any(LAYAN_QUOTE in e for e in shown)  # both signals

    r = client.post(f"/api/professor/assignments/{world['assignment_id']}/plan/draft", headers=prof,
                    json={"category": "conflicting_evidence", "misconception_code": "MC-BASE-SMALLEST", "student_ids": [sub.student_id]})
    assert r.status_code == 422

    # The original AI claim is kept for audit and labelled as disputed.
    detail = client.get(f"/api/professor/submissions/{sub.id}", headers=prof).json()
    ai = next(x for x in detail["misconceptions"] if x["source"] == "ai")
    assert ai["quote"] == LAYAN_QUOTE and ai["disputed"]
    rows = client.get(f"/api/professor/assignments/{world['assignment_id']}/submissions", headers=prof).json()
    assert db.scalar(select(m.MisconceptionEvidence).where(m.MisconceptionEvidence.submission_id == sub.id,
                                                           m.MisconceptionEvidence.source == "ai")) is not None
    assert rows  # list still renders

    # The insight lists the set-aside flag and an insight-based draft leaves the student out.
    ins = client.get(f"/api/professor/assignments/{world['assignment_id']}/insights", headers=prof).json()["insights"]
    smallest = next(i for i in ins if i["misconception_code"] == "MC-BASE-SMALLEST")
    assert any(c["kind"] == "disputed_reading" and sub.id in c["submission_ids"] for c in smallest["evidence"]["contradictions"])
    iv = client.post(f"/api/professor/insights/{smallest['id']}/intervention", headers=prof).json()
    assert sub.student_id not in iv["target_student_ids"]

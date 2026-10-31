from sqlalchemy import select

from athar import models as m
from athar.ai.provider import set_provider_override
from athar.cli import evaluate
from athar.grading.pipeline import start_run

from .conftest import FailingProvider, ScriptedProvider


def _insights(db, run_id):
    return {i.misconception_code or i.kind: i for i in db.scalars(select(m.Insight).where(m.Insight.run_id == run_id)).all()}


def test_grading_without_llm_is_honest_about_what_was_not_analysed(db, world, no_llm):
    run = start_run(db, world["assignment_id"], None, background=False)
    assert (run.status, run.ai_status) == ("done", "unavailable")
    expl = db.scalars(select(m.CriterionEvidence).join(m.RubricCriterion)
                      .where(m.RubricCriterion.method == "explanation", m.CriterionEvidence.source == "ai")).all()
    assert expl and all(e.judgment == "ai_unavailable" and e.points is None and e.needs_review for e in expl)

    ins = _insights(db, run.id)
    # Test-detectable patterns are found; the explanation-only pattern is not invented.
    assert ins["MC-BASE-SMALLEST"].student_count == 16
    assert "MC-STOP-IMPLICIT" not in ins
    missing = {x["kind"] for x in ins["MC-BASE-SMALLEST"].evidence["missing"]}
    assert {"not_submitted", "explanations_not_analyzed"} <= missing


def test_insight_counts_are_derived_from_stored_evidence(db, world, no_llm):
    run = start_run(db, world["assignment_id"], None, background=False)
    insight = _insights(db, run.id)["MC-BASE-SMALLEST"]
    sub_ids = set(insight.evidence["submission_ids"])
    stored = {e.submission_id for e in db.scalars(select(m.MisconceptionEvidence)
                                                  .where(m.MisconceptionEvidence.misconception_code == "MC-BASE-SMALLEST")).all()}
    assert sub_ids == stored
    assert len(sub_ids) == insight.student_count
    # Every example points at a submission inside the group.
    assert all(ex["submission_id"] in sub_ids for ex in insight.evidence["examples"])


def test_detection_matches_planted_labels(db, world, no_llm):
    start_run(db, world["assignment_id"], None, background=False)
    report = evaluate(db)
    for code in ("MC-BASE-SMALLEST", "MC-BASE-VALUE", "MC-NO-PROGRESS"):
        assert report[code]["missed"] == 0 and report[code]["extra"] == 0, report[code]


def test_ai_path_finds_working_code_with_confused_reasoning(db, world, scripted):
    run = start_run(db, world["assignment_id"], None, background=False)
    assert run.ai_status == "used" and run.ai_failed == 0
    ins = _insights(db, run.id)
    implicit = ins["MC-STOP-IMPLICIT"]
    assert implicit.evidence["counts"]["working_code_confused_reasoning"] > 0
    assert any(x["kind"] == "no_test_probe" for x in implicit.evidence["missing"])
    # Every stored AI quote really appears in that student's explanation.
    for e in db.scalars(select(m.MisconceptionEvidence).where(m.MisconceptionEvidence.source == "ai")).all():
        assert e.quote.lower() in db.get(m.Submission, e.submission_id).explanation.lower()


def test_fabricated_ai_quotes_never_become_evidence(db, world):
    set_provider_override(ScriptedProvider(fabricate_quotes=True))
    run = start_run(db, world["assignment_id"], None, background=False)
    assert db.scalars(select(m.MisconceptionEvidence).where(m.MisconceptionEvidence.source == "ai")).all() == []
    assert "MC-STOP-IMPLICIT" not in _insights(db, run.id)


def test_provider_outage_is_recorded_not_hidden(db, world):
    set_provider_override(FailingProvider())
    run = start_run(db, world["assignment_id"], None, background=False)
    assert run.status == "done" and run.ai_status == "failed" and run.ai_failed > 0
    failed = db.scalars(select(m.CriterionEvidence).where(m.CriterionEvidence.judgment == "ai_failed")).all()
    assert failed and all(e.needs_review and e.points is None for e in failed)


def test_regrading_keeps_professor_decisions(db, world, no_llm):
    start_run(db, world["assignment_id"], None, background=False)
    sub = db.scalar(select(m.Submission).where(m.Submission.student_id == world["sara_id"]))
    crit = next(c for c in sub.assignment.criteria if c.code == "C3")
    db.add(m.CriterionEvidence(submission_id=sub.id, criterion_id=crit.id, source="professor", judgment="partial", points=1.0))
    db.commit()
    start_run(db, world["assignment_id"], None, background=False)
    rows = db.scalars(select(m.CriterionEvidence).where(m.CriterionEvidence.submission_id == sub.id,
                                                        m.CriterionEvidence.source == "professor")).all()
    assert len(rows) == 1 and rows[0].points == 1.0


def test_starting_a_run_while_one_is_active_is_idempotent(db, world):
    a = world["assignment_id"]
    db.add(m.GradingRun(assignment_id=a, status="running"))
    db.commit()
    run = start_run(db, a, None, background=False)
    assert run.status == "running"
    assert len(db.scalars(select(m.GradingRun)).all()) == 1


def test_rule_baseline_is_labelled_and_never_publishable_alone(db, world, rule_baseline):
    run = start_run(db, world["assignment_id"], None, background=False)
    assert run.ai_status == "baseline" and run.ai_provider.startswith("rules-")
    rows = db.scalars(select(m.CriterionEvidence).where(m.CriterionEvidence.source == "baseline")).all()
    assert rows and all(r.model.startswith("rules-") for r in rows)
    from athar.grading.evidence import publish_blockers
    sub = db.scalar(select(m.Submission).where(m.Submission.student_id == world["sara_id"]))
    assert any("Rule-baseline" in b for b in publish_blockers(sub, list(sub.assignment.criteria)))
    assert "MC-STOP-IMPLICIT" in _insights(db, run.id)

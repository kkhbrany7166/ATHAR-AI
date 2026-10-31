"""LLM reader v2: validation and failure handling. All providers here are test doubles; no live inference."""

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from athar import models as m
from athar.ai import explanations as ex
from athar.ai.provider import AnthropicProvider, LLMError, OpenAIProvider, _Budget, set_provider_override
from athar.ai.reader import set_analyzer_override
from athar.grading.pipeline import start_run

CRIT = [{"code": "C3", "title": "stops", "description": "d"}, {"code": "C4", "title": "combines", "description": "d"}]
MISC = [{"code": "MC-STOP-IMPLICIT", "title": "t", "description": "d"}, {"code": "MC-BASE-SMALLEST", "title": "t", "description": "d"}]
OBJ = [{"code": "REC-1", "title": "t"}, {"code": "REC-3", "title": "t"}]


def reading(**kw):
    base = dict(answer_type="conceptual_explanation", code_issue="none", criteria=[], misconceptions=[], objectives=[],
                contradictions=[], missing_evidence=[], abstain=False, abstain_reason="", professor_summary="s")
    base.update(kw)
    return ex.ExplanationReading(**base)


def cj(code, judgment, quotes, conf="high"):
    return ex.CriterionJudgment(criterion_code=code, judgment=judgment, rationale="r", quotes=quotes, confidence=conf)


class Fixed:
    name, model = "fixed", "test-double"

    def __init__(self, out):
        self.out, self.prompts = out, []

    def parse(self, system, user, schema, max_tokens=4000):
        self.prompts.append(user)
        if isinstance(self.out, Exception):
            raise self.out
        return self.out

    def chat(self, *a, **k):
        return ""


def run(out, text):
    return ex.analyze(Fixed(out), explanation=text, criteria=CRIT, misconceptions=MISC, objectives=OBJ,
                      assignment_prompt="p", explanation_prompt="e", code="c", test_summary="t", conditions="unsupervised")


def test_negated_misconception_is_not_counted_as_held():
    text = "It doesn't stop on its own: the check exp == 0 stops it and returns 1."
    out = run(reading(criteria=[cj("C3", "met", ["the check exp == 0 stops it"])],
                      misconceptions=[ex.MisconceptionFinding(code="MC-STOP-IMPLICIT", stance="rejects", quote="doesn't stop on its own",
                                                              reasoning="explicitly rejected", confidence="high")]), text)
    assert out.signals == [] and [r.code for r in out.rejected_ideas] == ["MC-STOP-IMPLICIT"]
    assert out.criteria["C3"].judgment == "met"


def test_abstention_overrides_confident_judgments():
    out = run(reading(criteria=[cj("C3", "met", ["it works"])], abstain=True, abstain_reason="bare claim"), "it works")
    assert out.abstained and out.criteria["C3"].judgment == "unclear" and "abstained" in out.criteria["C3"].review_reasons


def test_held_misconception_and_met_criterion_are_flagged_as_inconsistent():
    text = "It stops when exp is 1 because base to the first is base."
    out = run(reading(criteria=[cj("C3", "met", ["It stops when exp is 1"])],
                      misconceptions=[ex.MisconceptionFinding(code="MC-BASE-SMALLEST", stance="holds", quote="stops when exp is 1",
                                                              reasoning="r", confidence="high")]), text)
    assert out.criteria["C3"].judgment == "unclear" and "internal_inconsistency" in out.criteria["C3"].review_reasons


def test_fabricated_quotes_and_unknown_codes_never_survive():
    text = "Recursion halts at zero."
    out = run(reading(criteria=[cj("C3", "met", ["halts when n reaches its base"]), cj("C9", "met", [])],
                      misconceptions=[ex.MisconceptionFinding(code="MC-INVENTED", stance="holds", quote="halts at zero", reasoning="r", confidence="high")],
                      objectives=[ex.ObjectiveEvidence(objective_code="REC-1", status="supported", quote="made-up text"),
                                  ex.ObjectiveEvidence(objective_code="REC-9", status="supported", quote="halts at zero")]), text)
    assert out.criteria["C3"].quotes == [] and "no_supporting_quote" in out.criteria["C3"].review_reasons
    assert "C9" not in out.criteria and out.signals == []
    assert out.objectives == [{"objective_code": "REC-1", "status": "no_evidence", "quote": ""}]


def test_prompt_contains_objectives_conditions_code_and_tests():
    p = Fixed(reading())
    ex.analyze(p, explanation="x y z w", criteria=CRIT, misconceptions=MISC, objectives=OBJ, assignment_prompt="ASSIGN",
               explanation_prompt="EXPLAIN", code="def f(): pass", test_summary="- t: error (RecursionError)", conditions="unsupervised")
    u = p.prompts[0]
    assert all(s in u for s in ("REC-1", "unsupervised", "def f(): pass", "RecursionError", "ASSIGN", "<student_explanation>"))


def test_provider_errors_are_wrapped(monkeypatch):
    import anthropic

    prov = AnthropicProvider.__new__(AnthropicProvider)
    prov._anthropic, prov.model = anthropic, "m"
    prov.client = SimpleNamespace(messages=SimpleNamespace(parse=lambda **k: (_ for _ in ()).throw(ValueError("bad json"))))
    with pytest.raises(LLMError, match="malformed"):
        prov.parse("s", "u", ex.ExplanationReading)
    prov.client = SimpleNamespace(messages=SimpleNamespace(parse=lambda **k: SimpleNamespace(stop_reason="max_tokens", parsed_output=None)))
    with pytest.raises(LLMError, match="truncated"):
        prov.parse("s", "u", ex.ExplanationReading)

    import openai
    oprov = OpenAIProvider.__new__(OpenAIProvider)
    oprov._openai, oprov.model = openai, "m"
    timeout = openai.APITimeoutError(request=SimpleNamespace(method="POST", url="u"))
    oprov.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(parse=lambda **k: (_ for _ in ()).throw(timeout))))
    with pytest.raises(LLMError, match="APITimeoutError"):
        oprov.parse("s", "u", ex.ExplanationReading)


def test_call_budget_is_a_hard_ceiling():
    b = _Budget(2)
    b.take(), b.take()
    with pytest.raises(LLMError, match="budget"):
        b.take()


def test_llm_mode_without_provider_does_not_silently_use_rules(db, world):
    set_provider_override(None)
    set_analyzer_override("llm")
    run_ = start_run(db, world["assignment_id"], None, background=False)
    assert run_.ai_status == "unavailable"
    assert db.scalars(select(m.CriterionEvidence).where(m.CriterionEvidence.source == "baseline")).all() == []


def test_malformed_outputs_during_grading_are_recorded_per_submission(db, world):
    set_provider_override(Fixed(LLMError("malformed model output: ValidationError")))
    run_ = start_run(db, world["assignment_id"], None, background=False)
    assert run_.status == "done" and run_.ai_status == "failed"
    failed = db.scalars(select(m.CriterionEvidence).where(m.CriterionEvidence.judgment == "ai_failed")).all()
    assert failed and all("malformed" in e.rationale for e in failed)
    assert db.scalars(select(m.CriterionEvidence).where(m.CriterionEvidence.source == "baseline")).all() == []


def test_readings_are_persisted_with_summary_and_abstention(db, world):
    set_provider_override(Fixed(reading(criteria=[cj("C3", "unclear", [], "low"), cj("C4", "unclear", [], "low")],
                                        abstain=True, abstain_reason="too thin", professor_summary="Cannot tell.")))
    start_run(db, world["assignment_id"], None, background=False)
    recs = db.scalars(select(m.ExplanationReadingRecord)).all()
    assert recs and all(r.abstained and r.prompt_version == ex.PROMPT_VERSION and r.summary == "Cannot tell." for r in recs)

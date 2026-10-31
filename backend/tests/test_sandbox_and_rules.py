from types import SimpleNamespace

from athar.ai.explanations import CriterionJudgment, ExplanationAnalysis, MisconceptionSignal, quote_in_text, validate
from athar.grading.evidence import probe_hits
from athar.grading.sandbox import TestSpec, run_tests

POWER_TESTS = [TestSpec(1, "power", [2, 10], 1024), TestSpec(2, "power", [2, 0], 1)]


def test_sandbox_passes_correct_code():
    code = "def power(b, e):\n    return 1 if e == 0 else b * power(b, e - 1)\n"
    assert [o.status for o in run_tests(code, POWER_TESTS).outcomes] == ["pass", "pass"]


def test_sandbox_reports_recursion_error_per_test():
    code = "def power(b, e):\n    if e == 1:\n        return b\n    return b * power(b, e - 1)\n"
    out = run_tests(code, POWER_TESTS).outcomes
    assert out[0].status == "pass"
    assert (out[1].status, out[1].error_type) == ("error", "RecursionError")


def test_sandbox_times_out_infinite_loops():
    code = "def power(b, e):\n    while True:\n        pass\n"
    out = run_tests(code, POWER_TESTS, per_test_seconds=0.3).outcomes
    assert all(o.status == "timeout" for o in out)


def test_sandbox_reports_syntax_errors_as_load_errors():
    report = run_tests("def power(b, e)\n    return 1\n", POWER_TESTS)
    assert report.load_error and report.load_error["type"] == "SyntaxError"
    assert all(o.status == "error" for o in report.outcomes)


def test_sandbox_runs_in_isolated_temp_dir():
    code = "import os\ndef power(b, e):\n    return os.getcwd()\n"
    out = run_tests(code, [TestSpec(1, "power", [1, 1], "x")]).outcomes[0]
    assert "athar-run-" in out.actual


def _tc(probes):
    return SimpleNamespace(probes=probes)


SMALLEST_PROBES = [{"misconception": "MC-BASE-SMALLEST", "on": "error", "error_types": ["RecursionError", "IndexError"]},
                   {"misconception": "MC-BASE-VALUE", "on": "wrong_value"}]


def test_probe_maps_recursion_error_to_smallest_input_misconception():
    assert probe_hits(_tc(SMALLEST_PROBES), "error", "RecursionError", load_failed=False) == ["MC-BASE-SMALLEST"]


def test_probe_maps_wrong_value_to_base_value_misconception():
    assert probe_hits(_tc(SMALLEST_PROBES), "fail", "", load_failed=False) == ["MC-BASE-VALUE"]


def test_probe_ignores_unrelated_errors_and_unloadable_code():
    assert probe_hits(_tc(SMALLEST_PROBES), "error", "TypeError", load_failed=False) == []
    assert probe_hits(_tc(SMALLEST_PROBES), "error", "RecursionError", load_failed=True) == []
    assert probe_hits(_tc(SMALLEST_PROBES), "pass", "", load_failed=False) == []


def test_quote_matching_is_whitespace_and_case_tolerant_but_not_fuzzy():
    text = "My power function stops when exp is 1,  because anything to the power of 1 is itself."
    assert quote_in_text("stops when exp is 1, because", text)
    assert quote_in_text("“My power function stops when exp is 1”", text)
    assert not quote_in_text("stops when exp is 0", text)
    assert not quote_in_text("is", text)  # too short to count as evidence


def test_validation_drops_fabricated_quotes_and_unknown_codes():
    text = "It keeps calling itself until there is nothing left to multiply."
    raw = ExplanationAnalysis(
        criteria=[CriterionJudgment(criterion_code="C3", judgment="not_met", rationale="r", quotes=["the base case is exp == 0"], confidence="high"),
                  CriterionJudgment(criterion_code="C9", judgment="met", rationale="r", quotes=[], confidence="high")],
        misconceptions=[MisconceptionSignal(code="MC-STOP-IMPLICIT", quote="nothing left to multiply", reasoning="r", confidence="high"),
                        MisconceptionSignal(code="MC-STOP-IMPLICIT", quote="it stops magically", reasoning="r", confidence="high"),
                        MisconceptionSignal(code="MC-INVENTED", quote="keeps calling itself", reasoning="r", confidence="high")],
    )
    v = validate(raw, explanation=text, criterion_codes=["C3", "C4"], misconception_codes=["MC-STOP-IMPLICIT"])
    assert set(v.criteria) == {"C3"}
    assert v.criteria["C3"].quotes == []
    assert "quote_not_found" in v.criteria["C3"].review_reasons
    assert "no_supporting_quote" in v.criteria["C3"].review_reasons
    assert [s.quote for s in v.signals] == ["nothing left to multiply"]
    assert len(v.rejected) == 4

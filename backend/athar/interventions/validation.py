"""Validate that an assessment item genuinely tests the targeted misconception.

An item is valid only if BOTH hold:
1. the reference solution passes every test, and
2. an implementation containing the misconception fails at least one probe test *in the way the probe
   describes* (e.g. RecursionError on the smallest input), so the item can tell the two apart.

This runs real code in the sandbox. No model opinion is involved.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from ..grading.evidence import probe_hits
from ..grading.sandbox import TestSpec, run_tests


def _specs(tests: list[dict[str, Any]]) -> list[TestSpec]:
    return [TestSpec(i, t["function"], t["args"], t["expected"]) for i, t in enumerate(tests)]


def validate_item(*, tests: list[dict[str, Any]], reference_solution: str, misconception_solution: str, misconception_code: str) -> dict[str, Any]:
    problems: list[str] = []
    if not tests:
        problems.append("The item has no tests.")
    probe_idx = [i for i, t in enumerate(tests) if any(p.get("misconception") == misconception_code for p in t.get("probes", []))]
    if tests and not probe_idx:
        problems.append(f"No test probes {misconception_code}.")

    ref = run_tests(reference_solution, _specs(tests)) if tests else None
    ref_failures = [tests[o.id]["name"] + f" ({o.error_type or 'got ' + o.actual})" for o in (ref.outcomes if ref else []) if o.status != "pass"]
    if ref and ref.load_error:
        problems.append(f"Reference solution does not load: {ref.load_error['type']}.")
    elif ref_failures:
        problems.append("Reference solution fails: " + "; ".join(ref_failures) + ".")

    mis = run_tests(misconception_solution, _specs(tests)) if tests else None
    caught = []
    if mis and not mis.load_error:
        for o in mis.outcomes:
            if o.id in probe_idx:
                tc = SimpleNamespace(probes=tests[o.id].get("probes", []))
                if misconception_code in probe_hits(tc, o.status, o.error_type, load_failed=False):
                    caught.append(f"{tests[o.id]['name']} ({o.error_type or 'got ' + o.actual})")
    if mis and mis.load_error:
        problems.append("Misconception implementation does not load, so it proves nothing.")
    elif tests and not caught:
        problems.append("The misconception implementation passes every probe: this item cannot detect the misconception.")

    return {
        "valid": not problems,
        "problems": problems,
        "reference_passed": sum(o.status == "pass" for o in ref.outcomes) if ref else 0,
        "total": len(tests),
        "misconception_caught_by": caught,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "method": "sandbox: reference must pass all tests; misconception implementation must fail a probe as described",
    }

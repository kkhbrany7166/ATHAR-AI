"""Rule-based explanation reader: the non-AI baseline.

A deliberately simple, transparent analyzer for the recursion explanation criteria. It exists for two reasons:
1. ATHAR must stay useful without model credits. Its output is labelled "Rule baseline", never "AI".
2. Evaluation needs a baseline to compare the LLM against.

The phrase lists were written from the *development* explanation templates only (seed/synthetic.py),
before the held-out set existed. They are frozen for evaluation: do not tune them on held-out results.
"""

from __future__ import annotations

import re

from .explanations import ValidatedAnalysis, ValidatedCriterion, ValidatedSignal

VERSION = "rules-v1"

IMPLICIT_STOP = [
    r"on its own", r"\breturn statement\b", r"\breturn line\b", r"\bruns? out\b", r"small enough",
    r"reaches the end", r"recursion is finished", r"used up", r"just ends", r"until it'?s done",
]
SMALLEST_BELIEF = [
    r"\bexp (is|==|equals) 1\b", r"exp ?== ?1", r"\bone (element|item)\b", r"last (element|number|multiplication)",
    r"wouldn'?t (really )?be passed", r"shouldn'?t happen", r"never needs to handle", r"smallest exponent where",
]
EXPLICIT_SMALLEST = [
    r"\b(exp|n|exponent)\s*(==|is|reaches|becomes|hits|equals|gets to)\s*(0|zero)\b", r"exp ?== ?0", r"empty list",
    r"\[\]", r"zero power", r"power (of )?0",
]
COMBINE_GOOD = [r"returns? 1.*\b2\b.*\b4\b.*\b8\b", r"2\s*\*\s*1.*2\s*\*\s*2.*2\s*\*\s*4", r"on the way back", r"multiplied?.*as (it|they|each) returns?"]
COMBINE_CONFUSED = [r"at the start", r"immediately", r"pass(es)? the answer along", r"same 8"]

_SENT = re.compile(r"(?<=[.!?])\s+")


def _find(patterns: list[str], text: str) -> str | None:
    """Return the sentence containing the first matching pattern, or None."""
    for sentence in _SENT.split(text):
        low = sentence.lower()
        if any(re.search(p, low) for p in patterns):
            return sentence.strip()
    return None


def analyze(explanation: str, criteria: list[dict]) -> ValidatedAnalysis:
    signals: list[ValidatedSignal] = []
    implicit = _find(IMPLICIT_STOP, explanation)
    smallest = _find(SMALLEST_BELIEF, explanation)
    if implicit:
        signals.append(ValidatedSignal("MC-STOP-IMPLICIT", implicit, "Matched a phrase that attributes stopping to something other than a condition.", "medium"))
    if smallest:
        signals.append(ValidatedSignal("MC-BASE-SMALLEST", smallest, "Matched a phrase placing the stopping point after the smallest input.", "medium"))

    out: dict[str, ValidatedCriterion] = {}
    codes = [c["code"] for c in criteria]
    if "C3" in codes:
        explicit = _find(EXPLICIT_SMALLEST, explanation)
        if implicit or smallest:
            q = implicit or smallest
            out["C3"] = ValidatedCriterion("C3", "not_met", "A matched phrase suggests the stopping condition is misunderstood.", [q], "medium", ["rule_baseline"])
        elif explicit:
            out["C3"] = ValidatedCriterion("C3", "met", "Names an explicit stopping condition at the smallest input.", [explicit], "medium", ["rule_baseline"])
        else:
            out["C3"] = ValidatedCriterion("C3", "unclear", "No recognised description of the stopping condition.", [], "low", ["rule_baseline", "unclear"])
    if "C4" in codes:
        confused = _find(COMBINE_CONFUSED, explanation)
        good = _find(COMBINE_GOOD, explanation)
        if confused:
            out["C4"] = ValidatedCriterion("C4", "partial", "Trace suggests values are computed up front rather than combined on return.", [confused], "medium", ["rule_baseline"])
        elif good:
            out["C4"] = ValidatedCriterion("C4", "met", "Traces return values combining on the way back up.", [good], "medium", ["rule_baseline"])
        else:
            out["C4"] = ValidatedCriterion("C4", "unclear", "No recognised trace of returns combining.", [], "low", ["rule_baseline", "unclear"])
    return ValidatedAnalysis(out, signals, [])

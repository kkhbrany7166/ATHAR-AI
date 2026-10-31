"""Conflict checks on machine readings: when a reading's misconception claim is not supported by its own evidence.

A reader (AI or rules) may say an explanation holds a misconception and quote a sentence as proof. That claim
is *disputed*, and must not become a diagnosis on its own, when:

  quote_states_correct_idea  the quoted sentence names the correct stopping condition (the frozen rules-v1
                             "explicit smallest input" phrases) and contains none of the misconception phrases
  reader_rejects_same_idea   the same reading also lists that misconception among ideas the student rejects

The stored reading and evidence rows are never changed. This runs at read time, so the original AI output
stays available for audit. Disputed claims send the student to professor review, not to automated help.
"""

from __future__ import annotations

import re

from .. import models as m
from ..ai.baseline import EXPLICIT_SMALLEST, IMPLICIT_STOP, SMALLEST_BELIEF

READING_SOURCES = ("ai", "baseline")

REASONS = {
    "quote_states_correct_idea": "The quoted sentence states the correct stopping condition, so it can't show this misconception.",
    "reader_rejects_same_idea": "The same reading also says the student rejects this idea.",
}


def _matches(patterns: list[str], text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in patterns)


def dispute_reason(e: m.MisconceptionEvidence, reading: m.ExplanationReadingRecord | None) -> str | None:
    """Why this reading-sourced misconception claim is disputed, or None if it stands. Test evidence is never disputed."""
    if e.source not in READING_SOURCES:
        return None
    if e.quote and _matches(EXPLICIT_SMALLEST, e.quote) and not _matches(SMALLEST_BELIEF + IMPLICIT_STOP, e.quote):
        return "quote_states_correct_idea"
    if reading and e.misconception_code in {r.get("code") for r in (reading.rejected_ideas or [])}:
        return "reader_rejects_same_idea"
    return None


def disputed_ids(mevs: list[m.MisconceptionEvidence], reading: m.ExplanationReadingRecord | None) -> dict[int, str]:
    return {e.id: r for e in mevs if (r := dispute_reason(e, reading))}

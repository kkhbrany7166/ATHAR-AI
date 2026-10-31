"""Deterministic checks on the note students read first. Flags problems; never rewrites or truncates the text.

A note with problems can be saved and edited, but not sent: approval is refused until the professor fixes it.
"""

from __future__ import annotations

import re

WORD_LIMIT = 90

_GREETING = re.compile(r"^\s*(hi|hello|hey|dear|greetings|good (morning|afternoon|evening))\b|^\s*\w+ students\s*[,!]", re.I)
_LIST_LINE = re.compile(r"^\s*(#|[-*•]\s|\d+[.)]\s)", re.M)
_ASSIGNMENT_CALLS = re.compile(r"\b(power|sum_list)\s*\(")


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def check_note(text: str, kind: str) -> dict:
    words = word_count(text)
    problems: list[str] = []
    if not text.strip():
        problems.append("The note is empty.")
    if words > WORD_LIMIT:
        problems.append(f"Too long: {words} words. The limit is {WORD_LIMIT}, so students read it before they start.")
    if _GREETING.search(text):
        problems.append("Starts with a greeting. Begin with the idea instead.")
    if "!" in text:
        problems.append("Uses exclamation marks.")
    if _LIST_LINE.search(text):
        problems.append("Uses headings or lists. Write it as two or three plain sentences.")
    if kind != "debugging" and _ASSIGNMENT_CALLS.search(text):
        problems.append("Reuses the assignment's own function (power or sum_list). Use a new tiny example so the follow-up stays a fair check.")
    return {"words": words, "limit": WORD_LIMIT, "problems": problems, "ok": not problems}

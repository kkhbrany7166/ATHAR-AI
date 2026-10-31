"""AI-proposed follow-up checks, released only if the sandbox validator accepts them.

The model proposes a new problem, a reference solution, an implementation that holds the targeted
misconception, and test cases. ATHAR does not trust any of it:
- argument and expected values arrive as JSON strings and must parse,
- the function name must be new (not the assignment's own problem) and actually defined by the reference,
- there must be at least two general tests and one smallest-input test,
- probe tags are attached by ATHAR, never by the model,
- then the item goes through the same sandbox validation as authored items: the reference must pass every
  test, and the misconception implementation must fail a probe the way the misconception predicts.

Rejected proposals are stored with their reasons so the professor can see what was tried.
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models as m
from ..ai.provider import LLMError, LLMProvider
from .validation import validate_item

GEN_VERSION = "variant-gen-v1"
PROBES = {
    "MC-BASE-SMALLEST": [{"misconception": "MC-BASE-SMALLEST", "on": "error", "error_types": ["RecursionError", "IndexError", "Timeout"]},
                         {"misconception": "MC-BASE-VALUE", "on": "wrong_value"}],
    "MC-BASE-VALUE": [{"misconception": "MC-BASE-VALUE", "on": "wrong_value"},
                      {"misconception": "MC-BASE-SMALLEST", "on": "error", "error_types": ["RecursionError", "IndexError", "Timeout"]}],
}
FORBIDDEN_FUNCTIONS = {"power", "sum_list"}


class GenTest(BaseModel):
    args_json: str = Field(description='JSON array of positional arguments, e.g. "[[1, 2, 3]]" or "[\\"ab\\", 0]"')
    expected_json: str = Field(description="JSON value the reference solution returns")
    purpose: Literal["general", "smallest_input"]


class GeneratedItem(BaseModel):
    title: str
    prompt: str = Field(description="Student-facing task, 1-3 sentences, recursion required, no loops")
    explanation_prompt: str
    function_name: str
    starter_code: str
    reference_solution: str
    misconception_solution: str = Field(description="A plausible student solution that holds exactly the targeted misconception")
    tests: list[GenTest]
    alignment: str = Field(description="One sentence: how the smallest-input test separates the misconception from correct understanding")


GEN_SYSTEM = """You write short recursion exercises for an introductory programming course.
Write ONE new Python problem (not power, not sum_list) that tests the given misconception about base cases.
Provide: a reference solution, a second solution that a student holding exactly that misconception would write,
and 4-6 tests (args and expected values as JSON strings). Include at least one test on the smallest valid input,
marked purpose "smallest_input", which the misconception solution fails. Keep it solvable in under 10 lines.
Use only plain values (ints, strings, lists). No imports, no I/O, no randomness."""


def _defines(code: str, name: str) -> bool:
    return re.search(rf"^\s*def\s+{re.escape(name)}\s*\(", code, re.M) is not None


def build_item(raw: GeneratedItem, misconception_code: str) -> tuple[list[dict], list[str]]:
    problems: list[str] = []
    name = raw.function_name.strip()
    if not re.fullmatch(r"[a-z_][a-z0-9_]{1,40}", name):
        problems.append(f"Function name {name!r} is not a plain Python name.")
    if name in FORBIDDEN_FUNCTIONS:
        problems.append("The proposal reuses the original assignment's problem instead of a new one.")
    if not _defines(raw.reference_solution, name):
        problems.append("The reference solution does not define the named function.")
    if not _defines(raw.misconception_solution, name):
        problems.append("The misconception solution does not define the named function.")
    if re.search(r"\bimport\b|\bopen\(|\bwhile\b|\bfor\b", raw.reference_solution):
        problems.append("The reference solution uses imports, I/O or loops.")
    tests = []
    for i, t in enumerate(raw.tests):
        try:
            args, expected = json.loads(t.args_json), json.loads(t.expected_json)
        except json.JSONDecodeError:
            problems.append(f"Test {i + 1} has arguments or an expected value that isn't valid JSON.")
            continue
        if not isinstance(args, list):
            problems.append(f"Test {i + 1}: arguments must be a JSON array.")
            continue
        smallest = t.purpose == "smallest_input"
        tests.append({"name": f"{name}({', '.join(json.dumps(a) for a in args)}) is {json.dumps(expected)}", "function": name,
                      "args": args, "expected": expected, "criterion": "C2" if smallest else "C1", "hidden": False,
                      "probes": PROBES.get(misconception_code, []) if smallest else []})
    if sum(t["criterion"] == "C1" for t in tests) < 2:
        problems.append("Fewer than two general tests.")
    if not any(t["criterion"] == "C2" for t in tests):
        problems.append("No smallest-input test.")
    return tests, problems


def generate_followup(db: Session, provider: LLMProvider, iv: m.Intervention) -> m.AssessmentItem:
    mc = db.query(m.Misconception).filter(m.Misconception.code == iv.misconception_code).one()
    user = f"<misconception code=\"{mc.code}\">\n{mc.title}. {mc.description}\n</misconception>"
    try:
        raw = provider.parse(GEN_SYSTEM, user, GeneratedItem, max_tokens=3000)
    except LLMError:
        raise
    tests, problems = build_item(raw, mc.code)
    validation = {"valid": False, "problems": problems, "reference_passed": 0, "total": len(tests), "misconception_caught_by": [],
                  "method": f"{GEN_VERSION}: structural checks, then sandbox validation", "alignment_claim": raw.alignment}
    if not problems:
        v = validate_item(tests=tests, reference_solution=raw.reference_solution, misconception_solution=raw.misconception_solution,
                          misconception_code=mc.code)
        validation.update(v)
        validation["method"] = f"{GEN_VERSION}: structural checks, then " + v["method"]
        validation["alignment_claim"] = raw.alignment
    item = m.AssessmentItem(course_id=iv.course_id, objective_id=mc.objective_id, misconception_code=mc.code,
                            key=f"ai-{raw.function_name.strip()[:40]}", role="followup", title=f"Check: {raw.title.strip()[:120]}",
                            prompt=raw.prompt.strip(), explanation_prompt=raw.explanation_prompt.strip(), starter_code=raw.starter_code,
                            reference_solution=raw.reference_solution, misconception_solution=raw.misconception_solution,
                            tests=tests, hints=[], source=f"ai:{provider.model}", validation=validation)
    db.add(item)
    db.add(m.AuditEvent(actor_id=iv.created_by, action="item.generate", entity="intervention", entity_id=iv.id,
                        payload={"valid": validation["valid"], "problems": validation["problems"]}))
    db.commit()
    return item

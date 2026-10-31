"""AI-generated follow-up checks are gated by structural checks and the sandbox validator. Mock providers only."""

import json

from athar.ai.provider import LLMError, set_provider_override
from athar.grading.pipeline import start_run
from athar.interventions.generation import GenTest, GeneratedItem

from .conftest import login


def proposal(**kw):
    base = dict(title="list_length", prompt="Write list_length(xs) recursively.", explanation_prompt="Why does it stop?",
                function_name="list_length", starter_code="def list_length(xs):\n    pass\n",
                reference_solution="def list_length(xs):\n    if not xs:\n        return 0\n    return 1 + list_length(xs[1:])\n",
                misconception_solution="def list_length(xs):\n    if len(xs) == 1:\n        return 1\n    return 1 + list_length(xs[1:])\n",
                tests=[GenTest(args_json=json.dumps([[1, 2, 3]]), expected_json="3", purpose="general"),
                       GenTest(args_json=json.dumps([[9]]), expected_json="1", purpose="general"),
                       GenTest(args_json=json.dumps([[]]), expected_json="0", purpose="smallest_input")],
                alignment="The empty list separates the two.")
    base.update(kw)
    return GeneratedItem(**base)


class Gen:
    name, model = "gen", "test-double"

    def __init__(self, out):
        self.out = out

    def parse(self, *a, **k):
        if isinstance(self.out, Exception):
            raise self.out
        return self.out

    def chat(self, *a, **k):
        return ""


def _draft(client, db, world):
    start_run(db, world["assignment_id"], None, background=False)
    prof = login(client, world["professor_id"])
    ins = client.get(f"/api/professor/assignments/{world['assignment_id']}/insights", headers=prof).json()["insights"]
    smallest = next(i for i in ins if i["misconception_code"] == "MC-BASE-SMALLEST")
    iv = client.post(f"/api/professor/insights/{smallest['id']}/intervention", headers=prof).json()
    return prof, iv


def _gen(client, prof, iv):
    return client.post(f"/api/professor/interventions/{iv['id']}/generate-check", headers=prof)


def test_valid_generated_check_becomes_selectable(client, db, world, rule_baseline):
    prof, iv = _draft(client, db, world)
    set_provider_override(Gen(proposal()))
    r = _gen(client, prof, iv).json()
    assert r["item"]["validation"]["valid"] and r["item"]["source"] == "ai:test-double"
    assert any(o["id"] == r["item"]["id"] for o in r["intervention"]["followup_options"])
    ok = client.patch(f"/api/professor/interventions/{iv['id']}", json={"followup_item_id": r["item"]["id"]}, headers=prof)
    assert ok.status_code == 200


def test_generated_check_that_cannot_detect_the_misconception_is_rejected(client, db, world, rule_baseline):
    prof, iv = _draft(client, db, world)
    set_provider_override(Gen(proposal(misconception_solution=proposal().reference_solution)))  # "misconception" is actually correct
    item = _gen(client, prof, iv).json()["item"]
    assert not item["validation"]["valid"] and any("cannot detect" in p for p in item["validation"]["problems"])


def test_structurally_bad_proposals_never_reach_the_sandbox(client, db, world, rule_baseline):
    prof, iv = _draft(client, db, world)
    for bad, expect in [(proposal(function_name="power"), "reuses"),
                        (proposal(tests=[GenTest(args_json="not json", expected_json="1", purpose="general")]), "valid JSON"),
                        (proposal(tests=proposal().tests[:2]), "smallest-input"),
                        (proposal(reference_solution="import os\ndef list_length(xs):\n    return 0\n"), "imports")]:
        set_provider_override(Gen(bad))
        item = _gen(client, prof, iv).json()["item"]
        assert not item["validation"]["valid"] and any(expect in p for p in item["validation"]["problems"]), (expect, item["validation"])


def test_generation_failures_are_explicit(client, db, world, rule_baseline):
    prof, iv = _draft(client, db, world)
    set_provider_override(None)
    assert _gen(client, prof, iv).status_code == 503
    set_provider_override(Gen(LLMError("timeout")))
    r = _gen(client, prof, iv)
    assert r.status_code == 502 and "timeout" in r.json()["detail"]
    # An unvalidated item can never be chosen as the follow-up.
    set_provider_override(Gen(proposal(function_name="power")))
    bad = _gen(client, prof, iv).json()["item"]
    client.patch(f"/api/professor/interventions/{iv['id']}", json={"followup_item_id": bad["id"]}, headers=prof)
    assert client.post(f"/api/professor/interventions/{iv['id']}/approve", headers=prof).status_code == 422

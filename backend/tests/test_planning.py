"""Adaptive planning: diagnosis from evidence, the right kind of activity per group, and verification per kind."""

from sqlalchemy import func, select

from athar import models as m
from athar.grading.pipeline import start_run

from .conftest import login


def _plan(client, db, world):
    start_run(db, world["assignment_id"], None, background=False)
    prof = login(client, world["professor_id"])
    plan = client.get(f"/api/professor/assignments/{world['assignment_id']}/plan", headers=prof).json()
    return prof, {(g["category"], g["misconception_code"]): g for g in plan["groups"]}


def test_diagnosis_separates_concept_syntax_reasoning_and_demonstrated(client, db, world, rule_baseline):
    _, g = _plan(client, db, world)
    assert len(g[("concept_gap", "MC-BASE-SMALLEST")]["students"]) == 16
    assert g[("concept_gap", "MC-BASE-SMALLEST")]["action"] == "concept_practice"
    assert len(g[("concept_gap", "MC-BASE-VALUE")]["students"]) == 6
    # The two syntax-error submissions are routed to debugging, never to a recursion misconception.
    assert len(g[("execution_error", "")]["students"]) == 2 and g[("execution_error", "")]["action"] == "debugging"
    assert g[("reasoning_gap", "")]["action"] == "explain_reasoning"
    assert all("All tests pass" in s["evidence"][0] for s in g[("reasoning_gap", "")]["students"])
    assert g[("demonstrated", "")]["action"] == "none" and not g[("demonstrated", "")]["draftable"]
    assert len(g[("no_submission", "")]["students"]) == 6 and not g[("no_submission", "")]["draftable"]
    total = sum(len(x["students"]) for x in g.values())
    assert total == 120  # every enrolled student lands in exactly one group


def test_without_any_reading_working_code_is_unconfirmed_not_demonstrated(client, db, world, no_llm):
    _, g = _plan(client, db, world)
    assert ("demonstrated", "") not in g  # nothing is "demonstrated" when no one read the reasoning
    assert len(g[("reasoning_unconfirmed", "")]["students"]) > 50


def test_group_drafts_are_validated_against_current_evidence(client, db, world, rule_baseline):
    prof, g = _plan(client, db, world)
    url = f"/api/professor/assignments/{world['assignment_id']}/plan/draft"
    demo = [s["student_id"] for s in g[("demonstrated", "")]["students"]][:2]
    assert client.post(url, json={"category": "demonstrated", "student_ids": demo}, headers=prof).status_code == 422
    outsider = g[("demonstrated", "")]["students"][0]["student_id"]
    r = client.post(url, json={"category": "execution_error", "student_ids": [outsider]}, headers=prof)
    assert r.status_code == 422
    ids = [s["student_id"] for s in g[("execution_error", "")]["students"]]
    a = client.post(url, json={"category": "execution_error", "student_ids": ids}, headers=prof).json()
    b = client.post(url, json={"category": "execution_error", "student_ids": ids}, headers=prof).json()
    assert a["id"] == b["id"] and a["kind"] == "debugging" and a["status"] == "draft"


def test_debugging_intervention_end_to_end(client, db, world, rule_baseline):
    prof, g = _plan(client, db, world)
    ids = [s["student_id"] for s in g[("execution_error", "")]["students"]]
    iv = client.post(f"/api/professor/assignments/{world['assignment_id']}/plan/draft",
                     json={"category": "execution_error", "student_ids": ids}, headers=prof).json()
    assert iv["followup_item"]["validation"]["valid"]
    out = client.post(f"/api/professor/interventions/{iv['id']}/approve", headers=prof).json()
    assert out["status"] == "active" and out["progress"]["delivered"] == 2
    student = login(client, ids[0])
    tid = client.get("/api/student/home", headers=student).json()["tasks"][0]["id"]
    task = client.get(f"/api/student/tasks/{tid}", headers=student).json()
    assert task["kind"] == "debugging" and "def sum_list(xs)\n" in task["check"]["starter_code"]
    broken = client.post(f"/api/student/tasks/{tid}/followup", json={"code": task["check"]["starter_code"], "explanation": ""}, headers=student).json()
    assert broken["results"][-1]["outcome"] == "still_developing"
    fixed = "def sum_list(xs):\n    if not xs:\n        return 0\n    return xs[0] + sum_list(xs[1:])\n"
    ok = client.post(f"/api/student/tasks/{tid}/followup", json={"code": fixed, "explanation": "missing colon and a typo"}, headers=student).json()
    assert ok["results"][-1]["outcome"] == "demonstrated"


def test_explain_reasoning_uses_the_students_own_code_and_reads_only_reasoning(client, db, world, rule_baseline):
    prof, g = _plan(client, db, world)
    ids = [s["student_id"] for s in g[("reasoning_gap", "")]["students"]][:3]
    iv = client.post(f"/api/professor/assignments/{world['assignment_id']}/plan/draft",
                     json={"category": "reasoning_gap", "student_ids": ids}, headers=prof).json()
    assert iv["kind"] == "explain_reasoning" and iv["followup_item"] is None
    client.post(f"/api/professor/interventions/{iv['id']}/approve", headers=prof)
    student = login(client, ids[0])
    tid = client.get("/api/student/home", headers=student).json()["tasks"][0]["id"]
    task = client.get(f"/api/student/tasks/{tid}", headers=student).json()
    assert "def power" in task["my_original_code"]
    still = client.post(f"/api/student/tasks/{tid}/followup", json={"code": "IGNORED", "explanation": "It just stops on its own when done."}, headers=student).json()
    assert still["results"][-1]["outcome"] == "still_developing"
    good = client.post(f"/api/student/tasks/{tid}/followup", json={"code": "", "explanation": "It stops when exp is 0 and returns 1, since anything to the zero power is 1; each call lowers exp."}, headers=student).json()
    assert good["results"][-1]["outcome"] == "demonstrated"
    sub = db.scalars(select(m.Submission).where(m.Submission.student_id == ids[0]).order_by(m.Submission.id.desc())).first()
    assert sub.code != "IGNORED" and "def power" in sub.code


def test_students_in_an_open_intervention_are_marked_in_the_plan(client, db, world, rule_baseline):
    prof, g = _plan(client, db, world)
    ids = [s["student_id"] for s in g[("concept_gap", "MC-BASE-VALUE")]["students"]]
    iv = client.post(f"/api/professor/assignments/{world['assignment_id']}/plan/draft",
                     json={"category": "concept_gap", "misconception_code": "MC-BASE-VALUE", "student_ids": ids}, headers=prof).json()
    assert iv["kind"] == "concept_practice" and iv["followup_item"]["key"] == "countdown_value"
    plan = client.get(f"/api/professor/assignments/{world['assignment_id']}/plan", headers=prof).json()
    grp = next(x for x in plan["groups"] if x["misconception_code"] == "MC-BASE-VALUE")
    assert all(s["in_intervention"] == iv["id"] for s in grp["students"])
    assert db.scalar(select(func.count()).select_from(m.InterventionTask)) == 0  # draft only: nothing delivered

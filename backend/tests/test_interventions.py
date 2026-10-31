from sqlalchemy import func, select

from athar import models as m
from athar.grading.pipeline import start_run
from athar.interventions.validation import validate_item
from athar.interventions.verifier import TestObservation, VerifierInput, verify
from athar.seed import content

from .conftest import login

GOOD = 'def repeat_text(s, n):\n    if n == 0:\n        return ""\n    return s + repeat_text(s, n - 1)\n'
STILL_WRONG = "def repeat_text(s, n):\n    if n == 1:\n        return s\n    return s + repeat_text(s, n - 1)\n"
GOOD_EXPLANATION = "It stops when n is 0 and returns an empty string, because zero copies is nothing. Each call lowers n by one."


def _setup(client, db, world):
    start_run(db, world["assignment_id"], None, background=False)
    prof = login(client, world["professor_id"])
    ins = client.get(f"/api/professor/assignments/{world['assignment_id']}/insights", headers=prof).json()["insights"]
    smallest = next(i for i in ins if i["misconception_code"] == "MC-BASE-SMALLEST")
    return prof, smallest


def _draft(client, prof, insight):
    r = client.post(f"/api/professor/insights/{insight['id']}/intervention", headers=prof)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- validator

def test_item_bank_items_validate_in_the_sandbox():
    for spec in content.ITEM_BANK:
        v = validate_item(tests=spec["tests"], reference_solution=spec["reference_solution"],
                          misconception_solution=spec["misconception_solution"], misconception_code=spec["misconception"])
        assert v["valid"], (spec["key"], v["problems"])
        assert v["misconception_caught_by"]


def test_validator_rejects_items_that_cannot_detect_the_misconception():
    spec = content.ITEM_BANK[1]
    no_probe = [t for t in spec["tests"] if not t["probes"]]
    v = validate_item(tests=no_probe, reference_solution=spec["reference_solution"],
                      misconception_solution=spec["misconception_solution"], misconception_code=spec["misconception"])
    assert not v["valid"]
    bad_ref = validate_item(tests=spec["tests"], reference_solution=spec["misconception_solution"],
                            misconception_solution=spec["misconception_solution"], misconception_code=spec["misconception"])
    assert not bad_ref["valid"] and any("Reference solution fails" in p for p in bad_ref["problems"])


# ---------------------------------------------------------------- verifier rules

def _obs(probe_status="pass", general_status="pass", err=""):
    probes = [{"misconception": "MC-BASE-SMALLEST", "on": "error", "error_types": ["RecursionError"]}]
    return [TestObservation("general", general_status, "", []), TestObservation("smallest", probe_status, err, probes)]


def test_verifier_outcomes_follow_explicit_rules():
    base = dict(misconception_code="MC-BASE-SMALLEST", load_failed=False, explanation="n == 0 returns ''")
    assert verify(VerifierInput(tests=_obs(), stopping_judgment="met", **base)).outcome == "demonstrated"
    assert verify(VerifierInput(tests=_obs("error", err="RecursionError"), stopping_judgment="met", **base)).outcome == "still_developing"
    assert verify(VerifierInput(tests=_obs(), stopping_judgment="not_met", **base)).outcome == "still_developing"
    assert verify(VerifierInput(tests=_obs(), stopping_judgment="unclear", **base)).outcome == "insufficient_evidence"
    assert verify(VerifierInput(tests=_obs(), stopping_judgment=None, **base)).outcome == "insufficient_evidence"
    assert verify(VerifierInput(tests=_obs(), stopping_judgment="met", **{**base, "load_failed": True})).outcome == "insufficient_evidence"
    empty = verify(VerifierInput(tests=_obs(), stopping_judgment=None, **{**base, "explanation": ""}))
    assert empty.outcome == "insufficient_evidence"
    assert any("Unsupervised" in r for r in verify(VerifierInput(tests=_obs(), stopping_judgment="met", **base)).reasons)


# ---------------------------------------------------------------- workflow

def test_draft_is_idempotent_and_targets_come_from_the_insight(client, db, world, rule_baseline):
    prof, insight = _setup(client, db, world)
    a, b = _draft(client, prof, insight), _draft(client, prof, insight)
    assert a["id"] == b["id"] and a["status"] == "draft"
    assert sorted(a["target_student_ids"]) == sorted(insight["evidence"]["student_ids"])
    assert a["explanation_source"] == "template"  # no LLM configured in tests
    assert a["followup_item"]["validation"]["valid"]


def test_nothing_reaches_students_before_approval(client, db, world, rule_baseline):
    prof, insight = _setup(client, db, world)
    _draft(client, prof, insight)
    sara = login(client, world["sara_id"])
    assert client.get("/api/student/home", headers=sara).json()["tasks"] == []
    assert db.scalar(select(func.count()).select_from(m.InterventionTask)) == 0


def test_students_cannot_approve_and_invalid_transitions_are_refused(client, db, world, rule_baseline):
    prof, insight = _setup(client, db, world)
    iv = _draft(client, prof, insight)
    sara = login(client, world["sara_id"])
    assert client.post(f"/api/professor/interventions/{iv['id']}/approve", headers=sara).status_code == 403
    assert client.post(f"/api/professor/interventions/{iv['id']}/execute", headers=prof).status_code == 409
    assert client.post(f"/api/professor/interventions/{iv['id']}/complete", headers=prof).status_code == 409


def test_approval_executes_once_and_only_targets_see_it(client, db, world, rule_baseline):
    prof, insight = _setup(client, db, world)
    iv = _draft(client, prof, insight)
    out = client.post(f"/api/professor/interventions/{iv['id']}/approve", headers=prof).json()
    assert out["status"] == "active" and out["progress"]["delivered"] == len(iv["target_student_ids"])
    # Repeating approve/execute never duplicates tasks or follow-up assignments.
    client.post(f"/api/professor/interventions/{iv['id']}/approve", headers=prof)
    client.post(f"/api/professor/interventions/{iv['id']}/execute", headers=prof)
    assert db.scalar(select(func.count()).select_from(m.InterventionTask)) == len(iv["target_student_ids"])
    assert db.scalar(select(func.count()).select_from(m.Assignment).where(m.Assignment.targeted.is_(True))) == 1
    # Editing after approval is refused.
    assert client.patch(f"/api/professor/interventions/{iv['id']}", json={"explanation": "x"}, headers=prof).status_code == 409

    sara = login(client, world["sara_id"])
    assert len(client.get("/api/student/home", headers=sara).json()["tasks"]) == 1
    outsider = next(s for s in db.scalars(select(m.User).where(m.User.role == "student")).all() if s.id not in iv["target_student_ids"])
    other = login(client, outsider.id)
    assert client.get("/api/student/home", headers=other).json()["tasks"] == []
    task_id = client.get("/api/student/home", headers=sara).json()["tasks"][0]["id"]
    assert client.get(f"/api/student/tasks/{task_id}", headers=other).status_code == 404
    # The targeted follow-up isn't reachable as an ordinary assignment either.
    assert client.get(f"/api/student/assignments/{out['followup_assignment_id']}", headers=other).status_code == 404


def test_student_activity_and_verification_persist(client, db, world, rule_baseline):
    prof, insight = _setup(client, db, world)
    iv = _draft(client, prof, insight)
    client.post(f"/api/professor/interventions/{iv['id']}/approve", headers=prof)
    sara = login(client, world["sara_id"])
    tid = client.get("/api/student/home", headers=sara).json()["tasks"][0]["id"]
    task = client.get(f"/api/student/tasks/{tid}", headers=sara).json()
    assert task["my_earlier_evidence"] and "power(2, 0)" in task["my_earlier_evidence"][0]
    assert "reference_solution" not in str(task["practice"]) and "misconception_solution" not in str(task)

    client.post(f"/api/student/tasks/{tid}/checkpoint", json={"kind": "initial", "text": "It returns 1?"}, headers=sara)
    t = client.post(f"/api/student/tasks/{tid}/hint", headers=sara).json()
    assert len(t["hints"]) == 1
    t = client.post(f"/api/student/tasks/{tid}/practice", json={"code": content.ITEM_BANK[0]["misconception_solution"]}, headers=sara).json()
    assert t["practice_attempts"][-1]["passed"] < t["practice_attempts"][-1]["total"]
    reply = client.post(f"/api/student/tasks/{tid}/assistant", json={"message": "why does [] break?"}, headers=sara).json()
    assert reply["messages"][-1]["source"] == "unavailable"  # honest when no model is configured

    # First attempt still has the bug → still developing. Second attempt is correct → demonstrated.
    r1 = client.post(f"/api/student/tasks/{tid}/followup", json={"code": STILL_WRONG, "explanation": GOOD_EXPLANATION}, headers=sara).json()
    assert r1["results"][-1]["outcome"] == "still_developing"
    r2 = client.post(f"/api/student/tasks/{tid}/followup", json={"code": GOOD, "explanation": GOOD_EXPLANATION}, headers=sara).json()
    assert r2["results"][-1]["outcome"] == "demonstrated"

    prof_view = client.get(f"/api/professor/interventions/{iv['id']}", headers=prof).json()
    me = next(s for s in prof_view["students"] if s["student_id"] == world["sara_id"])
    assert me["verification"]["outcome"] == "demonstrated" and me["task"]["has_initial"] and me["task"]["practice_attempts"] == 1
    assert me["before"]


def test_simulated_classmates_go_through_the_real_verifier(client, db, world, rule_baseline):
    prof, insight = _setup(client, db, world)
    iv = _draft(client, prof, insight)
    client.post(f"/api/professor/interventions/{iv['id']}/approve", headers=prof)
    out = client.post(f"/api/professor/interventions/{iv['id']}/simulate", headers=prof).json()
    p = out["intervention"]["progress"]
    assert out["simulated_attempts"] > 0 and p["simulated"] == out["simulated_attempts"]
    assert p["demonstrated"] + p["still_developing"] + p["insufficient_evidence"] == p["verified"]
    sara = next(s for s in out["intervention"]["students"] if s["student_id"] == world["sara_id"])
    assert sara["verification"] is None  # the demo persona is never simulated
    assert out["intervention"]["recommendations"]


def test_first_answer_locks_once_practice_starts(client, db, world, rule_baseline):
    prof, insight = _setup(client, db, world)
    iv = _draft(client, prof, insight)
    client.post(f"/api/professor/interventions/{iv['id']}/approve", headers=prof)
    sara = login(client, world["sara_id"])
    tid = client.get("/api/student/home", headers=sara).json()["tasks"][0]["id"]
    ok = client.post(f"/api/student/tasks/{tid}/checkpoint", json={"kind": "initial", "text": "first try"}, headers=sara)
    assert ok.status_code == 200 and ok.json()["initial_locked"] is False
    assert client.post(f"/api/student/tasks/{tid}/checkpoint", json={"kind": "initial", "text": "edited before practice"}, headers=sara).status_code == 200
    client.post(f"/api/student/tasks/{tid}/hint", headers=sara)
    locked = client.post(f"/api/student/tasks/{tid}/checkpoint", json={"kind": "initial", "text": "rewritten after a hint"}, headers=sara)
    assert locked.status_code == 409
    task = client.get(f"/api/student/tasks/{tid}", headers=sara).json()
    assert task["initial_reasoning"] == "edited before practice" and task["initial_locked"] is True
    assert task["my_earlier_result"]["passed"] < task["my_earlier_result"]["total"]

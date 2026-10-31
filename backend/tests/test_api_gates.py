from athar.grading.pipeline import start_run

from .conftest import login


def _grade(db, world):
    return start_run(db, world["assignment_id"], None, background=False)


def _sara_submission(client, prof, world):
    rows = client.get(f"/api/professor/assignments/{world['assignment_id']}/submissions", headers=prof).json()
    return next(r for r in rows if r["student"]["id"] == world["sara_id"])


def test_roles_are_enforced_server_side(client, world):
    student = login(client, world["sara_id"])
    prof = login(client, world["professor_id"])
    assert client.get("/api/professor/courses").status_code == 401
    assert client.get("/api/professor/courses", headers=student).status_code == 403
    assert client.get("/api/student/home", headers=prof).status_code == 403
    assert client.get("/api/professor/courses", headers={"Authorization": "Bearer forged.token"}).status_code == 401


def test_student_view_hides_solution_hidden_tests_and_hypotheses(client, world):
    student = login(client, world["sara_id"])
    body = client.get(f"/api/student/assignments/{world['assignment_id']}", headers=student).json()
    flat = str(body)
    assert "reference_solution" not in body["assignment"]
    assert "power(9, 0) is 1" not in body["assignment"]["visible_tests"]
    assert "MC-" not in flat and "probes" not in flat


def test_ai_only_grades_cannot_be_published(client, db, world, scripted):
    _grade(db, world)
    prof = login(client, world["professor_id"])
    row = _sara_submission(client, prof, world)
    res = client.post(f"/api/professor/assignments/{world['assignment_id']}/publish", json={"submission_ids": [row["id"]]},
                      headers=prof).json()
    assert res["published"] == []
    assert any("not yet confirmed" in r for r in res["blocked"][0]["reasons"])


def test_confirming_ai_suggestions_then_publishing_releases_feedback(client, db, world, scripted):
    _grade(db, world)
    prof = login(client, world["professor_id"])
    row = _sara_submission(client, prof, world)
    confirmed = client.post(f"/api/professor/submissions/{row['id']}/confirm-ai", json={}, headers=prof).json()
    assert set(confirmed["accepted"]) == {"C3", "C4"}
    assert confirmed["submission"]["publish_blockers"] == []
    res = client.post(f"/api/professor/assignments/{world['assignment_id']}/publish", json={"submission_ids": [row["id"]]},
                      headers=prof).json()
    assert res["published"] == [row["id"]]

    student = login(client, world["sara_id"])
    sub = client.get(f"/api/student/assignments/{world['assignment_id']}", headers=student).json()["submissions"][0]
    assert sub["status"] == "feedback_ready" and sub["feedback"]["total"] is not None
    # Published grades are frozen in this prototype.
    crit_id = confirmed["submission"]["criteria"][2]["id"]
    again = client.post(f"/api/professor/submissions/{row['id']}/decisions",
                        json={"criterion_id": crit_id, "judgment": "met", "points": 2}, headers=prof)
    assert again.status_code == 409


def test_unavailable_ai_cannot_be_confirmed_only_decided(client, db, world, no_llm):
    _grade(db, world)
    prof = login(client, world["professor_id"])
    row = _sara_submission(client, prof, world)
    res = client.post(f"/api/professor/submissions/{row['id']}/confirm-ai", json={}, headers=prof).json()
    assert res["accepted"] == [] and len(res["skipped"]) == 2
    detail = res["submission"]
    for c in detail["criteria"]:
        if c["method"] == "explanation":
            r = client.post(f"/api/professor/submissions/{row['id']}/decisions",
                            json={"criterion_id": c["id"], "judgment": "partial", "points": 1, "note": "Read it myself."}, headers=prof)
            assert r.status_code == 200
    assert r.json()["publish_blockers"] == [] and r.json()["grade_status"] == "reviewed"


def test_decision_validation(client, db, world, no_llm):
    _grade(db, world)
    prof = login(client, world["professor_id"])
    row = _sara_submission(client, prof, world)
    detail = client.get(f"/api/professor/submissions/{row['id']}", headers=prof).json()
    c3 = next(c for c in detail["criteria"] if c["code"] == "C3")
    assert client.post(f"/api/professor/submissions/{row['id']}/decisions",
                       json={"criterion_id": c3["id"], "judgment": "met", "points": 5}, headers=prof).status_code == 422
    assert client.post(f"/api/professor/submissions/{row['id']}/decisions",
                       json={"criterion_id": 999, "judgment": "met", "points": 1}, headers=prof).status_code == 422

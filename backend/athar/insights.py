"""Classroom intelligence: aggregate stored evidence into traceable insights.

Everything here is deterministic. The insight's existence, its counts and its examples come from
rows produced by the grading run (test results, criterion evidence, misconception evidence). Each
insight stores the ids it was built from, so the UI can link every number back to submissions.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import models as m
from .grading.evidence import authoritative

MIN_GROUP = 3  # never report a "pattern" for fewer students than this


def _threshold(submitted: int) -> int:
    return max(MIN_GROUP, math.ceil(0.03 * submitted))


def compute_insights(db: Session, assignment: m.Assignment, run: m.GradingRun) -> list[m.Insight]:
    db.execute(delete(m.Insight).where(m.Insight.assignment_id == assignment.id, m.Insight.status == "open"))

    from .grading.pipeline import latest_submissions  # local import avoids a cycle

    subs = latest_submissions(db, assignment.id)
    sub_by_id = {s.id: s for s in subs}
    enrolled = db.scalars(select(m.Enrollment.student_id).where(m.Enrollment.course_id == assignment.course_id)).all()
    submitted_ids = {s.student_id for s in subs}
    not_submitted = [sid for sid in enrolled if sid not in submitted_ids]
    criteria = list(assignment.criteria)
    test_criteria = [c for c in criteria if c.method == "tests"]
    expl_criteria = [c for c in criteria if c.method == "explanation"]
    tests = list(assignment.tests)
    users = {u.id: u for u in db.scalars(select(m.User).where(m.User.id.in_([s.student_id for s in subs]))).all()}

    mevs = db.scalars(select(m.MisconceptionEvidence).where(m.MisconceptionEvidence.run_id == run.id)).all()
    results = db.scalars(select(m.TestResult).where(m.TestResult.run_id == run.id)).all()
    results_by_sub: dict[int, dict[int, m.TestResult]] = defaultdict(dict)
    for r in results:
        results_by_sub[r.submission_id][r.test_case_id] = r

    # Explanation analysis coverage, for "missing evidence".
    expl_status: dict[int, str] = {}
    for s in subs:
        rows = [authoritative(s.evidence, c.id) for c in expl_criteria]
        judgments = {r.judgment for r in rows if r}
        if not s.explanation.strip():
            expl_status[s.id] = "none_submitted"
        elif judgments & {"ai_unavailable"}:
            expl_status[s.id] = "not_analyzed"
        elif judgments & {"ai_failed"}:
            expl_status[s.id] = "failed"
        elif any(r and r.needs_review for r in rows):
            expl_status[s.id] = "needs_review"
        else:
            expl_status[s.id] = "analyzed"
    not_analyzed = [sid for sid, st in expl_status.items() if st in ("not_analyzed", "failed")]

    by_code: dict[str, dict[int, list[m.MisconceptionEvidence]]] = defaultdict(lambda: defaultdict(list))
    for e in mevs:
        if e.submission_id in sub_by_id:
            by_code[e.misconception_code][e.submission_id].append(e)

    misconceptions = {mc.code: mc for mc in db.scalars(
        select(m.Misconception).join(m.LearningObjective).where(m.LearningObjective.course_id == assignment.course_id)).all()}
    threshold = _threshold(len(subs))
    created: list[m.Insight] = []

    def test_met(s: m.Submission) -> bool:
        return all((a := authoritative(s.evidence, c.id)) is not None and a.judgment == "met" for c in test_criteria)

    for code, per_sub in by_code.items():
        mc = misconceptions.get(code)
        if mc is None or len(per_sub) < threshold:
            continue
        tests_only, expl_only, both = [], [], []
        for sid, rows in per_sub.items():
            sources = {"explanation" if r.source in ("ai", "baseline") else r.source for r in rows}
            (both if sources == {"tests", "explanation"} else tests_only if sources == {"tests"} else expl_only).append(sid)
        group = list(per_sub)
        group_set = set(group)
        working_but_confused = [sid for sid in expl_only if test_met(sub_by_id[sid])]

        # Test outcomes: probes for this misconception, group vs everyone else who submitted.
        probe_tests = [t for t in tests if any(p.get("misconception") == code for p in (t.probes or []))]
        test_rows = []
        for t in probe_tests:
            def rate(ids):
                vals = [results_by_sub[i].get(t.id) for i in ids]
                vals = [v for v in vals if v is not None]
                return (sum(v.status == "pass" for v in vals), len(vals))
            g_pass, g_n = rate(group)
            others = [s.id for s in subs if s.id not in group_set]
            o_pass, o_n = rate(others)
            errs = Counter(results_by_sub[i][t.id].error_type or "wrong value" for i in group
                           if t.id in results_by_sub[i] and results_by_sub[i][t.id].status != "pass")
            test_rows.append({"test_case_id": t.id, "name": t.name, "hidden": t.hidden,
                              "group_passed": g_pass, "group_total": g_n, "others_passed": o_pass, "others_total": o_n,
                              "common_failures": [{"kind": k, "count": n} for k, n in errs.most_common(3)]})

        # Criteria: share of the group meeting each criterion, vs the rest of the class.
        crit_rows = []
        for c in criteria:
            def met_share(ids):
                rows = [authoritative(sub_by_id[i].evidence, c.id) for i in ids]
                judged = [r for r in rows if r and r.judgment in ("met", "partial", "not_met")]
                return sum(r.judgment == "met" for r in judged), len(judged)
            g_met, g_n = met_share(group)
            o_met, o_n = met_share([s.id for s in subs if s.id not in group_set])
            crit_rows.append({"criterion_id": c.id, "code": c.code, "title": c.title, "method": c.method,
                              "linked": c.objective_id == mc.objective_id,
                              "group_met": g_met, "group_judged": g_n, "others_met": o_met, "others_judged": o_n})

        examples = _examples(per_sub, sub_by_id, users, both, expl_only, tests_only)

        missing = []
        if not_submitted:
            missing.append({"kind": "not_submitted", "count": len(not_submitted),
                            "text": f"{len(not_submitted)} enrolled students did not submit, so there is no evidence for them either way."})
        if not_analyzed:
            missing.append({"kind": "explanations_not_analyzed", "count": len(not_analyzed),
                            "text": f"{len(not_analyzed)} written explanations were not analysed by AI (provider unavailable or the call failed). "
                                    "Explanation-only cases could be undercounted."})
        if code in ("MC-STOP-IMPLICIT",) and not any(p for t in tests for p in (t.probes or []) if p.get("misconception") == code):
            missing.append({"kind": "no_test_probe", "count": 0,
                            "text": "No test can detect this belief. It rests only on machine readings of written explanations, not yet confirmed by you."})
        low_conf = [sid for sid, rows in per_sub.items() if all(r.source in ("ai", "baseline") and r.confidence == "low" for r in rows)]
        if low_conf:
            missing.append({"kind": "low_confidence", "count": len(low_conf),
                            "text": f"For {len(low_conf)} of these students, the only evidence is a low-confidence AI reading."})

        contradictions = []
        if working_but_confused:
            contradictions.append({"kind": "working_code_confused_reasoning", "count": len(working_but_confused),
                                   "submission_ids": working_but_confused,
                                   "text": f"{len(working_but_confused)} students passed every test, but their explanation suggests this misconception."})
        says_right = [sid for sid in tests_only
                      if all((a := authoritative(sub_by_id[sid].evidence, c.id)) is not None and a.source in ("ai", "baseline") and a.judgment == "met"
                             for c in expl_criteria if c.objective_id == mc.objective_id) and expl_status.get(sid) == "analyzed"]
        if says_right:
            contradictions.append({"kind": "explanation_correct_code_wrong", "count": len(says_right), "submission_ids": says_right,
                                   "text": f"{len(says_right)} students explained the stopping condition correctly, but their code fails the probing tests."})

        n = len(group)
        parts = []
        if tests_only:
            parts.append(f"{len(tests_only)} from test outcomes only")
        if expl_only:
            parts.append(f"{len(expl_only)} from written explanations only")
        if both:
            parts.append(f"{len(both)} from both")
        summary = f"{n} of {len(subs)} submissions flagged ({', '.join(parts)}). Flags from explanations are AI suggestions until you review them."

        insight = m.Insight(
            assignment_id=assignment.id, run_id=run.id, kind="misconception", objective_id=mc.objective_id,
            misconception_code=code, title=mc.title, summary=summary, student_count=n,
            evidence={
                "counts": {"students": n, "submitted": len(subs), "enrolled": len(enrolled), "tests_only": len(tests_only),
                           "explanation_only": len(expl_only), "both": len(both), "working_code_confused_reasoning": len(working_but_confused)},
                "misconception": {"code": mc.code, "title": mc.title, "description": mc.description},
                "why_it_matters": mc.why_it_matters,
                "criteria": crit_rows,
                "tests": test_rows,
                "examples": examples,
                "conditions": {"kind": assignment.kind, "conditions": assignment.conditions, "ai_policy": assignment.ai_policy},
                "missing": missing,
                "contradictions": contradictions,
                "submission_ids": sorted(group),
                "student_ids": sorted(sub_by_id[s].student_id for s in group),
                "by_source": {"tests_only": sorted(tests_only), "explanation_only": sorted(expl_only), "both": sorted(both)},
                "threshold": threshold,
            },
        )
        db.add(insight)
        created.append(insight)

    support = _needs_support(subs, criteria, users, not_submitted, db, assignment.id, run.id)
    if support:
        db.add(support)
        created.append(support)
    db.flush()
    return created


def _examples(per_sub, sub_by_id, users, both, expl_only, tests_only, k: int = 4) -> list[dict]:
    """Pick a few examples that show the range of evidence: both sources first, then each single source."""
    order = both[:2] + expl_only[:1] + tests_only[:1]
    for pool in (both, expl_only, tests_only):
        for sid in pool:
            if len(order) >= k:
                break
            if sid not in order:
                order.append(sid)
    out = []
    for sid in order[:k]:
        s = sub_by_id[sid]
        rows = per_sub[sid]
        quote = next((r.quote for r in rows if r.source in ("ai", "baseline") and r.quote), "")
        test_detail = next((r.detail for r in rows if r.source == "tests"), "")
        u = users.get(s.student_id)
        out.append({"submission_id": sid, "student_id": s.student_id, "student_name": u.name if u else "",
                    "is_synthetic": s.is_synthetic, "quote": quote, "test_evidence": test_detail,
                    "sources": sorted({r.source for r in rows})})
    return out


def _needs_support(subs, criteria, users, not_submitted, db, assignment_id: int, run_id: int) -> m.Insight | None:
    struggling = []
    for s in subs:
        not_met = [c.code for c in criteria if (a := authoritative(s.evidence, c.id)) is not None and a.judgment == "not_met"]
        if len(not_met) >= 2:
            struggling.append({"submission_id": s.id, "student_id": s.student_id,
                               "student_name": users[s.student_id].name if s.student_id in users else "", "criteria_not_met": not_met})
    if not struggling and not not_submitted:
        return None
    names = {u.id: u.name for u in db.scalars(select(m.User).where(m.User.id.in_(not_submitted))).all()} if not_submitted else {}
    return m.Insight(
        assignment_id=assignment_id, run_id=run_id, kind="needs_support",
        title="Students who may need direct support",
        summary=f"{len(struggling)} students did not meet two or more criteria, and {len(not_submitted)} did not submit.",
        student_count=len(struggling) + len(not_submitted),
        evidence={"struggling": struggling, "not_submitted": [{"student_id": i, "student_name": names.get(i, "")} for i in not_submitted]},
    )

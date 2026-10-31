"""ATHAR evaluation suite.

    .venv/bin/python -m evals.run                     # dev + held-out, rule baseline (+ LLM if a key is configured)
    .venv/bin/python -m evals.run --split heldout
    .venv/bin/python -m evals.run --no-system         # skip the workflow/system checks (pytest)

Splits
- dev:     generated from the synthetic-class templates in athar/seed/synthetic.py. The rule baseline was
           written from these, so dev numbers for the baseline are optimistic by construction.
- heldout: hand-written in evals/datasets/heldout/ after the baseline, probes and verifier rules were frozen
           (see git history). Nothing was tuned on it.

Results go to evals/results/<split>.json (previous results are kept as <split>.prev.json for regression
deltas) and docs/EVALUATION.md is regenerated.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from athar.ai import baseline as rule_baseline
from athar.ai import explanations as llm_expl
from athar.ai.provider import get_provider, provider_status
from athar.grading.evidence import probe_hits
from athar.grading.sandbox import TestSpec, run_tests
from athar.interventions.validation import validate_item
from athar.interventions.verifier import TestObservation, VerifierInput, verify
from athar.seed import content, synthetic

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT.parent
DOCS = BACKEND.parent / "docs"
CODES = ["MC-BASE-SMALLEST", "MC-BASE-VALUE", "MC-NO-PROGRESS", "MC-STOP-IMPLICIT"]
EXPL_CODES = ["MC-STOP-IMPLICIT", "MC-BASE-SMALLEST"]
EXPL_CRITERIA = [{"code": c["code"], "title": c["title"], "description": c["description"]} for c in content.CRITERIA if c["method"] == "explanation"]
MISC = [{"code": x["code"], "title": x["title"], "description": x["description"]} for x in content.MISCONCEPTIONS]


# ------------------------------------------------------------------ datasets

def dev_sets() -> dict:
    names, plans = synthetic.generate_class()
    expl_map = {"solid": ([], "met"), "implicit_stop": (["MC-STOP-IMPLICIT"], "not_met"), "smallest_belief": (["MC-BASE-SMALLEST"], "not_met"),
                "vague": ([], "unclear"), "combine_confused": ([], "met")}
    expl = [{"id": f"dx{i:03d}", "text": p.explanation, "misconceptions": expl_map[p.explanation_pattern][0], "c3": expl_map[p.explanation_pattern][1]}
            for i, p in enumerate(plans) if p.code and p.explanation]
    expl.append({"id": "dx-sara", "text": synthetic.SARA_EXPLANATION, "misconceptions": ["MC-BASE-SMALLEST"], "c3": "not_met"})

    def code_label(pat: str) -> tuple[list[str], str]:
        if pat.startswith("base_smallest"):
            return ["MC-BASE-SMALLEST"], "not_met" if pat.endswith("both") else "partial"
        if pat.startswith("base_value"):
            return ["MC-BASE-VALUE"], "partial"
        if pat.startswith("no_progress"):
            return ["MC-NO-PROGRESS"], "met"
        if pat == "syntax_error":
            return [], "not_met"
        return [], "met"
    code = [{"id": f"dc{i:03d}", "code": p.code, "misconceptions": code_label(p.code_pattern)[0], "c2": code_label(p.code_pattern)[1]}
            for i, p in enumerate(plans) if p.code]

    rt = next(i for i in content.ITEM_BANK if i["key"] == "repeat_text")
    SIM_CODE = {"correct": rt["reference_solution"], "still_smallest": rt["misconception_solution"],
                "correct_alt": 'def repeat_text(s, n):\n    if n <= 0:\n        return ""\n    else:\n        return repeat_text(s, n - 1) + s\n'}
    # Dev explanations: written in the same style as the synthetic-class templates (rules-v1 was built from that style).
    SIM_EXPLANATION = {
        "solid": ["It stops when n is 0 and returns an empty string, because repeating something zero times gives nothing. Each call lowers n by one so it always reaches 0.",
                  "The base case is n == 0, which returns \"\". That is the smallest valid input, and every recursive call uses n - 1, so we always get there."],
        "still_confused": ["It keeps adding s until it runs out of copies, then the recursion is finished and it returns.",
                           "The return statement stops the recursion once all the copies are added."],
        "smallest": ["It stops when n is 1 because one copy is just s. n = 0 wouldn't really be passed in."],
    }
    ver = []
    for k in ("correct", "correct_alt"):
        for e in SIM_EXPLANATION["solid"]:
            ver.append({"code": SIM_CODE[k], "explanation": e, "expected": "demonstrated"})
        for e in SIM_EXPLANATION["still_confused"]:
            ver.append({"code": SIM_CODE[k], "explanation": e, "expected": "still_developing"})
        ver.append({"code": SIM_CODE[k], "explanation": "", "expected": "insufficient_evidence"})
    ver.append({"code": SIM_CODE["still_smallest"], "explanation": SIM_EXPLANATION["smallest"][0], "expected": "still_developing"})
    for i, v in enumerate(ver):
        v["id"] = f"dv{i:02d}"

    var = []
    for it in content.ITEM_BANK:
        var.append({"id": f"di-{it['key']}", "label_valid": True, "misconception_code": it["misconception"], "reference": it["reference_solution"], "misconception": it["misconception_solution"], "tests_full": it["tests"]})
        var.append({"id": f"di-{it['key']}-swapped", "label_valid": False, "misconception_code": it["misconception"], "reference": it["misconception_solution"], "misconception": it["reference_solution"], "tests_full": it["tests"]})
        var.append({"id": f"di-{it['key']}-noprobe", "label_valid": False, "misconception_code": it["misconception"], "reference": it["reference_solution"], "misconception": it["misconception_solution"],
                    "tests_full": [t for t in it["tests"] if not t["probes"]]})
    return {"explanations": expl, "code": code, "verifier": ver, "variants": var,
            "provenance": "Generated from athar/seed/synthetic.py (seed 201) and the authored item bank. The rule baseline was written from these templates."}


def heldout_sets() -> dict:
    d = ROOT / "datasets" / "heldout"
    load = lambda n: json.loads((d / f"{n}.json").read_text())  # noqa: E731
    variants = load("variants")
    for c in variants["cases"]:
        c["tests_full"] = [{"name": f"{fn}{tuple(args)}", "function": fn, "args": args, "expected": exp, "criterion": "C2" if probe else "C1",
                            "hidden": False, "probes": variants["probe"] if probe else []} for fn, args, exp, probe in c["tests"]]
    return {"explanations": load("explanations")["cases"], "code": load("code")["cases"], "verifier": load("verifier")["cases"],
            "variants": variants["cases"],
            "provenance": "Hand-written after rules-v1 and the probes/verifier were frozen. Still unseen for those. NOT unseen for the "
                          "LLM reader: its failures were inspected while designing reader-v2, so LLM numbers here are development numbers."}


def final_sets() -> dict:
    d = ROOT / "datasets" / "final"
    load = lambda n: json.loads((d / f"{n}.json").read_text())  # noqa: E731
    variants = load("variants")
    for c in variants["cases"]:
        c["tests_full"] = [{"name": f"{fn}{tuple(args)}", "function": fn, "args": args, "expected": exp, "criterion": "C2" if probe else "C1",
                            "hidden": False, "probes": variants["probe"] if probe else []} for fn, args, exp, probe in c["tests"]]
    return {"explanations": load("explanations")["cases"], "verifier": load("verifier")["cases"], "variants": variants["cases"],
            "diagnosis": load("diagnosis")["cases"],
            "provenance": "Hand-written after reader-v2, rules-v1, the verifier and the diagnosis rules were frozen; committed before any run "
                          "(git log -- backend/evals/datasets/final). This is the reported generalisation result."}


# ------------------------------------------------------------------ metrics

def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p and r else (0.0 if tp + fp + fn > 0 else None)
    return {"precision": _r(p), "recall": _r(r), "f1": _r(f), "tp": tp, "fp": fp, "fn": fn}


def _r(x):
    return None if x is None else round(x, 3)


def multilabel(cases: list[dict], preds: dict[str, set[str]], codes: list[str]) -> dict:
    out, tp_all, fp_all, fn_all = {}, 0, 0, 0
    for code in codes:
        tp = sum(1 for c in cases if code in c["misconceptions"] and code in preds[c["id"]])
        fp = sum(1 for c in cases if code not in c["misconceptions"] and code in preds[c["id"]])
        fn = sum(1 for c in cases if code in c["misconceptions"] and code not in preds[c["id"]])
        out[code] = prf(tp, fp, fn)
        tp_all, fp_all, fn_all = tp_all + tp, fp_all + fp, fn_all + fn
    out["micro"] = prf(tp_all, fp_all, fn_all)
    return out


# ------------------------------------------------------------------ suites

A3_TESTS = [SimpleNamespace(id=i, **{k: v for k, v in t.items()}) for i, t in enumerate(content.TESTS)]


def suite_code(cases: list[dict]) -> dict:
    """Grading + test-based misconception identification vs. a pass/fail baseline."""
    specs = [TestSpec(t.id, t.function, t.args, t.expected) for t in A3_TESTS]
    preds, naive, c2_hits, failures = {}, {}, 0, []
    for c in cases:
        rep = run_tests(c["code"], specs)
        load_failed = rep.load_error is not None or any(o.error_type == "Crash" for o in rep.outcomes)
        found = set()
        for o in rep.outcomes:
            found |= set(probe_hits(A3_TESTS[o.id], o.status, o.error_type, load_failed))
        preds[c["id"]] = found
        naive[c["id"]] = any(o.status != "pass" for o in rep.outcomes)
        c2 = [o for o in rep.outcomes if A3_TESTS[o.id].criterion == "C2"]
        passed = sum(o.status == "pass" for o in c2)
        j = "met" if passed == len(c2) else "not_met" if passed == 0 else "partial"
        c2_hits += j == c["c2"]
        if found != set(c["misconceptions"]) or j != c["c2"]:
            failures.append({"id": c["id"], "expected": sorted(c["misconceptions"]), "found": sorted(found), "c2_expected": c["c2"], "c2_got": j})
    stop_codes = {"MC-BASE-SMALLEST", "MC-BASE-VALUE"}
    gold_bin = {c["id"]: bool(stop_codes & set(c["misconceptions"])) for c in cases}
    probe_bin = {c["id"]: bool(stop_codes & preds[c["id"]]) for c in cases}

    def acc(pred):
        return _r(sum(pred[i] == gold_bin[i] for i in gold_bin) / len(gold_bin))
    return {
        "n": len(cases), "misconceptions": multilabel(cases, preds, ["MC-BASE-SMALLEST", "MC-BASE-VALUE", "MC-NO-PROGRESS"]),
        "exact_set_accuracy": _r(sum(preds[c["id"]] == set(c["misconceptions"]) for c in cases) / len(cases)),
        "c2_judgment_accuracy": _r(c2_hits / len(cases)),
        "stopping_condition_flag_accuracy": {"probes": acc(probe_bin), "baseline_any_failing_test": acc(naive)},
        "failures": failures,
    }


OBJECTIVES = [{"code": o["code"], "title": o["title"]} for o in content.OBJECTIVES]


def _read(kind: str, provider, text: str, code: str = "(not shown)", test_summary: str = "(not shown)", prompt: str | None = None):
    if kind == "baseline":
        return rule_baseline.analyze(text, EXPL_CRITERIA)
    return llm_expl.analyze(provider, explanation=text, criteria=EXPL_CRITERIA, misconceptions=MISC, objectives=OBJECTIVES,
                            conditions="assessment check, unsupervised",
                            assignment_prompt=prompt or content.ASSIGNMENT["prompt"], explanation_prompt=content.ASSIGNMENT["explanation_prompt"],
                            code=code, test_summary=test_summary)


def suite_explanations(cases: list[dict], kind: str, provider) -> dict:
    preds, c3, errors, failures, outputs, abstained = {}, {}, 0, [], [], 0
    q_ret = q_kept = 0
    from concurrent.futures import ThreadPoolExecutor

    def read_one(c):
        try:
            return c, _read(kind, provider, c["text"]), None
        except Exception as e:  # noqa: BLE001
            return c, None, e
    with ThreadPoolExecutor(max_workers=6 if kind == "llm" else 1) as pool:
        readings = list(pool.map(read_one, cases))
    for c, a, err in readings:
        try:
            if err:
                raise err
            q_ret, q_kept = q_ret + a.quotes_returned, q_kept + a.quotes_kept
            preds[c["id"]] = {s.code for s in a.signals} & set(EXPL_CODES)
            c3[c["id"]] = a.criteria["C3"].judgment if "C3" in a.criteria else "missing"
            abstained += bool(a.abstained)
            outputs.append({"id": c["id"], "holds": sorted(preds[c["id"]]), "rejects": [r.code for r in a.rejected_ideas], "c3": c3[c["id"]],
                            "abstained": a.abstained, "summary": a.summary, "validation_notes": a.rejected})
        except Exception as e:  # noqa: BLE001 - counted, never hidden
            errors += 1
            preds[c["id"]], c3[c["id"]] = set(), f"error: {e.__class__.__name__}"
            outputs.append({"id": c["id"], "error": f"{e.__class__.__name__}: {e}"[:300]})
        if preds[c["id"]] != set(c["misconceptions"]) or c3[c["id"]] != c["c3"]:
            failures.append({"id": c["id"], "text": c["text"][:110], "expected": sorted(c["misconceptions"]), "found": sorted(preds[c["id"]]),
                             "c3_expected": c["c3"], "c3_got": c3[c["id"]]})
    unclear = [c for c in cases if c["c3"] == "unclear"]
    decided = [c for c in cases if c["c3"] != "unclear"]
    majority = {c["id"]: set() for c in cases}
    return {
        "n": len(cases), "reader": kind, "errors": errors,
        "misconceptions": multilabel(cases, preds, EXPL_CODES),
        "c3_accuracy": _r(sum(c3[c["id"]] == c["c3"] for c in cases) / len(cases)),
        "abstains_when_evidence_is_insufficient": _r(sum(c3[c["id"]] == "unclear" for c in unclear) / len(unclear)) if unclear else None,
        "wrongly_abstains_when_decidable": _r(sum(c3[c["id"]] == "unclear" for c in decided) / len(decided)) if decided else None,
        "c3_correct": sum(c3[c["id"]] == c["c3"] for c in cases),
        "quotes": {"returned": q_ret, "verbatim": q_kept},
        "negation": (lambda neg: {"n": len(neg), "no_false_misconception": sum(1 for c in neg if not preds[c["id"]]),
                                  "c3_correct": sum(1 for c in neg if c3[c["id"]] == c["c3"])})([c for c in cases if c.get("category") == "negation"]),
        "c3_confusion": [{"expected": e, "got": g, "count": n} for (e, g), n in sorted(Counter((c["c3"], c3[c["id"]]) for c in cases).items())],
        "abstention_rate": _r(abstained / len(cases)) if kind == "llm" else None,
        "unclear_rate": _r(sum(c3[c["id"]] == "unclear" for c in cases) / len(cases)),
        "by_category": {cat: {"n": len(cc), "fully_correct": sum(1 for c in cc if preds[c["id"]] == set(c["misconceptions"]) and c3[c["id"]] == c["c3"])}
                        for cat in sorted({c.get("category", "all") for c in cases})
                        for cc in [[c for c in cases if c.get("category", "all") == cat]]},
        "outputs": outputs,
        "trivial_baseline_always_met_no_misconception": {
            "c3_accuracy": _r(sum(c["c3"] == "met" for c in cases) / len(cases)),
            "micro_f1": multilabel(cases, majority, EXPL_CODES)["micro"]["f1"]},
        "failures": failures,
    }


def suite_verifier(cases: list[dict], kind: str, provider) -> dict:
    conf, hits, failures = Counter(), 0, []
    for c in cases:
        item = next(i for i in content.ITEM_BANK if i["key"] == c.get("item", "repeat_text"))
        tests = item["tests"]
        specs = [TestSpec(i, t["function"], t["args"], t["expected"]) for i, t in enumerate(tests)]
        rep = run_tests(c["code"], specs)
        load_failed = rep.load_error is not None or any(o.error_type == "Crash" for o in rep.outcomes)
        obs = [TestObservation(tests[o.id]["name"], o.status, o.error_type, tests[o.id]["probes"]) for o in rep.outcomes]
        judgment, signals = None, []
        if c["explanation"].strip():
            try:
                a = _read(kind, provider, c["explanation"], code=c["code"], prompt=item["prompt"],
                          test_summary="\n".join(f"- {tests[o.id]['name']}: {o.status} {o.error_type}" for o in rep.outcomes))
                judgment = a.criteria["C3"].judgment if "C3" in a.criteria else None
                signals = [s.code for s in a.signals]
            except Exception:  # noqa: BLE001
                judgment = None
        res = verify(VerifierInput("MC-BASE-SMALLEST", obs, load_failed, c["explanation"], judgment, signals))
        conf[(c["expected"], res.outcome)] += 1
        hits += res.outcome == c["expected"]
        if res.outcome != c["expected"]:
            failures.append({"id": c["id"], "expected": c["expected"], "got": res.outcome, "reasons": res.reasons[:1]})
    return {"n": len(cases), "reader": kind, "accuracy": _r(hits / len(cases)), "correct": hits,
            "confusion": [{"expected": e, "got": g, "count": n} for (e, g), n in sorted(conf.items())], "failures": failures}


def suite_diagnosis(cases: list[dict], kind: str, provider) -> dict:
    """Planning end to end: sandbox → probes → reading → diagnosis rules. kind='none' is the no-reader ablation."""
    from athar.interventions.planning import diagnose_submission

    specs = [TestSpec(t.id, t.function, t.args, t.expected) for t in A3_TESTS]
    crit = [SimpleNamespace(id=i + 1, code=c["code"], method=c["method"]) for i, c in enumerate(content.CRITERIA)]
    c3 = next(c for c in crit if c.code == "C3")
    conf, hits, failures = Counter(), 0, []
    for c in cases:
        rep = run_tests(c["code"], specs)
        load_failed = rep.load_error is not None
        results = [SimpleNamespace(status=o.status, error_type=o.error_type, error_message=o.error_message, actual=o.actual) for o in rep.outcomes]
        mevs = [SimpleNamespace(source="tests", misconception_code=code, detail=f"{A3_TESTS[o.id].name}: {o.error_type or o.actual}", quote="")
                for o in rep.outcomes for code in probe_hits(A3_TESTS[o.id], o.status, o.error_type, load_failed)]
        evidence, reading = [], None
        if kind != "none" and c["explanation"].strip():
            try:
                a = _read(kind, provider, c["explanation"], code=c["code"],
                          test_summary="\n".join(f"- {A3_TESTS[o.id].name}: {o.status} {o.error_type}" for o in rep.outcomes))
                mevs += [SimpleNamespace(source="ai" if kind == "llm" else "baseline", misconception_code=s.code, detail=s.reasoning, quote=s.quote)
                         for s in a.signals]
                j = a.criteria.get("C3")
                if j:
                    evidence.append(SimpleNamespace(id=1, criterion_id=c3.id, source="ai" if kind == "llm" else "baseline", judgment=j.judgment,
                                                    created_at=0))
                reading = SimpleNamespace(abstained=a.abstained, code_issue=a.code_issue)
            except Exception:  # noqa: BLE001 - treated as unread
                pass
        elif not c["explanation"].strip():
            evidence.append(SimpleNamespace(id=1, criterion_id=c3.id, source="rules", judgment="not_met", created_at=0))
        sub = SimpleNamespace(id=0, student_id=0, explanation=c["explanation"], evidence=evidence)
        got = diagnose_submission(sub, results, mevs, reading, crit).category
        conf[(c["expected"], got)] += 1
        hits += got == c["expected"]
        if got != c["expected"]:
            failures.append({"id": c["id"], "expected": c["expected"], "got": got})
    return {"n": len(cases), "reader": kind, "accuracy": _r(hits / len(cases)), "correct": hits,
            "confusion": [{"expected": e, "got": g, "count": n} for (e, g), n in sorted(conf.items())], "failures": failures}


def suite_variants(cases: list[dict]) -> dict:
    hits, failures = 0, []
    for c in cases:
        v = validate_item(tests=c["tests_full"], reference_solution=c["reference"], misconception_solution=c["misconception"],
                          misconception_code=c.get("misconception_code", "MC-BASE-SMALLEST"))
        hits += v["valid"] == c["label_valid"]
        if v["valid"] != c["label_valid"]:
            failures.append({"id": c["id"], "expected_valid": c["label_valid"], "validator": v["valid"], "problems": v["problems"], "note": c.get("note", "")})
    return {"n": len(cases), "accuracy": _r(hits / len(cases)), "correct": hits, "failures": failures}


def suite_system() -> dict:
    """Workflow guarantees, exercised end-to-end through the API by the pytest suite."""
    files = ["tests/test_interventions.py", "tests/test_api_gates.py", "tests/test_pipeline_and_insights.py",
             "tests/test_llm_reader.py", "tests/test_planning.py", "tests/test_generation.py"]
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rf", *files], cwd=BACKEND, capture_output=True, text=True)
    tail = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-300:]
    failed = [ln.removeprefix("FAILED ") for ln in p.stdout.splitlines() if ln.startswith("FAILED ")]
    return {"command": "pytest -q " + " ".join(files), "summary": tail, "ok": p.returncode == 0, "failed": failed}


# ------------------------------------------------------------------ main

def run_split(name: str, sets: dict, provider) -> dict:
    from athar.ai.provider import USAGE
    USAGE.reset()
    readers = ["baseline"] + (["llm"] if provider else [])
    res = {"split": name, "provenance": sets["provenance"], "variants": suite_variants(sets["variants"]),
           "explanations": {k: suite_explanations(sets["explanations"], k, provider) for k in readers},
           "verifier": {k: suite_verifier(sets["verifier"], k, provider) for k in readers}}
    if "code" in sets:
        res["code"] = suite_code(sets["code"])
    if "diagnosis" in sets:
        res["diagnosis"] = {k: suite_diagnosis(sets["diagnosis"], k, provider) for k in ["none", *readers]}
    res["llm_usage"] = USAGE.snapshot(provider.model) if provider else None
    if not provider:
        msg = {"not_run": "No model credentials configured. Nothing was simulated or replayed in its place."}
        res["explanations"]["llm"] = res["verifier"]["llm"] = msg
        if "diagnosis" in res:
            res["diagnosis"]["llm"] = msg
    return res


def git_rev() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BACKEND, capture_output=True, text=True).stdout.strip()
    except OSError:
        return "unknown"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "heldout", "final", "all"], default="all")
    ap.add_argument("--no-system", action="store_true")
    args = ap.parse_args()
    provider = get_provider()
    from athar.interventions.verifier import RULE_VERSION
    meta = {"commit": git_rev(), "ran_at": time.strftime("%Y-%m-%d %H:%M:%S %z"), "llm": provider_status(),
            "baseline_version": rule_baseline.VERSION, "reader_prompt_version": llm_expl.PROMPT_VERSION, "verifier_version": RULE_VERSION,
            "python": sys.version.split()[0]}
    splits = {"dev": dev_sets, "heldout": heldout_sets, "final": final_sets}
    names = ["dev", "heldout", "final"] if args.split == "all" else [args.split]
    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    results = {}
    for n in names:
        r = {"meta": meta, **run_split(n, splits[n](), provider)}
        path = out_dir / f"{n}.json"
        if path.exists():
            path.replace(out_dir / f"{n}.prev.json")
        path.write_text(json.dumps(r, indent=2, ensure_ascii=False))
        results[n] = r
        print(f"wrote {path.relative_to(BACKEND)}")
    system = None if args.no_system else suite_system()
    if system:
        (out_dir / "system.json").write_text(json.dumps({"meta": meta, **system}, indent=2))
    from .report import write_report
    write_report(DOCS / "EVALUATION.md", out_dir, system)
    print(f"wrote {DOCS / 'EVALUATION.md'}")


if __name__ == "__main__":
    main()

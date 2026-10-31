"""Generate the README charts as SVG (light and dark) from committed evaluation results and the demo database.

Run from backend/:  .venv/bin/python ../docs/assets/make_charts.py
Standard library only, plus the athar package for the class plan and planted-label recovery. No model calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "backend" / "evals" / "results"
OUT = Path(__file__).resolve().parent / "charts"
OUT.mkdir(exist_ok=True)

THEMES = {
    "light": {"bg": "#FAF8F3", "ink": "#1D1F1A", "muted": "#5F625A", "line": "#E2DFD6", "ai": "#2F6B4F", "rules": "#9AA096",
              "amber": "#A86A12", "slate": "#5B6B7F", "faint": "#8A8D84"},
    "dark": {"bg": "#141614", "ink": "#E8E6DF", "muted": "#A3A69C", "line": "#2A2D29", "ai": "#5FA884", "rules": "#6E736A",
             "amber": "#D9A441", "slate": "#8DA2BA", "faint": "#7C8077"},
}
FONT = "'IBM Plex Sans', -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg(w: int, h: int, body: str, t: dict, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">'
            f'<title>{esc(title)}</title><rect width="{w}" height="{h}" rx="12" fill="{t["bg"]}"/>'
            f'<g font-family="{FONT}">{body}</g></svg>')


def text(x, y, s, t, size=14, color="ink", anchor="start", weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{t[color]}" text-anchor="{anchor}" font-weight="{weight}">{esc(s)}</text>'


def write(name: str, make) -> None:
    for mode, t in THEMES.items():
        (OUT / f"{name}-{mode}.svg").write_text(make(t))
    print("wrote", name)


# ---------------------------------------------------------------- A. AI vs rules, final set (n=36) and final-2 (n=24), separately

final = json.loads((RESULTS / "final.json").read_text())
final2 = json.loads((RESULTS / "final2.json").read_text())


def bars_chart(t, heading, sub, rows, note):
    """rows: (label, value 0..1, display, kind)"""
    w, left, barw = 760, 250, 250
    h = 120 + len(rows) * 46 + 40
    out = [text(32, 44, heading, t, 18, weight=600), text(32, 68, sub, t, 13, "muted")]
    y = 104
    for label, v, disp, kind in rows:
        out.append(text(32, y + 19, label, t, 14))
        out.append(f'<rect x="{left}" y="{y + 4}" width="{barw}" height="22" rx="4" fill="{t["line"]}"/>')
        out.append(f'<rect x="{left}" y="{y + 4}" width="{max(2, barw * v):.1f}" height="22" rx="4" fill="{t[kind]}"/>')
        out.append(text(left + barw + 12, y + 20, disp, t, 14, weight=600))
        y += 46
    out.append(text(32, y + 22, note, t, 12, "faint"))
    return svg(w, h, "".join(out), t, heading)


def chart_final(t):
    b, l = final["explanations"]["baseline"]["misconceptions"]["micro"], final["explanations"]["llm"]["misconceptions"]["micro"]
    n = final["explanations"]["llm"]["n"]
    v = final["meta"]["reader_prompt_version"]
    rows = [
        (f"AI reader ({v}) · F1", l["f1"], f'{l["f1"]:.2f}  ({l["tp"]} found, {l["fp"]} false, {l["fn"]} missed)', "ai"),
        ("Keyword rules (rules-v1) · F1", b["f1"], f'{b["f1"]:.2f}  ({b["tp"]} found, {b["fp"]} false, {b["fn"]} missed)', "rules"),
    ]
    return bars_chart(t, "Finding misconceptions in written explanations",
                      f"Final set: {n} hand-written explanations, frozen before any run · {l['tp'] + l['fn']} held misconceptions · gpt-4.1-mini",
                      rows, "Micro F1 over the two stopping-condition misconceptions. Source: backend/evals/results/final.json")


def chart_final2(t):
    r = final2["readers"]
    v3, ru = r["reader-v3"], r["rules"]
    wc, wr = v3["working_code_confused_reasoning"], ru["working_code_confused_reasoning"]
    rows = [
        ("AI reader (reader-v3)", wc["caught"] / wc["n"], f'{wc["caught"]} of {wc["n"]}', "ai"),
        ("Keyword rules (rules-v1)", wr["caught"] / wr["n"], f'{wr["caught"]} of {wr["n"]}', "rules"),
        ("AI reader (reader-v3) · F1", v3["misconceptions"]["micro"]["f1"], f'{v3["misconceptions"]["micro"]["f1"]:.2f}', "ai"),
        ("Keyword rules (rules-v1) · F1", ru["misconceptions"]["micro"]["f1"], f'{ru["misconceptions"]["micro"]["f1"]:.2f}', "rules"),
    ]
    return bars_chart(t, "Working code, confused reasoning: the case tests can't see",
                      f"Final-2: {v3['n']} code + explanation pairs, frozen before reader-v3 existed · first two rows: the {wc['n']} cases with passing code",
                      rows, "Source: backend/evals/results/final2.json")


write("ai-vs-rules-final", chart_final)
write("ai-vs-rules-final2", chart_final2)

# ---------------------------------------------------------------- B. How the demo class is routed (live plan from the synthetic class)

sys.path.insert(0, str(ROOT / "backend"))
from athar import models as m  # noqa: E402
from athar.cli import evaluate  # noqa: E402
from athar.db import SessionLocal  # noqa: E402
from athar.interventions.planning import plan_for_assignment  # noqa: E402

with SessionLocal() as db:
    plan = plan_for_assignment(db, db.get(m.Assignment, 1))
    recovery = evaluate(db)

LABEL = {
    "concept_gap": ("Tests show a base-case gap", "concept practice + new check", "slate"),
    "conflicting_evidence": ("Evidence conflicts", "professor reviews first", "amber"),
    "reasoning_gap": ("Working code, reasoning flagged", "explain-your-reasoning task", "amber"),
    "execution_error": ("Code didn't run", "debugging exercise", "slate"),
    "reasoning_unconfirmed": ("Reasoning not confirmed", "explain-your-reasoning task", "faint"),
    "no_submission": ("No submission", "professor reaches out", "faint"),
    "demonstrated": ("Tests pass, reasoning reads sound", "no extra work", "ai"),
}
counts: dict[str, int] = {}
for g in plan["groups"]:
    counts[g["category"]] = counts.get(g["category"], 0) + len(g["students"])
total = sum(counts.values())


def chart_routing(t):
    w, left, barw = 760, 270, 170
    rows = [c for c in LABEL if c in counts]
    h = 120 + len(rows) * 44 + 34
    out = [text(32, 44, f"Different needs, different help: the {total}-student demo class", t, 18, weight=600),
           text(32, 68, "Synthetic class (CS201, Assignment 3). Fixed rules over test results and the stored AI reading. Nothing is sent before approval.", t, 12.5, "muted")]
    y = 100
    for c in rows:
        lab, action, kind = LABEL[c]
        n = counts[c]
        out.append(text(32, y + 18, lab, t, 14))
        out.append(f'<rect x="{left}" y="{y + 4}" width="{barw}" height="20" rx="4" fill="{t["line"]}"/>')
        out.append(f'<rect x="{left}" y="{y + 4}" width="{max(2, barw * n / total):.1f}" height="20" rx="4" fill="{t[kind]}"/>')
        out.append(text(left + barw + 10, y + 19, str(n), t, 14, weight=600))
        out.append(text(left + barw + 44, y + 19, "→ " + action, t, 13, "muted"))
        y += 44
    out.append(text(32, y + 20, "Source: athar/interventions/planning.py on the demo database. Amber = rests partly on AI readings.", t, 12, "faint"))
    return svg(w, h, "".join(out), t, "How the demo class is routed")


write("class-routing", chart_routing)

# ---------------------------------------------------------------- C. Over-flagging on the synthetic class (planted labels)

r = recovery["MC-STOP-IMPLICIT"]


def chart_overflag(t):
    w, left, barw = 760, 300, 360
    mx = max(r["detected"], r["planted"])
    rows = [("Planted in the synthetic class", r["planted"], "slate"),
            ("Flagged by the AI reading", r["detected"], "amber"),
            ("Flagged after the conflict check", r["after_dispute_rule"]["detected"], "amber"),
            ("…of which match a planted case", r["after_dispute_rule"]["true_positive"], "ai")]
    h = 120 + len(rows) * 44 + 34
    out = [text(32, 44, "Where the AI over-flags: “recursion stops by itself”", t, 18, weight=600),
           text(32, 68, "Synthetic class with planted labels. The AI catches every planted case but flags many more, so every flag waits for the professor.", t, 12.5, "muted")]
    y = 100
    for lab, n, kind in rows:
        out.append(text(32, y + 18, lab, t, 14))
        out.append(f'<rect x="{left}" y="{y + 4}" width="{barw * n / mx:.1f}" height="20" rx="4" fill="{t[kind]}"/>')
        out.append(text(left + barw * n / mx + 10, y + 19, str(n), t, 14, weight=600))
        y += 44
    out.append(text(32, y + 20, "Source: athar.cli eval on the demo database. The conflict check was added after the frozen sets were run.", t, 12, "faint"))
    return svg(w, h, "".join(out), t, "Over-flagging on the synthetic class")


write("overflagging", chart_overflag)
print(json.dumps({"routing": counts, "total": total, "stop_implicit": r}, indent=1))

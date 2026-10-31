# ATHAR | أثر — Architecture and roadmap

## The loop the system is built around

```
ASSESS ──► UNDERSTAND ──► INTERVENE ──► VERIFY ──┐
  ▲                                              │
  └──────────────────────────────────────────────┘
```

Every module maps to one step. If a feature doesn't strengthen one of these steps, it waits.

| Step | What happens | Who decides | Module |
|---|---|---|---|
| Assess | Submissions are run against tests; AI drafts rubric judgments on written reasoning | Tests (deterministic), AI (suggestion only) | `grading/` |
| Understand | Evidence is aggregated per learning objective and misconception | Deterministic rules over stored evidence | `insights.py` |
| Intervene | A plan is drafted, edited, approved, then executed as real records | Professor (approval gate), state machine | `interventions/` (M2) |
| Verify | Follow-up attempts are tested on a validated variant; outcome is computed | Explicit verifier rules | `verification/` (M2) |

## Principles that shape the code

1. **AI suggests, rules decide, professors approve.** LLM output is always stored as a
   *suggestion* with its source, model and confidence. Nothing consequential (publishing a
   grade, delivering an intervention, declaring an outcome) happens because an LLM said so.
2. **Every claim is traceable.** An insight carries the IDs of the submissions, test results and
   evidence rows behind it. The UI links each number to those records.
3. **AI output is validated before use.** Structured outputs are parsed with Pydantic, and every
   quoted "evidence" span has to actually appear in the student's text. Spans that don't are dropped
   and the row is flagged for review.
4. **No silent fallbacks.** If no LLM is configured or a call fails, the affected rows are marked
   `ai_unavailable`/`ai_failed` and the UI says so. The deterministic parts keep working.
5. **Synthetic data is labelled synthetic**, both in the database (`is_synthetic`) and in the UI.
   The seed plants patterns with ground-truth labels in a separate table that analysis code
   never reads. The labels exist only to measure whether ATHAR recovers those patterns.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind 3 + TanStack Query + React Router | Requested stack. TanStack Query gives honest loading and error states cheaply |
| Backend | FastAPI + Pydantic 2 + SQLAlchemy 2 | Typed API boundary. SQLAlchemy models are portable to Postgres |
| Storage | SQLite file (`backend/data/athar.db`) | Zero setup. Migration path: add Alembic once the M2 schema settles, then point `ATHAR_DATABASE_URL` at Postgres |
| Code execution | Subprocess per submission, `python -I`, CPU/memory/file limits, per-test alarm, tmp dir | Enough for synthetic and demo data. **Not a hardened sandbox.** Production needs a container or gVisor/nsjail runner behind the same interface |
| LLM | `ai/provider.py` with an Anthropic and an OpenAI implementation, chosen by env | Structured output via `messages.parse` / `chat.completions.parse` straight into Pydantic models |
| Background work | One worker thread per grading run, with state persisted in `grading_runs` | No queue infrastructure. A run survives page reloads, and its status is in the database |

There's no multi-agent framework. ATHAR's "agency" is a stateful workflow: persisted runs,
interventions with explicit transitions, and focused LLM calls for specific judgments.

## Data model (M1)

```
users ─┬─ courses ── enrollments
       │     ├── learning_objectives ── misconceptions (hypotheses authored with the rubric)
       │     ├── materials
       │     └── assignments ─┬─ rubric_criteria ─► objective
       │                      ├─ test_cases ─► criterion, probes (misconception, trigger)
       │                      ├─ submissions ─┬─ test_results
       │                      │               └─ criterion_evidence (source: tests | ai | professor)
       │                      ├─ grading_runs
       │                      └─ insights (computed, with evidence ids)
       └─ audit_events
synthetic_labels   (ground truth for synthetic data; never read by analysis code)
```

### How a misconception becomes an insight

1. The professor's rubric (seeded for the demo) defines *candidate* misconceptions per objective,
   and tags tests as *probes*. For example, `power(2, 0) == 1` probes "base case doesn't cover the smallest input"
   when it fails with `RecursionError`.
2. Grading runs every test in the sandbox and records the raw outcome.
3. The evidence rules turn probe outcomes into misconception evidence. Deterministic.
4. The AI reads each written explanation against the explanation criteria and the misconception
   list. It returns judgments plus exact quotes, and the quotes are validated against the text.
5. `insights.py` groups students by misconception. It reports counts by evidence type (tests only,
   explanation only, both), cases where code passes but the reasoning is confused, missing evidence,
   and example excerpts with links.

So *whether* a pattern exists, and *how many* students it affects, is always computed from stored submissions.

## Permissions

The demo has persona sign-in (no passwords) that issues an HMAC-signed token with the user's role.
The server enforces access on every route:
- Professor routes require `role == professor` and ownership of the course.
- Student routes only ever return the caller's own records. Reference solutions, hidden tests
  and other students' work are never serialised to students.

## Roadmap

| Milestone | Scope | Done when |
|---|---|---|
| **M0** Foundation | Separate repo, architecture, design tokens | This document, a running skeleton |
| **M1** Assess → Understand | Seeded CS201 with ~120 synthetic students, sandboxed test grading, AI explanation analysis (when a key is configured), evidence rules, insight engine, grade review and override, professor UI, minimal student home | The professor sees a computed recursion-base-case insight with traceable evidence, and tests cover the evidence rules and approval gates |
| **M2** Intervene → Verify | Intervention drafting, variant generation validated against reference and misconception implementations, approval state machine, delivery to students, student reasoning workspace and AI helper, follow-up assessment, verifier, updated professor view | The full Layla → Sara → Layla journey runs on real state |
| **M3** Grounding and authoring | Material upload (PDF and text), retrieval-grounded assistant, AI-proposed objectives from materials, grounded Q&A about the class | Assistant answers cite course material, and the professor can ask "who is struggling with X and why" |
| **M4** Polish | Voice input (optional, consent-based), calibration views, accessibility pass, demo script | One-minute demo runs cleanly |

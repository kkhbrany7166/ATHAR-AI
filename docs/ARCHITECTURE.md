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

## Status (Oct 31, 2026)

- **M1 done.** Grading, evidence rules, insights, grade review with publish gates.
- **M2 done, except AI-generated variants.**
  - Interventions follow `draft → approved → active → completed` (or `draft → rejected`), with every transition enforced in `interventions/service.py`.
  - Follow-up items come from an authored item bank and are validated in the sandbox (`interventions/validation.py`).
  - Students work through think, practise, look back, then check.
  - `interventions/verifier.py` (`verify-v1`) decides outcomes with explicit rules.
- **Added beyond the plan:**
  - `ai/baseline.py` (`rules-v1`): a transparent rule-based explanation reader. It keeps the product useful without model credits and serves as the evaluation baseline. It is always labelled as rules, never as AI.
  - `ai/reader.py`: chooses the LLM, the rules, or nothing via `ATHAR_ANALYZER`.
  - `evals/`: dev and held-out evaluation with baselines, system checks and a generated report.

### Why a rule baseline, and not a mock LLM
The hackathon provides no model credits. A fake "AI" that returns plausible text would make the demo look better and the product
dishonest. The rule reader is real software with measurable, documented weaknesses: on held-out explanations it is roughly coin-flip
on the stopping-condition judgment. Showing that gap is the argument for the LLM reader, not something to hide.

### Why deterministic verification
Whether a student has demonstrated something decides what the professor does next, so it can't rest on a model's opinion. The
verifier combines sandboxed test outcomes with the reasoning reading, and it only says *demonstrated* when both agree. Its errors
therefore lean towards *insufficient evidence*. In the held-out set, its one miss comes from the rule reader misreading a negation.

## Milestone 3 additions (Oct 31): AI reading, adaptive planning, gated generation

```
submission ─► sandbox tests ─► probe evidence ─┐
explanation ─► reader (LLM reader-v2 │ rules-v1 │ none) ─► validated reading ─┤
                                                                            ▼
                                     planning.py: fixed diagnosis rules ─► proposed action per group
                                                                            ▼
                                  professor drafts / edits / approves (LLM may draft text, propose checks)
                                                                            ▼
                         deterministic, idempotent executor ─► tasks ─► student work ─► verifier rules
```

- **`ai/explanations.py` (reader-v2)** gets the question, objectives, rubric, conditions, code and test outcomes. It returns per-criterion judgments, misconception findings with a *stance* (holds or rejects), per-objective evidence, the code issue (conceptual or an unrelated syntax/runtime error), contradictions, missing evidence, an abstain flag and a short summary for the professor. Validation then:
  - drops unknown codes
  - removes every quote that isn't verbatim in the student's text
  - turns "rejects" findings into notes
  - forces abstained readings to *unclear*
  - downgrades readings that contradict themselves
- **`ai/provider.py`** sets a 45 s timeout and one retry. Malformed, truncated or refused output raises `LLMError`. A per-process call budget (`ATHAR_LLM_MAX_CALLS`) caps spend.
- **`interventions/planning.py`** places each student in exactly one category from stored evidence. Each category maps to one action:

  | Category | Action |
  |---|---|
  | concept gap | concept practice |
  | execution error | debugging |
  | reasoning gap / reasoning unconfirmed | explain your reasoning |
  | demonstrated | no action |
  | no submission | personal follow-up |

- **`interventions/generation.py`** lets the LLM propose a new follow-up check. Structural checks run first, then the same sandbox validation as authored items. Rejected proposals are kept with their reasons.

## Design decisions

**Why an LLM for reading explanations.** Students write about recursion in endlessly varied ways: synonyms, negation, other languages, terse notation. On the untouched final set, the phrase-matching reader judged the stopping condition correctly in 14 of 36 cases, no better than always answering "met", and caught 1 of 14 held misconceptions. This is a language-understanding task, so it is the one place an LLM is justified.

**Why code execution stays deterministic.** Whether `power(2, 0)` raises `RecursionError` is a fact, and a sandbox establishes it exactly and repeatably. Asking a model would only add uncertainty and cost.

**Why consequential actions need approval.** Interventions change what a student is asked to do and how their work is read. The LLM may draft text and propose checks. Only the professor approves, and only deterministic code changes records. A machine reading never publishes a grade.

**Why an independent verifier.** Assistance and evidence must stay separate. The verifier ignores practice, hints and assistant chats. It looks only at a new attempt on a validated check, under stated conditions, and says *demonstrated* only when tests and reasoning agree. Its errors therefore lean towards *insufficient evidence*: on the final set, all 4 of its misses are cautious, and none is a false *demonstrated*.

**Why assisted practice isn't demonstrated understanding.** In practice a student can get hints and ask the assistant. That is learning, and it is never penalised. It also says nothing about what they can do alone, so outcomes come only from the unsupervised check, and even those carry the caveat that unsupervised work can't rule out outside help.

**Why some cases are escalated rather than classified.** An explanation like "it works" or "Recursion." supports no judgment. The reader is allowed, and asked, to abstain. The diagnosis then reports *reasoning unconfirmed*, and the verifier reports *insufficient evidence*, both marked for professor review. A confident wrong label would send a student the wrong help.

**Why no multi-agent framework.** The workflow is a state machine with a few focused model calls. Extra agents would add failure modes without adding evidence, and the evaluation gives no reason to add them.

# ATHAR | أثر

**Behind every answer is a student.** More time to teach, more room to learn.

ATHAR helps a professor see where students need help and reach them before they fall behind. It runs one loop
on real stored work: **Assess → Understand → Intervene → Verify**. AI handles the repetitive reading. The professor
makes every consequential decision. Students do the learning.

- Architecture and decisions: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Measured results (dev vs held-out, with baselines): [docs/EVALUATION.md](docs/EVALUATION.md)
- Three-minute demo path: [docs/DEMO.md](docs/DEMO.md)
- Evidence for each judging criterion: [docs/JUDGING.md](docs/JUDGING.md)

### Enabling live AI
Put one line in `backend/.env` (git-ignored), then run `chmod 600 backend/.env` and restart the API:
`ANTHROPIC_API_KEY=...` (model `claude-opus-5-5` by default; override with `ATHAR_ANTHROPIC_MODEL`) **or** `OPENAI_API_KEY=...`.
Optional: `ATHAR_LLM_TIMEOUT` (default 45 s), `ATHAR_LLM_MAX_CALLS` (default 400 per process), `ATHAR_LLM_MAX_COST_USD`
(default 1.00 per process, estimated from tokens) and `ATHAR_READER_PROMPT` (default `reader-v3`).

**Costs with gpt-4.1-mini:** grading the 114-student class is about 114 calls (≈ $0.22). `evals.run --split final` is about 58 calls (≈ $0.08).
`athar.cli reset-interventions` returns the demo to "insights ready" for free. Every live run is appended to `backend/evals/results/spend.jsonl`.

## The journey that works end to end

1. **Assess.** Professor Layla's CS201 recursion assignment has 114 synthetic submissions. Each one runs against tests in an isolated
   process, and rubric criteria are scored from the results. Written explanations are read by an LLM when a key is configured,
   otherwise by a clearly labelled rule-based reader.
2. **Understand.** Evidence is aggregated per misconception: counts by source, real excerpts, this group's test pass rates against the
   rest of the class, missing and contradicting evidence. *"18 students' stopping condition misses the smallest input"* is computed, not seeded.
3. **Intervene.** Layla drafts an intervention from the insight. ATHAR assembles:
   - an explanation (AI-drafted, or a labelled template)
   - a guided practice problem with progressive hints
   - a follow-up check that has been **validated in the sandbox**: the reference solution passes, and code with the misconception fails a probe the expected way

   She edits and approves it. Approval creates a targeted follow-up assignment and one task per student. Delivery is idempotent.
4. **Verify.** Sara works through it: think first → practise (real test runs, hints, assistant) → look back → an unsupervised check
   on a new problem. Explicit rules decide *demonstrated / still developing / insufficient evidence*, and Layla's view updates with
   per-student outcomes and next steps.

## What is real, what is not

| Capability | Status |
|---|---|
| Test execution, rubric scoring from tests, probe-based misconception evidence | **Deterministic, live** |
| Insights, intervention state machine, approval gates, task delivery, verification outcomes | **Deterministic, live**, persisted in SQLite |
| Follow-up item validation (reference vs misconception implementation) | **Deterministic, live** |
| Reading written explanations | **LLM reader-v2** (Anthropic or OpenAI) when a key is set: stance-aware, can abstain, quotes verified. Otherwise the **rule-based reader `rules-v1`**, labelled "Rule-based reading (not AI)" everywhere it appears. `ATHAR_ANALYZER=llm` refuses the rule fallback |
| Deciding who needs what (concept practice / debugging / explain reasoning / no action) | **Deterministic rules** over tests and the reading (`interventions/planning.py`) |
| Proposing new follow-up checks | **LLM** when a key is set, released only after structural checks and sandbox validation |
| Drafting the intervention explanation | **LLM** with citations checked against course notes when a key is set. Otherwise a **template**, labelled "Template draft (no AI)" |
| Student assistant chat | **LLM** when a key is set. Otherwise it says plainly that it isn't connected. Hints still work |
| Students, courses, submissions | **Synthetic**, labelled in the database and the UI |
| Classmates' follow-up attempts | **Simulated** on demand ("Simulate synthetic classmates"), sent through the real submission and verification path, and labelled *Simulated attempt* |
| LLM evaluation numbers | **Not run in this repository's committed results.** No credentials were available, and nothing was simulated or replayed in their place |
| Live AI evaluation | **Measured** with `gpt-4.1-mini` on untouched sets: misconception F1 0.93 vs rules 0.12 (final, n=36); working code with confused reasoning caught 7/7 vs 2/7 (final-2, n=24). Known weakness: the stopping-condition judgment overuses "partial". See docs/EVALUATION.md |
| Not built yet | Material upload and retrieval, voice, LMS integration, real authentication |

Machine readings (AI or rules) never publish a grade. A professor must confirm them.

## Run it

Requirements: Python 3.12+, Node 20+.

```bash
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env                              # optional: ANTHROPIC_API_KEY or OPENAI_API_KEY
.venv/bin/python -m athar.cli reset --grade       # fresh demo: seed + grading run
.venv/bin/uvicorn athar.main:app --port 8710
```

```bash
cd frontend && npm install && npm run dev         # http://localhost:5710
```

Ports 8710 (API) and 5710 (web) are ATHAR's own. `reset --grade` restores the demo to its starting point at any time.

## Test and evaluate

```bash
cd backend
.venv/bin/python -m pytest -q          # unit, integration and workflow tests
.venv/bin/python -m evals.run          # dev + held-out evaluation, regenerates docs/EVALUATION.md
cd ../frontend && npm run typecheck && npm run build
```

`ATHAR_ANALYZER=auto|llm|baseline|none` chooses how explanations are read (default `auto`: LLM if configured, else rules).

## Honesty rules this codebase follows
- Synthetic data is labelled synthetic. Simulated attempts are labelled simulated.
- Insights, counts and outcomes are computed from stored records, never written into the seed.
- Every AI quote must appear verbatim in the student's text, or it's dropped.
- If the AI is unavailable or fails, the records say so. No silent fallbacks.
- The held-out evaluation set was committed before anything ran on it. Failures are reported case by case.
- The code sandbox is prototype-grade (process isolation and resource limits). Real student code needs a container-based runner.

# ATHAR | أثر

**Agentic teaching intelligence.** Every student understood. Every skill earned.

ATHAR connects assessment, teaching decisions, personalised learning and evidence of understanding
in one loop: **Assess → Understand → Intervene → Verify**. AI handles the repetitive work.
Professors make the teaching judgments. Students do the learning.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design, the data model and the roadmap.

## Status: milestone 1 (Assess → Understand)

Working now:
- A professor workspace and a student workspace, with roles enforced on the server
- A seeded CS201 course: Professor Layla, Sara and 118 more synthetic students (114 submissions), plus a recursion assignment with a rubric and tests
- A grading run: every submission is executed against the tests in a separate, resource-limited Python process
- Deterministic evidence rules: each rubric criterion is scored from test outcomes, and failing "probe" tests are mapped to misconception hypotheses
- AI analysis of written explanations (when a provider is configured): structured output, and every quoted span must appear verbatim in the student's text before it is stored
- Classroom insights built only from stored evidence: counts by source, example excerpts, test comparisons with the rest of the class, assessment conditions, missing and contradictory evidence
- Grade review: accept AI suggestions, override any criterion, publish. Grades resting on unconfirmed AI suggestions cannot be published.

Next: milestone 2 (Intervene → Verify). See the roadmap.

## Run it

Requirements: Python 3.12+, Node 20+.

```bash
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # optional: add ANTHROPIC_API_KEY or OPENAI_API_KEY
.venv/bin/python -m athar.cli reset --grade     # seed the demo and run grading
.venv/bin/uvicorn athar.main:app --port 8710
```

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5710
```

ATHAR uses ports **8710** (API) and **5710** (web), so it doesn't clash with other local projects.

### Without an AI key
Everything except explanation analysis works. Explanation criteria are marked *Not analysed*,
and the UI says so wherever it matters. Nothing is faked.

## Test

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run typecheck && npm run build
```

`python -m athar.cli eval` compares what the pipeline detected with the patterns planted in the
synthetic data (stored in `synthetic_labels`, which the analysis code never reads).

## Honesty rules this codebase follows
- Synthetic data is labelled synthetic, in the database and in the UI.
- Insights and counts are computed from stored submissions. They are never written into the seed.
- AI output is a suggestion with its source, model and confidence. It never publishes a grade on its own.
- If the AI is unavailable or fails, the affected records say so. There are no silent fallbacks.
- The code sandbox is prototype-grade (process isolation and resource limits, no network or filesystem
  jail). Real student code needs a container-based runner.

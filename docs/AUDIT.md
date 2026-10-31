# ATHAR: Final Engineering and Evidence Audit

Audited Oct 31, 2026 against the repository at the checkpoint that adds this file. Every figure is taken from code, committed result files, the demo database or a command run during the audit. Where something wasn't measured, the audit says so.

## 0. Summary

- **Built:** a working professor and student loop: Assess → Understand → Intervene → Verify. Sandboxed testing, an LLM explanation reader with verified quotes, fixed-rule planning, approval-gated execution, a five-step student studio and a rule-based verifier, all persisted in SQLite.
- **Measured:** on untouched hand-written sets, the AI reader beats keyword rules clearly at finding misconceptions:
  - F1 0.93 vs 0.12 (final, n=36, reader-v2)
  - 7/7 vs 2/7 working-code-confused-reasoning (final-2, n=24, reader-v3)

  It is weak at certifying correct reasoning (C3 20/36), over-flags on the synthetic class (45 flagged vs 20 planted), and varies between runs.
- **Not shown:** any real-world use, a second annotator, learning gains over time, or local-model performance.
- **Critical blockers before submission:** choose a licence, decide repository visibility and history, publish, record the video, make the slides, and fill in the links. Details in §8.

## 1. How it was built (from git history)

All ATHAR commits are dated Oct 31, 2026, between 08:05 and the audit, in a separate repository from HADIR. HADIR's last commit is from Oct 30, and it is untouched.

| Phase | Commits | What happened |
|---|---|---|
| Foundation | `d950209` → `6ad4755` | Data model, sandboxed grading, evidence rules, insights, API and tests. Professor and student workspaces |
| Baseline before data | `6dc37e5` | Rule reader `rules-v1` written and frozen **before** the held-out set existed |
| Intervene → Verify | `4646584`, `61cecad` | Item bank with sandbox validation, intervention state machine, idempotent execution, student activity, verifier |
| Evaluation discipline | `05f1070`, `827499a`, `88bbc0a`, `5a60100`, `6498ae8` | Held-out set, evaluation suite, **final** set written after freezing, freeze record with hashes, **final-2** written before reader-v3 |
| LLM reader | `abc98f9`, `77826b3`, `7869292` | reader-v2 (stance, abstention, consistency checks), then reader-v3 chosen on dev (v3.1 rejected). Live runs on all splits |
| Adaptive planning | `9e2ada6`, `c2096e1`, `47a24d5` | Diagnosis per student, three intervention kinds, AI-generated checks behind validation |
| Honesty and design passes | `a255027` → `b492f5e` | "Flags for review" language, evidence kinds, review queue, signature submission screen, studio stepper, typography, clarity passes |
| Safety after findings | `4bbb491` | Conflict check (disputed AI claims → professor review), note check (≤ 90 words, approval blocked) |
| Mentor feedback | `1124d6e` | Local small-model feasibility study (desk research only) |

## 2. Product functionality

**Professor (implemented and browser-tested)**
- **Course overview:** "What needs your attention".
- **Who needs attention:** a review queue in seven groups, including evidence conflicts.
- **All submissions:** search, six filters with counts, sorting, paging, and a return to the same position.
- **Submission review:** "What ATHAR noticed", explanation beside code, failing tests, evidence, and per-criterion Accept / Change / Why?
- **Publish gates.**
- **Insight evidence pages.**
- **Intervention draft:** an editable note with a word count and flagged problems, validated practice and check, a validation pair, target selection, *Approve and send*, *Reject*.
- **Intervention outcomes:** a flow strip, outcome counts, search and filters, real vs simulated, before and after, next steps.
- **Evaluation page.**
- **One-click persona switch.**

**Student (implemented and browser-tested)**
- **My learning:** "Picked for you" tasks and assignment status.
- **Task studio, in five steps:**
  - Why this: a personal opener from her own earlier result.
  - Think first: locked once practice starts, enforced by the API with a 409.
  - Practise with help: real test runs, three progressive hints, an AI assistant.
  - Look back: before and after side by side.
  - Show it: labelled attempts, a persistent draft that never erases code, and "Independent check: no built-in hints or assistant".

**End-to-end journey.** All 15 acceptance steps passed through the real UI, from Layla through Sara and back to Evaluation (scripted Playwright run, Oct 31). The run included permission checks: Sara gets 403 on professor actions, and a request with no token gets 401.

| Capability | Kind |
|---|---|
| Test execution, rubric scoring from tests, probe evidence | Deterministic |
| Explanation reading (criteria, misconceptions with stance, contradictions, abstention) | **Live AI** (gpt-4.1-mini), validated |
| Conflict check, planning, insights, note check, item validation, verifier, next steps | Deterministic rules |
| Note drafting, new-check proposals, assistant chat | **Live AI** (gated: note check, sandbox validation, labelled) |
| Students, course, submissions | **Synthetic**, labelled |
| Classmates' follow-up attempts | **Simulated** on request, through the real verifier, labelled |
| Class grading shown in the demo | **Stored** output of a live AI run, not replayed |

**Not implemented:** real authentication, an LMS, material upload or retrieval, voice, multiple assignments with real data, a production sandbox, local models.

## 3. Technical architecture

| Component | Where |
|---|---|
| Backend | FastAPI, SQLAlchemy 2, Pydantic 2, SQLite (`backend/athar/`) |
| Frontend | React 18.3, TypeScript 5.6, Vite 5.4, Tailwind 3.4, TanStack Query 5, React Router 6 (`frontend/src/`) |
| Model | OpenAI `gpt-4.1-mini` via `chat.completions.parse`; Anthropic provider implemented. Reader prompt `reader-v3` |
| Model controls | 45 s timeout, call budget, cost ceiling, spend ledger, labelled rule fallback, `ATHAR_ANALYZER=llm` refuses fallback |
| Sandbox | Fresh `python -I` process, empty temp directory, CPU, memory, file-size and process limits, per-test alarm, wall clock. **Doesn't block network or filesystem reads**, so it's prototype-grade |
| State | Intervention state machine: draft → approved → active → completed / rejected. Approval and execution are idempotent |
| Authorization | HMAC-signed demo tokens, role checks on every route, ownership checks for courses and assignments, task access limited to the target student |
| Validation | Follow-up items are usable only if the reference solution passes and the misconception solution is caught by a probe |
| Audit trail | `audit_events` records demo login, grading start and finish, draft, approve, execute, simulate, follow-up submit, item generation and resets. It isn't yet visible in the UI |

## 4. Evaluation

**Completed experiments** (`backend/evals/results/*.json`)

| Set (n) | Reader | Misconception P / R / F1 | C3 | Other |
|---|---|---|---|---|
| final (36) | reader-v2 | 0.93 / 0.93 / **0.93** (13 TP, 1 FP, 1 FN) | 20/36 | quotes 101/101; verifier 11/12; routing 9/12 |
| final (36) | rules-v1 | 0.33 / 0.07 / **0.12** (1, 2, 13) | 14/36 | verifier 8/12; routing 9/12 (no reader 7/12) |
| final-2 (24) | reader-v3 | 0.69 / 1.00 / **0.82** (9, 4, 0) | 12/24 | working-code-confused 7/7; routing 15/24 |
| final-2 (24) | reader-v2 | 0.73 / 0.89 / 0.80 | 11/24 | 7/7; routing 16/24 |
| final-2 (24) | reader-v3-blind | 0.69 / 1.00 / 0.82 | 14/24 | routing 17/24 (ablation, not default) |
| final-2 (24) | rules-v1 | 0.60 / 0.33 / 0.43 | 12/24 | 2/7; routing 14/24 |
| held-out (32) | reader-v2 | F1 0.96 | 15/32 | **development numbers for the LLM** (failures informed the prompt) |
| dev (114) | reader-v2 / rules | F1 0.79 / 0.90 | 86 / 106 | rules optimistic by construction |

Deterministic results: item validator 6/6 (final), 8/8 (held-out), 15/15 (dev). Held-out code grading: exact misconception set 18/20, base-case criterion 20/20. Synthetic class, "stops by itself": 20 planted, 45 flagged, 20 correct, 41 flagged after the conflict check.

**Frozen inputs.** `FREEZE.json` records model, prompt, validator, verifier, planning and dataset hashes (frozen at `6498ae8`). The final and final-2 sets were committed before any run. The final run used reader-v2 because that was the frozen version. reader-v3 was chosen on dev evidence, and only final-2 measures it untouched.

**Known methodological weaknesses**
- **Labels:** one author wrote and labelled every case. Small sets (36, 24). One topic (recursion base cases). Synthetic phrasing.
- **Final-2 timing:** final-2 was written after reader-v2's results were seen. It's untouched for every reader, but not blind to the kinds of errors v2 made.
- **One run per configuration:** results are single runs at provider-default sampling. On the class, two runs of v3 flagged 39 and 45, so expect variance on the small sets.
- **Conflict check:** designed after seeing one case, and measured only on the synthetic class, not on a frozen set.
- **Never measured:** real student text, inter-annotator agreement, learning outcomes, professor time saved, local models, Arabic or code-switched explanations at scale.

**Failure modes seen:** C3 over-caution (0/10 correct paraphrases fully correct), C3 on negation 0/4, anchoring on failing code (the blind ablation is better on C3), over-flagging, run-to-run variance, one long note (fixed by the schema change and note check), one AI-generated check rejected by the validator (working as intended).

## 5. Reliability

| Check | Result at this checkpoint |
|---|---|
| Backend tests | `pytest -q`: see §9 |
| Frontend type check and production build | See §9 |
| Browser-tested paths | 15-step journey, Layan conflict view, note editor gate, keyboard focus visible on all tabbable elements on 6 main screens, 0 px sideways overflow on 7 mobile screens |
| Error handling | Provider timeout, malformed output, refusal, budget and outage are covered by mocked tests; the UI shows error states; page error boundary |
| Duplicate prevention | Draft, approve and execute are idempotent (tested; repeat approve created 0 extra tasks in the browser run) |
| Recovery | `athar.cli reset-interventions` (free, rebuilds insights from stored evidence); backup of the AI-graded database in `backend/data/backups/` (git-ignored) |

**Remaining bugs and rough edges**
1. The AI reading's own wording can be awkward or long. It's folded behind *Full AI reading*.
2. Mobile tables (all submissions, evaluation details) scroll inside their own box.
3. Drafts in *Show it* live in browser storage, so they don't follow the student to another device.
4. The audit trail isn't shown in the UI.
5. No screen-reader pass beyond labels, focus rings and `aria-current`.
6. The C3 judgment is too cautious, which sends some students who understand to an extra short task.

## 6. Privacy and security

| Item | Status |
|---|---|
| Secrets | `backend/.env` is git-ignored and mode 600. `.env.example` has empty placeholders only. The key is never sent to the frontend |
| Git history scan | `git log --all -p` for key patterns (`sk-…`): see §9 |
| Data sent to the AI provider | Rubric, misconception list, student code, test outcomes and explanation, with **no names or IDs**. Assistant chat sends the student's messages. Note drafting sends anonymised evidence lines |
| Stored locally | SQLite database and backups (git-ignored), spend ledger (committed, no content), `review-package/` (git-ignored) |
| Production gaps | Demo sign-in only, no encryption at rest, no retention policy, process-level sandbox, no rate limiting, no data-processing agreement |

## 7. GitHub readiness

| Item | Status |
|---|---|
| Structure | `backend/`, `frontend/`, `docs/` (with `assets/`), README at the root |
| README | Rewritten for judges and developers. Images use relative paths in `docs/assets/`, with charts in light and dark versions through `<picture>`. Mermaid diagrams render natively on GitHub |
| Setup | Commands checked against the repository (`requirements.txt`, `package.json` scripts, `athar.cli`, `evals.run`) |
| History | ✅ Cleaned before publishing. `git filter-branch` removed only `athar-review-package.zip` and `athar-review-package/` (old local review copies) from history. Commits before `41c5798`, including every evaluation run and freeze commit, keep their original SHAs. The ten later commits got new SHAs, and their references in the docs were updated. The untouched full history is kept locally as a git bundle and the tag `local-backup-before-history-cleanup` (not pushed). The largest published object is 0.3 MB |
| Licence | ❌ None. **Decision needed** (MIT is common for hackathons) |
| Private files | `.env`, `backend/data/`, `review-package/`, `athar-review-package*`, `node_modules/`, `.venv/` are all ignored |
| A judge without a key | ✅ `athar.cli reset --replay` seeds the synthetic class, runs the real tests and replays the 114 recorded reader-v3 outputs (`backend/athar/seed/recorded_readings.json`), labelled *recorded, replayed*. Checked to reproduce the live run's evidence row for row; covered by `tests/test_replay.py` |

## 8. Judging readiness

| Criterion | Evidence | Strongest | Weak or unproven | A judge can inspect |
|---|---|---|---|---|
| **1. Task performance** | Full loop works in the browser; F1 0.93 vs 0.12; 7/7 vs 2/7; verifier 11/12 | The AI finds what tests can't, measured on untouched sets | C3 20/36; over-flagging; synthetic only | `evals/results/`, the Evaluation page, the 15-step journey |
| **2. Robustness and adaptation** | Seven-group routing; abstention; conflict check; validator rejecting an AI check; 752 calls with 0 failures; mocked failure tests | Different needs → different actions, and disputed evidence → human | Run-to-run variance; real-world text unseen | `planning.py`, `disputes.py`, the review queue, tests |
| **3. Evaluation and iteration** | Four splits, freeze hashes, baselines, ablation, v3.1 rejected, failures per case | Discipline: sets written and frozen before runs, honest reporting of dev vs untouched | One annotator, small n, single runs | `FREEZE.json`, `git log -- backend/evals/datasets`, `EVALUATION.md` |
| **4. Technical judgment and creativity** | LLM only for language; sandbox for facts; quote verification; approval gate; independent check after assisted practice; conflict check without retuning | Separating assistance from evidence | Local-model privacy path untested | `ARCHITECTURE.md` design decisions, README §6–§9 |
| **5. Engineering quality** | 62 tests, type-check, build, idempotency, state machine, audit events, cost controls | Tests can never call a live model; permission gates tested | Prototype sandbox and auth; SQLite | `backend/tests/`, `provider.py`, `sandbox.py` |
| **6. Communication** | README, walkthrough, honest labels in the UI (synthetic, simulated, AI suggestion) | Every AI output labelled; limitations stated first | Video and slides not yet made | README, the app itself |

**Prioritised blockers**
1. Licence decision.
2. Repository name, visibility and history decision. Then publish.
3. Record the demo video (≤ 3 min) and add the link.
4. Make 8–10 slides and add the link.
5. Submit with the correct challenge before 8:00 PM Saudi time.

**Optional improvements, if time allows**
1. ~~Database snapshot so judges see AI evidence without a key.~~ Done as the replay mode (`reset --replay`).
2. `docs/EVALUATORS.md`, a five-minute path.
3. Local-model measurement on the frozen sets (free in API cost, about 1–2 h compute plus a download).

## 9. Verification at this checkpoint

| Check | Result |
|---|---|
| Backend tests | `pytest -q`: **62 passed** |
| Frontend | `tsc -b --noEmit` clean; `vite build` succeeds |
| README and docs links, image and chart paths | All relative links resolve (scripted check); both Mermaid diagrams render (mermaid 10.9) |
| Secrets in history | `git log --all -p` key-pattern matches: **0**. No `.env` or `.db` tracked |
| Frozen evaluation inputs | `git diff 7869292 -- backend/evals/datasets backend/evals/FREEZE.json`: **no changes**. Committed `results/*.json` unchanged |
| Demo grading | Preserved. Interventions reset with `reset-interventions` (free) after the screenshot run |
| HADIR | `git status` clean; last commit Oct 30 |
| Spend | This audit made two live calls (note draft and Sara's check, about $0.005) for the README screenshots. No regrading, no model downloads |

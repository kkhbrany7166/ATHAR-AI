# ATHAR against the judging criteria

Every number here comes from `docs/EVALUATION.md` (generated from `backend/evals/results/*.json`) and was measured with live
`gpt-4.1-mini` calls on Oct 31, 2026. Configuration, prompt hashes and dataset hashes are recorded in `backend/evals/FREEZE.json`.

**The question ATHAR answers:** a student submits working code, but do they understand why it works?

## 1. Task performance

The headline is the AI reader on sets nothing was tuned on.

| Untouched set | Measure | Rule reader | AI reader |
|---|---|---|---|
| Final (36 explanations) | Misconception F1 (tp/fp/fn) | 0.12 (1/2/13) | **0.93 (13/1/1)** |
| Final | "Stops after the smallest input" found | 1/7 | **7/7**, 0 false alarms |
| Final | "Stops on its own" found | 0/7 | **6/7**, 1 false alarm |
| Final | Negation: no misconception wrongly attributed | 3/4 | **4/4** |
| Final | Verifier outcome (sandbox tests + reading + rules) | 8/12 | **11/12** |
| Final-2 (24, code + explanation) | **Working code, confused reasoning caught** | 2/7 | **7/7** |
| Final-2 | Misconception F1 | 0.43 | **0.82** (reader-v3) |
| Final-2 | Right kind of help for the student | 14/24 | 15/24 (v3), 16/24 (v2) |
| All live runs | Evidence quotes verbatim in the student's text | — | 99–100% (the rest removed by validation) |

**Where the AI is weak** (also measured):
- **The stopping-condition judgment (C3)** is only 20/36 on final and 12/24 on final-2. The AI calls most correct explanations *partial* instead of *met*, so ATHAR under-certifies understanding and routes those students to a short explain-your-reasoning task. It errs towards caution, not harm, but it adds professor review.
- **Failing code makes it mark correct reasoning down.** It anchors on the code: final-2 case g09, and the student Layan in the browser test. *Handled downstream, not by changing the model:* a deterministic conflict check (`grading/disputes.py`) sets aside an AI misconception claim when the quoted sentence states the correct stopping condition (using the frozen rules-v1 phrase lists), or when the same reading says the student rejects that idea. Those students go to *Evidence conflicts: needs your review*, with no automated help, and the original AI output is kept. On the synthetic class this removes 4 of 25 extra "stops on its own" flags and moves 9 students to review; all 9 have no planted reasoning misconception, and recall stays 20/20. It was designed after seeing Layan and is measured only on the synthetic class. The frozen sets report the reader without it.
- **It gives different answers to the same prompt.** On the same 114 synthetic explanations, reader-v3 flagged "stops on its own" for 39 students on one run and 45 on another.

Deterministic parts on untouched data:
- Follow-up item validator: 6/6 (final) and 8/8 (held-out).
- Code grading on held-out programs: base-case criterion 20/20, exact misconception set 18/20.

## 2. Robustness and adaptation

- **Live:** 752 calls in the ledger, plus about 10 interactive browser calls, with 0 provider failures. Timeouts, malformed output, refusals, the budget ceiling and outages are covered by tests that use mocked providers, and each is recorded per submission. In "AI only" mode, failures never fall back to rules silently.
- **Language:** paraphrase, negation (recorded as *rejected ideas*), code-switching, terse notation, and vague answers (the AI abstained on 4 of the class's 114 explanations, with reasons).
- **Code and explanation disagreeing:** working code with confused reasoning is caught 7/7. Failing code with correct reasoning is a known weakness, flagged as a contradiction. Syntax errors go to *debugging*, never to a recursion misconception.
- **Activities:** the AI-generated check for "no progress" was rejected by the validator in the live run, and it can't be approved. Intervention drafts can exist without a check, but approval is blocked until a validated one is chosen.
- **Workflow:** duplicate drafts, approvals and executions are idempotent. All 60 backend tests pass.
- **AI-written notes:** a deterministic check (`interventions/note_check.py`) flags notes over 90 words, greetings, exclamation marks, lists, and reuse of the assignment's own functions. It never rewrites or truncates; approval is refused until the professor edits the note. Tested with a mocked over-long AI draft, with no paid call.

## 3. Evaluation and iteration

- **Five data sets, each with an explicit status:**
  - **dev:** generated; the rule reader was written from it.
  - **held-out:** informed the v2 prompt, so it is not unseen for the AI.
  - **final:** untouched, reader-v2.
  - **final-2:** written before v3 existed, untouched for v2 and v3.
  - **the synthetic class:** development data, scored against planted labels.
- **Iteration on development data only:**
  - **v2 → v3** raised recall on "stops on its own" in the class from 7/20 to 19/20, but precision fell.
  - **v3.1 was tried and rejected:** 25 extra flags against v3's 20. It stays recorded.
  - **v3 was chosen on development evidence before final-2 ran.**
- **Ablation:** reading the explanation without the code improved C3 (14/24 vs 12/24) and the action chosen (17/24 vs 15/24) on final-2. Because one final-2 case prompted that comparison, it is reported as an ablation, not deployed.
- **Reproducibility:** freeze record, spend ledger, regression deltas, per-case outputs and case-by-case failures.

## 4. Technical judgment and creativity

The full reasoning is in [ARCHITECTURE.md](ARCHITECTURE.md) → *Design decisions*.
- **The LLM is used only to read natural-language reasoning.** That's where rules fail: 0.12 vs 0.93 F1 on the untouched final set.
- **Code execution, probes, validation, diagnosis and verification are deterministic.** They decide what happens to students.
- **Misconception → validated new check:** an item is released only if correct code passes it *and* code holding the misconception fails it in the predicted way. AI proposals face the same gate, and in the live run the gate rejected one.
- **Assisted practice is separate from independent verification.** Outcomes come only from new, unsupervised attempts, and the verifier says *demonstrated* only when tests and reasoning agree. Its misses lean cautious.
- **No multi-agent framework.** One stateful workflow with focused model calls.

## 5. Engineering quality

- Module boundaries: `grading/`, `ai/`, `interventions/`, `insights.py`, `api/`.
- State persisted for every step, an audit trail, and roles and ownership enforced on the server.
- **Cost controls:**
  - 45 s timeout and one retry
  - per-process call budget and spending ceiling
  - an append-only spend ledger
  - tests can never call live models
- Secrets stay in `backend/.env`, which git ignores and the browser never sees.
- **Reproducible:**
  - `pytest` runs 55 tests
  - `npm run typecheck`, `npm run build`
  - `python -m evals.run` (`--final2 ...`)
  - `athar.cli reset --grade` (live: ≈ $0.22)
  - `athar.cli reset-interventions` (free)

## 6. Communication

[README](../README.md) (what is AI, rules or simulated) · [DEMO.md](DEMO.md) · [EVALUATION.md](EVALUATION.md) · the in-app **Evaluation** page, where every percentage shows its count.

## Honest disclosures

- **Everything is synthetic:** students, submissions and labels. One person wrote the labels, with no second annotator, and the sets are small (24–36 cases each).
- **The rule reader looks better on the demo class than it is,** because the class was generated from the templates it was written from. This matters less now that the class is read by the AI.
- **Simulated classmates** use the check's own reference and misconception solutions and short generic explanations.
- **Spend:** ≈ $1.34 in the ledger plus ≈ $0.02 outside it, under the $1.50 ceiling (`backend/evals/results/spend.jsonl`).
- **Not built:** material upload and retrieval, voice, LMS integration, real authentication.

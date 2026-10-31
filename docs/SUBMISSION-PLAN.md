# Submission plan (for approval, Oct 31)

> The storyboard and slide outline here are superseded by [STORY.md](STORY.md). The interview notes in §D still apply.

Nothing here has been built or recorded yet. Numbers come from the current app (commit `f9348d5`) and the stored evaluation results.

## A. Three-minute demo video: the real app, start to finish

Record at about 1360 px wide. Reset first with `reset-interventions` (free). Two steps make live model calls, about $0.005 in all: drafting the note and reading Sara's check. Everything else comes from stored results. One caption, ideally on screen, says so: *"Class grading was run earlier with gpt-4.1-mini and is shown from stored results. The note draft and Sara's check run live."*

| Time | Screen | What happens | Line (voice or caption) |
|---|---|---|---|
| 0:00–0:12 | Landing | The headline, then Noura's card: 10/10 tests, one quoted sentence | "Her code passes every test. Does she understand why it works?" |
| 0:12–0:40 | *Inspect the evidence*: Noura's submission | "What ATHAR noticed": test result, AI reading, the quote highlighted in her words; per-criterion *Accept / Change* | "Tests are facts. The AI reading is a suggestion, quoted word for word, and it counts only when the professor accepts it." |
| 0:40–1:00 | Assignment 3, *Who needs attention* | The queue; open *Evidence conflicts: needs your review* and then Layan | "When the evidence disagrees with itself, ATHAR doesn't guess. Layan's explanation is right and her code is wrong, so she goes to the professor, not to a lesson she doesn't need." |
| 1:00–1:25 | *Plan for 14*, then the draft | Note with "67 / 90 words", the validation pair (correct code passes, misconception code is caught), *Approve and send* → *Delivered · now* | "The AI drafts. A sandbox proves the new check can tell the difference. Nothing reaches students until she approves." |
| 1:25–2:15 | *See as Sara*, then the task | *Why this* (her own earlier result) → *Think first* → *Practise*: a failing run, one hint, a passing run → *Look back*: before and after → *Show it*: no hints, submit → *You showed it on this task* | "Help is part of practising and never counts against her. The proof is a new problem, done alone." |
| 2:15–2:35 | *See as Layla*, then the intervention | Sara: real student, demonstrated, before and after. Simulated classmates are counted separately | "The professor gets new evidence, not a claim, and real and simulated students are never mixed." |
| 2:35–2:55 | Evaluation | The three findings; open *Where the AI over-flags* | "Measured on sets nobody tuned on: 0.93 vs 0.12 F1 against rules, 7 of 7 working-code-confused-reasoning cases. And where it's weak: it over-flags, so every flag waits for a human." |
| 2:55–3:00 | Back to the landing page or the logo | "Behind every answer is a student." | |

**Fallback if a live call fails while recording:** the note falls back to the labelled template, and Sara's result would read *insufficient evidence*, which is honest. Re-record that scene after `reset-interventions`.

## B. Nine slides, one message each

| # | Message | Evidence on the slide |
|---|---|---|
| 1 | **A correct answer isn't always understanding.** | Noura's card: 10/10 tests beside one quoted sentence. Subtitle: "Behind every answer is a student." |
| 2 | **Professors can't read 120 explanations; tests can't read any.** | The gap: the synthetic class has 33 students who pass every test but whose explanation is flagged. Credit the professor's time, not the model. |
| 3 | **One loop: assess, understand, intervene, verify. The professor approves every step that matters.** | The loop diagram, with the approval gate and the independent check marked. |
| 4 | **The AI does only what needs language understanding.** | Architecture: sandboxed tests (deterministic) · LLM reader with verbatim-quote validation · fixed planning rules · sandbox-validated checks · rule-based verifier. AI vs deterministic in two colours. |
| 5 | **It works on data nobody tuned on.** | Final set (36 cases): misconception F1 0.93 vs 0.12 for rules. Final-2 (24 cases): working code + confused reasoning 7/7 vs 2/7. Untouched-set status. |
| 6 | **It fails safely.** | Abstains on thin answers (4 of 114); conflict check sends disputed flags to review (9 students, none planted with a reasoning misconception); notes over 90 words can't be sent; AI check rejected by the validator; 752 logged calls, 0 provider failures. |
| 7 | **We measured our own weaknesses and changed the design because of them.** | Over-flagging 45 vs 20 planted; stopping judgment 20/36 (too cautious); run-to-run variance (39 vs 45); reader-v3.1 tried and rejected; what each finding changed in the UI. |
| 8 | **Small, inspectable, cheap.** | About $0.002 per student reading; whole-class read ≈ $0.22; 60 backend tests; idempotent workflow; why no multi-agent framework. |
| 9 | **What's next, and what we won't claim.** | Real classroom pilot, second labeller, container sandbox, more languages. Limits: synthetic data, one labeller, unsupervised checks can't rule out outside help. Close on the tagline. |

## C. Repository readiness checklist

| Item | Status | Action |
|---|---|---|
| Secrets in the working tree | ✅ `.env` git-ignored (mode 600); only `.env.example` tracked | Re-run the scan just before publishing |
| Secrets in history | ✅ `git log --all -p` has 0 matches for key patterns | Same |
| Large files in history | ⚠️ A 39 MB review ZIP and a 74-file package folder were committed in `a81646a` and untracked in `58226e1` / `f9348d5` | **Your decision:** publish a fresh single-commit history (orphan branch), or keep the history. Both are under GitHub's 100 MB limit, but clones are about 80 MB |
| HADIR untouched | ✅ No changes; its last commit is Oct 30 | — |
| Setup commands | ✅ README "Run it" | Add the free path for evaluators **without** a key (below) |
| Evaluator without an API key | ⚠️ A fresh clone has no database. `reset --grade` without a key uses the rule reader, so the AI readings wouldn't appear | **Recommend:** commit a snapshot of the AI-graded synthetic class (no personal data, no keys), plus a `restore-snapshot` command, so judges see the stored AI evidence for free. Needs your OK |
| Tests | ✅ 60 backend tests pass; `tsc` clean; `vite build` passes | List the counts in the README |
| Evaluation reproducibility | ✅ `evals/report.py` rebuilds `EVALUATION.md` from stored results (free); `evals/run.py` re-runs live (costs money) | Say clearly in the README which one is free |
| Frozen datasets | ✅ `FREEZE.json` hashes; final and final-2 untouched | — |
| Evaluator guide | ⚠️ `docs/DEMO.md`, `JUDGING.md` and the review guide exist | Add a one-page `docs/EVALUATORS.md`: 5-minute path, what is live vs stored, costs |
| License | ❌ None | Choose one (MIT is typical for hackathons) |
| Demo Link field | — | The GitHub URL, plus the video link |

## D. Technical interview preparation

**Architecture in one breath.** FastAPI + SQLite backend and a React frontend. Student code runs in a subprocess sandbox with time and memory limits, and the test outcomes are facts. Explanations are read by gpt-4.1-mini through structured output, and every quote must appear word for word in the student's text or it's dropped. Fixed Python rules turn that evidence into groups and actions. The LLM drafts notes and can propose new checks; a check is usable only if the sandbox shows that correct code passes and misconception code fails. The professor approves; deterministic code executes. A rule-based verifier decides outcomes from a new, unassisted attempt.

**Evaluation, and why you can trust it.**
- **Splits:** dev (prompt work), held-out (looked at once), final (36 cases, frozen before any run), final-2 (24 code + explanation pairs, frozen).
- **Metrics:** micro precision, recall and F1 on misconception labels, accuracy on the stopping judgment, and the routing that results.
- **Baseline:** rules-v1, written from dev templates only.
- **Ablation:** reader-v3-blind.
- **What changed because of results:** reader-v3.1 was rejected; abstention was added; the UI was made honest about over-flagging.
- **Limits:** one labeller, synthetic text, small sets.

**Limitations to state before you're asked.**
- Over-flagging (45 vs 20 planted).
- It's too cautious on correct reasoning (stopping judgment 20/36).
- Run-to-run variance.
- The prototype sandbox isn't safe for real untrusted code.
- An unsupervised check can't rule out outside help.
- The conflict check was designed after seeing one case, and it is measured only on the synthetic class.

**Trade-offs you chose.**
- The LLM is used only for language. Execution is never done by the model.
- Approval gates are slower than automation, but safer for students.
- Caution over coverage: a wrong *demonstrated* is worse than *insufficient evidence*.
- No agent framework: a state machine with a few model calls is easier to test.
- gpt-4.1-mini for cost: about $0.002 per reading.

**What you personally need to be able to explain without notes.**
1. How quote validation works, and why it stops fabricated evidence.
2. The six planning categories and why *conflicting_evidence* sends students to review.
3. The verifier's three outcomes and why practice never counts.
4. What "frozen" means here and how `FREEZE.json` proves it.
5. Why F1 0.93 on 36 cases is promising but not conclusive.
6. What the spend ledger records (about $1.34 logged, about $1.46 in total).
7. How you'd take this to a real course: consent, a second labeller, a container sandbox, and measuring learning gains over time.

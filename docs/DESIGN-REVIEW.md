# Clarity pass: before and after (Oct 31, afternoon)

Before: `review-package/screenshots-after/` (design pass) · After: `review-package/screenshots-v3/` (1440 px desktop, 390 px mobile).
The question for every screen was: can a first-time judge say what it's for in about ten seconds?

| Screen | Before | After | How it helps a judge understand |
|---|---|---|---|
| **Type** | Inter + Source Serif; generic | IBM Plex Sans for UI, Newsreader for headings and student writing, Plex Mono for code, Plex Sans Arabic for أثر. Picked over two alternatives (`typography/`); lining numerals in the serif so scores line up | Student writing reads as writing and system text reads as UI, so whose words are on screen is obvious at a glance |
| **Landing** | A slogan and a classroom count | "A correct answer isn't always understanding." plus one real stored case: Noura's code passes 10/10, her sentence is quoted, "a flag is a question, not a verdict", *Inspect the evidence →* | The whole idea is shown with one concrete case in a few seconds, and one click lands on the evidence |
| **Course overview** | A dashboard of counts | "What needs your attention": drafts waiting, new results, the top four groups. Goals and materials are folded away | Answers "what do I do today?" first |
| **Who needs attention** | Group cards with long text | A review queue: count, plain title, a one-line evidence preview, evidence tags, the suggested action. A single amber line says flags can be wrong | Reads as a to-do list. False-positive risk is visible, not buried |
| **Submission review** (signature screen) | Three dense columns that opened on the AI's reading | "What ATHAR noticed" first: what the tests show, what the AI suggests, and the conflict between them (for Layan, the reader's own note that her *explanation is right and her code isn't*). Then explanation beside code, failing tests only, then the evidence and per-criterion Accept / Change / Why? | The student's work comes before the AI. A failing test isn't allowed to hide correct reasoning, and an AI suggestion never looks like a decision |
| **All submissions** | One very long table | Search, six filters with counts (needs review, tests failed, AI flagged, awaiting decision, reviewed), sorting, pages of 20; *Back* returns to the same page and filter | Any student can be found in a couple of clicks |
| **Intervention** | Flow strip plus 16 long rows | The flow strip marks the current stage ("· now"). Outcomes have search, real/simulated, outcome filters and paging. Only *demonstrated* gets the solid green; *still developing* is amber and *insufficient* neutral. Simulated classmates are counted separately | The approval gate and the verified/simulated split are visible at a glance |
| **Student studio** | Generic opener; first answer editable; the check editor reset to the starter after a result | A personal *Why this* from her own earlier result; *Think first* locks once practice starts (enforced by the API, 409); clearer practice failures ("should be … · your code gave …"); *Show it* lists labelled attempts (time, tests, what was submitted), keeps a draft per attempt, starts attempt 2 from attempt 1's code and says "Independent check: no built-in hints or assistant" | Assisted and independent work are clearly separate, and nothing the student wrote disappears |
| **Evaluation** | Headline figures plus many tables | Three numbered plain findings (0.93 vs 0.12 F1 on the untouched final set; 7/7 vs 2/7 working-code-confused-reasoning on final-2; over-flagging on the synthetic class). Datasets, metrics, failures and how to reproduce are in expandable sections | The claim, the proof and the weakness come first, and the detail is one click away |
| **AI note to students** | Could open with "Hello students!" and run long | The prompt allows at most 90 words, no greeting or headings, one idea, one tiny example, and ends with a question. Labelled "drafted with AI and approved by your professor" | The AI's voice is constrained and honestly labelled |

## Navigation map

```
Landing (/)
├─ Open the professor view → Courses (/p) → CS201 overview (/p/courses/1)
│   ├─ What needs your attention → drafts / results / groups
│   └─ Assignment 3 (/p/assignments/1)
│       ├─ Who needs attention (default)  → See the evidence → full evidence (/p/insights/:id)
│       │                                 → Plan for N → Intervention (/p/interventions/:id)
│       │                                     Evidence · Proposed support · Your approval · Delivered · Verified outcomes
│       ├─ All submissions (?tab=submissions&q&f&sort&page) → Review → Submission (/p/submissions/:id) → Back (same page)
│       └─ Rubric
│   Evaluation (/p/evaluation): three findings → expandable details
├─ Inspect the evidence (landing card) → Submission (/p/submissions/2)
└─ Open Sara's student view → My learning (/s)
    ├─ Picked for you → Task studio (/s/tasks/:id): Why this · Think first · Practise with help · Look back · Show it
    └─ Assignment 3 (her own submission and feedback once published)
Sidebar "Demo · switch view" swaps Layla ⇄ Sara from any page.
```

## Remaining bugs and weaknesses

1. ~~**The live AI note can overrun.**~~ Fixed after this review: the output schema had asked for "120-200 words", which contradicted the prompt. Notes are now checked (≤ 90 words, no greeting, lists or reuse of the assignment) and can't be approved until edited. The next live draft came out at 67 words. Original note: In the last live run it came out at 97 words (the limit is 90) and reused the assignment's own `power` example despite the instruction not to. The professor sees and edits it before approval, but nothing enforces the limit after the model returns.
2. ~~**The AI sometimes misattributes evidence.**~~ Handled after this review by a deterministic conflict check: the claim is labelled disputed, and the student goes to professor review. Original note: Layan (submission 46): the reader quotes a *correct* sentence as evidence of "stops after the smallest input". The top finding now surfaces the reader's own contradiction note, but the misconception tag is still applied.
3. ~~**"The reader thinks the student argues against: …"**~~ Reworded to "Ideas the reader judged the student does not hold". Original note: is awkward wording and can name an idea the student actually holds.
4. **Long AI readings** still make the evidence section long. It's folded behind *Full AI reading*, but the summary can be wordy.
5. **Over-flagging on the synthetic class** (45 flagged vs 20 planted for "stops by itself"). It's shown honestly on the queue and the Evaluation page, but not fixed.
6. **Mobile tables** (all submissions, evaluation details) scroll sideways inside their own box. The page itself has no horizontal overflow (checked: 0 px).
7. **Not done:** a keyboard-only walkthrough and a screen-reader pass beyond labels, focus rings and `aria-current` on the step bar.
8. **Drafts in *Show it*** are stored in the browser (localStorage), so they don't follow the student to another device.

## Verification

- Backend: `pytest`, **56 passed**, including the new `test_first_answer_locks_once_practice_starts`.
- Frontend: `tsc -b` clean; `vite build` succeeds.
- The full workflow (draft → approve → Sara's five steps → two attempts → simulate) ran once through the API for the screenshots. The changed screens were then recaptured **navigation-only**, with zero non-GET requests apart from the free demo login. The demo was then reset with `reset-interventions`, keeping the stored AI grading.
- The draft fix was checked in the browser: after attempt 1, the attempt 2 editor starts with attempt 1's code and explanation.
- **Spend:** the ledger shows about $1.34. Including calls outside the ledger the estimate is about $1.45 of the $1.50 ceiling. No paid calls were made after the screenshot workflow.

---

# Earlier: design pass, before and after (Oct 31, morning)

Before: `review-package/screenshots/` · After: `review-package/screenshots-after/` (same pages, 1440 px desktop and 390 px mobile).

| Change | Before | After | Criteria it serves |
|---|---|---|---|
| **Honest AI language** | "45 students … misconception"; the landing page said "Their explanations tell a different story." | "Flagged for review". Counts are split into *test result* vs *AI reading*, and the over-flagging is stated on the assignment and evidence pages. The landing page says "flagged their explanations for a closer look" | Task performance (claims match what was measured), Communication |
| **Four evidence kinds** | AI, test and professor evidence looked alike | Distinct tags everywhere: test result (slate), AI reading (amber, dashed), your decision (green), verified outcome (solid green, demonstrated only) | Technical judgment, Communication |
| **Assignment page** | Insights tab + Who-needs-what tab + a long duplicate support list | One "Who needs attention" view: four summary figures, one row per group with *why*, evidence type, proposed action, activity status, and a drill-down to students and the full evidence page | Communication, Robustness (different needs → different actions) |
| **Evidence review** | One narrow column | Three columns: their reasoning + AI reading / their code + what ran / your decisions (sticky). Plain criterion names, codes on hover | Communication, Engineering quality |
| **Plain language** | C1–C4, REC-1, MC-STOP-IMPLICIT in the main UI | "Smallest input", "Explains why it stops", "Thinks recursion stops by itself". Codes stay in tooltips | Communication |
| **Learning studio** | Five long stacked sections; progress hidden on mobile | A step bar on every screen size, one step in view at a time, free revisiting, before/after answers side by side, reflection optional, the independent check visibly separated | Communication (assisted vs independent) |
| **Intervention page** | A status rail and one-line rows | A flow strip (evidence → plan → your approval → delivered → verified), a validation pair (correct passes / misconception caught), before (Assignment 3 + assisted practice) vs after (independent check) per student | Technical judgment, Robustness |
| **Evaluation** | Tables only | Headline AI-vs-rules figures with their sets, a dataset table with untouched status, the iteration note, and the synthetic class's over-flagging computed live from stored readings | Evaluation & iteration, Communication |
| **Accessibility** | 11 px labels, dim captions, wrapping code | 12 px minimum, higher contrast, focus rings kept, step bar `aria-current`, labelled legend, no wrapping in the code editor, no sideways scroll on mobile (checked) | Engineering quality |
| **Review support** | Port 8710 showed `{"detail":"Not Found"}`; switching roles meant signing out | The API root points to the app; one-click "Demo · switch view" | Engineering quality |

## Remaining weaknesses (seen in the after screenshots)

1. **The submission page is still long** when the AI writes a long reading. The three columns help, but "How the AI read it" can be verbose.
2. **The assignment header repeats counts:** the grading strip (submitted / prepared / need review / published) sits above the four new figures. One of them could be folded away.
3. **The intervention student list is long** (16 rows). It has filters but no "needs your action first" ordering.
4. ~~The student check editor didn't keep the last attempt's code.~~ Fixed in the clarity pass.
5. **The AI's own wording is sometimes dubious.** For example, "ideas the student rejects" can list an idea the student actually holds. It's labelled as an AI suggestion, but it still reads oddly.
6. **Mobile tables** (all submissions, evaluation) scroll sideways inside their container. They're usable, but not designed for phones.
7. **Not done:** a keyboard-only walkthrough and a screen-reader pass beyond labels and focus rings.

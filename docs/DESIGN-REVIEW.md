# Design pass: before and after (Oct 31)

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
4. **The student check editor doesn't keep the last attempt's code** after a result, so it resets to the starter.
5. **The AI's own wording is sometimes dubious.** For example, "ideas the student rejects" can list an idea the student actually holds. It's labelled as an AI suggestion, but it still reads oddly.
6. **Mobile tables** (all submissions, evaluation) scroll sideways inside their container. They're usable, but not designed for phones.
7. **Not done:** a keyboard-only walkthrough and a screen-reader pass beyond labels and focus rings.

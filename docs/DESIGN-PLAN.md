# Design plan: from developer dashboard to a teaching workspace

The "before" screenshots are in `review-package/screenshots/` (taken Oct 31, 10:00). Each change lists the judging criteria it serves.

## Problems seen in the current screens

| # | Problem | Where (before screenshot) |
|---|---|---|
| 1 | AI flags read as facts: "45 students … misconception" | 04-prof-assignment-insights, 08-…stops-on-its-own, 01-landing |
| 2 | Insights and Who needs what repeat the same students. A long "may need support" list duplicates the groups | 04, 05 |
| 3 | Internal codes in the main UI: C3, REC-1, MC-STOP-IMPLICIT | 06-prof-submissions, 09, 10 |
| 4 | Submission review is one narrow column. Code, explanation, AI reading and decisions can't be compared side by side | 10, 11, 12 |
| 5 | The student task is a long five-section form, and progress is hidden on mobile | 20, 21, 22, m07 |
| 6 | No visual of the loop. Validation is only text | 16b, 18, 23 |
| 7 | Evaluation reads as one table; the over-flagging on the synthetic class isn't shown | 13 |
| 8 | Small grey uppercase labels, borderline contrast | throughout |

## Direction

- **One question per screen.** The assignment page answers "Who needs my attention, and why?"; the submission page answers "What does this student's work show?"; the student page answers "What do I do now?".
- **Four evidence kinds, always visibly different:**
  - *Test result* (deterministic, slate)
  - *AI reading* (a suggestion, amber, dashed edge)
  - *Your decision* (forest green)
  - *Verified outcome* (a solid green mark)
- **Plain language first, technical identifiers in details.**
- **Editorial, not dashboard:** serif headlines, hairline rules, a wider canvas where comparison matters, no new cards or charts unless they show a real relationship.

## Changes, in order

1. **Honest AI language** (Task performance, Communication). Counts become "flagged for review", split by test vs AI evidence, with the measured over-flagging stated where it matters.
2. **A merged "Overview" tab** (Communication, Technical judgment). One list of student groups answering *who needs attention*. Each group shows its evidence type, a proposed action, its activity status, and a drill-down to students and to the full evidence page. The duplicate support list is removed.
3. **Wide evidence review** (Communication, Engineering quality). Three columns: reasoning (explanation + AI reading), code + tests, your decisions. Plain criterion names, codes on hover.
4. **Learning studio** (Communication). A step bar, one step in view at a time, free movement between steps, and progress visible on mobile.
5. **Meaningful visuals** (Technical judgment, Robustness). A flow strip from evidence → plan → approval → delivered → verified, a before/after comparison per student, and a validation pair (reference passes / misconception fails).
6. **Evaluation** (Evaluation & iteration). A dataset table with sizes and status, the iteration log (v2 → v3, v3.1 rejected), and the synthetic-class over-flagging computed live from stored data.
7. **Accessibility** (Engineering quality). A minimum text size, contrast, focus rings, labels and touch targets.

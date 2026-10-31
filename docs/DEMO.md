# Three-minute demo: "A student submits working code. But do they understand why it works?"

**Before recording**
- Run `cd backend && .venv/bin/python -m athar.cli reset-interventions`. It's free and keeps the live AI grading of the class.
- A full re-grade (`reset --grade`) makes about 114 live calls (≈ $0.22). Only run it if the class data was lost.
- Use a browser window about 1360 px wide at 100–110% zoom, so the text is readable in the video.
- Every person is fictional. Keep the "Synthetic" tags visible.

| Time | Screen | Show | One line on screen or voice |
|---|---|---|---|
| 0:00 | Landing | "A correct answer isn't always understanding." and the stored example card (Noura, 10/10 tests, a flagged sentence) | *Their code works. ATHAR flags the explanations a professor should read.* Say "flags for review": on this synthetic class about 20 of the flagged cases match the planted labels, and the rest are false or debatable flags (reader-v3 precision ≈ 0.44 here). |
| 0:15 | Assignment 3 → Who needs attention | "Believes recursion stops on its own": the count and the "working code, confused reasoning" figure | *The tests pass. The AI read 114 explanations, quoting each one word for word.* |
| 0:30 | Landing card → *Inspect the evidence*, or a queue row → *See the evidence* | "What ATHAR noticed": the test result, the AI reading and any conflict, then explanation beside code | *Every claim links to the student's own words. AI suggests; it never grades alone.* |
| 0:50 | The groups on the same tab | Groups: concept gap, working code with confused reasoning, code that didn't run, demonstrated, no submission | *Different needs, different help. Syntax errors get debugging, not a lecture. Students who showed understanding get nothing extra.* |
| 1:10 | *Plan for 16* on the smallest-input group → **Show solutions and tests** | The validated check: correct code passes, misconception code fails | *The new check is proven to separate understanding from the misconception before any student sees it.* |
| 1:25 | **Approve and send** | The flow strip moves to *Delivered* ("· now"), 16 tasks | *Nothing reaches students until the professor approves.* |
| 1:35 | Sara → *Picked for you* → *Why this* | Her own earlier result, then *Think first* (locked once practice starts), a failing practice run, a hint | *Help is part of practice and is never held against her.* |
| 2:10 | Sara → *Show it* (on your own) | Submit the solution below → *You showed it on this task* | *Tests run in a sandbox, AI reads the reasoning, and rules decide. With caveats: one task, unsupervised.* |
| 2:25 | Layla → the intervention | Sara verified, before and after, next steps | *The professor sees new evidence, not a claim.* |
| 2:40 | **Evaluation** | The three numbered findings: AI 0.93 vs rules 0.12 F1 on the final set, 7/7 vs 2/7 on final-2, and the over-flagging. Open one detail section only if there's time | *Measured on cases nothing was tuned on, including where it's still weak.* |

**Optional cuts** if there's time, otherwise use them in the slides:
- **Abstention:** submission 29 (Tariq), where the AI declines to judge a one-line answer.
- **Rejected AI check:** draft the "no progress" group, then *Generate a new check with AI*. The validator rejects it.

**Sara's follow-up**

```python
def repeat_text(s, n):
    if n == 0:
        return ""
    return s + repeat_text(s, n - 1)
```

*"It stops when n is 0 and returns an empty string, because repeating something zero times gives nothing. Each call lowers n by one, so for any n >= 0 it always reaches 0. So repeat_text("ab", 0) is ""."*

Sara's submission makes one live call (≈ $0.002). The model's reading can vary between runs. In rehearsal this explanation was judged *met* and Sara reached *demonstrated*.

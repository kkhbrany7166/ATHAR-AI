# Three-minute demo path

Reset first: `cd backend && .venv/bin/python -m athar.cli reset --grade`, then open http://localhost:5710.
Without an API key the explanations are read by the rule reader, and every screen says so. Say it out loud too.

| Time | Screen | What to show | What to say |
|---|---|---|---|
| 0:00 | Landing | Headline, "A moment in the classroom" | Behind every answer is a student. This finding is computed from the class's (synthetic) work. |
| 0:15 | Professor → Assignment 3 → Insights | The smallest-input insight: quotes, test comparison, evidence that disagrees | Grades hide this: most of this code passes typical tests. Every number links to student work. |
| 0:40 | **Who needs what** tab | Groups: concept gap, working code with confused reasoning, syntax errors, demonstrated | Different difficulties get different help. Syntax errors get a debugging exercise, not a recursion lecture. Students who demonstrated it get nothing extra. |
| 1:00 | Draft for the concept group → intervention draft | Editable text, "Show solutions and tests", "Generate a new check with AI" | The follow-up check is validated in the sandbox: correct code passes, and code with the misconception fails. AI proposals face the same gate. |
| 1:20 | Approve and send | Status rail → *Delivered* | Nothing reached students before this. Approving twice changes nothing. |
| 1:35 | Sara → Picked for you | Her own earlier error, think first, a practice run, a hint | Help is part of practice and is never held against her. |
| 2:10 | Sara → Show what you can do | Submit the solution below → result card | Demonstrated *on this task*, with caveats: unsupervised, one task. |
| 2:25 | Layla → Intervention → Simulate classmates | Outcome counts, per-student before and after, next steps | Outcomes come from explicit rules. Classmates are simulated and labelled. |
| 2:45 | Evaluation | Final-set table and the ablation | Measured, with counts. The rule reader fails on paraphrase, which is exactly the job for the AI reader. We report it rather than hide it. |

Sara's follow-up:

```python
def repeat_text(s, n):
    if n == 0:
        return ""
    return s + repeat_text(s, n - 1)
```

*"It stops when n is 0 and returns an empty string, because repeating something zero times gives nothing. Each call lowers n by one, so it always reaches 0."*

If a key is configured, also show a submission's **How the explanation was read** panel: the summary, rejected ideas, abstention, and what validation removed.

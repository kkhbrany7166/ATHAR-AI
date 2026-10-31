# Three-minute demo path

Reset first: `cd backend && .venv/bin/python -m athar.cli reset --grade`, then open http://localhost:5710.

| Time | Screen | What to show | What to say |
|---|---|---|---|
| 0:00 | Landing | The headline and "A moment in the classroom" | Behind every answer is a student. This number is computed from the class's real (synthetic) submissions. |
| 0:20 | Professor → Assignment 3 | The grading panel and the insight list | 114 submissions ran against tests in a sandbox. Explanations were read too, and the panel says honestly by what. |
| 0:40 | Insight: smallest input | Figures, quotes, test comparison, "evidence that disagrees" | Every number links to student work. Two students passed every test but explained it wrong, which grades alone would hide. |
| 1:10 | Draft an intervention | The editable explanation, the validated follow-up check, "Show solutions and tests" | ATHAR checked this new problem in the sandbox: correct code passes, and code with the misconception fails. |
| 1:30 | Approve and send | The status rail moving to *Delivered*, 18 tasks | Approval creates real records. Nothing reached students before this. |
| 1:45 | Sara → Picked for you | Why this, think first, practice with a failing test, a hint | Help is part of practice. Her own earlier error is shown back to her. |
| 2:20 | Sara → Show what you can do | Submit `repeat_text`, the result card | Demonstrated *on this task*, with caveats: unsupervised, one task. |
| 2:35 | Layla → Intervention | Simulate classmates, then the outcome counts and next steps | Outcomes come from explicit rules. Still-developing students get a suggested next step. |
| 2:50 | Evaluation | Held-out vs dev table | Deterministic parts generalise. The rule reader doesn't, which is exactly the job for the LLM. We report it plainly. |

Working follow-up for Sara:

```python
def repeat_text(s, n):
    if n == 0:
        return ""
    return s + repeat_text(s, n - 1)
```

Explanation: *"It stops when n is 0 and returns an empty string, because repeating something zero times gives nothing. Each call lowers n by one, so it always reaches 0."*

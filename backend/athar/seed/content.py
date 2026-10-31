"""Course content for the CS201 demo: objectives, misconception hypotheses, assignment, rubric, tests.

This is what a professor would author (or import) with an assignment. None of it states which
students hold which misconception; that is computed from submissions.
"""

COURSE = {
    "code": "CS201",
    "title": "Introduction to Programming",
    "term": "Fall 2026",
    "description": "Foundations of programming in Python: control flow, functions, recursion, and data structures.",
}

OBJECTIVES = [
    {
        "code": "REC-1",
        "title": "Define stopping conditions that cover every smallest valid input and return the correct value",
        "description": "A base case is the answer to the smallest sub-problem. It must be reachable for every valid input, including empty and zero-sized ones.",
    },
    {
        "code": "REC-2",
        "title": "Make every recursive call progress toward a base case",
        "description": "Each call must work on a strictly smaller problem so the recursion is guaranteed to stop.",
    },
    {
        "code": "REC-3",
        "title": "Explain how a recursive computation unfolds and how results combine as calls return",
        "description": "Trace the chain of calls down to the base case and the chain of returns back up.",
    },
]

MISCONCEPTIONS = [
    {
        "objective": "REC-1",
        "code": "MC-BASE-SMALLEST",
        "title": "Stopping condition does not cover the smallest valid input",
        "description": "The base case is placed at a later point (for example exp == 1, or a one-element list), so the smallest valid input (exp == 0, an empty list) recurses past it or crashes.",
        "why_it_matters": "This code passes most typical tests, so grades alone hide it. Students who believe recursion 'stops at the last real item' will struggle with empty structures, trees and divide-and-conquer later in the course.",
    },
    {
        "objective": "REC-1",
        "code": "MC-BASE-VALUE",
        "title": "Base case returns the wrong value",
        "description": "The stopping condition is in the right place but returns a value that is not the identity of the combining operation (for example 0 for a product or None for a sum).",
        "why_it_matters": "It suggests the base case is seen as a stop signal rather than as the answer to the smallest sub-problem.",
    },
    {
        "objective": "REC-1",
        "code": "MC-STOP-IMPLICIT",
        "title": "Believes recursion stops on its own, or because of 'return'",
        "description": "The explanation attributes termination to the function running out of work, reaching the end, or simply returning, rather than to an explicit condition checked before the recursive call.",
        "why_it_matters": "Students with this belief can write working code by pattern-matching, but cannot design stopping conditions for unfamiliar problems. It is invisible to tests.",
    },
    {
        "objective": "REC-2",
        "code": "MC-NO-PROGRESS",
        "title": "Recursive call does not move toward the base case",
        "description": "The recursive call is made on the same (or a larger) input, so the base case is never reached.",
        "why_it_matters": "Indicates the student has not connected 'smaller sub-problem' with termination.",
    },
]

ASSIGNMENT = {
    "title": "Assignment 3 — Recursion: power and sum_list",
    "kind": "assessment_check",
    "conditions": "unsupervised",
    "ai_policy": "Take-home and unsupervised. You may ask an AI tool conceptual questions; disclose any use. Code and explanation must be your own work.",
    "prompt": (
        "Write two recursive functions. Do not use loops or built-ins such as sum() or **.\n\n"
        "1. power(base, exp) returns base raised to exp, for any integer base and any integer exp >= 0.\n"
        "2. sum_list(xs) returns the sum of a list of integers. The list may be empty."
    ),
    "explanation_prompt": (
        "In your own words (4-8 sentences): explain exactly when and why each function stops recursing, "
        "trace what happens when power(2, 3) is called, and say what sum_list([]) returns and why."
    ),
    "starter_code": "def power(base, exp):\n    pass\n\n\ndef sum_list(xs):\n    pass\n",
    "reference_solution": (
        "def power(base, exp):\n    if exp == 0:\n        return 1\n    return base * power(base, exp - 1)\n\n\n"
        "def sum_list(xs):\n    if not xs:\n        return 0\n    return xs[0] + sum_list(xs[1:])\n"
    ),
}

CRITERIA = [
    {"code": "C1", "title": "Correct results on general inputs", "method": "tests", "objective": "REC-2", "max_points": 4,
     "description": "Both functions return correct results for typical inputs, including negative numbers."},
    {"code": "C2", "title": "Base cases handle the smallest valid inputs", "method": "tests", "objective": "REC-1", "max_points": 2,
     "description": "power(x, 0) returns 1 and sum_list([]) returns 0."},
    {"code": "C3", "title": "Explains when and why the recursion stops", "method": "explanation", "objective": "REC-1", "max_points": 2,
     "description": "Identifies the explicit stopping condition for each function, explains why it is reached for every valid input, and why it returns the value it does."},
    {"code": "C4", "title": "Explains how results combine as calls return", "method": "explanation", "objective": "REC-3", "max_points": 2,
     "description": "Traces power(2, 3) down to the base case and back up, showing how each return value is combined."},
]

_SMALLEST_ERR = ["RecursionError", "IndexError", "Timeout"]
_NO_PROGRESS_ERR = ["RecursionError", "Timeout"]


def _general(name, fn, args, expected, hidden=False):
    return {"name": name, "function": fn, "args": args, "expected": expected, "criterion": "C1", "hidden": hidden,
            "probes": [{"misconception": "MC-NO-PROGRESS", "on": "error", "error_types": _NO_PROGRESS_ERR}]}


def _smallest(name, fn, args, expected, hidden=False):
    return {"name": name, "function": fn, "args": args, "expected": expected, "criterion": "C2", "hidden": hidden,
            "probes": [{"misconception": "MC-BASE-SMALLEST", "on": "error", "error_types": _SMALLEST_ERR},
                       {"misconception": "MC-BASE-VALUE", "on": "wrong_value"}]}


TESTS = [
    _general("power(2, 10) is 1024", "power", [2, 10], 1024),
    _general("power(3, 4) is 81", "power", [3, 4], 81),
    _general("power(-2, 3) is -8", "power", [-2, 3], -8),
    _general("power(5, 1) is 5", "power", [5, 1], 5),
    _smallest("power(2, 0) is 1", "power", [2, 0], 1),
    _smallest("power(9, 0) is 1", "power", [9, 0], 1, hidden=True),
    _general("sum_list([4, 1, 7]) is 12", "sum_list", [[4, 1, 7]], 12),
    _general("sum_list([10]) is 10", "sum_list", [[10]], 10),
    _general("sum_list([-3, 3, 5, 0]) is 5", "sum_list", [[-3, 3, 5, 0]], 5, hidden=True),
    _smallest("sum_list([]) is 0", "sum_list", [[]], 0),
]

LECTURE_NOTES = """Lecture 7 — Recursion

A recursive function solves a problem by calling itself on a smaller version of the same problem.
Every recursive function needs two parts:

1. Base case (stopping condition). An explicit check, made before any recursive call, that recognises
   the smallest version of the problem and returns its answer directly. The base case must be reachable
   for every valid input. For a function over non-negative integers the smallest input is usually 0;
   for a function over lists it is usually the empty list [].

2. Recursive case. Reduce the problem, call the function on the smaller input, and combine the result.
   Each call must make progress toward the base case, otherwise the recursion never stops and Python
   raises RecursionError.

The value returned by the base case matters. It is the answer to the smallest problem, and it must be
the identity of the combining operation: 1 for multiplication (x * 1 == x), 0 for addition (x + 0 == x).

Recursion does not stop "on its own", and it does not stop because a function returns. It stops because
a call reaches an input for which the base-case condition is true, and that call returns without
recursing. The pending calls then finish one by one, each combining the value it received.

Tracing factorial(3):
  factorial(3) waits on factorial(2)
  factorial(2) waits on factorial(1)
  factorial(1) waits on factorial(0)
  factorial(0) is the base case and returns 1
  factorial(1) returns 1 * 1 = 1
  factorial(2) returns 2 * 1 = 2
  factorial(3) returns 3 * 2 = 6
"""

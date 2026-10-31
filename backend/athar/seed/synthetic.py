"""Synthetic CS201 class: ~120 fictional students and their Assignment 3 submissions.

The generator deliberately plants a mix of code and explanation patterns so that we can check
whether ATHAR recovers them. The planted labels are written to `synthetic_labels`, which analysis
code never reads. Everything here is fictional.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

FIRST = [
    "Omar", "Noura", "Faisal", "Reem", "Yousef", "Lina", "Khalid", "Hessa", "Abdullah", "Maha", "Turki", "Dana",
    "Saud", "Joud", "Fahad", "Ghala", "Nasser", "Shahad", "Majed", "Raghad", "Ali", "Lama", "Hamad", "Rana",
    "Ibrahim", "Wafa", "Ziad", "Aseel", "Bader", "Haya", "Mohammed", "Layan", "Tariq", "Nada", "Adel", "Jana",
    "Daniel", "Priya", "Mateo", "Aisha", "Kenji", "Elena", "Samuel", "Mariam", "Lucas", "Hana",
]
LAST = [
    "Al-Qahtani", "Al-Otaibi", "Al-Ghamdi", "Al-Zahrani", "Al-Shehri", "Al-Dosari", "Al-Mutairi", "Al-Anazi",
    "Al-Shammari", "Al-Malki", "Al-Subaie", "Al-Rashidi", "Al-Juhani", "Al-Omari", "Al-Saud", "Al-Amri",
    "Haddad", "Nasser", "Rahman", "Okafor", "Tanaka", "Silva", "Kowalski", "Mensah", "Novak", "Farouk",
]

# ---------- code variants ----------

POWER = {
    "correct_a": "def power(base, exp):\n    if exp == 0:\n        return 1\n    return base * power(base, exp - 1)\n",
    "correct_b": (
        "def power(base, exp):\n    if exp == 0:\n        return 1\n    half = power(base, exp // 2)\n"
        "    if exp % 2 == 0:\n        return half * half\n    return base * half * half\n"
    ),
    "correct_c": "def power(base, exp):\n    # anything to the power 0 is 1\n    if exp <= 0:\n        return 1\n    else:\n        return base * power(base, exp - 1)\n",
    "smallest": "def power(base, exp):\n    if exp == 1:\n        return base\n    return base * power(base, exp - 1)\n",
    "smallest_b": "def power(base, exp):\n    # stop at the last multiplication\n    if exp == 1:\n        return base\n    else:\n        return power(base, exp - 1) * base\n",
    "value": "def power(base, exp):\n    if exp == 0:\n        return 0\n    return base * power(base, exp - 1)\n",
    "value_b": "def power(base, exp):\n    if exp == 0:\n        return base\n    return base * power(base, exp - 1)\n",
    "no_progress": "def power(base, exp):\n    if exp == 0:\n        return 1\n    return base * power(base, exp)\n",
}

SUM_LIST = {
    "correct_a": "def sum_list(xs):\n    if not xs:\n        return 0\n    return xs[0] + sum_list(xs[1:])\n",
    "correct_b": "def sum_list(xs):\n    if len(xs) == 0:\n        return 0\n    return xs[0] + sum_list(xs[1:])\n",
    "correct_c": "def sum_list(xs, i=0):\n    if i == len(xs):\n        return 0\n    return xs[i] + sum_list(xs, i + 1)\n",
    "smallest": "def sum_list(xs):\n    if len(xs) == 1:\n        return xs[0]\n    return xs[0] + sum_list(xs[1:])\n",
    "value": "def sum_list(xs):\n    if not xs:\n        return None\n    rest = sum_list(xs[1:])\n    return xs[0] + (rest or 0)\n",
    "no_progress": "def sum_list(xs):\n    if not xs:\n        return 0\n    return xs[0] + sum_list(xs)\n",
}

SYNTAX_ERROR = "def power(base, exp)\n    if exp == 0:\n        return 1\n    return base * power(base, exp - 1)\n\n" + SUM_LIST["correct_a"]

# ---------- explanation fragments ----------

STOP_SOLID = [
    "power stops when exp reaches 0, because that check happens before the recursive call and base**0 is 1. Every call lowers exp by one, so starting from any exp >= 0 we must hit 0.",
    "The base case for power is exp == 0, which returns 1 since any number to the zero power is 1. Because each call passes exp - 1, the exponent keeps shrinking until the base case is true.",
    "The recursion in power ends at an explicit condition: if exp is 0 we return 1 without calling again. Each step reduces exp, so it always gets there for non-negative exp.",
    "I check exp == 0 first. That is the smallest problem and its answer is 1 (multiplying by 1 doesn't change anything). Every recursive call uses a smaller exp so this condition is eventually reached.",
]
SUM_SOLID = [
    "sum_list stops when the list is empty and returns 0, because the sum of nothing is 0 and adding 0 doesn't change the total.",
    "For sum_list the base case is the empty list, which returns 0. Each call drops the first element, so the list always shrinks to [].",
    "sum_list([]) returns 0. The empty list is the smallest input, and 0 is the right answer because it is the identity for addition.",
]
TRACE_SOLID = [
    "Tracing power(2, 3): it calls power(2, 2), which calls power(2, 1), which calls power(2, 0). That returns 1, then power(2, 1) returns 2*1 = 2, power(2, 2) returns 2*2 = 4, and power(2, 3) returns 2*4 = 8.",
    "power(2, 3) waits on power(2, 2), which waits on power(2, 1), then power(2, 0) returns 1. On the way back up the results are multiplied: 2, then 4, then 8.",
    "For power(2,3) the calls go 3 -> 2 -> 1 -> 0. The exp=0 call returns 1, and each waiting call multiplies by 2 as it returns, giving 2, 4 and finally 8.",
]
STOP_IMPLICIT = [
    "The function keeps calling itself until there is nothing left to multiply, and then it stops on its own and gives back the answer.",
    "Recursion stops when the function hits the return statement, because return ends the function and so the calls stop.",
    "Python stops calling power once exp gets small enough, then all the answers come back together.",
    "It runs until it reaches the end of the problem, and at that point the recursion is finished so it returns the total.",
    "The return line is what makes it stop recursing. Without return it would keep going forever.",
]
SUM_IMPLICIT = [
    "sum_list works the same way, it keeps adding until it runs out of numbers and then it's done.",
    "sum_list([]) gives 0 I think because there's nothing in it, the function just ends.",
    "For sum_list the recursion finishes once all the elements have been used up.",
]
STOP_SMALLEST_BELIEF = [
    "power stops when exp is 1, because base to the power 1 is just base, so there is nothing left to multiply.",
    "The base case is exp == 1. That's the last multiplication, so we return base there instead of calling again.",
    "My recursion ends at exp == 1 since that is the smallest exponent where there is still a number to return.",
]
SUM_SMALLEST_BELIEF = [
    "sum_list stops when there is one element left and returns it. An empty list wouldn't really be passed in, since there would be nothing to sum.",
    "For sum_list the base case is a list with one item. sum_list([]) shouldn't happen, but if it did it would probably just return nothing.",
    "sum_list stops at the last element, because the last number is its own sum.",
]
TRACE_COMBINE_CONFUSED = [
    "power(2, 3) multiplies 2 three times right at the start and then each call returns the same 8 back up.",
    "When power(2,3) runs it does 2*2*2 immediately and the other calls just pass the answer along.",
]
VAGUE = [
    "It calls itself until it's done and then returns the answer.",
    "Recursion means the function calls itself. Mine works and passes the examples.",
    "power and sum_list use recursion to solve smaller problems until the answer is found.",
]

DISCLOSURES = ["", "", "", "", "Asked ChatGPT to explain what a base case is.", "Used an AI assistant to understand a RecursionError.", "Used AI to check my explanation wording."]


@dataclass
class Planned:
    code_pattern: str
    explanation_pattern: str
    code: str | None  # None => did not submit
    explanation: str
    disclosure: str


def _join(*parts: str) -> str:
    return " ".join(p for p in parts if p)


def _casual(rng: random.Random, text: str) -> str:
    if rng.random() < 0.25:
        text = text[0].lower() + text[1:]
    if rng.random() < 0.2:
        text = text.replace(", ", " ", 1)
    return text


def _plan(rng: random.Random, kind: str) -> Planned:
    c = rng.choice
    correct_power = POWER[c(["correct_a", "correct_a", "correct_b", "correct_c"])]
    correct_sum = SUM_LIST[c(["correct_a", "correct_b", "correct_c"])]
    solid = _join(c(STOP_SOLID), c(SUM_SOLID), c(TRACE_SOLID))
    disclosure = c(DISCLOSURES)

    if kind == "missing":
        return Planned("not_submitted", "none", None, "", "")
    if kind == "correct_solid":
        return Planned("correct", "solid", correct_power + "\n\n" + correct_sum, solid, disclosure)
    if kind == "correct_implicit":
        exp = _join(c(STOP_IMPLICIT), c(SUM_IMPLICIT), c(TRACE_SOLID) if rng.random() < 0.6 else "")
        return Planned("correct", "implicit_stop", correct_power + "\n\n" + correct_sum, exp, disclosure)
    if kind == "correct_vague":
        return Planned("correct", "vague", correct_power + "\n\n" + correct_sum, c(VAGUE), disclosure)
    if kind == "correct_combine":
        exp = _join(c(STOP_SOLID), c(SUM_SOLID), c(TRACE_COMBINE_CONFUSED))
        return Planned("correct", "combine_confused", correct_power + "\n\n" + correct_sum, exp, disclosure)
    if kind == "smallest_belief":
        which = c(["power", "sum", "both"])
        p = POWER[c(["smallest", "smallest_b"])] if which in ("power", "both") else correct_power
        s = SUM_LIST["smallest"] if which in ("sum", "both") else correct_sum
        stop = c(STOP_SMALLEST_BELIEF) if which in ("power", "both") else c(STOP_SOLID)
        summ = c(SUM_SMALLEST_BELIEF) if which in ("sum", "both") else c(SUM_SOLID)
        return Planned(f"base_smallest_{which}", "smallest_belief", p + "\n\n" + s, _join(stop, summ, c(TRACE_SOLID)), disclosure)
    if kind == "smallest_says_right":
        return Planned("base_smallest_power", "solid", POWER["smallest"] + "\n\n" + correct_sum, solid, disclosure)
    if kind == "correct_smallest_belief":
        return Planned("correct", "smallest_belief", correct_power + "\n\n" + correct_sum,
                       _join(c(STOP_SMALLEST_BELIEF), c(SUM_SMALLEST_BELIEF), c(TRACE_SOLID)), disclosure)
    if kind == "wrong_value":
        which = c(["power", "sum"])
        p = POWER[c(["value", "value_b"])] if which == "power" else correct_power
        s = SUM_LIST["value"] if which == "sum" else correct_sum
        exp = solid if rng.random() < 0.5 else c(VAGUE)
        return Planned(f"base_value_{which}", "solid" if exp == solid else "vague", p + "\n\n" + s, exp, disclosure)
    if kind == "no_progress":
        which = c(["power", "sum"])
        p = POWER["no_progress"] if which == "power" else correct_power
        s = SUM_LIST["no_progress"] if which == "sum" else correct_sum
        return Planned(f"no_progress_{which}", "vague", p + "\n\n" + s, c(VAGUE), disclosure)
    if kind == "syntax_error":
        return Planned("syntax_error", "solid", SYNTAX_ERROR, solid, disclosure)
    raise ValueError(kind)


# How many of the 119 non-persona students get each planted pattern.
DISTRIBUTION = {
    "missing": 6,
    "correct_solid": 52,
    "correct_implicit": 20,
    "correct_vague": 7,
    "correct_combine": 6,
    "smallest_belief": 13,
    "smallest_says_right": 2,
    "correct_smallest_belief": 2,
    "wrong_value": 6,
    "no_progress": 3,
    "syntax_error": 2,
}

SARA_CODE = POWER["smallest"] + "\n\n" + SUM_LIST["correct_a"]
SARA_EXPLANATION = (
    "My power function stops when exp is 1, because anything to the power of 1 is itself, so there is nothing "
    "left to multiply. sum_list stops when the list is empty and returns 0 because there is nothing to add. "
    "For power(2, 3): it returns 2 * power(2, 2), which is 2 * 2 * power(2, 1), and power(2, 1) returns 2, "
    "so the answer is 8. I don't think power ever needs to handle exp = 0 since there would be nothing to multiply."
)


def generate_class(seed: int = 201) -> tuple[list[str], list[Planned]]:
    """Return (student names, planned submissions) for the 119 synthetic non-persona students."""
    rng = random.Random(seed)
    kinds = [k for k, n in DISTRIBUTION.items() for _ in range(n)]
    rng.shuffle(kinds)
    names: list[str] = []
    seen = {"Sara Al-Harbi"}
    while len(names) < len(kinds):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        if name not in seen:
            seen.add(name)
            names.append(name)
    plans = []
    for k in kinds:
        p = _plan(rng, k)
        p.explanation = _casual(rng, p.explanation) if p.explanation else ""
        plans.append(p)
    return names, plans

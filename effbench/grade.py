"""Letter grade for a run's pass rate.

A >=95, B >=85, C >=70, D >=55, E >=40, F below, U = could not run
(no tasks completed — server unreachable, auth failure, etc).

Grades judge ACCURACY only. Speed is reported separately; a fast F is still
an F. Colour mapping lives in tokens.py (PASS/WARN/FAIL ramp) so both
surfaces stay in sync.
"""
from __future__ import annotations

GRADES = [
    ("A", 95, "pass"),
    ("B", 85, "pass"),
    ("C", 70, "warn"),
    ("D", 55, "warn"),
    ("E", 40, "fail"),
    ("F", 0, "fail"),
]


def grade_run(n_pass: int, n_total: int) -> dict:
    """Return {letter, tone, pct, label}. U when nothing ran."""
    if not n_total:
        return {"letter": "U", "tone": "ink_dim", "pct": None,
                "label": "not run — server unreachable or auth failed"}
    pct = 100.0 * n_pass / n_total
    for letter, floor, tone in GRADES:
        if pct >= floor:
            labels = {
                "A": "top-tier accuracy",
                "B": "good — minor gaps only",
                "C": "usable, with a fix target",
                "D": "noticeably gappy",
                "E": "struggling",
                "F": "accuracy fails the run",
            }
            return {"letter": letter, "tone": tone, "pct": round(pct, 1),
                    "label": labels[letter]}
    return {"letter": "F", "tone": "fail", "pct": round(pct, 1),
            "label": "accuracy fails the run"}

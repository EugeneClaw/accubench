"""Letter grade for a run's pass rate.

A ≥93 · B+ ≥87 · B ≥80 · C ≥70 · D ≥55 · E ≥40 · F below · U = not run.
(no tasks completed — server unreachable, auth failure, etc).

Grades judge ACCURACY only. Speed is reported separately; a fast F is still
an F. Colour mapping lives in tokens.py (PASS/WARN/FAIL ramp) so both
surfaces stay in sync.

Calibration note: local-quant frontier models (27B class on 24–32GB GPUs)
typically land 85–95% on this suite. The B+ tier exists so 'a couple of
format-only misses' doesn't read as 'needs a better model' — the verdict
text says what to do about the remainder.
"""
from __future__ import annotations

GRADES = [
    ("A", 93, "good"),
    ("B+", 87, "good"),
    ("B", 80, "pass"),
    ("C", 70, "warn"),
    ("D", 55, "warn"),
    ("E", 40, "fail"),
    ("F", 0, "fail"),
]

LABELS = {
    "A": "top-tier accuracy",
    "B+": "excellent — a handful of slips",
    "B": "good — minor gaps only",
    "C": "usable, with a fix target",
    "D": "noticeably gappy",
    "E": "struggling",
    "F": "accuracy fails the run",
}


def grade_run(n_pass: int, n_total: int) -> dict:
    """Return {letter, tone, pct, label}. U when nothing ran."""
    if not n_total:
        return {"letter": "U", "tone": "ink_dim", "pct": None,
                "label": "not run — server unreachable or auth failed"}
    pct = 100.0 * n_pass / n_total
    for letter, floor, tone in GRADES:
        if pct >= floor:
            return {"letter": letter, "tone": tone, "pct": round(pct, 1),
                    "label": LABELS[letter]}
    return {"letter": "F", "tone": "fail", "pct": round(pct, 1),
            "label": LABELS["F"]}

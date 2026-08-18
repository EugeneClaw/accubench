"""Letter grade for a run's pass rate.

A* ≥100 (perfect) · A+ ≥96 · A ≥93 · A− ≥90 · B+ ≥87 · B ≥80 · B− ≥75 ·
C+ ≥65 · C ≥55 · C− ≥45 · D ≥35 · F below · U = not run.

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
    ("A*", 100, "good"),
    ("A+", 96, "good"),
    ("A", 93, "good"),
    ("A−", 90, "good"),
    ("B+", 87, "good"),
    ("B", 80, "pass"),
    ("B−", 75, "pass"),
    ("C+", 65, "warn"),
    ("C", 55, "warn"),
    ("C−", 45, "fail"),
    ("D", 35, "fail"),
    ("F", 0, "fail"),
]

LABELS = {
    "A*": "perfect — every task correct",
    "A+": "near-perfect — one slip in fifty",
    "A": "top-tier accuracy",
    "A−": "strong — a few slips",
    "B+": "excellent — a handful of slips",
    "B": "good — minor gaps only",
    "B−": "solid — some real misses",
    "C+": "usable — real misses to chase",
    "C": "usable, with a fix target",
    "C−": "gappy — accuracy needs work",
    "D": "struggling",
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

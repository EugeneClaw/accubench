"""CSV export for Sheets, Excel, Numbers, or anything that likes CSV.

Three shapes:
- per-task: one row per (tag, task) — the spreadsheet pivot point
- per-run summary: one row per tag — recipe-level numbers
- compare: side-by-side per-task for two tags
"""
import csv
import statistics

from .explainer import for_task
from .ledger import aggregate


def export_per_task(records, path):
    """One row per (tag, task). Columns cover pass, t/s, eff, purpose, difficulty."""
    fieldnames = [
        "tag", "task", "category", "purpose", "difficulty",
        "pass", "tok_s", "wall_s", "accept_pct", "draft_n",
        "error", "grader_detail",
    ]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            purpose, difficulty, _ = for_task(r["task"])
            w.writerow({
                "tag": r.get("tag", ""),
                "task": r.get("task", ""),
                "category": r.get("category", ""),
                "purpose": purpose,
                "difficulty": difficulty,
                "pass": "1" if r.get("pass") else "0",
                "tok_s": r.get("tok_s", ""),
                "wall_s": r.get("wall_s", ""),
                "accept_pct": r.get("accept_pct", ""),
                "draft_n": r.get("draft_n", ""),
                "error": r.get("error", ""),
                "grader_detail": r.get("grader_detail", ""),
            })


def export_summary(records_by_tag, path):
    """One row per tag with the headline numbers."""
    fieldnames = [
        "tag", "n_tasks", "n_pass", "pass_rate", "raw_tps_median",
        "eff_tps", "accept_pct_median", "fit_band_lo", "fit_band_hi",
    ]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for tag, recs in records_by_tag.items():
            agg = aggregate(recs)
            w.writerow({
                "tag": tag,
                "n_tasks": agg.get("n", 0),
                "n_pass": agg.get("n_pass", 0),
                "pass_rate": agg.get("pass_rate", ""),
                "raw_tps_median": agg.get("raw_tps", ""),
                "eff_tps": agg.get("eff_tps", ""),
                "accept_pct_median": agg.get("accept_pct_median", ""),
                "fit_band_lo": agg.get("fit_band_lo", ""),
                "fit_band_hi": agg.get("fit_band_hi", ""),
            })


def export_compare(records_a, records_b, tag_a, tag_b, path):
    """Side-by-side per-task comparison. Columns: task, purpose, a_pass, a_tps, b_pass, b_tps, delta_tps."""
    fieldnames = [
        "task", "purpose", "difficulty",
        f"{tag_a}_pass", f"{tag_a}_tps",
        f"{tag_b}_pass", f"{tag_b}_tps",
        "tps_delta", "pass_delta",
    ]
    by_task_a = {r["task"]: r for r in records_a}
    by_task_b = {r["task"]: r for r in records_b}
    tasks = sorted(set(by_task_a) | set(by_task_b))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for tid in tasks:
            ra = by_task_a.get(tid, {})
            rb = by_task_b.get(tid, {})
            purpose, difficulty, _ = for_task(tid)
            at = ra.get("tok_s") or 0
            bt = rb.get("tok_s") or 0
            ap = 1 if ra.get("pass") else 0
            bp = 1 if rb.get("pass") else 0
            w.writerow({
                "task": tid,
                "purpose": purpose,
                "difficulty": difficulty,
                f"{tag_a}_pass": ap,
                f"{tag_a}_tps": round(at, 2) if at else "",
                f"{tag_b}_pass": bp,
                f"{tag_b}_tps": round(bt, 2) if bt else "",
                "tps_delta": round(bt - at, 2) if (at and bt) else "",
                "pass_delta": bp - ap,
            })
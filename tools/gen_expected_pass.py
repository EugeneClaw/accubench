#!/usr/bin/env python3
"""Regenerate effbench/expected_pass.json from the reference soak ledger.

Expected-pass = how the REFERENCE rig (RTX 5090, Qwen3.8-27B IQ4_XS, no-think)
did on each task across the 2026-08-17 soak (253 full cycles + 2 paired quick
cycles + baseline). A task the reference rig fails is marked expected:false —
a fail on YOUR rig for that task is normal, not news.

This is reference data for report badges, NOT a grader. Tasks, prompts and
graders are untouched. Rerun if a new suite task is added:

    python3 tools/gen_expected_pass.py [path-to-soak-results.jsonl]

Reads soak-results.jsonl + baseline.jsonl from the pre-rename archive if no
path is given; writes effbench/expected_pass.json next to the package.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.expanduser("~/Dev/llama-effbench")
OUT = os.path.join(HERE, "effbench", "expected_pass.json")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ARCHIVE, "soak-results.jsonl")
    recs = []
    for path in (src, os.path.join(ARCHIVE, "baseline.jsonl")):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                recs.extend(json.loads(l) for l in f if l.strip())

    stats = {}  # task -> [fails, total]
    for r in recs:
        if "task" not in r:
            continue  # heartbeat records
        s = stats.setdefault(r["task"], [0, 0])
        s[1] += 1
        if not r.get("pass"):
            s[0] += 1

    out = {
        "_doc": ("Reference pass/fail per task, from the 2026-08-17 soak "
                 "(253 full cycles + 2 paired quick cycles) on RTX 5090 + "
                 "Qwen3.8-27B IQ4_XS, no-think, temp 0. Used ONLY for report "
                 "badges: 'reference rig also fails this' context. Not a grader."),
        "_source": os.path.basename(src),
        "quick": {},
        "full": {},
    }
    for task in sorted(stats):
        fails, total = stats[task]
        bucket = "quick" if task.startswith("q-") else "full"
        out[bucket][task] = fails == 0  # expected to pass iff never failed

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    nq, nf = len(out["quick"]), len(out["full"])
    print(f"wrote {OUT}: {nf} full tasks, {nq} quick tasks")
    exp_f = [t for t, v in out["full"].items() if not v]
    exp_q = [t for t, v in out["quick"].items() if not v]
    print("expected-fail (full):", ", ".join(exp_f) or "none")
    print("expected-fail (quick):", ", ".join(exp_q) or "none")


if __name__ == "__main__":
    main()

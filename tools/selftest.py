#!/usr/bin/env python3
"""Self-tests for effbench. Run: python3 tools/selftest.py  (no pytest needed)."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from effbench.verify import grade, extract_code, _norm  # noqa: E402
from effbench.tasks import load_suite, validate_task  # noqa: E402
from effbench.ledger import aggregate, append_record, load_ledger  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL += 1
        print(f" FAIL {name}  {detail}")


def t_norm():
    check("norm strips trailing ws", _norm("a  \nb\t\n") == "a\nb")
    check("norm single trailing nl", _norm("x\n\n\n") == "x")


def t_extract():
    c = "intro\n```python\nprint(1)\n```\nafter\n```python\nprint(2)\n```"
    check("extract last block", extract_code(c, "python") == "print(2)")
    check("extract none", extract_code("no code here") is None)
    check("extract untagged", extract_code("```\nhi\n```") == "hi")


def t_graders():
    g = {"type": "exact", "expect": "hello\nworld"}
    check("exact pass", grade(g, "hello\nworld\n")[0])
    check("exact fail", not grade(g, "goodbye")[0])
    g = {"type": "contains", "needle": "ANSWER: 42"}
    check("contains pass", grade(g, "blah blah ANSWER: 42.")[0])
    check("contains fail", not grade(g, "ANSWER: 41")[0])
    g = {"type": "contains_all", "needles": ["a", "b"]}
    check("contains_all pass", grade(g, "x a y b z")[0])
    check("contains_all miss", not grade(g, "x a y")[0])
    g = {"type": "regex", "pattern": r"ANSWER:\s*17\b"}
    check("regex pass", grade(g, "… ANSWER: 17")[0])
    check("regex boundary", not grade(g, "ANSWER: 175")[0])
    g = {"type": "json", "expect_keys": {"a": 1}}
    check("json pass", grade(g, 'here {"a": 1} done')[0])
    check("json wrong val", not grade(g, '{"a": 2}')[0])
    # code grader: real subprocess exec
    g = {"type": "code", "language": "python", "expect_stdout": "1\n2\n3", "timeout_s": 5}
    good = "```python\nfor i in range(1, 4): print(i)\n```"
    bad = "```python\nfor i in range(1, 3): print(i)\n```"
    check("code pass", grade(g, good)[0])
    check("code fail short", not grade(g, bad)[0])
    g_timeout = {"type": "code", "language": "python", "expect_stdout": "x", "timeout_s": 2}
    slow = "```python\nimport time\ntime.sleep(5)\nprint('x')\n```"
    check("code timeout", not grade(g_timeout, slow)[0])
    crash = "```python\nraise SystemExit(3)\n```"
    check("code nonzero exit", not grade(g, crash)[0])


def t_tasks():
    suite = load_suite(os.path.join(HERE, "suites"))
    ids = [t["id"] for t in suite]
    check("suite loads", len(ids) >= 8, f"got {len(ids)}")
    check("unique ids", len(ids) == len(set(ids)))
    check("validate rejects junk", validate_task({"id": "x"}) != [])


def t_ledger():
    recs = [
        {"tag": "a", "task": "t1", "category": "c", "pass": True, "tok_s": 100.0, "wall_s": 1.0},
        {"tag": "a", "task": "t2", "category": "c", "pass": False, "tok_s": 80.0, "wall_s": 1.0},
        {"tag": "a", "task": "t3", "category": "c", "pass": True, "error": True, "wall_s": 2.0},
    ]
    agg = aggregate(recs)
    check("agg n", agg["n"] == 3)
    # semantic: errored record counts as FAILURE (pass_rate = 1/3, not 2/3)
    # tolerance 2e-4: pass_rate is stored rounded to 4dp
    check("agg pass_rate", abs(agg["pass_rate"] - 1 / 3) < 2e-4, str(agg["pass_rate"]))
    check("agg raw median", agg["raw_tps"] == 90.0, str(agg["raw_tps"]))
    check("agg eff", agg["eff_tps"] == 30.0, str(agg["eff_tps"]))
    check("agg cats", "c" in agg["categories"])
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        tmp = f.name
    try:
        for r in recs:
            append_record(tmp, r)
        # torn tail line tolerated
        with open(tmp, "a") as f:
            f.write('{"tag": "a", "task": "t4"')  # no newline, invalid cut
        loaded = load_ledger(tmp)
        check("ledger torn tail skipped", len(loaded) == 3, f"got {len(loaded)}")
    finally:
        os.unlink(tmp)


def t_cli():
    r = subprocess.run([sys.executable, "-m", "effbench", "validate",
                        "--suite", os.path.join(HERE, "suites")],
                       cwd=HERE, capture_output=True, text=True)
    check("cli validate green", r.returncode == 0, r.stdout[-300:])


def main():
    print("effbench selftest")
    for fn in (t_norm, t_extract, t_graders, t_tasks, t_ledger, t_cli):
        print(f"[{fn.__name__}]")
        fn()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()

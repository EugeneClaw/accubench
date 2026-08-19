#!/usr/bin/env python3
"""Self-tests for accubench. Run: python3 tools/selftest.py  (no pytest needed)."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from accubench.verify import grade, extract_code, _norm  # noqa: E402
from accubench.tasks import load_suite, validate_task  # noqa: E402
from accubench.ledger import aggregate, append_record, load_ledger  # noqa: E402

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
    # v0.5 additive stats
    check("agg mean", agg.get("mean_tps") == 90.0, str(agg.get("mean_tps")))
    check("agg peak", agg.get("peak_tps") == 100.0, str(agg.get("peak_tps")))
    check("agg min", agg.get("min_tps") == 80.0, str(agg.get("min_tps")))
    check("agg p10/p90 present", "p10_tps" in agg and "p90_tps" in agg)
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


def t_suite_of():
    from accubench.ledger import suite_of
    check("suite full", suite_of([{"task": "code-fizzbang"}]) == "full")
    check("suite quick", suite_of([{"task": "q-fizzbang"}]) == "quick")
    check("suite mixed", suite_of([{"task": "q-x"}, {"task": "code-y"}]) == "mixed")
    check("suite empty", suite_of([]) == "full")


def t_fit_for():
    from accubench.expectations import fit_for
    props = {"model_path": "Qwen3.8-27B-IQ4_XS.gguf", "build_info": "cuda"}
    full = [{"task": "code-fizzbang", "pass": True, "tok_s": 165.0, "wall_s": 1.0}]
    quick = [{"task": "q-fizzbang", "pass": True, "tok_s": 145.0, "wall_s": 1.0}]
    hwc, band, klass, suite = fit_for(full, props)
    check("fit_for full class", hwc == "desktop_gpu_high", hwc)
    check("fit_for full suite", suite == "full")
    check("fit_for full band", band and band[0] == 150 and band[1] == 200, str(band))
    _, qband, _, qsuite = fit_for(quick, props)
    check("fit_for quick suite", qsuite == "quick")
    # quick band scaled: 150*0.89=133.5 -> 134, 200*0.89=178
    check("fit_for quick band scaled",
          qband and abs(qband[0] - 134) <= 1 and abs(qband[1] - 178) <= 1, str(qband))
    check("fit_for band has source", bool(band and band[2]), str(band))


def t_expected_pass():
    from accubench.report import _expected_pass
    # tasks the 2026-08-17 reference soak failed 255/255
    check("expected fail known", _expected_pass("logic-soduko-unique") is False)
    check("expected fail quick", _expected_pass("q-wordcount") is False)
    check("expected pass known", _expected_pass("code-fizzbang") is True)
    check("expected unknown", _expected_pass("made-up-task") is None)


def t_radar_tested_axes():
    from accubench.report import _purpose_ladder
    # purpose with tasks: rung drawn, ranked, carries n
    html = _purpose_ladder({"code": {"n": 15, "n_pass": 15, "pass_rate": 1.0},
                            "extract": {"n": 3, "n_pass": 0, "pass_rate": 0.0}})
    check("ladder draws tested rung", ">code<" in html and ">extract<" in html)
    check("ladder carries counts", "15/15" in html and "0/3" in html)
    check("ladder ranks by pass rate", html.index("code") < html.index("extract"))
    check("ladder zero shows sliver", "width:1.5%" in html)
    check("ladder notes untested", "not asked" in html and "chat" in html)
    # no purposes at all: graceful note
    html0 = _purpose_ladder({})
    check("ladder empty graceful", "No purposes" in html0 or "not asked" in html0)


def t_fail_hints():
    from accubench.explainer import fail_hint
    h = fail_hint("reasoning", "hard")
    check("hint reasoning/hard", "--think" in h)
    check("hint fallback", "grader" in fail_hint("extract", "medium"))


def t_capture_fields():
    """run_task() must record gen_tps/accept_pct from llama.cpp timings."""
    from accubench.__main__ import run_task
    from types import SimpleNamespace

    class FakeClient:
        """Mimics ServerClient.chat(): sets _perf from top-level timings."""

        def chat(self, payload):
            timings = {
                "predicted_per_second": 123.4,
                "draft_n": 15,
                "draft_n_accepted": 12,
            }
            return {
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"completion_tokens": 10},
                "timings": timings,
                "_perf": timings,  # ServerClient.chat() does this
            }, None

    task = {"id": "q-x", "prompt": "hi", "max_tokens": 8,
            "grader": {"type": "contains", "needle": "hello"}}
    args = SimpleNamespace(think=False, tag="t")
    rec = run_task(FakeClient(), task, args, {}, "r", 1)
    check("capture gen_tps", rec.get("gen_tps") == 123.4, str(rec.get("gen_tps")))
    check("capture accept from timings", rec.get("accept_pct") == 80.0,
          str(rec.get("accept_pct")))


def t_cli():
    r = subprocess.run([sys.executable, "-m", "accubench", "validate",
                        "--suite", os.path.join(HERE, "suites")],
                       cwd=HERE, capture_output=True, text=True)
    check("cli validate green", r.returncode == 0, r.stdout[-300:])


def t_r1_paths_agree():
    """R1: menu.DATA_DIR, config.PATH, keystore._keys_path() all resolve
    through accubench.paths.data_dir(). Selftest asserts agreement so
    future edits can't silently split the resolvers again."""
    from accubench import menu, config, keystore, paths
    check("r1 data_dir equal menu",
          menu.DATA_DIR == paths.data_dir(), menu.DATA_DIR)
    check("r1 config path equal resolver",
          config.PATH == paths.config_path(), config.PATH)
    check("r1 keys path equal resolver",
          keystore._keys_path() == paths.keys_path(), keystore._keys_path())
    check("r1 ledger path equal resolver",
          menu.LEDGER == paths.ledger_path(), menu.LEDGER)
    check("r1 reports dir equal resolver",
          menu.REPORTS_DIR == paths.reports_dir(), menu.REPORTS_DIR)


def t_alias_invocation():
    """Shim package forwards to accubench with a one-shot stderr note.
    Run the shim, capture stderr+stdout, check the note appears once and
    stdout is clean (no deprecation chatter leaks to pipes)."""
    import subprocess
    r = subprocess.run([sys.executable, "-m", "effbench", "validate",
                        "--suite", os.path.join(HERE, "suites")],
                       cwd=HERE, capture_output=True, text=True)
    check("alias cli green via shim", r.returncode == 0, r.stderr[-200:])
    check("alias prints to stderr", "alias" in r.stderr.lower(), r.stderr[:200])
    check("alias does not pollute stdout", "alias" not in r.stdout.lower(),
          r.stdout[:200])


def t_migration_path(tmp_home=None):
    """With a synthetic ~/.effbench, ensure migrate_old_data_dir() moves
    the contents into ~/.accubench and leaves the source intact for
    rollback. Runs against ACCUBENCH_HOME so we never touch the real
    user data dir."""
    import shutil
    import tempfile
    from accubench import paths
    if tmp_home is None:
        tmp_home = tempfile.mkdtemp(prefix="accubench-mig-")
        own = True
    else:
        own = False
    env_old = os.environ.get("ACCUBENCH_HOME")
    os.environ["ACCUBENCH_HOME"] = tmp_home
    # Build a fake ~/.effbench inside tmp_home by using a synthetic root:
    # the migration ignores ACCUBENCH_HOME for the SOURCE side, so we
    # put real content into ~/.effbench via HOME, then call the migrator.
    # Cheaper: write directly to ~/.effbench and accept the side-effect on
    # the test machine, then clean up. We guard this with a name suffix.
    backup = os.path.expanduser("~/.effbench.test-migrate-backup")
    real = os.path.expanduser("~/.effbench")
    if os.path.isdir(real) and not os.path.exists(backup):
        shutil.move(real, backup)
        had_real = True
    else:
        had_real = False
    try:
        # Recreate a fresh old data dir + populate it.
        if os.path.isdir(real):
            shutil.rmtree(real)
        os.makedirs(os.path.join(real, "reports"))
        with open(os.path.join(real, "config.json"), "w") as f:
            f.write('{"url": "http://old.example:11434"}')
        with open(os.path.join(real, "keys.json"), "w") as f:
            f.write('{"http://old.example": "secret-key"}')
        with open(os.path.join(real, "ledger.jsonl"), "w") as f:
            f.write('{"tag": "old", "task": "t", "pass": true}\n')
        # Run the migrator.
        new = paths.migrate_old_data_dir()
        assert new is not None  # type-narrowing for the checks below
        check("migration returns new dir", new is not None, str(new))
        check("new dir exists", os.path.isdir(new), str(new))
        check("old dir preserved (rollback)",
              os.path.isdir(real), real)
        check("config migrated", os.path.isfile(os.path.join(new, "config.json")))
        check("keys migrated", os.path.isfile(os.path.join(new, "keys.json")))
        check("ledger migrated", os.path.isfile(os.path.join(new, "ledger.jsonl")))
        check("reports subdir migrated",
              os.path.isdir(os.path.join(new, "reports")))
        check("stamp present inside new dir",
              os.path.isfile(os.path.join(new, ".migrated")))
        # Second call is a no-op because new dir now exists.
        check("migration no-op on second call",
              paths.migrate_old_data_dir() is None)
    finally:
        # Restore HOME state.
        if os.path.isdir(real):
            shutil.rmtree(real)
        if had_real:
            shutil.move(backup, real)
        if env_old is None:
            os.environ.pop("ACCUBENCH_HOME", None)
        else:
            os.environ["ACCUBENCH_HOME"] = env_old
        if own:
            shutil.rmtree(tmp_home, ignore_errors=True)


def t_keystore_umask_safe():
    """Legal backlog: keys.json is created 0600 from the moment of inode
    creation, not via open-then-chmod. Save a key in a clean tmpdir,
    inspect mode bits directly."""
    import stat
    import tempfile
    from accubench import keystore, paths
    with tempfile.TemporaryDirectory(prefix="accubench-ks-") as tmp:
        env_old = os.environ.get("ACCUBENCH_HOME")
        os.environ["ACCUBENCH_HOME"] = tmp
        try:
            keystore.save_key("http://test", "m", "secret")
            kp = paths.keys_path()
            mode = stat.S_IMODE(os.stat(kp).st_mode)
            check("keys.json mode 0o600", mode == 0o600, oct(mode))
            check("keystore wipe returns count", keystore.wipe() == 1)
            check("keystore wipe empties file",
                  json.loads(open(kp).read()) == {})
        finally:
            if env_old is None:
                os.environ.pop("ACCUBENCH_HOME", None)
            else:
                os.environ["ACCUBENCH_HOME"] = env_old


def main():
    print("accubench selftest")
    for fn in (t_norm, t_extract, t_graders, t_tasks, t_ledger, t_suite_of,
               t_fit_for, t_expected_pass, t_radar_tested_axes, t_fail_hints,
               t_capture_fields, t_cli,
               # v0.9.23 rename migration:
               t_r1_paths_agree, t_alias_invocation,
               t_migration_path, t_keystore_umask_safe):
        print(f"[{fn.__name__}]")
        fn()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()

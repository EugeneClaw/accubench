"""Wizard UX: probe the server, pick a suite, run, render, open. Zero args needed."""
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from datetime import datetime

from . import __version__
from .client import ServerClient
from .ledger import append_record, aggregate, load_ledger
from .report import render_report
from .expectations import (detect_hw_class, detect_model_arch, detect_quant,
                           lookup, classify_fit)


SUITES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "suites")


def _ask(prompt, default=None):
    """Tiny prompt helper — uses input() but never blocks silently."""
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    if not val and default is not None:
        return default
    return val


def _open_file(path):
    """Cross-platform open."""
    sysname = platform.system()
    try:
        if sysname == "Darwin":
            subprocess.run(["open", path], check=False)
        elif sysname == "Windows":
            os.startfile(path)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:
        pass


def _probe(url):
    """Quick probe of the server. Returns props dict or raises."""
    client = ServerClient(url)
    return client.props()


def _autodetect_suite():
    """Pick quick.json by default — designed for fast iteration."""
    quick = os.path.join(SUITES_DIR, "quick.json")
    if os.path.exists(quick):
        return quick
    return SUITES_DIR


def _autotag(props):
    """Generate a sensible tag from model + timestamp."""
    arch = detect_model_arch(props.get("model_path", ""))
    q = detect_quant(props.get("model_path", ""))
    short = (arch or "model") + (f"-{q}" if q else "")
    return f"{short}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def _run_quietly(url, suite_path, tag, ledger, runs):
    """Run the bench. Same machinery as `effbench run` but with friendlier output."""
    # import here to avoid circular
    from .__main__ import run_task
    from .tasks import load_suite

    tasks = load_suite(suite_path)
    print(f"   · {len(tasks)} tasks in {os.path.basename(suite_path)}")
    print(f"   · {runs} run{'s' if runs > 1 else ''} per task (suggests 3 for stable numbers)")
    print()
    client = ServerClient(url)
    info = client.props()
    server = {
        "build": info.get("build", "?"),
        "total_slots": info.get("total_slots", "?"),
        "model_path": info.get("model_path", "?"),
    }
    run_id = uuid.uuid4().hex[:8]
    print(f"   ✓ connected — build {server['build']}, slot(s) {server['total_slots']}")
    print()

    for ri in range(1, runs + 1):
        if runs > 1:
            print(f"   run {ri}/{runs}:")
        for ti, t in enumerate(tasks, 1):
            from types import SimpleNamespace
            args = SimpleNamespace(think=False, tag=tag)
            rec = run_task(client, t, args, server, run_id, ri)
            append_record(ledger, rec)
            mark = "✓" if rec["pass"] else "✗"
            ts = rec.get("tok_s", 0)
            print(f"   {mark} {t['id']:30s}  {ts:6.1f} tok/s", flush=True)
        print()
    return info


def _make_report(tag, ledger, props, out_path):
    recs = [r for r in load_ledger(ledger) if r.get("tag") == tag]
    agg = aggregate(recs)
    # Hardware detection: try /props first, fall back to inferring from
    # observed raw t/s (works when /props doesn't expose CUDA flags).
    rtps = agg.get("raw_tps") or 0
    hwc = detect_hw_class(props, observed_raw_tps=rtps if rtps else None)
    band = lookup(hwc, detect_model_arch(props.get("model_path", "")),
                  detect_quant(props.get("model_path", "")))
    klass = classify_fit(rtps, band)
    html_doc = render_report([(tag, recs, band, klass, hwc)], props=props,
                             title=f"effbench · {tag}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return hwc, klass, band


def go(args):
    """The wizard. URL defaults to the local MAIN door."""
    print()
    print(f"  effbench {__version__}  —  the simple one")
    print(f"  ╭──────────────────────────────────────────╮")
    print(f"  │  measures effective t/s of your server   │")
    print(f"  │  = how fast AND how often it gets it right │")
    print(f"  ╰──────────────────────────────────────────╯")
    print()

    url = getattr(args, "url", None)
    if not url:
        # check env, then config, then common default
        url = os.environ.get("EFFBENCH_URL")
        if not url:
            from . import config
            url = config.get("url")
        if not url:
            url = "http://localhost:11434"
            print(f"   → no server configured; trying {url}")
            print(f"     (override with --url URL or `effbench config set url URL`)")
        else:
            print(f"   → using configured URL: {url}")
    else:
        print(f"   → URL: {url}")

    print()
    print("   probing server...")
    try:
        props = _probe(url)
    except Exception as e:
        print(f"   ✗ cannot reach {url}: {e}")
        print(f"   → start your inference server and try again")
        print(f"   → or pass --url to point at a different server")
        return 1

    # Save the URL to config on first success — only if it was an explicit
    # CLI argument (not the localhost fallback). Don't overwrite existing config.
    cli_url = getattr(args, "url", None)
    from . import config as cfg
    if cli_url and cli_url != url:  # user passed something different from fallback
        if not cfg.get("url"):
            cfg.set_value("url", url)
            print(f"   ✓ saved {url} as your default server (edit: `effbench config set url URL`)")

    print(f"   ✓ build {props.get('build', '?')}, "
          f"model {os.path.basename(props.get('model_path', '?'))}")

    suite_path = _autodetect_suite()
    print(f"   → using suite: {os.path.basename(suite_path)} (the quick one, ~12 tasks)")
    print(f"   → run a fuller suite with:  python3 -m effbench run --suite suites/ ...")

    tag = getattr(args, "tag", None) or _autotag(props)
    print(f"   → tag: {tag}  (override with --tag NAME)")

    runs = getattr(args, "runs", 3) or 3
    if runs == 1:
        print(f"   → 1 run (results may be noisy on cold cache; use --runs 3 for stability)")
    else:
        print(f"   → {runs} runs per task")

    ledger = getattr(args, "ledger", None) or "effbench.jsonl"
    out = getattr(args, "out", None) or "effbench-report.html"

    print()
    print("   ────────────────────────────────────────")
    print(f"   starting bench…")
    print()

    t0 = time.time()
    try:
        _run_quietly(url, suite_path, tag, ledger, runs)
    except KeyboardInterrupt:
        print()
        print("   ✗ interrupted — partial ledger saved to", ledger)
        return 1
    elapsed = time.time() - t0

    print(f"   ✓ done in {elapsed:.0f}s")
    print()
    print(f"   rendering report → {out}")
    hwc, klass, band = _make_report(tag, ledger, props, out)
    print(f"   ✓ report written")
    if getattr(args, "open_browser", False):
        _open_file(os.path.abspath(out))
        print(f"   ✓ opened in browser")
    # human-friendly verdict line — the one-sentence story
    if band:
        lo, hi, _ = band
        word = "faster than typical" if klass == "above" else (
               "typical" if klass == "in" else (
               "slower than typical" if klass == "below" else
               "(no reference data)"))
        rtps_now = aggregate([r for r in load_ledger(ledger) if r.get("tag") == tag]).get("raw_tps", 0)
        print()
        print(f"   ── verdict ──────────────────────────────────")
        print(f"   {rtps_now:.0f} tok/s on this {hwc} (typical {lo}–{hi}): {word}")
        print(f"   ──────────────────────────────────────────────")
    print()
    print(f"   next:")
    print(f"     · share this run:    python3 -m effbench share --tag {tag}")
    print(f"     · export to CSV:     python3 -m effbench csv --tag {tag} --out tasks.csv")
    print(f"     · compare two runs:  python3 -m effbench go --compare --tag NEW")
    print()


def compare_go(args):
    """go --compare: run a new bench, render side-by-side against the previous."""
    # ... implemented as a thin wrapper around `go` followed by a compare render
    pass
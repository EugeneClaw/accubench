"""Interactive menu — the default UI after installation.

Typing `effbench` with no arguments opens this menu. Everything a
non-technical user needs is reachable from here; flags still exist for
scripting but nobody has to know them.
"""
import glob
import os
import shutil
import sys
from datetime import datetime

from . import __version__
from . import config
from . import wizard
from .client import ServerClient
from .ledger import load_ledger, aggregate, suite_of
from .report import render_report
from .expectations import (detect_hw_class, detect_model_arch, detect_quant,
                           lookup, classify_fit, fit_for)

DATA_DIR = os.path.expanduser("~/.effbench")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
LEDGER = os.path.join(DATA_DIR, "ledger.jsonl")

CANDIDATE_URLS = [
    "http://localhost:11434",   # llama.cpp / Ollama
    "http://localhost:8080",    # llama.cpp default
    "http://localhost:5000",    # common Flask wrappers
    "http://localhost:1234",    # LM Studio
]


def _choice(prompt, valid):
    """Ask until we get one of `valid`. None on EOF/Ctrl-C."""
    while True:
        try:
            val = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if val in valid:
            return val
        print(f"   please enter one of: {', '.join(sorted(valid))}")


def _resolve_server():
    """Find a reachable server: config, env, common ports — then prompt.

    Returns (url, props) or (None, None) if the user gives up.
    """
    candidates = []
    for url in [config.get("url"), os.environ.get("EFFBENCH_URL")] + CANDIDATE_URLS:
        if url and url not in candidates:
            candidates.append(url)
    for url in candidates:
        print(f"   · looking for a server at {url}…", end="", flush=True)
        try:
            props = ServerClient(url).props()
            print(" found")
            if config.get("url") != url:
                config.set_value("url", url)
                print(f"   ✓ remembered {url} for next time")
            return url, props
        except Exception:
            print(" nothing there")

    print()
    print("   I couldn't find your AI server automatically.")
    print("   It's the program that serves the model (llama.cpp, LM Studio,")
    print("   Ollama, vLLM…). Start it first, or tell me where it is:")
    while True:
        try:
            url = input("   server URL (e.g. http://localhost:11434, or q to cancel): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None, None
        if url.lower() in ("q", "quit", "cancel"):
            return None, None
        if not url:
            continue
        try:
            props = ServerClient(url).props()
            config.set_value("url", url)
            print(f"   ✓ connected — remembered {url} for next time")
            return url, props
        except Exception as e:
            print(f"   ✗ can't reach {url} ({e})")


def _suite_path(which):
    if which == "quick":
        p = os.path.join(wizard.SUITES_DIR, "quick.json")
        return p if os.path.exists(p) else wizard.SUITES_DIR
    return wizard.SUITES_DIR


def _do_run(which):
    est = "~15 seconds" if which == "quick" else "2-4 minutes"
    n = "12 quick" if which == "quick" else "all"
    print()
    url, props = _resolve_server()
    if not url:
        return
    tag = wizard._autotag(props)
    runs = 1 if which == "quick" else max(1, int(config.get("runs") or 1))
    suite = _suite_path(which)
    out = os.path.join(REPORTS_DIR, f"{tag}.html")
    os.makedirs(REPORTS_DIR, exist_ok=True)

    model_name = os.path.basename(props.get("model_path", "?"))
    print()
    print(f"   model:   {model_name}")
    print(f"   tasks:   {n} ({est})")
    print(f"   run id:  {tag}")
    print()
    print("   ────────────────────────────────────────")
    try:
        wizard._run_quietly(url, suite, tag, LEDGER, runs)
    except KeyboardInterrupt:
        print()
        print("   stopped — partial results kept")
        return

    hwc, klass, band = wizard._make_report(tag, LEDGER, props, out)
    print(f"   ✓ report saved: {out}")
    if config.get("open") is not False:
        wizard._open_file(os.path.abspath(out))
        print("   ✓ opened in your browser")

    agg = aggregate([r for r in load_ledger(LEDGER) if r.get("tag") == tag])
    rtps = agg.get("raw_tps") or 0
    eff = agg.get("eff_tps") or (rtps * (agg.get("pass_rate") or 0))
    print()
    print("   ── your result ─────────────────────────────")
    print(f"   speed:    {rtps:.0f} tok/s (tokens per second)")
    print(f"   accuracy: {(agg.get('pass_rate') or 0)*100:.0f}% of tasks right")
    print(f"   overall:  {eff:.0f} effective tok/s (speed × accuracy)")
    if band:
        lo, hi, _ = band
        word = {"above": "faster than typical", "in": "typical",
                "below": "slower than typical"}.get(klass, "?")
        print(f"   vs others on similar hardware: {word} ({lo}–{hi} tok/s)")
    print("   ─────────────────────────────────────────────")
    print()


def _tags_summary():
    if not os.path.exists(LEDGER):
        return []
    recs = load_ledger(LEDGER)
    out = []
    for tag in sorted({r["tag"] for r in recs if r.get("tag")}):
        bag = [r for r in recs if r["tag"] == tag]
        agg = aggregate(bag)
        when = datetime.fromtimestamp(min(r.get("ts", 0) for r in bag))
        # custom display name (rename feature) — sidecar next to the report
        custom = None
        side = os.path.join(REPORTS_DIR, f"{tag}.name")
        try:
            with open(side, encoding="utf-8") as f:
                custom = f.read().strip() or None
        except OSError:
            pass
        out.append({
            "tag": tag,
            "custom": custom,
            "when": when.strftime("%Y-%m-%d %H:%M"),
            "pass": agg.get("pass_rate") or 0,
            "tps": agg.get("raw_tps") or 0,
            "eff_tps": agg.get("eff_tps") or 0,
            "suite": suite_of(bag),
        })
    out.sort(key=lambda x: x["when"], reverse=True)
    return out


def _do_compare():
    print()
    tags = _tags_summary()
    if len(tags) < 2:
        print("   you need at least two finished runs to compare.")
        print("   (run a benchmark twice — e.g. before and after a change —")
        print("   and they'll both appear here.)")
        return
    print("   pick the two runs to compare:")
    for i, t in enumerate(tags, 1):
        print(f"   {i}) {t['when']}  ·  {t['tps']:.0f} tok/s  ·  "
              f"{t['pass']*100:.0f}% right  ·  {t['tag']}")
    a = _choice("   first (newer) run number: ", {str(i) for i in range(1, len(tags) + 1)})
    if a is None:
        return
    b = _choice("   second (older) run number: ", {str(i) for i in range(1, len(tags) + 1)})
    if b is None:
        return
    ta, tb = tags[int(a) - 1]["tag"], tags[int(b) - 1]["tag"]
    if ta == tb:
        print("   ✗ pick two different runs")
        return
    recs = load_ledger(LEDGER)
    ra = [r for r in recs if r["tag"] == ta]
    rb = [r for r in recs if r["tag"] == tb]
    props = None
    try:
        props = ServerClient(config.get("url") or "").props()
    except Exception:
        props = None
    model_path = (props or {}).get("model_path", "")
    obs = (aggregate(ra).get("raw_tps", 0) + aggregate(rb).get("raw_tps", 0)) / 2
    hwc = detect_hw_class(props or {}, observed_raw_tps=obs if obs else None)
    # suite-aware bands per side (quick runs get the ×0.89 scale)
    _, band_a, ka, _ = fit_for(ra, props or {})
    _, band_b, kb, _ = fit_for(rb, props or {})
    out = os.path.join(REPORTS_DIR, f"compare-{ta}-vs-{tb}.html")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    html = render_report([(ta, ra, band_a, ka, hwc), (tb, rb, band_b, kb, hwc)],
                         props=props, mode="compare")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"   ✓ comparison saved: {out}")
    if config.get("open") is not False:
        wizard._open_file(os.path.abspath(out))
        print("   ✓ opened in your browser")
    print()


def _do_reports():
    print()
    reports = sorted(glob.glob(os.path.join(REPORTS_DIR, "*.html")),
                     key=os.path.getmtime, reverse=True)
    if not reports:
        print("   no saved reports yet — run a benchmark first (option 1).")
        return
    print("   saved reports (newest first):")
    show = reports[:15]
    for i, r in enumerate(show, 1):
        when = datetime.fromtimestamp(os.path.getmtime(r)).strftime("%Y-%m-%d %H:%M")
        print(f"   {i}) {when}  ·  {os.path.basename(r)}")
    c = _choice("   open which? (number, or q to go back): ",
                {str(i) for i in range(1, len(show) + 1)} | {"q"})
    if c is None or c == "q":
        return
    path = os.path.abspath(show[int(c) - 1])
    wizard._open_file(path)
    print(f"   ✓ opened in your browser")
    print()


def _do_settings():
    while True:
        print()
        print("   settings")
        print("   ────────")
        print(f"   1) server URL:        {config.get('url') or '(not set — auto-detect)'}")
        print(f"   2) runs per task:     {config.get('runs')}")
        print(f"   3) open browser after run: {'on' if config.get('open') is not False else 'off'}")
        print("   4) back")
        c = _choice("   change which? ", {"1", "2", "3", "4", "q"})
        if c in (None, "4", "q"):
            return
        if c == "1":
            try:
                url = input("   new server URL (blank = auto-detect): ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if url:
                try:
                    ServerClient(url).props()
                    config.set_value("url", url)
                    print(f"   ✓ saved — server reachable")
                except Exception as e:
                    print(f"   ✗ can't reach {url}: {e} (not saved)")
            else:
                config.set_value("url", None)
                print("   ✓ cleared — will auto-detect next time")
        elif c == "2":
            try:
                v = input("   runs per task (1 = fastest, 3 = most stable): ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if v.isdigit() and int(v) >= 1:
                config.set_value("runs", int(v))
                print("   ✓ saved")
            else:
                print("   ✗ enter a number 1 or higher")
        elif c == "3":
            cur = config.get("open") is not False
            config.set_value("open", not cur)
            print(f"   ✓ open browser is now {'on' if not cur else 'off'}")


def _do_uninstall(interactive=True):
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prefix = os.path.dirname(os.path.dirname(pkg_root))
    # Only offer to delete if we're inside a real install layout
    # (~/.local/share/effbench or %LOCALAPPDATA%\effbench\share\effbench).
    # A git clone in ~/Dev is NOT an install — refuse to touch it.
    marker = os.path.join(pkg_root, ".git")
    in_store = "share" in pkg_root.lower() or "effbench" == os.path.basename(os.path.dirname(pkg_root)).lower()
    if not in_store and os.path.exists(marker):
        print()
        print("   this looks like a git clone, not an installed copy.")
        print(f"   to remove it, just delete the folder: {pkg_root}")
        print("   (your settings and reports live in {d})".format(d=DATA_DIR))
        return
    paths = [p for p in [pkg_root,
                         os.path.join(prefix, "bin", "effbench"),
                         os.path.join(prefix, "bin", "effbench.cmd")]
             if os.path.exists(p)]
    is_windows = sys.platform.startswith("win")

    print()
    print("   uninstall effbench")
    print("   ──────────────────")
    if not paths:
        print("   (no installed copy found — only user data remains)")
    for p in paths:
        print(f"     · {p}")
    print(f"     · {DATA_DIR}  (your settings, saved reports, results)")

    if not interactive:
        return
    try:
        ok = input("\n   delete all of the above? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ok = "n"
    if ok != "y":
        print("   cancelled — nothing deleted")
        return
    keep_data = input("   also delete your saved reports and results? [y/N]: ").strip().lower() == "y"

    failures = []
    for p in paths:
        try:
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=False)
            else:
                os.remove(p)
            print(f"   ✓ removed {p}")
        except Exception as e:
            failures.append((p, e))
    if keep_data:
        try:
            shutil.rmtree(DATA_DIR, ignore_errors=True)
            print(f"   ✓ removed {DATA_DIR}")
        except Exception as e:
            failures.append((DATA_DIR, e))
    for p, e in failures:
        print(f"   ✗ couldn't remove {p}: {e}")
        print("     delete it manually once this window is closed")
    if is_windows:
        print("   (the PATH entry can stay — it points at a folder that no longer exists)")
    print()
    print("   uninstalled. to reinstall later:")
    print("     curl -fsSL https://raw.githubusercontent.com/EugeneClaw/effbench/main/install.sh | bash")
    print()


def main_menu():
    print()
    print(f"  effbench {__version__}")
    print("  how fast — and how accurate — is your local AI?")
    print()
    while True:
        print("  ────────────────────────────────────────────")
        print("   1) quick benchmark          (~15 seconds)")
        print("   2) full benchmark           (2-4 minutes)")
        print("   3) compare two past runs")
        print("   4) open a past report")
        print("   5) settings")
        print("   6) uninstall")
        print("   q) quit")
        print()
        c = _choice("  what would you like to do? ", {"1", "2", "3", "4", "5", "6", "q"})
        if c is None or c == "q":
            print("  bye")
            return 0
        if c == "1":
            _do_run("quick")
        elif c == "2":
            _do_run("full")
        elif c == "3":
            _do_compare()
        elif c == "4":
            _do_reports()
        elif c == "5":
            _do_settings()
        elif c == "6":
            _do_uninstall()

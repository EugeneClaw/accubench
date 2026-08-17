#!/usr/bin/env python3
"""effbench: quality-weighted benchmark for any OpenAI-compatible inference server.

Usage:
    python3 -m effbench go          [--url URL] [--tag NAME] [--runs N]
                                  [--out report.html] [--open]
    python3 -m effbench run         --url URL --suite DIR [--tag NAME] [--runs N]
    python3 -m effbench report       --ledger FILE --out FILE.html [--tags A,B]
    python3 -m effbench compare      --ledger FILE --tag A --against B --out FILE.html
    python3 -m effbench share       --ledger FILE --tag NAME
    python3 -m effbench csv         --ledger FILE --tag NAME [--summary|--compare OTHER]
    python3 -m effbench validate    --suite DIR
"""
import argparse
import json
import os
import sys
import time
import uuid

from . import __version__
from .client import ServerClient
from .tasks import load_suite
from .verify import grade
from .ledger import append_record, load_ledger, aggregate, compare
from .report import render_report
from . import wizard
from .csv_export import export_per_task, export_summary, export_compare
from .share import render_markdown
from .expectations import (detect_hw_class, detect_model_arch, detect_quant,
                          lookup, classify_fit)


def cmd_run(args):
    tasks = load_suite(args.suite)
    print(f"loaded {len(tasks)} tasks from {args.suite}")
    client = ServerClient(args.url)
    try:
        info = client.props()
    except Exception as e:
        print(f"cannot reach {args.url}: {e}", file=sys.stderr)
        return 1
    server = {
        "build": info.get("build", "?"),
        "total_slots": info.get("total_slots", "?"),
        "model_path": info.get("model_path", "?"),
    }
    run_id = uuid.uuid4().hex[:8]
    print(f"server: {server['build']}  run_id={run_id}")
    n_fail_connect = 0
    for r in range(1, args.runs + 1):
        for t in tasks:
            rec = run_task(client, t, args, server, run_id, r)
            append_record(args.ledger, rec)
            status = "PASS" if rec["pass"] else "FAIL"
            extra = f" accept={rec.get('accept_pct')}%" if rec.get("draft_n") else ""
            print(f"[{args.tag}] {t['id']:32s} {status} "
                  f"{rec['tok_s']:6.1f} tok/s  {rec['wall_s']:5.1f}s{extra}")
    return 0


def run_task(client, task, args, server, run_id, run_idx):
    payload = {
        "model": "bench",
        "messages": [{"role": "user", "content": task["prompt"]}],
        "max_tokens": task.get("max_tokens", 1024),
        "temperature": task.get("temperature", 0.0),
    }
    if not getattr(args, "think", False):
        # default: disable thinking so CoT verbosity doesn't consume the
        # completion budget (thinking models otherwise emit empty content on
        # hard tasks). --think restores raw thinking behaviour.
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    start = time.time()
    data, err = client.chat(payload)
    elapsed = time.time() - start
    if err:
        return {
            "ts": round(time.time(), 1),
            "tag": getattr(args, "tag", "run"),
            "task": task["id"],
            "category": task.get("category", "misc"),
            "run_id": run_id,
            "run_idx": run_idx,
            "pass": False,
            "error": True,
            "wall_s": round(elapsed, 2),
            "tok_s": None,
            "grader_detail": err[:200],
        }
    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""
    usage = data.get("usage", {})
    n_completion = usage.get("completion_tokens") or 0
    tok_s = (n_completion / elapsed) if elapsed > 0 else 0
    out = {
        "ts": round(time.time(), 1),
        "tag": getattr(args, "tag", "run"),
        "task": task["id"],
        "category": task.get("category", "misc"),
        "run_id": run_id,
        "run_idx": run_idx,
        "wall_s": round(elapsed, 2),
        "tok_s": round(tok_s, 1) if tok_s else 0,
        "n_completion": n_completion,
        "content": content,
        "reasoning": reasoning,
    }
    # speculative-decode fields if present
    sd = usage.get("draft_tokens") or usage.get("speculative") or {}
    if isinstance(sd, dict):
        out["draft_n"] = sd.get("draft_n") or sd.get("draft")
        out["accept_pct"] = sd.get("accept_pct")
    passed, detail = grade(task["grader"], content, reasoning)
    out["pass"] = bool(passed)
    out["grader_detail"] = detail
    return out


def cmd_validate(args):
    from .tasks import validate_task
    tasks = load_suite(args.suite)
    n_total = len(tasks)
    n_ok = 0
    bad = []
    for t in tasks:
        problems = validate_task(t)
        if problems:
            bad.append((t["id"], problems))
            continue
        # verify good/bad fixtures actually pass/fail
        g_pass, g_detail = grade(t["grader"], t.get("good_output", ""), "")
        b_pass, _ = grade(t["grader"], t.get("bad_output", ""), "")
        if g_pass and not b_pass:
            n_ok += 1
        else:
            bad.append((t["id"], f"GRADER BROKEN: good={g_pass} bad={b_pass} ({g_detail[:60]})"))
    print(f"validating {n_total} task graders against known-good/known-bad outputs")
    for tid, msg in bad:
        print(f"  {tid:32s} {msg}")
    if bad:
        print(f"\n{len(bad)} BROKEN GRADERS")
        return 1
    print(f"\nALL {n_ok} GRADERS OK")
    return 0


def cmd_report(args):
    recs = load_ledger(args.ledger, tags=args.tags.split() if args else None)
    # if mixed, group by tag and render first
    tags = sorted({r["tag"] for r in recs if r.get("tag")})
    if not tags:
        print("no records in ledger")
        return 1
    # we want the props from the first record's tag
    # for simplicity: ask server is optional
    props = None
    if hasattr(args, "url") and args.url:
        try:
            props = ServerClient(args.url).props()
        except Exception:
            props = None

    if len(tags) == 1:
        tag = tags[0]
        bag = [r for r in recs if r["tag"] == tag]
        model_path = (props or {}).get("model_path", "")
        # Use observed t/s for hardware classification (since /props is often opaque)
        observed_tps = aggregate(bag).get("raw_tps") or 0
        hwc = detect_hw_class(props or {}, observed_raw_tps=observed_tps if observed_tps else None)
        band = lookup(hwc, detect_model_arch(model_path), detect_quant(model_path)) if props else None
        klass = classify_fit(observed_tps, band)
        html_doc = render_report([(tag, bag, band, klass, hwc)], props=props)
    else:
        # multi: compare the first two
        a, b = tags[0], tags[1]
        recs_a = [r for r in recs if r["tag"] == a]
        recs_b = [r for r in recs if r["tag"] == b]
        model_path = (props or {}).get("model_path", "")
        # Use the average of both runs as the observed signal
        obs_tps = (aggregate(recs_a).get("raw_tps", 0) + aggregate(recs_b).get("raw_tps", 0)) / 2
        hwc = detect_hw_class(props or {}, observed_raw_tps=obs_tps if obs_tps else None)
        band_a = lookup(hwc, detect_model_arch(model_path), detect_quant(model_path)) if props else None
        band_b = band_a
        klass_a = classify_fit(aggregate(recs_a).get("raw_tps", 0), band_a)
        klass_b = classify_fit(aggregate(recs_b).get("raw_tps", 0), band_b)
        html_doc = render_report([(a, recs_a, band_a, klass_a, hwc),
                                  (b, recs_b, band_b, klass_b, hwc)],
                                 props=props, mode="compare")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"wrote {args.out}  ({len(recs)} records)")
    return 0


def cmd_compare(args):
    recs = load_ledger(args.ledger)
    recs_a = [r for r in recs if r["tag"] == args.tag]
    recs_b = [r for r in recs if r["tag"] == args.against]
    if not recs_a or not recs_b:
        print(f"missing tag(s): {args.tag} ({len(recs_a)}) / {args.against} ({len(recs_b)})")
        return 1
    props = None
    if hasattr(args, "url") and args.url:
        try:
            props = ServerClient(args.url).props()
        except Exception:
            props = None
    model_path = (props or {}).get("model_path", "")
    obs_tps = (aggregate(recs_a).get("raw_tps", 0) + aggregate(recs_b).get("raw_tps", 0)) / 2
    hwc = detect_hw_class(props or {}, observed_raw_tps=obs_tps if obs_tps else None)
    arch = detect_model_arch(model_path)
    q = detect_quant(model_path)
    band_a = lookup(hwc, arch, q) if props else None
    band_b = band_a
    klass_a = classify_fit(aggregate(recs_a).get("raw_tps", 0), band_a)
    klass_b = classify_fit(aggregate(recs_b).get("raw_tps", 0), band_b)
    if args.out and args.out.endswith(".html"):
        html_doc = render_report([(args.tag, recs_a, band_a, klass_a, hwc),
                                  (args.against, recs_b, band_b, klass_b, hwc)],
                                 props=props, mode="compare")
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(html_doc)
        print(f"wrote {args.out}")
    else:
        for line in compare(recs_a, recs_b, args.tag, args.against):
            print(line)
    return 0


def cmd_share(args):
    """Print a copy-pasteable Markdown summary of one tag."""
    recs = [r for r in load_ledger(args.ledger) if r["tag"] == args.tag]
    if not recs:
        print(f"no records for tag {args.tag}")
        return 1
    agg = aggregate(recs)
    props = None
    if hasattr(args, "url") and args.url:
        try:
            props = ServerClient(args.url).props()
        except Exception:
            props = None
    model_path = (props or {}).get("model_path", "")
    observed_tps = agg.get("raw_tps") or 0
    hwc = detect_hw_class(props or {}, observed_raw_tps=observed_tps if observed_tps else None)
    arch = detect_model_arch(model_path)
    q = detect_quant(model_path)
    band = lookup(hwc, arch, q) if props else None
    klass = classify_fit(observed_tps, band)
    print(render_markdown(args.tag, recs, agg, fit_band=band, fit_class=klass))
    return 0


def cmd_csv(args):
    """Export per-task CSV (default), summary CSV (--summary), or compare CSV (--compare OTHER)."""
    recs = load_ledger(args.ledger)
    if getattr(args, "compare", None):
        ra = [r for r in recs if r["tag"] == args.tag]
        rb = [r for r in recs if r["tag"] == args.compare]
        export_compare(ra, rb, args.tag, args.compare, args.out)
        print(f"wrote {args.out}  ({args.tag} vs {args.compare})")
    elif getattr(args, "summary", False):
        tags = sorted({r["tag"] for r in recs if r.get("tag")})
        recs_by_tag = {t: [r for r in recs if r["tag"] == t] for t in tags}
        # band lookup per tag — same model assumed unless overridden
        for t, rs in recs_by_tag.items():
            band = None
            # attach band from existing agg we already stored? No — just pass None.
        export_summary(recs_by_tag, args.out)
        print(f"wrote {args.out}  ({len(tags)} tags)")
    else:
        recs_tag = [r for r in recs if r["tag"] == args.tag]
        export_per_task(recs_tag, args.out)
        print(f"wrote {args.out}  ({len(recs_tag)} task records)")
    return 0


def cmd_go(args):
    return wizard.go(args)


def cmd_config(args):
    """View or edit persistent config at ~/.effbench/config.json."""
    from . import config as cfg
    if getattr(args, "set_key", None):
        # `effbench config set KEY VALUE`
        key = args.set_key
        value = args.set_value
        if value in ("true", "false"):
            value = (value == "true")
        elif value in ("null", "None", ""):
            value = None
        elif value.isdigit():
            value = int(value)
        cfg.set_value(key, value)
        print(f"set {key} = {value!r}")
    elif getattr(args, "get_key", None):
        # `effbench config get KEY`
        val = cfg.get(args.get_key)
        if val is None:
            print(f"{args.get_key}: (not set)")
        else:
            print(f"{args.get_key}: {val}")
    elif getattr(args, "path", False):
        print(cfg.PATH)
    elif getattr(args, "show", False):
        import json
        print(json.dumps(cfg.load(), indent=2))
    else:
        # `effbench config` — default to show
        import json
        print(json.dumps(cfg.load(), indent=2))
    return 0


def cmd_setup(args):
    """First-run wizard: probe a candidate server, save the URL if successful."""
    from . import config as cfg
    print()
    print("  effbench setup")
    print("  ──────────────")
    print()
    print("  This finds your inference server and saves the URL")
    print("  to ~/.effbench/config.json so effbench go works without --url.")
    print()

    # Common candidates to try, in order, deduplicated
    candidates = []
    existing = cfg.get("url")
    if existing:
        candidates.append(existing)
    for url in [
        "http://localhost:11434",
        "http://localhost:8080",
        "http://localhost:5000",
        "http://localhost:1234",   # LM Studio
    ]:
        if url not in candidates:
            candidates.append(url)
    # Also try a LAN scan if the user gave a partial (we'll keep it simple for v0.2)

    print(f"   trying {len(candidates)} common URLs...")
    found = None
    for url in candidates:
        try:
            client = ServerClient(url)
            # health first — cheap and tells us the server is actually up
            health = client.health()
            if health.get("status") != "ok":
                print(f"   · {url}  → health check returned {health}")
                continue
            # then /props for model/build info
            info = client.props()
            print(f"   ✓ {url}  → build {info.get('build', '?')}, model "
                  f"{os.path.basename(info.get('model_path', '?'))}")
            if found is None:
                found = url
        except Exception:
            print(f"   · {url}  → not reachable")
    print()
    if not found:
        print("   ✗ no server found at any common address.")
        print()
        print("   Try one of these:")
        print("     · start your server (inference server with OpenAI-compatible API)")
        print("     · find its URL (often http://localhost:PORT)")
        print("     · run:  effbench setup --url http://your-server:port")
        print()
        return 1

    print(f"   using {found}")
    cfg.set_value("url", found)
    print(f"   ✓ saved to {cfg.PATH}")
    print()
    print("   next:  effbench go")
    print()


def cmd_uninstall(args):
    from . import menu
    menu._do_uninstall()
    return 0


def cmd_ui(args):
    from . import webui
    return webui.launch()


def cmd_menu(args):
    from . import menu
    return menu.main_menu()


def build_parser():
    p = argparse.ArgumentParser(prog="effbench",
                                description="quality-weighted benchmark for any OpenAI-compatible inference server")
    sub = p.add_subparsers(dest="cmd")

    pg = sub.add_parser("go", help="wizard: probe, run, render, open — zero args needed")
    pg.add_argument("--url", help="server URL (default: $EFFBENCH_URL or http://localhost:11434)")
    pg.add_argument("--tag", help="name for this run (default: auto from model + time)")
    pg.add_argument("--runs", type=int, default=3, help="runs per task (default 3)")
    pg.add_argument("--ledger", help="ledger path (default: effbench.jsonl)")
    pg.add_argument("--out", help="report path (default: effbench-report.html)")
    pg.add_argument("--open", dest="open_browser", action="store_true",
                    help="open the report in the default browser when done")
    pg.set_defaults(func=cmd_go)

    pset = sub.add_parser("setup", help="first-run wizard: find your server, save the URL")
    pset.add_argument("--url", help="skip the search and save this URL directly")
    pset.set_defaults(func=cmd_setup)

    pcf = sub.add_parser("config", help="view or edit ~/.effbench/config.json")
    pcfsub = pcf.add_subparsers(dest="config_cmd")
    pcfsub.add_parser("show", help="show the full config").set_defaults(show=True)
    pcfsub.add_parser("path", help="print the config file path").set_defaults(path=True)
    pcg = pcfsub.add_parser("get")
    pcg.add_argument("get_key")
    pcs = pcfsub.add_parser("set")
    pcs.add_argument("set_key")
    pcs.add_argument("set_value")
    pcf.set_defaults(func=cmd_config)

    pr = sub.add_parser("run", help="low-level: run a suite against a server")
    pr.add_argument("--url", required=True)
    pr.add_argument("--suite", required=True)
    pr.add_argument("--ledger", default="results.jsonl")
    pr.add_argument("--tag", default="run")
    pr.add_argument("--runs", type=int, default=1)
    pr.add_argument("--think", action="store_true",
                    help="leave model thinking enabled (default: disable via "
                         "chat_template_kwargs for apples-apples results)")
    pr.set_defaults(func=cmd_run)

    pp = sub.add_parser("report", help="render an HTML report from a ledger")
    pp.add_argument("--ledger", required=True)
    pp.add_argument("--out", required=True)
    pp.add_argument("--tags", help="comma-separated tag filter (default: all)")
    pp.add_argument("--url", help="server URL for hardware-fit context")
    pp.set_defaults(func=cmd_report)

    pc = sub.add_parser("compare", help="compare two tags")
    pc.add_argument("--ledger", required=True)
    pc.add_argument("--tag", required=True)
    pc.add_argument("--against", required=True)
    pc.add_argument("--out", help="HTML output path; omit for terminal table")
    pc.add_argument("--url", help="server URL for hardware-fit context")
    pc.set_defaults(func=cmd_compare)

    psh = sub.add_parser("share", help="copy-pasteable Markdown summary for posting")
    psh.add_argument("--ledger", required=True)
    psh.add_argument("--tag", required=True)
    psh.add_argument("--url", help="server URL for hardware-fit context")
    psh.set_defaults(func=cmd_share)

    pcv = sub.add_parser("csv", help="export CSV for Sheets/Excel/Numbers")
    pcv.add_argument("--ledger", required=True)
    pcv.add_argument("--tag", required=True)
    pcv.add_argument("--out", required=True)
    pcv.add_argument("--summary", action="store_true",
                     help="export one row per tag instead of one row per task")
    pcv.add_argument("--compare", metavar="OTHER_TAG",
                     help="export side-by-side per-task comparison vs OTHER_TAG")
    pcv.set_defaults(func=cmd_csv)

    pu = sub.add_parser("uninstall", help="remove effbench (asks before deleting anything)")
    pu.set_defaults(func=cmd_uninstall)

    pu2 = sub.add_parser("ui", help="open the browser UI (default when you type bare `effbench`)")
    pu2.set_defaults(func=cmd_ui)

    pu3 = sub.add_parser("menu", help="terminal menu (fallback when no browser is available)")
    pu3.set_defaults(func=cmd_menu)

    pv = sub.add_parser("validate", help="self-test every task grader")
    pv.add_argument("--suite", required=True)
    pv.set_defaults(func=cmd_validate)

    return p


def main():
    # Windows consoles default to cp1252/cp437 — our output contains ✓/✗/·.
    # Force UTF-8 with replacement so printing never crashes the run.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "cmd", None):
        # bare `effbench` → browser UI
        from . import webui
        return webui.launch()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
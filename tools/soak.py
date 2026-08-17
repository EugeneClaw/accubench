#!/usr/bin/env python3
"""Overnight soak: loop effbench against a server, forever (or --hours N).

Each cycle: run the full suite, tag soak-N, append heartbeat with /props
snapshot. Survives server restarts (waits for /health between cycles).
Results land in soak-results.jsonl; render anytime:
    python3 -m effbench report --ledger soak-results.jsonl --out soak-report.html
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request

HERE = "/opt/effbench"


def get(url, timeout=8):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_healthy(url, max_s=1800):
    """Block until /health responds ok. Returns True/False."""
    start = time.time()
    while time.time() - start < max_s:
        try:
            if get(url.rstrip("/") + "/health", timeout=5).get("status") == "ok":
                return True
        except Exception:
            pass
        time.sleep(10)
    return False


def heartbeat(path, url, note=""):
    rec = {"ts": round(time.time(), 1), "type": "heartbeat", "url": url, "note": note}
    try:
        props = get(url.rstrip("/") + "/props", timeout=8)
        rec["model"] = (props.get("model_path") or "?").split("\\")[-1].split("/")[-1]
        rec["build"] = props.get("build", "?")
        rec["total_slots"] = props.get("total_slots")
    except Exception as e:
        rec["error"] = str(e)[:200]
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=None,
                   help="server URL (default: $EFFBENCH_URL or http://localhost:11434)")
    p.add_argument("--suite", default=f"{HERE}/suites")
    p.add_argument("--ledger", default=f"{HERE}/soak-results.jsonl")
    p.add_argument("--hours", type=float, default=0, help="0 = forever")
    p.add_argument("--gap", type=float, default=30.0, help="seconds between cycles")
    args = p.parse_args()

    deadline = time.time() + args.hours * 3600 if args.hours else None
    cycle = 0
    print(f"soak: {args.url} suite={args.suite} hours={args.hours or '∞'}", flush=True)
    while deadline is None or time.time() < deadline:
        cycle += 1
        hb = heartbeat(args.ledger, args.url, note=f"pre-cycle {cycle}")
        print(f"[{time.strftime('%H:%M:%S')}] cycle {cycle}: {hb.get('model', '?')} "
              f"({hb.get('error', 'healthy')})", flush=True)
        if "error" in hb:
            print("  server down, waiting for recovery...", flush=True)
            if not wait_healthy(args.url):
                print("  server never recovered within 30min; heartbeat logged", flush=True)
                time.sleep(60)
                continue
        cmd = [sys.executable, "-m", "effbench", "run",
               "--url", args.url, "--suite", args.suite,
               "--ledger", args.ledger, "--tag", f"soak-{cycle:03d}"]
        t0 = time.time()
        r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
        dt = time.time() - t0
        ok = r.returncode == 0
        print(f"  effbench {'OK' if ok else 'FAILED'} in {dt:.0f}s", flush=True)
        if not ok:
            print("  stderr tail:", r.stderr.strip()[-500:], flush=True)
            open(f"{HERE}/soak-errors.log", "a").write(
                f"--- cycle {cycle} @ {time.strftime('%Y-%m-%d %H:%M:%S')} rc={r.returncode}\n"
                + r.stdout[-2000:] + r.stderr[-2000:] + "\n")
        heartbeat(args.ledger, args.url, note=f"post-cycle {cycle} rc={r.returncode}")
        # honour deadline mid-cycle
        if deadline is not None and time.time() >= deadline:
            break
        time.sleep(args.gap)
    print("soak complete", flush=True)


if __name__ == "__main__":
    main()

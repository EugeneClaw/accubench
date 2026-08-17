"""Append-only JSONL ledger + aggregation + comparison."""
import json
import os
import statistics

from .explainer import for_task


def append_record(path, rec):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def load_ledger(path, tags=None):
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue  # torn tail line from a crash; skip, never crash
            if tags and r.get("tag") not in tags:
                continue
            recs.append(r)
    return recs


def aggregate(recs):
    """Aggregate one tag's records into summary stats (with category and purpose breakdowns)."""
    out = _flat_stats(recs)
    cats = {}
    for r in recs:
        c = r.get("category", "misc")
        cats.setdefault(c, []).append(r)
    out["categories"] = {c: _flat_stats(v) for c, v in sorted(cats.items())}

    # purpose breakdown for the human-facing report
    purposes = {}
    for r in recs:
        p, _, _ = for_task(r.get("task", ""))
        purposes.setdefault(p, []).append(r)
    out["by_purpose"] = {p: _flat_stats(v) for p, v in sorted(purposes.items())}
    return out


def _flat_stats(recs):
    """Stats for one homogeneous set of records (no category recursion)."""
    if not recs:
        return {}
    done = [r for r in recs if not r.get("error")]
    passed = [r for r in done if r.get("pass")]
    toks = [r["tok_s"] for r in done if r.get("tok_s") is not None]
    out = {
        "n": len(recs),
        "n_ok": len(done),
        "n_pass": len(passed),
        "pass_rate": round(len(passed) / len(recs), 4),
        "raw_tps": round(statistics.median(toks), 1) if toks else None,
        "eff_tps": None,
        "wall_total_s": round(sum(r.get("wall_s", 0) for r in recs), 1),
        "accept_pct": None,
    }
    accs = [r["accept_pct"] for r in done if r.get("accept_pct") is not None]
    if accs:
        out["accept_pct"] = round(statistics.mean(accs), 1)
        out["accept_pct_median"] = round(statistics.median(accs), 1)
    if out["raw_tps"] is not None:
        out["eff_tps"] = round(out["raw_tps"] * out["pass_rate"], 1)
    return out


def _fmt_delta(a, b):
    if a is None or b is None:
        return "—"
    d = a - b
    arrow = "▲" if d > 0 else ("▼" if d < 0 else "=")
    return f"{d:+.1f} {arrow}"


def compare(recs_a, recs_b, tag_a, tag_b):
    """Human-readable comparison table of two tags."""
    A, B = aggregate(recs_a), aggregate(recs_b)
    hdr = f"{'metric':16s} {tag_a:>14s} {tag_b:>14s}   delta"
    lines = [hdr, "-" * len(hdr)]
    for k, label in (("raw_tps", "raw t/s"), ("pass_rate", "pass rate"),
                     ("eff_tps", "eff t/s"), ("accept_pct", "accept %"),
                     ("wall_total_s", "total wall s")):
        va, vb = A.get(k), B.get(k)
        if k == "pass_rate" and va is not None and vb is not None:
            va, vb = round(100 * va, 1), round(100 * vb, 1)
        lines.append(f"{label:16s} {str(va):>14s} {str(vb):>14s}   {_fmt_delta(va, vb)}")
    lines.append("")
    per_a = {t: r for t, r in ((r["task"], r) for r in recs_a if not r.get("error"))}
    per_b = {t: r for t, r in ((r["task"], r) for r in recs_b if not r.get("error"))}
    flips = []
    for t in sorted(set(per_a) & set(per_b)):
        pa, pb = per_a[t].get("pass"), per_b[t].get("pass")
        if pa != pb:
            flips.append(f"  {t}: {tag_a}={'PASS' if pa else 'FAIL'}  {tag_b}={'PASS' if pb else 'FAIL'}")
    lines.append("task flips: " + (str(len(flips)) if flips else "none"))
    lines.extend(flips[:20])
    return lines

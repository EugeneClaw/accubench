"""Self-contained HTML report: inline SVG, dark theme, zero external assets.

Three views:
- run view (one recipe) — number, per-purpose radar, per-task table, hardware-fit verdict
- compare view (two recipes) — side-by-side, per-task deltas, headline winners
"""
import html
import json
import math
import os
import statistics
from collections import OrderedDict

from .explainer import (for_task, fail_hint, PURPOSE_DESCRIPTIONS,
                        DIFFICULTY_DESCRIPTIONS)
from .ledger import aggregate, suite_of
from .expectations import classify_fit, hw_class_blurb

DARK = {
    "bg": "#0f1216",
    "panel": "#1a1f26",
    "panel2": "#22272e",
    "ink": "#e6e9ef",
    "ink_dim": "#8a93a0",
    "accent": "#4dd2c0",
    "good": "#5dd576",
    "warn": "#f0b94e",
    "bad": "#e26a6a",
    "rule": "#2a3138",
}

_EXPECTED = None


def _expected_pass(task_id):
    """Did the reference rig (5090 + 27B IQ4_XS soak) pass this task?

    Returns True/False from expected_pass.json, or None when unknown.
    Badge context only — never affects grading.
    """
    global _EXPECTED
    if _EXPECTED is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "expected_pass.json")
        try:
            with open(path, encoding="utf-8") as f:
                _EXPECTED = json.load(f)
        except Exception:
            _EXPECTED = {}
    bucket = "quick" if task_id.startswith("q-") else "full"
    return _EXPECTED.get(bucket, {}).get(task_id)


def _escape(s):
    return html.escape(str(s), quote=True)


def _bar(value, vmax, color=None):
    """Inline SVG horizontal bar. value is 0..vmax."""
    color = color or DARK["accent"]
    pct = max(0, min(100, (value / vmax) * 100)) if vmax else 0
    return (
        f'<svg width="120" height="14" viewBox="0 0 120 14" '
        f'style="vertical-align:middle">'
        f'<rect x="0" y="2" width="120" height="10" rx="5" fill="{DARK["panel2"]}"/>'
        f'<rect x="0" y="2" width="{pct*1.2:.1f}" height="10" rx="5" fill="{color}"/>'
        f'</svg>'
    )


def _radar(by_purpose, size=240):
    """Radar chart of pass rate by purpose.

    Tested axes only: purposes that actually have tasks get an axis. Purposes
    with no tasks in the suite are listed underneath as 'not tested' — a
    missing axis is 'we never asked', never 'the model scored zero'.
    """
    tested = {p: s for p, s in by_purpose.items() if s.get("n")}
    untested = [p for p in PURPOSE_DESCRIPTIONS if p not in tested]
    purposes = [p for p in PURPOSE_DESCRIPTIONS if p in tested]
    cos, sin = math.cos, math.sin
    n = len(purposes)
    if n == 0:
        note = ("No purposes tested — " + ", ".join(untested) + " not tested."
                if untested else "No purposes tested.")
        return f'<div class="hint">{_escape(note)}</div>'
    cx = cy = size / 2
    r = size * 0.38
    # axis rings
    rings = ""
    for level in (0.25, 0.5, 0.75, 1.0):
        pts = []
        for i in range(n):
            a = (2 * math.pi * i / n) - math.pi / 2
            x = cx + r * level * math.cos(a)
            y = cy + r * level * math.sin(a)
            pts.append(f"{x:.1f},{y:.1f}")
        rings += f'<polygon points="{" ".join(pts)}" fill="none" stroke="{DARK["rule"]}" stroke-width="1"/>'
    # data polygon
    data_pts = []
    labels = []
    for i, p in enumerate(purposes):
        a = (2 * math.pi * i / n) - math.pi / 2
        v = tested[p].get("pass_rate", 0) or 0
        x = cx + r * v * cos(a)
        y = cy + r * v * sin(a)
        data_pts.append(f"{x:.1f},{y:.1f}")
        lx = cx + (r + 24) * cos(a)
        ly = cy + (r + 18) * sin(a)
        anchor = "middle"
        if cos(a) > 0.3:
            anchor = "start"
        elif cos(a) < -0.3:
            anchor = "end"
        labels.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'fill="{DARK["ink_dim"]}" font-size="11">{_escape(p)}</text>'
        )
        # dot at value
        labels.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{DARK["accent"]}"/>'
        )
    inner = (
        rings
        + f'<polygon points="{" ".join(data_pts)}" fill="{DARK["accent"]}" '
          f'fill-opacity="0.18" stroke="{DARK["accent"]}" stroke-width="2"/>'
        + "".join(labels)
    )
    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'style="display:block;margin:0 auto">{inner}</svg>'
    )
    if untested:
        note = "Not tested by this suite: " + ", ".join(untested) + "."
        svg += f'<div class="hint" style="text-align:center">{_escape(note)}</div>'
    return svg


def _headline_card(label, value, sub="", color=None):
    color = color or DARK["ink"]
    return (
        f'<div class="card">'
        f'<div class="card-label">{_escape(label)}</div>'
        f'<div class="card-value" style="color:{color}">{_escape(value)}</div>'
        f'<div class="card-sub">{_escape(sub)}</div>'
        f'</div>'
    )


def _band_chart(agg, band, klass, suite, width=520, height=120):
    """Your median vs the typical band, with the band's source shown.

    Shows the band as a shaded region with lo/hi labels, your median as a
    marker, and mean/p10/p90 as a jitter strip below. The band source is
    printed verbatim so nobody mistakes n=1 for a crowd.
    """
    obs = agg.get("raw_tps") or 0
    lo, hi, src = band if band else (None, None, "")
    lo = lo or 0
    hi = max(hi or 0, obs * 1.25, 1)
    vmax = max(hi * 1.18, obs * 1.18, 10)
    def X(v):
        return 14 + (v / vmax) * (width - 28)
    parts = []
    if band:
        band_fill = (DARK["good"] if klass in ("in", "above") else
                     DARK["warn"] if klass == "below" else DARK["accent"])
        parts.append(
            f'<rect x="{X(lo):.1f}" y="18" width="{X(hi)-X(lo):.1f}" height="26" '
            f'rx="4" fill="{band_fill}" fill-opacity="0.18" stroke="{band_fill}" '
            f'stroke-opacity="0.55"/>'
        )
        parts.append(
            f'<text x="{X(lo):.1f}" y="58" text-anchor="middle" '
            f'fill="{DARK["ink_dim"]}" font-size="10">{lo:.0f}</text>'
        )
        parts.append(
            f'<text x="{X(hi):.1f}" y="58" text-anchor="middle" '
            f'fill="{DARK["ink_dim"]}" font-size="10">{hi:.0f}</text>'
        )
    mark_color = (DARK["good"] if klass in ("in", "above") else DARK["warn"])
    parts.append(
        f'<line x1="{X(obs):.1f}" y1="12" x2="{X(obs):.1f}" y2="50" '
        f'stroke="{mark_color}" stroke-width="3"/>'
    )
    parts.append(
        f'<text x="{X(obs):.1f}" y="10" text-anchor="middle" '
        f'fill="{mark_color}" font-size="11" font-weight="600">'
        f'you {obs:.1f}</text>'
    )
    # p10/p90/mean jitter strip
    p10, p90 = agg.get("p10_tps"), agg.get("p90_tps")
    if p10 is not None and p90 is not None:
        parts.append(
            f'<rect x="{X(p10):.1f}" y="72" width="{max(2, X(p90)-X(p10)):.1f}" '
            f'height="6" rx="3" fill="{DARK["panel2"]}" stroke="{DARK["rule"]}"/>'
        )
        for key, col in (("mean_tps", DARK["accent"]), ("raw_tps", DARK["ink"])):
            v = agg.get(key)
            if v is not None:
                parts.append(
                    f'<line x1="{X(v):.1f}" y1="68" x2="{X(v):.1f}" '
                    f'y2="82" stroke="{col}" stroke-width="2"/>'
                )
        parts.append(
            f'<text x="{X(p10):.1f}" y="96" text-anchor="middle" '
            f'fill="{DARK["ink_dim"]}" font-size="10">p10 {p10:.0f}</text>'
        )
        tick_side = "start" if X(p90) < width * 0.85 else "end"
        parts.append(
            f'<text x="{X(p90):.1f}" y="96" text-anchor="{tick_side}" '
            f'fill="{DARK["ink_dim"]}" font-size="10">p90 {p90:.0f}</text>'
        )
    # generation-only median: cache-invariant context
    gen = agg.get("gen_tps_median")
    if gen:
        gx = X(min(gen, vmax * 0.97))
        parts.append(
            f'<line x1="{gx:.1f}" y1="66" x2="{gx:.1f}" y2="84" '
            f'stroke="{DARK["accent"]}" stroke-width="2" stroke-dasharray="3 2"/>'
        )
        parts.append(
            f'<text x="{gx:.1f}" y="62" text-anchor="middle" '
            f'fill="{DARK["accent"]}" font-size="10">gen {gen:.0f}</text>'
        )
    note = "wall-clock includes prompt processing; gen is decode-only (cache-invariant)"
    parts.append(
        f'<text x="{width-14}" y="112" text-anchor="end" '
        f'fill="{DARK["ink_dim"]}" font-size="10">{_escape(note)}</text>'
    )
    parts.append(
        f'<text x="14" y="112" fill="{DARK["ink_dim"]}" font-size="10">'
        f'{_escape("band: " + (suite or "this suite") + " on this hardware")}'
        f'{(" — " + src) if src else ""}</text>'
    )
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="max-width:100%">{"".join(parts)}</svg>'
    )


def _task_row(r, show_tag=False):
    check = "✓" if r.get("pass") else "✗"
    color = DARK["good"] if r.get("pass") else DARK["bad"]
    purpose, difficulty, plain = for_task(r.get("task", ""))
    tok_s = r.get("tok_s") or 0
    # expected-pass badge: what the reference rig did on this task
    exp = _expected_pass(r.get("task", ""))
    badge = ""
    if exp is False:
        badge = ('<span class="tag dim" title="The reference rig '
                 '(RTX 5090 + 27B IQ4_XS) also fails this task — a fail here '
                 'is normal, not a fault in your setup.">ref fails too</span>')
    elif exp is True and not r.get("pass"):
        badge = ('<span class="tag" style="color:' + DARK["warn"] + '" '
                 'title="The reference rig passes this task — this fail is '
                 'worth a look.">ref passes</span>')
    hint = "" if r.get("pass") else fail_hint(purpose, difficulty)
    return (
        f'<tr>'
        f'<td><span class="chk" style="color:{color}">{check}</span></td>'
        f'<td class="t">{_escape(r.get("task", ""))}</td>'
        f'<td class="d">{_escape(plain)}</td>'
        f'<td><span class="tag">{_escape(purpose)}</span></td>'
        f'<td><span class="tag dim">{_escape(difficulty)}</span></td>'
        f'<td class="num">{tok_s:.1f}</td>'
        f'<td class="num">{(r.get("accept_pct") or 0):.0f}%</td>'
        + (f'<td class="tag">{_escape(r.get("tag", ""))}</td>' if show_tag else "")
        + '</tr>'
        + (f'<tr class="failrow"><td></td><td colspan="7" class="hint">'
           f'<b>Why it matters:</b> {_escape(hint)}</td></tr>' if hint else "")
        + (f'<tr class="failrow"><td></td><td colspan="7" class="hint">{badge}</td></tr>' if badge else "")
    )


def _css():
    return f"""
    body {{ background: {DARK["bg"]}; color: {DARK["ink"]}; font-family: -apple-system, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif; margin: 0; padding: 32px; line-height: 1.45; }}
    .wrap {{ max-width: 1100px; margin: 0 auto; }}
    h1 {{ font-size: 28px; margin: 0 0 8px; font-weight: 600; }}
    h2 {{ font-size: 18px; margin: 32px 0 12px; font-weight: 600; color: {DARK["ink"]}; }}
    .sub {{ color: {DARK["ink_dim"]}; margin: 0 0 24px; }}
    .row {{ display: flex; gap: 16px; flex-wrap: wrap; }}
    .card {{ background: {DARK["panel"]}; border-radius: 12px; padding: 16px 20px; flex: 1 1 180px; min-width: 160px; }}
    .card-label {{ color: {DARK["ink_dim"]}; font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }}
    .card-value {{ font-size: 32px; font-weight: 600; }}
    .card-sub {{ color: {DARK["ink_dim"]}; font-size: 12px; margin-top: 4px; }}
    .panel {{ background: {DARK["panel"]}; border-radius: 12px; padding: 20px; margin: 16px 0; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid {DARK["rule"]}; }}
    th {{ color: {DARK["ink_dim"]}; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.04em; }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    td.t {{ font-family: 'SF Mono', Menlo, monospace; font-size: 13px; }}
    td.d {{ color: {DARK["ink_dim"]}; font-size: 13px; }}
    .tag {{ display: inline-block; background: {DARK["panel2"]}; padding: 2px 8px; border-radius: 6px; font-size: 12px; }}
    .tag.dim {{ color: {DARK["ink_dim"]}; }}
    .chk {{ font-size: 16px; font-weight: 700; }}
    .verdict {{ padding: 12px 16px; border-radius: 8px; margin: 12px 0; }}
    .verdict.good {{ background: rgba(93,213,118,0.10); color: {DARK["good"]}; }}
    .verdict.warn {{ background: rgba(240,185,78,0.10); color: {DARK["warn"]}; }}
    .verdict.bad  {{ background: rgba(226,106,106,0.10); color: {DARK["bad"]}; }}
    .verdict.dim  {{ background: {DARK["panel2"]}; color: {DARK["ink_dim"]}; }}
    a {{ color: {DARK["accent"]}; }}
    .hint {{ color: {DARK["ink_dim"]}; font-size: 13px; margin-top: 6px; }}
    """


def _html_doc(title, content):
    return (
        f'<!DOCTYPE html><html><head><meta charset="utf-8">'
        f'<title>{_escape(title)}</title>'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<style>{_css()}</style></head><body>'
        f'<div class="wrap">{content}</div></body></html>'
    )


# ---------- RUN VIEW (one recipe) ----------

def render_run_view(tag, recs, props=None, fit_band=None, fit_class="unknown",
                    hw_class=None, title=None, suite=None):
    agg = aggregate(recs)
    n = agg.get("n", 0)
    pr = agg.get("pass_rate", 0)
    rtps = agg.get("raw_tps", 0)
    etps = agg.get("eff_tps", 0)
    title = title or f"effbench · {tag}"
    by_purpose = agg.get("by_purpose", {})
    suite = suite or suite_of(recs)

    # hardware-fit verdict — band provenance labelled
    src_note = ""
    if fit_band:
        lo, hi, src = fit_band
        scale_note = (" Quick tasks are short, so this band is scaled ×0.89 "
                      "for a fair comparison." if suite == "quick" else "")
        if fit_class == "above":
            verdict_html = (
                f'<div class="verdict good"><b>Faster than typical</b> for '
                f'{_escape(hw_class or "this hardware")} '
                f'(typical {lo}–{hi} tok/s, yours {rtps:.1f}).{scale_note}</div>'
            )
        elif fit_class == "in":
            verdict_html = (
                f'<div class="verdict good"><b>Typical</b> for '
                f'{_escape(hw_class or "this hardware")} '
                f'(typical {lo}–{hi} tok/s, yours {rtps:.1f}).{scale_note}</div>'
            )
        elif fit_class == "below":
            gen = agg.get("gen_tps_median")
            if gen and gen >= lo:
                cache_note = (
                    f" But generation-only speed is {gen:.1f} tok/s — inside "
                    f"the typical band. Your server isn't slow; wall-clock is "
                    f"dragged by prompt processing, which is normal on a "
                    f"first/cold run or short tasks."
                )
            else:
                cache_note = (
                    " Common causes: background load, slow KV cache quant, "
                    "reasoning model with thinking enabled, no speculative decoding."
                )
            verdict_html = (
                f'<div class="verdict warn"><b>Slower than typical</b> for '
                f'{_escape(hw_class or "this hardware")} '
                f'(typical {lo}–{hi} tok/s, yours {rtps:.1f}).{scale_note}'
                f'{cache_note}</div>'
            )
        else:
            verdict_html = (
                f'<div class="verdict dim">No reference data for this '
                f'{_escape(hw_class or "hardware")} + model combo.</div>'
            )
        if src:
            shown = (("reference: " + src[len("measured: "):])
                     if src.startswith("measured:") else ("band source: " + src))
            src_note = f'<div class="hint">{_escape(shown)}</div>'
    else:
        verdict_html = (
            '<div class="verdict dim">Could not detect hardware/model for '
            'reference comparison.</div>'
        )

    # purpose radar
    radar_svg = _radar(by_purpose)

    # purpose table
    purpose_rows = []
    for purpose, stats in by_purpose.items():
        purpose_rows.append(
            f'<tr><td>{_escape(purpose)}</td>'
            f'<td class="d">{_escape(PURPOSE_DESCRIPTIONS.get(purpose, ""))}</td>'
            f'<td class="num">{stats.get("n_pass", 0)}/{stats.get("n", 0)}</td>'
            f'<td class="num">{(stats.get("pass_rate", 0) or 0)*100:.0f}%</td>'
            f'<td class="num">{(stats.get("raw_tps") or 0):.1f}</td></tr>'
        )

    # tasks table
    task_rows = "\n".join(_task_row(r) for r in sorted(recs, key=lambda r: r["task"]))

    # hardware blurb
    blurb = ""
    if hw_class:
        b = hw_class_blurb(hw_class)
        if b:
            blurb = f'<div class="hint"><b>{_escape(hw_class)}:</b> {_escape(b)}</div>'

    # generation-only card when the server reported it
    gen_card = ""
    if agg.get("gen_tps_median"):
        gen_card = _headline_card(
            "Generation-only", f"{agg['gen_tps_median']:.1f}",
            "tok/s server-reported (excludes prompt processing)")

    body = f"""
    <h1>{_escape(title)}</h1>
    <p class="sub">{n} tasks · pass rate {pr*100:.1f}% · {suite} suite · generated by effbench</p>

    <div class="row">
      {_headline_card("Pass rate", f"{pr*100:.1f}%", f"{agg.get('n_pass', 0)} of {n} tasks")}
      {_headline_card("Median speed", f"{rtps:.1f}", "tok/s · the headline number")}
      {_headline_card("Effective speed", f"{etps:.1f}", "median × pass rate")}
    </div>

    <div class="row">
      {_headline_card("Mean", f"{agg.get('mean_tps') or 0:.1f}", "tok/s · all tasks")}
      {_headline_card("Peak", f"{agg.get('peak_tps') or 0:.1f}", "tok/s · fastest task")}
      {_headline_card("p10–p90", f"{agg.get('p10_tps') or 0:.0f}–{agg.get('p90_tps') or 0:.0f}", "tok/s · task spread")}
      {_headline_card("Speculative decode", f"{(agg.get('accept_pct_median') or 0):.0f}%",
                       "draft accept rate (0 if none)")}
    </div>
    {gen_card}

    {verdict_html}
    {src_note}

    <div class="panel">
      <h2>Speed vs typical</h2>
      <p class="sub">Your median against the typical band for this hardware + model — and where the band came from.</p>
      {_band_chart(agg, fit_band, fit_class, suite)}
    </div>

    <div class="panel">
      <h2>What this model is good for</h2>
      <p class="sub">Pass rate grouped by what the task is actually used for. The bigger the green area, the broader the model.</p>
      <div style="display:flex;gap:24px;align-items:center;flex-wrap:wrap">
        {radar_svg}
        <div style="flex:1;min-width:280px">
          <table>
            <tr><th>purpose</th><th>what it is</th><th class="num">pass</th><th class="num">rate</th><th class="num">tok/s</th></tr>
            {"".join(purpose_rows)}
          </table>
        </div>
      </div>
      {blurb}
    </div>

    <div class="panel">
      <h2>Every task</h2>
      <p class="sub">A green tick means the model's answer passed the deterministic check. A red ✗ gets a what-it-means note and a reference badge: <span class="tag dim">ref fails too</span> — the reference rig (RTX 5090 + 27B IQ4_XS) also fails this task, so a fail is expected here. <span class="tag" style="color:{DARK['warn']}">ref passes</span> — the reference rig passes it, so this fail is the interesting kind.</p>
      <table>
        <tr><th></th><th>task</th><th>what it asks</th><th>purpose</th><th>difficulty</th><th class="num">tok/s</th><th class="num">accept</th></tr>
        {task_rows}
      </table>
    </div>

    <p class="hint">Generated by effbench. Reproducible: <code>python3 -m effbench run --tag {tag} --suite &lt;suite&gt</code></p>
    """
    return _html_doc(title, body)


# ---------- COMPARE VIEW (two recipes) ----------

def render_compare_view(tag_a, recs_a, tag_b, recs_b,
                        band_a=None, band_b=None,
                        class_a="unknown", class_b="unknown",
                        hw_class=None, title=None):
    A, B = aggregate(recs_a), aggregate(recs_b)
    title = title or f"effbench · {tag_a} vs {tag_b}"

    def card(tag, agg, band, klass):
        pr = agg.get("pass_rate", 0)
        rtps = agg.get("raw_tps", 0)
        etps = agg.get("eff_tps", 0)
        fit = ("above" if klass == "above" else
               "in" if klass == "in" else
               "below" if klass == "below" else "—")
        fit_color = (DARK["good"] if klass == "above" else
                     DARK["good"] if klass == "in" else
                     DARK["warn"] if klass == "below" else DARK["ink_dim"])
        return (
            f'<div class="card">'
            f'<div class="card-label">{_escape(tag)}</div>'
            f'<div class="card-value">{rtps:.1f}</div>'
            f'<div class="card-sub">raw tok/s · pass {pr*100:.0f}% · eff {etps:.1f}</div>'
            f'<div class="card-sub" style="color:{fit_color}">'
            f'fit: {_escape(fit)}</div>'
            f'</div>'
        )

    # overall deltas
    def delta_arrow(a, b):
        if a is None or b is None:
            return "—"
        d = b - a
        sym = "▲" if d > 0 else ("▼" if d < 0 else "=")
        return f"{d:+.1f} {sym}"

    headers_row = (
        f'<tr>'
        f'<th></th><th>task</th><th>what it asks</th>'
        f'<th class="num">{_escape(tag_a)} pass</th><th class="num">{_escape(tag_a)} t/s</th>'
        f'<th class="num">{_escape(tag_b)} pass</th><th class="num">{_escape(tag_b)} t/s</th>'
        f'<th class="num">Δt/s</th><th class="num">Δpass</th>'
        f'</tr>'
    )

    per_a = {r["task"]: r for r in recs_a}
    per_b = {r["task"]: r for r in recs_b}
    task_rows = []
    for tid in sorted(set(per_a) | set(per_b)):
        ra = per_a.get(tid, {})
        rb = per_b.get(tid, {})
        purpose, difficulty, plain = for_task(tid)
        pa = ra.get("pass")
        pb = rb.get("pass")
        if pa is True and pb is True:
            chka, chkb = "✓", "✓"
        elif pa is True and pb is False:
            chka, chkb = "✓", "✗"
            chkb_color = DARK["bad"]
        elif pa is False and pb is True:
            chka, chkb = "✗", "✓"
            chka_color = DARK["bad"]
        else:
            chka, chkb = "✗", "✗"
        d_tps = delta_arrow(ra.get("tok_s"), rb.get("tok_s"))
        d_pass = ""
        if pa is not None and pb is not None:
            d_pass = "+1" if pb and not pa else ("-1" if pa and not pb else "0")
        color_a = DARK["bad"] if pa is False else DARK["good"]
        color_b = DARK["bad"] if pb is False else DARK["good"]
        task_rows.append(
            f'<tr>'
            f'<td><span class="chk" style="color:{color_a}">{chka}</span> '
            f'<span class="chk" style="color:{color_b}">{chkb}</span></td>'
            f'<td class="t">{_escape(tid)}</td>'
            f'<td class="d">{_escape(plain)}</td>'
            f'<td class="num">{(ra.get("tok_s") or 0):.1f}</td>'
            f'<td class="num">{(ra.get("accept_pct") or 0):.0f}%</td>'
            f'<td class="num">{(rb.get("tok_s") or 0):.1f}</td>'
            f'<td class="num">{(rb.get("accept_pct") or 0):.0f}%</td>'
            f'<td class="num">{d_tps}</td>'
            f'<td class="num">{d_pass}</td>'
            f'</tr>'
        )

    body = f"""
    <h1>{_escape(title)}</h1>
    <p class="sub">{A.get("n", 0)} tasks · generated by effbench</p>

    <div class="row">
      {card(tag_a, A, band_a, class_a)}
      {card(tag_b, B, band_b, class_b)}
      {_headline_card("Δ raw t/s", delta_arrow(A.get("raw_tps"), B.get("raw_tps")),
                      "tokens per second change", color=DARK["accent"])}
      {_headline_card("Δ pass rate",
                      f"{(B.get('pass_rate', 0) - A.get('pass_rate', 0))*100:+.1f}%",
                      "absolute percentage points",
                      color=DARK["accent"] if (B.get('pass_rate', 0) >= A.get('pass_rate', 0)) else DARK["bad"])}
    </div>

    <div class="panel">
      <h2>Per-task comparison</h2>
      <p class="sub">Left column is <code>{_escape(tag_a)}</code>, right is <code>{_escape(tag_b)}</code>. A red ✗ means the model failed that task. Δpass = +1 means <code>{_escape(tag_b)}</code> gained that task; -1 means it lost it.</p>
      <table>
        {headers_row}
        {"".join(task_rows)}
      </table>
    </div>

    <p class="hint">Generated by effbench.</p>
    """
    return _html_doc(title, body)


def render_report(tags_data, props=None, title=None, mode="run"):
    """Top-level entry.

    tags_data: list of (tag, recs, [band, class, hw_class]) tuples.
    mode: 'run' for single-recipe view; 'compare' for two-recipe view.
    """
    if mode == "compare" and len(tags_data) >= 2:
        tag_a, recs_a, ba, ca, ha = tags_data[0]
        tag_b, recs_b, bb, cb, hb = tags_data[1]
        return render_compare_view(tag_a, recs_a, tag_b, recs_b,
                                   band_a=ba, band_b=bb,
                                   class_a=ca, class_b=cb,
                                   hw_class=ha or hb)
    tag, recs, band, klass, hwc = tags_data[0]
    return render_run_view(tag, recs, props=props, fit_band=band,
                           fit_class=klass, hw_class=hwc, title=title)
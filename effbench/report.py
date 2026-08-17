"""Self-contained HTML report: inline SVG, dark theme, zero external assets.

Three views:
- run view (one recipe) — number, per-purpose radar, per-task table, hardware-fit verdict
- compare view (two recipes) — side-by-side, per-task deltas, headline winners
"""
import html
import statistics
from collections import OrderedDict

from .explainer import for_task, PURPOSE_DESCRIPTIONS, DIFFICULTY_DESCRIPTIONS
from .ledger import aggregate
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
    """Radar chart of pass-rate by purpose, 0..1 axes."""
    purposes = list(PURPOSE_DESCRIPTIONS.keys())
    # ensure we draw all, even if missing
    n = len(purposes)
    cx = cy = size / 2
    r = size * 0.38
    # axis rings
    rings = ""
    for level in (0.25, 0.5, 0.75, 1.0):
        pts = []
        import math
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
        v = by_purpose.get(p, {}).get("pass_rate", 0) or 0
        x = cx + r * v * math.cos(a)
        y = cy + r * v * math.sin(a)
        data_pts.append(f"{x:.1f},{y:.1f}")
        lx = cx + (r + 24) * math.cos(a)
        ly = cy + (r + 18) * math.sin(a)
        anchor = "middle"
        if math.cos(a) > 0.3:
            anchor = "start"
        elif math.cos(a) < -0.3:
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
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'style="display:block;margin:0 auto">{inner}</svg>'
    )


def _headline_card(label, value, sub="", color=None):
    color = color or DARK["ink"]
    return (
        f'<div class="card">'
        f'<div class="card-label">{_escape(label)}</div>'
        f'<div class="card-value" style="color:{color}">{_escape(value)}</div>'
        f'<div class="card-sub">{_escape(sub)}</div>'
        f'</div>'
    )


def _task_row(r, show_tag=False):
    check = "✓" if r.get("pass") else "✗"
    color = DARK["good"] if r.get("pass") else DARK["bad"]
    purpose, difficulty, plain = for_task(r.get("task", ""))
    tok_s = r.get("tok_s") or 0
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
                    hw_class=None, title=None):
    agg = aggregate(recs)
    n = agg.get("n", 0)
    pr = agg.get("pass_rate", 0)
    rtps = agg.get("raw_tps", 0)
    etps = agg.get("eff_tps", 0)
    title = title or f"effbench · {tag}"
    by_purpose = agg.get("by_purpose", {})

    # hardware-fit verdict
    if fit_band:
        lo, hi, ref = fit_band
        if fit_class == "above":
            verdict_html = (
                f'<div class="verdict good"><b>Faster than typical</b> for '
                f'{_escape(hw_class or "this hardware")} '
                f'(typical {lo}–{hi} tok/s, '
                f'yours {rtps:.1f}).</div>'
            )
        elif fit_class == "in":
            verdict_html = (
                f'<div class="verdict good"><b>Typical</b> for '
                f'{_escape(hw_class or "this hardware")} '
                f'(typical {lo}–{hi} tok/s, yours {rtps:.1f}).</div>'
            )
        elif fit_class == "below":
            verdict_html = (
                f'<div class="verdict warn"><b>Slower than typical</b> for '
                f'{_escape(hw_class or "this hardware")} '
                f'(typical {lo}–{hi} tok/s, yours {rtps:.1f}). '
                f'Common causes: background load, slow KV cache quant, '
                f'reasoning model with thinking enabled, no speculative decoding.'
                f'</div>'
            )
        else:
            verdict_html = (
                f'<div class="verdict dim">No reference data for this '
                f'{_escape(hw_class or "hardware")} + model combo.</div>'
            )
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

    body = f"""
    <h1>{_escape(title)}</h1>
    <p class="sub">{n} tasks · pass rate {pr*100:.1f}% · generated by effbench</p>

    <div class="row">
      {_headline_card("Pass rate", f"{pr*100:.1f}%", f"{agg.get('n_pass', 0)} of {n} tasks")}
      {_headline_card("Raw speed", f"{rtps:.1f}", "tokens per second")}
      {_headline_card("Effective speed", f"{etps:.1f}", "raw × pass rate")}
      {_headline_card("Speculative decode", f"{(agg.get('accept_pct_median') or 0):.0f}%",
                       "draft accept rate (0 if none)")}
    </div>

    {verdict_html}

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
      <p class="sub">A green tick means the model's answer passed the deterministic check. A red cross means it didn't — and why.</p>
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
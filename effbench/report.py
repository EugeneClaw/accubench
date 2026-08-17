"""Self-contained HTML report: inline SVG, instrument theme, zero external assets.

Three views:
- run view (one recipe) — hero cluster, purpose ladder, per-task rows, verdict
- compare view (two recipes) — side-by-side, dumbbell deltas, per-task rows
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
from . import tokens as T

DARK = {
    "bg": T.VOID, "panel": T.CARBON, "panel2": T.GRAPHITE, "graphite": T.GRAPHITE,
    "ink": T.INK, "ink_dim": T.INK2, "accent": T.MINT,
    "good": T.PASS, "warn": T.WARN, "bad": T.FAIL,
    "rule": T.HAIRLINE, "hairline": T.HAIRLINE, "ink3": T.INK3, "track": T.INK_TRACK,
    "sans": T.SANS, "mono": T.MONO,
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


def _purpose_ladder(by_purpose, width=520):
    """Ranked pass-rate ladder, one rung per tested purpose.

    Tested rungs only: purposes that actually have tasks get a rung, ranked
    by pass rate then n. Purposes with no tasks in the suite are listed
    underneath as 'not tested' — a missing rung is 'we never asked', never
    'the model scored zero'. Rungs carry n so a 100% of 3 tasks can't
    masquerade as a 100% of 15.
    """
    tested = {p: s for p, s in by_purpose.items() if s.get("n")}
    untested = [p for p in PURPOSE_DESCRIPTIONS if p not in tested]
    rows = sorted(tested.items(),
                  key=lambda kv: (-(kv[1].get("pass_rate") or 0), -kv[1].get("n", 0), kv[0]))
    if not rows and not untested:
        return '<div class="hint">No purposes tested.</div>'
    parts = ['<div class="ladder">']
    if rows:
        total_n = sum(s.get("n", 0) for _, s in rows)
        parts.append(
            f'<div class="ladder-head"><span>pass rate by purpose</span>'
            f'<span>{total_n} task-runs</span></div>'
        )
    for p, s in rows:
        rate = s.get("pass_rate") or 0
        npass, ntot = s.get("n_pass", 0), s.get("n", 0)
        col = DARK["good"] if rate >= 0.5 else DARK["bad"]
        w = max(rate * 100, 1.5)  # a zero still shows its sliver
        parts.append(
            f'<div class="ladder-row">'
            f'<span class="ladder-name">{_escape(p)}</span>'
            f'<div class="ladder-track"><div class="ladder-fill" '
            f'style="width:{w:.1f}%;background:{col}"></div></div>'
            f'<span class="ladder-val" style="color:{col}">'
            f'{rate*100:.0f}% · {npass}/{ntot}</span>'
            f'</div>'
        )
    if untested:
        parts.append(
            f'<div class="ladder-miss">not tested in this suite — '
            f'{_escape(" · ".join(untested))}</div>'
        )
    parts.append("</div>")
    return "".join(parts)


def _hero_cluster(agg, suite):
    """The one composition: hero effective speed, supporting metrics, arc."""
    etps = agg.get("eff_tps") or 0
    rtps = agg.get("raw_tps") or 0
    gen = agg.get("gen_tps_median") or 0
    peak = agg.get("peak_tps") or 0
    p10, p90 = agg.get("p10_tps"), agg.get("p90_tps")
    n = agg.get("n", 0)
    npass = agg.get("n_pass", 0)
    pr = agg.get("pass_rate", 0) or 0
    acc = agg.get("accept_pct_median") or 0

    # mini-bar scale: everything shares one axis (max of observed values)
    scale = max(rtps, gen, peak, 1)

    def mb(label, value, color, text):
        w = max(2.0, (value / scale) * 100)
        return (
            f'<div class="mb-row"><span>{label}</span>'
            f'<div class="mb-track"><div class="mb-fill" '
            f'style="width:{w:.1f}%;background:{color}"></div></div>'
            f'<span class="mb-val">{text}</span></div>'
        )

    bars = mb("wall", rtps, DARK["ink_dim"], f"{rtps:.0f}")
    if gen:
        bars += mb("gen", gen, DARK["accent"], f"{gen:.0f}")
    if peak:
        bars += mb("peak", peak, DARK["ink3"], f"{peak:.0f}")

    sub_bits = [f"wall {rtps:.1f}"]
    if gen:
        sub_bits.append(f'gen-only <b>{gen:.1f}</b>')
    if peak:
        sub_bits.append(f"peak {peak:.1f}")
    if p10 is not None and p90 is not None:
        sub_bits.append(f"p10–p90 {p10:.0f}–{p90:.0f}")
    sub = ('<span class="sep">·</span>').join(sub_bits)

    # pass-rate arc: 240° gauge
    import math as _m
    cx, cy, r = 60, 62, 46
    a0, a1 = _m.radians(200), _m.radians(-20)
    large = 0
    x0, y0 = cx + r * _m.cos(a0), cy + r * _m.sin(a0)
    x1, y1 = cx + r * _m.cos(a1), cy + r * _m.sin(a1)
    track = f"M {x0:.1f} {y0:.1f} A {r} {r} 0 {large} 1 {x1:.1f} {y1:.1f}"
    av = a0 + (a1 - a0) * min(max(pr, 0), 1)
    xv, yv = cx + r * _m.cos(av), cy + r * _m.sin(av)
    fillp = f"M {x0:.1f} {y0:.1f} A {r} {r} 0 {large} 1 {xv:.1f} {yv:.1f}"
    arc_col = DARK["good"] if pr >= 0.8 else (DARK["warn"] if pr >= 0.5 else DARK["bad"])
    arc = (
        f'<svg width="120" height="76" viewBox="0 0 120 76">'
        f'<path d="{track}" fill="none" stroke="{DARK["track"]}" stroke-width="7" stroke-linecap="round"/>'
        f'<path d="{fillp}" fill="none" stroke="{arc_col}" stroke-width="7" stroke-linecap="round"/>'
        f'<text x="60" y="56" text-anchor="middle" fill="{DARK["ink"]}" font-size="24" '
        f'font-weight="600" font-family="system-ui,sans-serif">{pr*100:.0f}%</text>'
        f'</svg>'
    )
    accept = (
        f'<div class="accept-strip"><span>ACCEPT RATE</span>'
        f'<b>{acc:.0f}%</b></div>'
    ) if acc else ""
    return (
        f'<div class="cluster">'
        f'<div>'
        f'<div class="k-label">Effective speed · raw × pass rate</div>'
        f'<div class="k-hero"><span class="k-num">{etps:.1f}</span>'
        f'<span class="k-unit">tok/s</span></div>'
        f'<div class="k-sub">{sub}</div>'
        f'<div class="mini-bars">{bars}</div>'
        f'</div>'
        f'<div class="arc-wrap">'
        f'{arc}'
        f'<div class="arc-lbl">{npass} OF {n} PASS</div>'
        f'{accept}'
        f'</div>'
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
    purpose, difficulty, plain = for_task(r.get("task", ""))
    tok_s = r.get("tok_s") or 0
    ok = bool(r.get("pass"))
    # expected-pass badge: what the reference rig did on this task
    exp = _expected_pass(r.get("task", ""))
    badge = ""
    if exp is False:
        badge = ('<span class="tbadge" title="The reference rig '
                 '(RTX 5090 + 27B IQ4_XS) also fails this task — a fail here '
                 'is normal, not a fault in your setup.">ref fails too</span>')
    elif exp is True and not ok:
        badge = ('<span class="tbadge warn" '
                 'title="The reference rig passes this task — this fail is '
                 'worth a look.">ref passes</span>')
    meta_bits = [plain]
    if not ok:
        hint = fail_hint(purpose, difficulty)
        if hint:
            meta_bits.append(hint)
    if r.get("err"):
        meta_bits.append("server error")
    badge_html = badge or '<span class="tbadge" style="visibility:hidden">·</span>'
    return (
        f'<div class="trow">'
        f'<span class="tmark {"pass" if ok else "fail"}">{"✓" if ok else "✗"}</span>'
        f'<span class="tname">{_escape(r.get("task", ""))}</span>'
        f'<span class="tmeta" title="{_escape(" — ".join(meta_bits))}">'
        f'{_escape(" · ".join(meta_bits))}</span>'
        f'<span class="ttps">{tok_s:.1f}</span>'
        f'{badge_html}'
        + (f'<span class="tag dim">{_escape(r.get("tag", ""))}</span>' if show_tag else "")
        + '</div>'
    )


def _css():
    return f"""
    body {{ background: {DARK['bg']}; color: {DARK['ink']};
           font-family: {DARK['sans']}; margin: 0; padding: 36px 24px 72px;
           line-height: 1.5; -webkit-font-smoothing: antialiased; }}
    .wrap {{ max-width: 1100px; margin: 0 auto; }}
    h1 {{ font-size: 24px; margin: 0 0 6px; font-weight: 600; letter-spacing: -0.01em; }}
    h2 {{ font-size: 17px; margin: 0 0 4px; font-weight: 600; color: {DARK['ink']}; }}
    .sub {{ color: {DARK['ink_dim']}; margin: 0 0 0; font-size: 13.5px; }}
    .eyebrow {{ font-family: {DARK['mono']}; font-size: 10.5px; text-transform: uppercase;
               letter-spacing: 0.1em; color: {DARK['ink3']}; margin: 0 0 8px; }}
    .row {{ display: flex; gap: 1px; flex-wrap: wrap; background: {DARK['hairline']};
           border: 1px solid {DARK['hairline']}; border-radius: 14px; overflow: hidden; margin: 20px 0; }}
    .row > * {{ flex: 1 1 180px; min-width: 160px; }}

    /* hero cluster */
    .cluster {{ display: grid; grid-template-columns: 1.6fr 1fr; gap: 1px;
               background: {DARK['hairline']}; border: 1px solid {DARK['hairline']};
               border-radius: 14px; overflow: hidden; margin: 20px 0; }}
    .cluster > div {{ background: {DARK['panel']}; padding: 22px 24px 18px; }}
    .k-label {{ font-family: {DARK['mono']}; font-size: 10px; text-transform: uppercase;
               letter-spacing: 0.1em; color: {DARK['ink3']}; margin-bottom: 10px; }}
    .k-hero {{ display: flex; align-items: baseline; gap: 10px; }}
    .k-num {{ font-size: 56px; font-weight: 600; letter-spacing: -0.03em; line-height: 1;
             font-variant-numeric: tabular-nums; color: {DARK['ink']};
             text-shadow: 0 0 24px rgba(79,227,193,0.18); }}
    .k-unit {{ font-family: {DARK['mono']}; font-size: 12px; color: {DARK['ink3']}; }}
    .k-sub {{ font-family: {DARK['mono']}; font-size: 11.5px; color: {DARK['ink_dim']};
             margin-top: 12px; font-variant-numeric: tabular-nums; }}
    .k-sub .sep {{ color: {DARK['ink3']}; margin: 0 7px; }}
    .k-sub b {{ color: {DARK['accent']}; font-weight: 500; }}
    .mini-bars {{ margin-top: 14px; display: grid; gap: 8px; }}
    .mb-row {{ display: grid; grid-template-columns: 42px 1fr 64px; gap: 10px; align-items: center;
              font-family: {DARK['mono']}; font-size: 10px; color: {DARK['ink3']}; }}
    .mb-track {{ height: 4px; background: {DARK['track']}; border-radius: 2px; position: relative; }}
    .mb-fill {{ position: absolute; inset: 0 auto 0 0; border-radius: 2px; }}
    .mb-val {{ text-align: right; color: {DARK['ink_dim']}; font-variant-numeric: tabular-nums; }}
    .arc-wrap {{ display: flex; flex-direction: column; align-items: center;
                justify-content: center; text-align: center; }}
    .arc-num {{ font-size: 34px; font-weight: 600; letter-spacing: -0.02em;
               font-variant-numeric: tabular-nums; }}
    .arc-lbl {{ font-family: {DARK['mono']}; font-size: 10px; color: {DARK['ink3']};
               margin-top: 6px; letter-spacing: 0.1em; }}
    .accept-strip {{ margin-top: 16px; border-top: 1px solid {DARK['rule']}; padding-top: 12px;
                    display: flex; justify-content: space-between; font-family: {DARK['mono']};
                    font-size: 10px; color: {DARK['ink3']}; letter-spacing: 0.08em; }}
    .accept-strip b {{ color: {DARK['ink_dim']}; font-weight: 500; font-variant-numeric: tabular-nums; }}

    /* legacy headline cards (compare view) */
    .card {{ background: {DARK['panel']}; padding: 16px 20px; }}
    .card-label {{ color: {DARK['ink3']}; font-family: {DARK['mono']}; font-size: 10px;
                  text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px; }}
    .card-value {{ font-size: 30px; font-weight: 600; font-variant-numeric: tabular-nums; }}
    .card-sub {{ color: {DARK['ink_dim']}; font-size: 12px; margin-top: 4px; }}

    .panel {{ background: {DARK['panel']}; border: 1px solid {DARK['hairline']};
             border-radius: 14px; padding: 20px 22px; margin: 20px 0; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid {DARK['rule']}; }}
    th {{ color: {DARK['ink3']}; font-family: {DARK['mono']}; font-size: 10px; font-weight: 500;
         text-transform: uppercase; letter-spacing: 0.08em; }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    td.t {{ font-family: {DARK['mono']}; font-size: 12px; }}
    td.d {{ color: {DARK['ink_dim']}; font-size: 12.5px; }}
    .tag {{ display: inline-block; background: {DARK['graphite']}; padding: 2px 8px;
           border-radius: 5px; font-size: 11px; font-family: {DARK['mono']}; }}
    .tag.dim {{ color: {DARK['ink3']}; }}
    .chk {{ font-size: 14px; font-weight: 700; }}
    .verdict {{ padding: 14px 18px; border-radius: 10px; margin: 14px 0; font-size: 14px; }}
    .verdict.good {{ background: rgba(74,222,128,0.08); color: {DARK['good']};
                    border-left: 2px solid {DARK['good']}; }}
    .verdict.warn {{ background: rgba(251,191,36,0.07); color: {DARK['warn']};
                    border-left: 2px solid {DARK['warn']}; }}
    .verdict.bad  {{ background: rgba(248,113,113,0.07); color: {DARK['bad']};
                    border-left: 2px solid {DARK['bad']}; }}
    .verdict.dim  {{ background: {DARK['graphite']}; color: {DARK['ink_dim']};
                    border-left: 2px solid {DARK['rule']}; }}
    .verdict b {{ color: inherit; }}
    a {{ color: {DARK['accent']}; }}
    .hint {{ color: {DARK['ink_dim']}; font-size: 12.5px; margin-top: 6px; }}
    .ladder {{ margin-top: 4px; }}
    .ladder-head {{ display: flex; justify-content: space-between; font-family: {DARK['mono']};
                   font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em;
                   color: {DARK['ink3']}; margin-bottom: 14px; }}
    .ladder-row {{ display: grid; grid-template-columns: 86px 1fr 110px; gap: 12px;
                  align-items: center; padding: 8px 0; border-bottom: 1px solid {DARK['rule']}; }}
    .ladder-row:last-of-type {{ border-bottom: none; }}
    .ladder-name {{ font-family: {DARK['mono']}; font-size: 11.5px; color: {DARK['ink_dim']}; }}
    .ladder-track {{ height: 14px; background: {DARK['track']}; border-radius: 3px;
                    position: relative; overflow: hidden; }}
    .ladder-fill {{ position: absolute; inset: 0 auto 0 0; }}
    .ladder-val {{ font-family: {DARK['mono']}; font-size: 11px; text-align: right;
                  font-variant-numeric: tabular-nums; }}
    .ladder-miss {{ font-family: {DARK['mono']}; font-size: 10.5px; color: {DARK['ink3']};
                   padding-top: 12px; }}

    /* dumbbell compare rows */
    .db-row {{ display: grid; grid-template-columns: 92px 1fr 64px; gap: 12px; align-items: center;
              padding: 9px 0; border-bottom: 1px solid {DARK['rule']}; }}
    .db-row:last-of-type {{ border-bottom: none; }}
    .db-name {{ font-family: {DARK['mono']}; font-size: 11px; color: {DARK['ink_dim']}; }}
    .db-track {{ height: 16px; position: relative; }}
    .db-line {{ position: absolute; top: 7px; height: 2px; border-radius: 1px; }}
    .db-dot {{ position: absolute; top: 3px; width: 10px; height: 10px; border-radius: 50%;
              border: 2px solid {DARK['panel']}; }}
    .db-val {{ font-family: {DARK['mono']}; font-size: 11px; text-align: right;
              font-variant-numeric: tabular-nums; }}
    .db-legend {{ display: flex; gap: 16px; margin-top: 12px; font-family: {DARK['mono']};
                 font-size: 10px; color: {DARK['ink3']}; }}
    .db-legend i {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%;
                   margin-right: 5px; }}

    /* task metric rows */
    .trow {{ display: grid; grid-template-columns: 26px 150px 1fr 64px 84px; gap: 10px;
            align-items: center; padding: 9px 12px; border-radius: 8px; }}
    .trow:hover {{ background: {DARK['graphite']}; }}
    .tmark {{ width: 18px; height: 18px; border-radius: 5px; display: inline-flex;
             align-items: center; justify-content: center; font-size: 11px; font-weight: 700; }}
    .tmark.pass {{ background: rgba(74,222,128,0.12); color: {DARK['good']}; }}
    .tmark.fail {{ background: rgba(248,113,113,0.12); color: {DARK['bad']}; }}
    .tname {{ font-family: {DARK['mono']}; font-size: 11.5px; color: {DARK['ink']}; }}
    .tmeta {{ font-size: 11px; color: {DARK['ink3']}; overflow: hidden; text-overflow: ellipsis;
             white-space: nowrap; }}
    .ttps {{ font-family: {DARK['mono']}; font-size: 11.5px; text-align: right; color: {DARK['ink_dim']};
            font-variant-numeric: tabular-nums; }}
    .tbadge {{ font-family: {DARK['mono']}; font-size: 9.5px; text-align: center; border-radius: 4px;
              padding: 2px 6px; background: rgba(154,166,181,0.10); color: {DARK['ink3']};
              letter-spacing: 0.03em; justify-self: end; }}
    .tbadge.warn {{ background: rgba(251,191,36,0.12); color: {DARK['warn']}; }}

    @media (prefers-reduced-motion: reduce) {{
      * {{ transition: none !important; animation: none !important; }}
    }}
    @media print {{
      body {{ background: #fff; color: #111; }}
      .wrap {{ max-width: 100%; }}
    }}
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

    # purpose ladder
    ladder_html = _purpose_ladder(by_purpose)

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
    gen_note = ""
    if agg.get("gen_tps_median"):
        gen_note = (
            f'<div class="hint">Generation-only speed (server-reported, excludes '
            f'prompt processing): <b>{agg["gen_tps_median"]:.1f}</b> tok/s.</div>'
        )

    body = f"""
    <div class="eyebrow">effbench · {suite} suite · {n} task-runs</div>
    <h1>{_escape(title)}</h1>
    <p class="sub">pass rate {pr*100:.1f}% ({agg.get('n_pass', 0)} of {n}) · pass rate {pr*100:.1f}% · generated by effbench</p>

    {_hero_cluster(agg, suite)}

    {verdict_html}
    {src_note}
    {gen_note}

    <div class="panel">
      <h2>Speed vs typical</h2>
      <p class="sub">Your median against the typical band for this hardware + model — and where the band came from.</p>
      {_band_chart(agg, fit_band, fit_class, suite)}
    </div>

    <div class="panel">
      <h2>What this model is good for</h2>
      <p class="sub">Pass rate grouped by what the task is actually used for. The longer the green rung, the broader the model.</p>
      {ladder_html}
      <div style="margin-top:14px">
        <table>
          <tr><th>purpose</th><th>what it is</th><th class="num">pass</th><th class="num">rate</th><th class="num">tok/s</th></tr>
          {"".join(purpose_rows)}
        </table>
      </div>
      {blurb}
    </div>

    <div class="panel">
      <h2>Every task</h2>
      <p class="sub">A green tick means the model's answer passed the deterministic check. A red ✗ carries a what-it-means note (hover for detail) and a reference badge: <span class="tbadge">ref fails too</span> — the reference rig (RTX 5090 + 27B IQ4_XS) also fails this task, so a fail is expected here. <span class="tbadge warn">ref passes</span> — the reference rig passes it, so this fail is the interesting kind.</p>
      {task_rows}
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

    # dumbbell deltas: the distance between the dots is the finding
    def _pct(a, b):
        if not a:
            return "—" if not b else "new"
        d = ((b - a) / a) * 100
        return f"{d:+.0f}%"

    def dumbbell(label, a, b, fmt="{:.1f}"):
        """One metric, two dots, the line between them."""
        vmax = max(a or 0, b or 0, 1)
        xa = 4 + ((a or 0) / vmax) * 92
        xb = 4 + ((b or 0) / vmax) * 92
        lo, hi = min(xa, xb), max(xa, xb)
        gain = (b or 0) >= (a or 0)
        col = DARK["accent"] if gain else DARK["bad"]
        # direction indicator: b is the newer recipe, gains are mint
        return (
            f'<div class="db-row">'
            f'<span class="db-name">{_escape(label)}</span>'
            f'<div class="db-track">'
            f'<div class="db-line" style="left:{lo:.1f}%;width:{max(hi-lo,1.5):.1f}%;background:{DARK["ink3"]}"></div>'
            f'<div class="db-dot" style="left:calc({xa:.1f}% - 5px);background:{DARK["ink3"]}"></div>'
            f'<div class="db-dot" style="left:calc({xb:.1f}% - 5px);background:{col}"></div>'
            f'</div>'
            f'<span class="db-val" style="color:{col}">{_pct(a, b)}</span>'
            f'</div>'
        )

    dumbbells = "".join([
        dumbbell("effective", A.get("eff_tps"), B.get("eff_tps")),
        dumbbell("median wall", A.get("raw_tps"), B.get("raw_tps")),
        dumbbell("gen-only", A.get("gen_tps_median"), B.get("gen_tps_median")),
        dumbbell("pass rate", (A.get("pass_rate") or 0) * 100, (B.get("pass_rate") or 0) * 100),
        dumbbell("accept", A.get("accept_pct_median"), B.get("accept_pct_median")),
    ])
    legend = (
        f'<div class="db-legend">'
        f'<span><i style="background:{DARK["ink3"]}"></i>{_escape(tag_a)} (older)</span>'
        f'<span><i style="background:{DARK["accent"]}"></i>{_escape(tag_b)} (newer)</span>'
        f'</div>'
    )

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
        d_tps = _pct(ra.get("tok_s"), rb.get("tok_s"))
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
    <div class="eyebrow">effbench · comparison</div>
    <h1>{_escape(title)}</h1>
    <p class="sub">{A.get("n", 0)} tasks · generated by effbench</p>

    <div class="row">
      {card(tag_a, A, band_a, class_a)}
      {card(tag_b, B, band_b, class_b)}
    </div>

    <div class="panel">
      <h2>What changed</h2>
      <p class="sub">Two dots per metric — <b>{_escape(tag_a)}</b> (grey, older) and <b>{_escape(tag_b)}</b> (mint, newer). The distance between them is the finding; the number on the right is the percent change.</p>
      {dumbbells}
      {legend}
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
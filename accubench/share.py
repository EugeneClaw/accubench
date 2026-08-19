"""Copy-pasteable Markdown summary for a tag, suitable for sharing in chat, GitHub issues, or a blog."""
import statistics


def render_markdown(tag, recs, agg, fit_band=None, fit_class="unknown"):
    """Produce a short Markdown summary."""
    by_purpose = agg.get("by_purpose", {})
    n = agg.get("n", 0)
    pr = agg.get("pass_rate", 0)
    rtps = agg.get("raw_tps", 0)
    etps = agg.get("eff_tps", 0)

    purpose_rows = []
    for purpose, stats in by_purpose.items():
        purpose_rows.append(
            f"| {purpose} | {stats.get('n', 0)} | "
            f"{stats.get('pass_rate', 0)*100:.0f}% | "
            f"{stats.get('raw_tps', 0):.1f} |"
        )
    purpose_table = "\n".join(purpose_rows) if purpose_rows else "_(none)_"

    fit_line = ""
    if fit_band:
        lo, hi, _ = fit_band
        verdict = {
            "above": "🚀 faster than typical",
            "in":    "✅ typical for this hardware",
            "below": "🐢 slower than typical",
            "unknown": "❓ no reference data",
        }.get(fit_class, "")
        fit_line = f"- **Hardware fit:** {verdict} (typical {lo}–{hi} tok/s)"

    md = f"""### effbench run: `{tag}`

- **{n} tasks**, pass rate **{pr*100:.1f}%**
- Raw t/s: **{rtps:.1f}** · Effective t/s: **{etps:.1f}**
{fit_line}

| purpose | n | pass | tok/s |
|---|---|---|---|
{purpose_table}

<details><summary>by task</summary>

| task | pass | tok/s |
|---|---|---|
"""
    # compact task table
    for r in sorted(recs, key=lambda r: r["task"]):
        check = "✓" if r.get("pass") else "✗"
        ts = r.get("tok_s", 0)
        md += f"| {r['task']} | {check} | {ts:.1f} |\n"
    md += "\n</details>\n"
    return md
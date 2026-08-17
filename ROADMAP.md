# Roadmap

effbench development priorities. Items move up or down as user feedback and soak results dictate.

## Shipped

- **v0.2.1** (2026-08-17) — rename, one-line installers, `effbench go` wizard, hardware-fit verdicts, CSV/share exports, security pass (no real IPs/names/paths anywhere), single-commit clean history
- **v0.3.0** (2026-08-17) — interactive terminal menu, server auto-detection, all user data under `~/.effbench/`, one-line uninstall, installers auto-launch
- **v0.4.0** (2026-08-17) — browser front end (localhost web UI: buttons, live progress, hosted reports, past runs + compare, settings), Windows cp1252 crash fix (all file I/O explicit UTF-8)
- **v0.5.0** (2026-08-17) — measured numbers: median/mean/peak/p10–p90 stats, generation-only (cache-invariant) speed, band sources labelled (warm-cache soak), quick-suite ×0.89 calibration, expected-pass badges from the reference soak, per-fail guidance, radar fix (no fake zero axes), spec-decode accept-rate fix (was always 0% on llama.cpp). Suites and graders untouched.
- **v0.7.0** (2026-08-17) — the reframe (Kimi K3 mandate): verdict line, confrontation lanes, speed waterfall, pass ticks, champion ceremony; forever-sweep + brag line + star badge killed.
- **v0.6.1** (2026-08-17) — effective speed celebrated: equation chip (raw × accuracy = effective), brag line, count-up + ★ new best, cold-run fit-line reframe (gen-in-band shows mint, not amber).
- **v0.6.0** (2026-08-17) — instrument redesign: `tokens.py` single design source (one palette across UI + reports), hero cluster with pass-rate arc, purpose ladder replaces radar, task metric rows, dumbbell compare with percent deltas, busy-animation system (pulse dot + sweeping segmented rail + row arrivals + elapsed clock, `prefers-reduced-motion` respected), desktop shortcuts (Win) / effbench.app (macOS) / menu entry (Linux) with close-window-to-stop lifecycle, print stylesheet. Design review: docs/design-review-v1.html.

## v0.7 — Findability (next)

- [ ] **Find-servers button** in the web UI: probe localhost ports + LAN subnet (short timeouts), list what answers with its model, one-click select, graceful none-found state with "here's how to start one" hints
- [ ] `effbench go --compare OLD --against NEW` — compare two recipes in a single command
- [ ] GPU VRAM detection from `/props` or `nvidia-smi` so hardware class comes from actual hardware, not observed t/s alone
- [ ] More expectations entries — Mistral, DeepSeek, Phi, Gemma bands; Apple Silicon Ultra, DGX Spark classes
- [ ] Model-optimisation guide: use effbench to sweep spec-decode params (draft depth, accept thresholds, context length) — run×3 + compare per recipe

## v0.7 — Presentation depth

- [ ] Eff-t/s trend line across run history (recipe sweep visualiser)
- [ ] Per-task timing detail in the report (P50/P90 wall time, not just t/s)
- [ ] Vision-QA pass over every surface (automated screenshot → model critique loop)
- [ ] Expand full suite to 50+ tasks for higher statistical confidence on ship decisions (additive — existing tasks frozen)

## v0.8 — Suite depth (additive only; existing tasks never change)

- [ ] `extract` purpose category with real tasks (NER, table extraction)
- [ ] `chat` purpose category — currently underrepresented
- [ ] JSON Schema for the ledger so other tools can consume/produce effbench data
- [ ] Hub: share runs as Markdown artefacts for CI pipelines
- [ ] `effbench update` self-update command

## Decisions log

- **Web UI: yes, but private.** v0.4 replaced the "self-contained HTML only" stance with a localhost-only web server (127.0.0.1, stdlib, dies with the terminal). It made the tool genuinely non-technical. The HTML file remains the export/share format.
- **Terminal still first-class.** `effbench menu`, `go`, `run`, `compare`, `share`, `csv` all remain; the browser UI is additive, never the only path.
- **No LLM-as-judge.** Every grader is deterministic. Same answer always gets the same verdict.
- **Append-only ledger.** Wrong run? Tag it and move on. Comparisons always reproducible from raw records.
- **Server-agnostic.** Any OpenAI-compatible HTTP server. No special case for llama.cpp in the bench; only the expectations table is calibrated against observed runs.
- **Explicit UTF-8 everywhere.** Python on Windows defaults to cp1252 and crashes on `✓`. Every `open()` passes `encoding="utf-8"`; launcher sets `PYTHONUTF8=1`. Never remove these.
- **Fixtures are oracle-generated.** Task answer keys are produced by verified scripts, never hand-written (hand-written ones were wrong 3×).
- **No pip installs / venv.** Single launcher, stdlib only. Friction kills adoption.
- **Versioning: tag + GitHub release per shippable state.** CHANGELOG.md carries the human-readable notes. CI (validate + selftest + PII scan) must stay green.
- **Suites are frozen (2026-08-17, user decision).** Tasks, prompts and graders don't change so comparisons stay meaningful across releases. Suite growth is additive only. Report/presentation changes don't invalidate comparisons.
- **Generation-only t/s is context, not headline.** Wall-clock median stays THE metric (it's what users experience); gen-only diagnoses server health and enables cache-invariant hardware classification.
- **Bands carry provenance.** Every "typical" number prints its source. The desktop_gpu_high band is one measured rig (warm-cache soak) — labelled as such, never presented as a crowd.

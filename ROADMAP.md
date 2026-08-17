# Roadmap

effbench development priorities. Items move up or down as user feedback and soak results dictate.

## Shipped

- **v0.2.1** (2026-08-17) — rename, one-line installers, `effbench go` wizard, hardware-fit verdicts, CSV/share exports, security pass (no real IPs/names/paths anywhere), single-commit clean history
- **v0.3.0** (2026-08-17) — interactive terminal menu, server auto-detection, all user data under `~/.effbench/`, one-line uninstall, installers auto-launch
- **v0.4.0** (2026-08-17) — browser front end (localhost web UI: buttons, live progress, hosted reports, past runs + compare, settings), Windows cp1252 crash fix (all file I/O explicit UTF-8)

## v0.5 — Accuracy of the verdict (next)

- [ ] **Quick-suite calibration** — quick tasks are short and prompt-processing-dominated, so quick medians read ~1 hardware class lower than the full suite (5090 reads ~64 t/s on quick vs ~167 full). Either lengthen quick tasks, report a quick-specific expectations band, or scale. This is the most misleading current behaviour.
- [ ] `effbench go --compare OLD --against NEW` — compare two recipes in a single command
- [ ] GPU VRAM detection from `/props` or `nvidia-smi` so hardware class comes from actual hardware, not observed t/s alone
- [ ] More expectations entries — Mistral, DeepSeek, Phi, Gemma bands; Apple Silicon Ultra, DGX Spark classes
- [ ] Model-optimisation guide: use effbench to sweep spec-decode params (draft depth, accept thresholds, context length) — run×3 + compare per recipe

## v0.6 — Suite depth

- [ ] Expand full suite to 50+ tasks for higher statistical confidence on ship decisions
- [ ] `extract` purpose category with real tasks (NER, table extraction)
- [ ] `chat` purpose category — currently underrepresented
- [ ] Per-task timing detail in the report (P50/P90 wall time, not just t/s)

## v0.7 — Ecosystem

- [ ] Hub: share runs as Markdown artefacts for CI pipelines
- [ ] JSON Schema for the ledger so other tools can consume/produce effbench data
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

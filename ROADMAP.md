# Roadmap

effbench development priorities. Items move up or down as user feedback and soak results dictate.

## v0.2 — Ship (this week)

- [x] Rename repo `llama-effbench` → `effbench`
- [x] Strip all llama.cpp / llama-bench framing from user-facing copy
- [x] `effbench go` wizard
- [x] `effbench csv` / `effbench share` exports
- [x] Hardware-fit verdict in the report
- [x] One-line installer for Mac/Linux + Windows
- [x] README rewritten for the new identity

## v0.3 — Polish (next)

- [ ] `effbench go --compare OLD --against NEW` — compare two recipes in a single command (currently `compare` is a separate command)
- [ ] GPU VRAM detection from `/props` or `nvidia-smi` so the hardware class can be detected from actual hardware, not observed t/s
- [ ] More expectations entries — known bands for Mistral, DeepSeek, Phi, Gemma; more hardware classes (Apple Silicon Ultra, DGX Spark)
- [ ] Render the report on stdout for the case where the user wants to share without saving a file
- [ ] `--quiet` flag for power users
- [ ] Auto-update: `effbench update` re-runs the installer

## v0.4 — Quality (after that)

- [ ] Expand the full suite to 50+ tasks (more code, more structured output, more reasoning) for higher statistical confidence on ship decisions
- [ ] Add an `extract` purpose category with real tasks (NER, table extraction from text, etc.)
- [ ] Add a `chat` purpose category — currently underrepresented
- [ ] Per-task timing detail in the report (P50/P90 wall time, not just t/s)
- [ ] Spec-decode tuning recipes in the README (draft depth, accept thresholds)

## v0.5 — Ecosystem (later)

- [ ] Hub: `effbench-hub` for sharing runs as Markdown artefacts in CI pipelines
- [ ] Optional HTML viewer that auto-refreshes when the ledger changes
- [ ] JSON Schema for the ledger, so other tools can produce effbench-consumable data
- [ ] effbench-as-a-service for comparing public model leaderboards

## Decisions log

- **No web UI.** A self-contained HTML file is the right answer for non-technical users. Adding a web server on top is over-engineering and a security surface.
- **No LLM-as-judge.** Every grader is deterministic. Same answer always gets the same verdict. No "AI judges AI" drama.
- **Append-only ledger.** Wrong run? Tag it and move on. Comparisons are always reproducible from the raw records.
- **Server-agnostic.** Any OpenAI-compatible HTTP server. No special case for llama.cpp in the bench itself; only the reference expectations table is calibrated against observed llama.cpp runs.
- **No virtual environment.** Single-file `effbench` launcher, no pip installs. The less friction, the more people actually use it.
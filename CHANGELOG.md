# Changelog

All notable changes to effbench, newest first.

## 0.2.0 — 2026-08-17

The "make it usable for everyone" release. Repo renamed from `llama-effbench` to `effbench`; no llama.cpp-specific references remain.

**Added:**
- `effbench go` — wizard command. Probes the server, picks a suite, runs, renders HTML, prints one-sentence hardware-fit verdict. Zero arguments needed.
- `effbench share` — copy-pasteable Markdown summary for posting in Discord / GitHub issues / blogs.
- `effbench csv` — per-task CSV (default), summary CSV (`--summary`), or side-by-side compare CSV (`--compare OTHER`). Opens in Excel, Numbers, Google Sheets.
- Hardware expectations library (`effbench/expectations.json`) — known-good raw-t/s bands for common models × hardware classes. The report tells you "faster than typical", "typical", or "slower than typical" relative to your hardware.
- Purpose tags (`chat`, `code`, `reasoning`, `extract`, `structure`, `summarise`) and difficulty tags (`easy`, `medium`, `hard`) on every task. The report shows a radar chart of pass-rate by purpose.
- `install.sh` (Mac/Linux) and `install.ps1` (Windows PowerShell) — one-line installers. Clone the repo, write a launcher, done.
- HTML report upgrade: purpose radar, hardware-fit verdict with one-sentence explanation, plain-English task descriptions in the per-task table.

**Changed:**
- Repo name: `llama-effbench` → `effbench`. GitHub: `EugeneClaw/effbench`.
- README rewritten for the new name and new copy-paste install path.
- The model_arch parser now handles Qwen3.8-27B-style filenames — picks the largest size token, not the minor version.

**Removed:**
- All "llama.cpp" / "llama-bench" framing in user-facing copy.

## 0.1.0 — 2026-08-16

Initial release. CLI + JSONL ledger + 36-task suite + 6 deterministic grader types (exact, contains, contains_all, regex, code-execution, JSON). Quality-weighted metric (effective t/s). Held under an 8-hour soak against MAIN door with zero drift.
# Changelog

All notable changes to effbench, newest first.

## 0.3.0 — 2026-08-17

The "no CLI knowledge required" release. After installation, everything is menu-driven.

**Added:**
- Interactive menu: bare `effbench` (or `effbench ui`) opens a numbered menu — quick benchmark, full benchmark, compare two past runs, open a past report, settings, uninstall. No flags or subcommands needed for normal use.
- Server auto-detection: config → `$EFFBENCH_URL` → common localhost ports (11434 llama.cpp/Ollama, 8080, 5000, 1234 LM Studio); falls back to a friendly prompt. First working URL remembered in `~/.effbench/config.json`.
- All user data (`ledger.jsonl`, `reports/*.html`, `config.json`) now lives under `~/.effbench/` instead of the current directory.
- `effbench uninstall` — removes the install (refuses to delete git clones, asks before touching saved reports).
- One-line uninstallers: `uninstall.sh` (Mac/Linux) and `uninstall.ps1` (Windows).

**Changed:**
- Installers (`install.sh` / `install.ps1`) auto-launch the menu on completion — install is now the only technical step.
- Reports open in the browser automatically after every run (config: `open`).

**Fixed:**
- Windows launcher (`effbench.cmd`) invoked `__main__.py` as a plain file — relative imports would crash. Now runs `python -m effbench` with `PYTHONPATH` set correctly.

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
# Changelog

All notable changes to accubench, newest first.

## 0.9.23 — 2026-08-19

Rename migration — module, CLI, and data directory renamed to accubench; effbench stays a working alias until v1.0; changelog rebuilt; README install commands corrected.

- **Module rename**: `effbench/` package → `accubench/`. Single import surface everywhere; CLI invocation is `python3 -m accubench`.
- **Data directory**: `~/.effbench/` → `~/.accubench/`. One-shot migration on first run after upgrade: copy to a temp dir next to the target, stamp `.migrated` inside, atomic rename into place. Old `~/.effbench/` is left untouched for instant rollback.
- **Single data-dir authority** (QR R1): new `accubench/paths.py` centralises resolution; menu, config, and keystore consume it — three independent resolvers gone. Selftest asserts all three agree at runtime.
- **Alias window** (v0.9.23 → v1.0): old command `effbench` still works. A 2-line compat package forwards to accubench and prints a one-shot stderr deprecation line (never stdout, never UI), with sunset date included. Old `.app`/`.lnk`/`.desktop` wrappers keep working without churn.
- **Installers write both names**: `accubench` (primary) + `effbench` shim, until v1.0. User-visible labels (`.app` bundle name, bundle id `com.eugeneclaw.effbench`, `.lnk` label, `.desktop` Name) stay `effbench` until v1.0 to avoid duplicate Launchpad entries / Windows shortcuts — embedded `-m` invocation switches to `accubench`.
- **Uninstallers sweep both** (QR R3): during the alias window, `install.sh`/`install.ps1` and the in-app uninstaller remove both command names, both data dirs, both source dirs, the `.app` bundle, and the `.lnk` shortcut.
- **Keystore hardening**: `keys.json` is now created with `os.open(O_CREAT, 0o600)` so the inode mode is 0600 from the moment of creation — no umask window between open and chmod. `clear_all()` deleted (byte-identical duplicate of `wipe()`); `webui.py:736` repointed. Atomic-rename write with cleanup on partial failure.
- **Port guard** (QR R5): `find_port()` explicitly bounds the probe to 8765..8776 (12 ports) so a quiet listener can't hide.
- **Raw URLs swept** (F3/F4 fold-in): `uninstall.sh:3` and `uninstall.ps1:2` now use release-asset URLs (`releases/latest/download/...`), not raw.githubusercontent.
- **CHANGELOG rebuilt** (F1): 15 missing releases (v0.9.6–v0.9.22) re-added; historical sections below preserve original `effbench` references per the sweep carve-out (R6).
- **README refreshed** (F2): bare `accubench` = browser UI (since v0.4.0), terminal menu is the explicit fallback; install one-liners point at `EugeneClaw/accubench`.

## 0.9.22 — 2026-08-19

Security pass — cross-site request rejection, key-reveal endpoint removed.

- Web UI now rejects cross-site requests on `/api/*` via `Sec-Fetch-Site` gate (probed cross-site GET+POST → 403, no-header → passes).
- `/api/key-reveal` endpoint removed (commit `e708669`); live probe confirms GET/POST → 404.
- Verified live against the actual v0.9.22 HTTP handler.

## 0.9.21 — 2026-08-19

loadConfig return, api() error propagation, picker/fill saved-key path, local custom URLs.

## 0.9.20 — 2026-08-19

Leaderboard sort by pass, batch-fill error handling + fallback, shortcut icon (`assets/accubench.ico`, install.ps1 IconLocation).

## 0.9.19 — 2026-08-19

Leaderboard number+trophy, eff-t/s speed crowns, key-saved placeholder.

## 0.9.18 — 2026-08-19

AccuBench branding pass, quiet connection-abort spam.

## 0.9.17 — 2026-08-19

Installer fetch+reset, report regeneration, friendly 404, handler chain fixes.

## 0.9.16 — 2026-08-19

Batch runs, export/import in reports section, AccuBench banner + ASCII startup.

## 0.9.15 — 2026-08-19

Export/import merge, provider-scoped keys.

## 0.9.14 — 2026-08-19

Stop-run button, suite-aware leaderboard, board visible by default.

## 0.9.13 — 2026-08-18

Wizard save: drop hidden detect call, bound api() with 60s timeout, wizFinish finally.

## 0.9.12 — 2026-08-18

Leaderboard (best run per model, badges), report delete, saved-key hint.

## 0.9.11 — 2026-08-18

Wizard: fix unclosed local-step div nesting cloud step; light text on choice cards; drop stray closer.

## 0.9.10 — 2026-08-18

Setup wizard v2: modal fork (local vs cloud), detect, summary card, blank-url guard.

## 0.9.9 — 2026-08-18

Settings: reset-to-blank (unsave), wipes config.json and optionally saved keys.

## 0.9.8 — 2026-08-18

Wizard: provider presets, live model list, key management, ollama preset.

## 0.9.7 — 2026-08-18

Cloud: handle reasoning-only streams, guard token math, ollama compat.

## 0.9.6 — 2026-08-18

Cloud key save: accept nested key, strip before config persist, surface save errors, no-cache UI.

## 0.9.5 — 2026-08-18

Cloud URLs work without the https:// prefix.

## 0.9.4 — 2026-08-18

Test-connection button fix.

## 0.9.3 — 2026-08-18

Cloud setup takes a pasted API key.

## 0.9.2 — 2026-08-18

Report polish.

## 0.9.1 — 2026-08-18

Grades recalibrated.

## 0.9.0 — 2026-08-19

Report readability and guided cloud setup.

## 0.8.1 — 2026-08-18

Security hardening and provider coverage.

- Provider error bodies are sanitised before reaching the ledger or any report — credential-shaped substrings are replaced and length capped, so a provider that echoes key/account details in an error cannot leak them into results.
- OpenAI preset added (api.openai.com, key from OPENAI_API_KEY); OpenRouter note expanded (Claude, Llama, Gemini reachable through it).
- CI PII blocklist no longer contains the blocked words in plaintext (patterns are decoded at run time).
- tools/ scripts no longer hardcode a user's home path.

## 0.8.0 — 2026-08-18

Three features: cloud endpoints, letter grades, named runs.

- **Cloud endpoints** — Settings now accepts a cloud provider (z.ai, OpenRouter, or any OpenAI-compatible URL) plus a model id and the NAME of the environment variable holding the API key. The key itself is never stored by effbench and never appears in reports or the ledger. Cloud runs are labelled cloud; speeds include network latency and the generation figure is marked estimated. Hardware "typical band" comparison is skipped for cloud runs — a cloud endpoint has no local hardware class.
- **Letter grades** — every run and report now carries a grade badge: A ≥95%, B ≥85%, C ≥70%, D ≥55%, E ≥40%, F below, U when nothing could run. Grades judge accuracy only; speed stays a separate verdict. The badge is coloured (green/amber/red) for at-a-glance reading.
- **Named runs** — `effbench run --name` and the web UI produce report filenames that identify what was measured (e.g. zai-glm-5.3-cloud-20260818-125558.html) instead of opaque tags. The underlying tag and all ledger metadata are unchanged.

Also fixed: cloud-quick reports crashed the band verdict (format on None); cloud runs no longer get a hardware class assigned from model-path heuristics.

## 0.7.1 — 2026-08-17

Report and summary now answer "is this good?" directly.

- **Verdict sentences** — both surfaces open with two plain statements: is this fast (judged on generation-only speed against the reference band for the hardware class) and is this accurate (pass rate). Wording is decisive: "This is fast." / "Decent speed — close to typical." / "Speed needs work." / "This is accurate." / "Accuracy needs work."
- **Named speeds** — the report shows PEAK SPEED / MEAN SPEED / WALL SPEED / EFFECTIVE SPEED as labelled rows with basis notes (peak & mean are generation-only — the figures quoted in public speed posts; wall and effective include prompt processing). Removes ambiguity about which number is which.
- Speed comparison now judges generation-only speed (comparable to external claims), not wall-clock, so cold-run prompt processing no longer reads as a slow server.

## 0.7.0 — 2026-08-17

Post-run summary redesigned.

- **Verdict line** — each run opens with a one-line verdict (four states, by pass rate) followed by the run facts: `62 checked tok/s · 11/12 graded · speed discounted 8% for wrong answers.`
- **Confrontation lanes** — "The number you could post": effective speed beside generation-only peak speed, two separate cards, never on a shared scale. Each lane carries its measurement basis (tasks graded, wall-clock / generation-only, best case).
- **Speed waterfall** — peak generation → typical generation → wall clock → effective, one scale, each drop labelled by cause (best-case vs median; cold prompt processing; × pass rate).
- **Pass ticks** — one tick per task (✓/✕); failed tasks listed by name with a fix-target hint. Replaces the pass-rate arc.
- **Run-history milestones** — first run of a suite shows "FIRST BASELINE"; beating the suite's best effective speed shows "NEW CHAMPION".
- **Run screen** — in-flight progress segment shows a steady fill (was a repeating sweep); live pass tally ("passed 7/7 so far"); rail segments of failed tasks marked amber.
- **Removed**: tone-matched summary sentence (v0.6.1), always-on count-up (fresh results only now), star badge.

## 0.6.1 — 2026-08-17

Minor update: effective-speed presentation and bug fixes.

- **Equation chip** — summary and report hero now show the arithmetic: raw wall speed × pass rate = effective speed (e.g. `67 × 92% = 62 tok/s`).
- **Fix**: band-chart provenance and cache note were overprinted on one line in the report; now stacked (chart height 120 → 140). Originally fixed for v0.6.0 but shipped without a version increment; this release carries it.
- **Fix**: cold runs with generation-only speed inside the reference band were flagged "slower than typical" in amber; now reported as in-band with the cold-run cause noted.

## 0.6.0 — 2026-08-17

The instrument release — a full visual redesign of both surfaces, built on the design review (docs/design-review-v1.html). Presentation only: suites, prompts, graders, fixtures and ledger format are untouched, so every past ledger keeps rendering and every number stays comparable.

### One design system
- New `effbench/tokens.py`: single source of truth for color, type and motion. Void-black panel, four-step graphite ramp, one mint accent. Web UI and reports can no longer drift apart.
- Type ramp with `tabular-nums` on every live digit — numbers stop wobbling.
- Motion scale (140ms hovers, 240ms panels, 160ms row arrivals) with full `prefers-reduced-motion` support.
- Print stylesheet: reports print as clean paper documents.

### Report
- **Hero cluster** replaces the stat-card row: one 56px effective-t/s number, supporting metrics on a shared micro-bar scale, pass-rate arc gauge, accept-rate strip. The screenshot is the summary.
- **Purpose ladder** replaces the radar: ranked rungs with n counts, zero-pass drawn as a visible sliver, untested purposes listed underneath.
- **Task metric rows**: drawn chips, tabular digits, fail hints and reference badges as distinct slots on a fixed grid.
- **Dumbbell compare**: per-metric two-dot rows with percent deltas — the distance between the dots is the finding.

### Web UI
- **Busy-animation system** — when anything is happening, something is always moving:
  - a pulse dot on the status line (busy),
  - a segmented progress rail where the in-flight segment sweeps forever (not hung — a frozen render can't fake it),
  - current task name + ticking elapsed clock (attention where it matters),
  - per-task rows fade in as they resolve.
- Hero cluster in miniature when a run finishes; the UI and report now speak the same visual language.
- Designed first-run state (no more eternal "loading…"), styled past-runs grid, mint focus states.

### Lifecycle (the appliance question)
- Windows installer drops an **effbench shortcut** on the Desktop + Start Menu: double-click starts the UI in a titled console ("close this window to stop"), no PowerShell needed. Nothing is backgrounded — close the window and it's gone.
- macOS installer creates `~/Applications/effbench.app` with the same semantics; Linux gets a Terminal=true menu entry.

## 0.5.0 — 2026-08-17

The measured-numbers release. Suites, prompts, graders and fixtures are untouched — every past and future ledger number stays comparable. Everything here is better measurement, better context, or a bug fix in what was displayed.

**Added:**
- **Full speed statistics**: median (still the headline), mean, peak, and p10–p90 spread — per run and in the report. One number hid that the same rig scores 74–206 t/s across tasks.
- **Generation-only speed** (`gen_tps`): recorded from llama.cpp `timings.predicted_per_second` and shown as its own card + marker on the band chart. Decode-only, cache-invariant — the number that actually answers "is my server slow?" Wall-clock includes prompt processing and varies 2–8× with prompt-cache state.
- **Labelled verdicts**: every typical-band now shows where it came from ("reference: own warm-cache soak 2026-08-17, RTX 5090"). The 120–200 desktop_gpu_high band is one measured rig, not a crowd — the report says so.
- **Cache-aware diagnosis**: when wall-clock is below band but generation-only is inside it, the verdict says your server isn't slow — prompt processing on a cold run is dragging wall-clock, which is normal.
- **Quick-suite calibration**: quick tasks are short and prompt-processing-dominated, so quick bands are scaled ×0.89 (measured from paired soak cycles: 0.899, 0.874). A cold quick run no longer reads a full hardware class low.
- **Expected-pass badges**: each task now carries what the reference rig (RTX 5090 + Qwen3.8-27B IQ4_XS) did on it. "ref fails too" = your fail is expected (the 4 hard full-suite tasks failed 255/255 reference runs). "ref passes" = your fail is the interesting kind. Generated by `tools/gen_expected_pass.py` from the soak ledger.
- **Failure guidance**: every failed task gets a plain-English note — what this kind of fail means and what to try (--think, higher quant, bigger model, or "recipes won't fix this").
- **Radar chart fix**: axes only for purposes the suite actually tests. Untested purposes (chat, summarise on quick) are listed as "not tested" instead of drawn as a zero score.
- New selftest coverage: suite detection, suite-aware fit, expected-pass data, radar axes, fail hints, capture fields (54 checks, up from 29).

**Fixed:**
- **Speculative-decode accept rate was always 0%** on llama.cpp servers: the stats live under `timings.draft_n`/`draft_n_accepted`, not `usage`. Now computed from either location. Real accept rates (77–100%) now show per task and in the report headline.
- Hardware class inference on cold runs: prefers cache-invariant generation-only speed over wall-clock, so a 5090 running a first-time quick suite no longer gets classified as mid-range hardware.

**Unchanged (by design):** tasks, prompts, graders, fixtures, scoring, `raw × pass-rate`. Old ledger records render fine in new reports; new fields are additive.

## 0.4.0 — 2026-08-17

The browser release. effbench is now a web app you click, not a command you type.

**Added:**
- Browser front end: bare `effbench` opens a localhost web UI (127.0.0.1, stdlib only, no dependencies) — run buttons with live per-task progress, past runs with one-click reports, side-by-side compare, settings. Reports are hosted at `/report/<name>`.
- The terminal menu (`effbench menu`) remains as a fallback; all CLI subcommands are unchanged.

**Fixed:**
- Windows cp1252 crash: every file read/write now passes `encoding="utf-8"` and the launcher sets `PYTHONUTF8=1`. `✓` no longer explodes the installer.

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
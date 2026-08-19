# AccuBench

**Quality-weighted benchmark for any local AI server.** Runs your model through real tasks and tells you **how fast** *and* **how often it gets it right**.

    effective t/s = raw t/s × task pass-rate

Local AI servers are fast. The question isn't just *"how fast?"* — it's *"how fast **and** useful?"* Two servers, same model:

| recipe | raw t/s | pass rate | effective t/s |
|---|---|---|---|
| your usual setup | 167 | 89% | **148.8** |
| a faster quant | 180 | 60% | **108.0** |

The faster quant is 8% faster and 33% worse. Raw benchmarks crown it; AccuBench doesn't.

---

## Get started — one command, zero config

```bash
# Mac / Linux
curl -fsSL https://github.com/EugeneClaw/accubench/releases/latest/download/install.sh | bash
```

```powershell
# Windows PowerShell
irm https://github.com/EugeneClaw/accubench/releases/latest/download/install.ps1 | iex
```

Install it and the browser UI opens — click "Quick benchmark", get a colour-coded report in seconds. The one-line install is the only technical step; after that everything is menu-driven.

The browser UI talks to your AI server automatically (llama.cpp, LM Studio, Ollama, vLLM — anything with an OpenAI-compatible API on localhost or your network), runs 12 short tasks (~15 seconds), and opens a colour-coded report. Can't find your server? It asks you where it is, once, and remembers. There's a terminal menu fallback (`accubench menu`) for when no browser is available.

Typing `accubench` any time re-opens the browser UI:

```
  accubench 0.9.22
  how fast — and how accurate — is your local AI?

   1) quick benchmark          (~15 seconds)
   2) full benchmark           (2-4 minutes)
   3) compare two past runs
   4) open a past report
   5) settings
   6) uninstall
   q) quit
```

Your results, settings and saved reports live in `~/.accubench/` — not scattered in whatever folder you ran the command from.

> **Upgrading from v0.9.22 or earlier?** Your `~/.effbench/` is copied to `~/.accubench/` on first run. The old command `effbench` keeps working as an alias until v1.0.

**Uninstall** is one line too:

```bash
curl -fsSL https://github.com/EugeneClaw/accubench/releases/latest/download/uninstall.sh | bash
```

```powershell
irm https://github.com/EugeneClaw/accubench/releases/latest/download/uninstall.ps1 | iex
```

**Persist your config?** All customisations live in `~/.accubench/config.json`. Manage it with:

```bash
accubench config show                 # show everything
accubench config set url http://...   # change your default server
accubench config get runs             # read a value
```

---

## What you get

The **HTML report** (one file, double-click to open, no server needed):

- **One-sentence verdict**: "167 tok/s on a high-end desktop GPU — typical for this hardware."
- **Pass-rate by purpose**: chat, code, reasoning, structured output, extraction. See where the model shines and where it doesn't.
- **Per-task table**: every task with a green tick or red cross and a plain-English description.
- **Hardware fit verdict**: "Typical for an RTX 5090", "slower than typical — check for thinking-mode overhead", etc.

The **share block** (one command, copy-paste ready):

```bash
accubench share --tag my-run
```

The **spreadsheet** (open in Excel, Numbers, Google Sheets):

```bash
accubench csv --tag my-run --out results.csv
```

---

## The commands

Most people only ever need the browser UI — type `accubench` and click. These exist for scripting and fine control:

| Command | What it does |
|---|---|
| `accubench` | **The browser UI.** Quick bench, full bench, compare, past reports, settings, uninstall. |
| `accubench menu` | Terminal menu fallback (no browser). |
| `accubench ui` | Same as bare `accubench` — explicit. |
| `accubench go` | Non-interactive wizard: probe, run, render, open. Good for scripts. |
| `accubench setup` | Find your server at common URLs, save the working one. |
| `accubench config` | View or edit `~/.accubench/config.json` (subcommands: `show`, `get`, `set`, `path`). |
| `accubench run` | Lower-level. Choose suite, runs, tag, ledger. |
| `accubench report` | Render an HTML report from any ledger. |
| `accubench compare` | Two tags, side-by-side HTML report. |
| `accubench share` | Copy-pasteable Markdown summary for Discord/forums/blogs. |
| `accubench csv` | Per-task CSV (default), summary CSV (`--summary`), or compare CSV (`--compare OTHER`). |
| `accubench uninstall` | Remove accubench (asks before deleting anything). |
| `accubench validate` | Self-test every task grader against known-good and known-bad fixtures. |

---

## What's inside

- **Two ready-to-use suites**, both deterministic and self-validating:

  | suite | tasks | runtime | use for |
  |---|---|---|---|
  | `quick.json` | 12 | ~5–15s per run | recipe sweeps, "did this change break anything?", CI checks |
  | `suites/` (all four) | 36 | ~50–105s per run | ship/share decisions, golden runs |

- **6 grader types**: exact, contains, regex, **code-execution** (real `python3` run, stdout compared), JSON, contains-all. No LLM-as-judge — same answer always gets the same verdict.

- **Hardware expectations library** (`accubench/expectations.json`): ships known-good raw-t/s bands for common models + quants across 5 hardware classes (phone_laptop, desktop_gpu_mid, desktop_gpu_high, workstation, dataclass). Your result is compared to the band and tagged `above` / `in` / `below`. Add new entries as the field moves.

- **Purpose tags** (`accubench/explainer.py`): each task is labelled with one of *chat, code, reasoning, extract, structure, summarise* and one of *easy, medium, hard*. The radar chart on the report shows where the model is broad vs narrow.

- **Append-only JSON ledger, never mutated.** Compare two runs without re-running anything.

## Platform support

- **OS:** macOS, Linux, Windows, WSL2 — anything with Python 3.9 or newer.
- **Server:** any OpenAI-compatible HTTP server exposing `/v1/chat/completions`. Works with llama.cpp, vLLM, LM Studio, Ollama, ExLlamaV2, LocalAI, text-generation-inference. The server runs on the same box or anywhere on your LAN.
- **Python:** 3.9+. No external dependencies. No virtual environment required. No pip installs.
- **Browser:** any. The HTML report is self-contained — no CDNs, no fonts loaded from the web, no analytics.

## When to use accubench

| If you want to know... | Run this |
|---|---|
| Is this server fast enough? | `accubench go` |
| Is this quant better than that quant? | `accubench go` twice, then `accubench compare --tag B --against A` |
| Is my new spec-decoding config actually better? | `accubench go --tag OLD` then `accubench go --tag NEW`, then `accubench compare` |
| What's my typical t/s for this hardware? | `accubench go` — the verdict tells you |
| Should I share a recipe publicly? | `accubench run --suite suites/ --tag FINAL --runs 3` |

## The full workflow recipe

```bash
# baseline run on your current setup
accubench go --tag recipe-current --out current.html

# try a different setup; re-run after editing the bat / launch script
accubench go --tag recipe-new --out new.html

# compare
accubench compare --ledger accubench.jsonl --tag recipe-new --against recipe-current \
                 --out compare.html

# shareable Markdown
accubench share --ledger accubench.jsonl --tag recipe-current

# spreadsheet
accubench csv --ledger accubench.jsonl --tag recipe-current --out current.csv
```

---

## How effective t/s works

Three numbers per task, two numbers per run:

- **Raw t/s** — tokens per second, from the server's `usage.completion_tokens / wall_time`. Wall-clock, not server-reported.
- **Pass rate** — fraction of tasks whose deterministic grader accepts the output.
- **Effective t/s** = raw × pass rate. The "fast-but-wrong is not fast" number.

An errored request (server 500, timeout, network drop) is recorded as a **failure**, not skipped. From the user's chair that's what an error is.

## Why this exists

I built this because I kept seeing two servers with the same model and very different answers. One was 30% faster on a benchmark and visibly worse on real work. The existing tools — speed benchmarks, eval harnesses, leader-boards — — measure one axis each. accubench measures the one that matters when you're actually using the model.

## License

MIT.
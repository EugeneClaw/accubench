# effbench

**Quality-weighted benchmark for any local AI server.** Runs your model through real tasks and tells you **how fast** *and* **how often it gets it right**.

    effective t/s = raw t/s × task pass-rate

Local AI servers are fast. The question isn't just *"how fast?"* — it's *"how fast **and** useful?"* Two servers, same model:

| recipe | raw t/s | pass rate | effective t/s |
|---|---|---|---|
| your usual setup | 167 | 89% | **148.8** |
| a faster quant | 180 | 60% | **108.0** |

The faster quant is 8% faster and 33% worse. Raw benchmarks crown it; effbench doesn't.

---

## Get started — one command, zero config

```bash
# Mac / Linux
curl -fsSL https://raw.githubusercontent.com/EugeneClaw/effbench/main/install.sh | bash
```

```powershell
# Windows PowerShell
irm https://raw.githubusercontent.com/EugeneClaw/effbench/main/install.ps1 | iex
```

Then point it at a running model:

```bash
effbench go                                # uses http://localhost:11434 if no config
effbench go --url http://192.168.1.x:11434 # or any local URL on your network
effbench go --url http://my-server:8080    # or anywhere with an OpenAI-compatible API
```

`effbench go` will save the first URL you use to `~/.effbench/config.json` so you only have to type it once.

That's it. It probes your server, runs 12 short tasks (~10 seconds), and opens a colour-coded HTML report in your browser.

**First run?** `effbench go` will ask for a URL once and remember it. You can also run `effbench setup` first — it tries a few common URLs and saves the first one that works.

**Persist your config?** All customisations live in `~/.effbench/config.json`. Manage it with:

```bash
effbench config show                 # show everything
effbench config set url http://...   # change your default server
effbench config get runs             # read a value
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
effbench share --tag my-run
```

The **spreadsheet** (open in Excel, Numbers, Google Sheets):

```bash
effbench csv --tag my-run --out results.csv
```

---

## The 9 commands

| Command | What it does |
|---|---|
| `effbench setup` | First-run wizard. Finds your server at common URLs, saves the working one. |
| `effbench config` | View or edit `~/.effbench/config.json` (subcommands: `show`, `get`, `set`, `path`). |
| `effbench go` | The benchmark wizard. Probe, run, render, open. Zero arguments needed. |
| `effbench run` | Lower-level. Choose suite, runs, tag, ledger. |
| `effbench report` | Render an HTML report from any ledger. |
| `effbench compare` | Two tags, side-by-side HTML report. |
| `effbench share` | Copy-pasteable Markdown summary for Discord/forums/blogs. |
| `effbench csv` | Per-task CSV (default), summary CSV (`--summary`), or compare CSV (`--compare OTHER`). |
| `effbench validate` | Self-test every task grader against known-good and known-bad fixtures. |

---

## What's inside

- **Two ready-to-use suites**, both deterministic and self-validating:

  | suite | tasks | runtime | use for |
  |---|---|---|---|
  | `quick.json` | 12 | ~5–15s per run | recipe sweeps, "did this change break anything?", CI checks |
  | `suites/` (all four) | 36 | ~50–105s per run | ship/share decisions, golden runs |

- **6 grader types**: exact, contains, regex, **code-execution** (real `python3` run, stdout compared), JSON, contains-all. No LLM-as-judge — same answer always gets the same verdict.

- **Hardware expectations library** (`effbench/expectations.json`): ships known-good raw-t/s bands for common models + quants across 5 hardware classes (phone_laptop, desktop_gpu_mid, desktop_gpu_high, workstation, dataclass). Your result is compared to the band and tagged `above` / `in` / `below`. Add new entries as the field moves.

- **Purpose tags** (`effbench/explainer.py`): each task is labelled with one of *chat, code, reasoning, extract, structure, summarise* and one of *easy, medium, hard*. The radar chart on the report shows where the model is broad vs narrow.

- **Append-only JSON ledger, never mutated.** Compare two runs without re-running anything.

---

## Platform support

- **OS:** macOS, Linux, Windows, WSL2 — anything with Python 3.9 or newer.
- **Server:** any OpenAI-compatible HTTP server exposing `/v1/chat/completions`. Works with llama.cpp, vLLM, LM Studio, Ollama, ExLlamaV2, LocalAI, text-generation-inference. The server runs on the same box or anywhere on your LAN.
- **Python:** 3.9+. No external dependencies. No virtual environment required. No pip installs.
- **Browser:** any. The HTML report is self-contained — no CDNs, no fonts loaded from the web, no analytics.

---

## When to use effbench

| If you want to know... | Run this |
|---|---|
| Is this server fast enough? | `effbench go` |
| Is this quant better than that quant? | `effbench go` twice, then `effbench compare --tag B --against A` |
| Is my new spec-decoding config actually better? | `effbench go --tag OLD` then `effbench go --tag NEW`, then `effbench compare` |
| What's my typical t/s for this hardware? | `effbench go` — the verdict tells you |
| Should I share a recipe publicly? | `effbench run --suite suites/ --tag FINAL --runs 3` |

---

## The full workflow recipe

```bash
# baseline run on your current setup
effbench go --tag recipe-current --out current.html

# try a different setup; re-run after editing the bat / launch script
effbench go --tag recipe-new --out new.html

# compare
effbench compare --ledger effbench.jsonl --tag recipe-new --against recipe-current \
                 --out compare.html

# shareable Markdown
effbench share --ledger effbench.jsonl --tag recipe-current

# spreadsheet
effbench csv --ledger effbench.jsonl --tag recipe-current --out current.csv
```

---

## How effective t/s works

Three numbers per task, two numbers per run:

- **Raw t/s** — tokens per second, from the server's `usage.completion_tokens / wall_time`. Wall-clock, not server-reported.
- **Pass rate** — fraction of tasks whose deterministic grader accepts the output.
- **Effective t/s** = raw × pass rate. The "fast-but-wrong is not fast" number.

An errored request (server 500, timeout, network drop) is recorded as a **failure**, not skipped. From the user's chair that's what an error is.

---

## Why this exists

I built this because I kept seeing two servers with the same model and very different answers. One was 30% faster on a benchmark and visibly worse on real work. The existing tools — speed benchmarks, eval harnesses, leader-boards — — measure one axis each. effbench measures the one that matters when you're actually using the model.

---

## License

MIT.
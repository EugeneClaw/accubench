# AccuBench — Architecture Brief

**What:** A deterministic, quality-weighted benchmark for llama.cpp (and any
OpenAI-compatible) local inference servers.

**Why:** Existing tools measure one axis. `llama-bench` measures raw t/s with
zero notion of output quality. Eval harnesses (lm-eval etc.) measure quality but
not serving throughput, and are heavy to point at a live `llama-server`. Nobody
publishes the metric that actually matters for a local box you *use*:

    effective t/s = raw t/s × task pass-rate

Fast-but-wrong is not fast. This tool measures both axes in one pass, for any
recipe (quant / draft depth / cache type / reasoning budget), and renders
self-contained HTML reports you can compare side by side.

## Non-negotiables

1. **Stdlib only.** Python 3.9+, no pip installs, no CDNs. Runs anywhere,
   including on the LAN box itself.
2. **Deterministic graders.** No LLM-as-judge. Every task has a machine-verifiable
   answer (exact / contains / regex / code-exec / json-schema-lite). A benchmark
   anyone can run must give the same verdict twice.
3. **Measured timing.** Wall-clock and server-reported `predicted_per_second`
   recorded separately; spec-decode draft/accept counts recorded when present;
   cold-start excluded from per-task t/s.
4. **Append-only ledger.** Results are JSONL, never mutated. Comparisons read
   the ledger. You can always answer "what changed and when".
5. **Self-contained reports.** One HTML file, inline SVG charts, dark theme,
   no external assets. Openable in 2036.

## Layout

    accubench/
    ├── README.md
    ├── LICENSE                      (MIT)
    ├── accubench/
    │   ├── __init__.py
    │   ├── __main__.py              CLI entry (argparse subcommands)
    │   ├── client.py                OpenAI-compatible HTTP client (urllib)
    │   ├── tasks.py                 task loading + validation
    │   ├── verify.py                graders (pure functions: (output, grader) -> (bool, detail))
    │   ├── ledger.py                JSONL append, load, aggregate, compare
    │   └── report.py                HTML + inline SVG generation
    ├── suites/
    │   ├── reasoning.json           ~8 tasks, deterministic answers
    │   ├── code.json                ~8 tasks, exec-verified
    │   └── longform.json            ~6 tasks, structural checks
    ├── examples/                    sample report + ledger
    └── tools/soak.py                long-duration stability loop (dogfood)

## CLI

    python3 -m accubench run    --url http://host:port --suite suites/ [--tag NAME]
    python3 -m accubench report --ledger results.jsonl --out report.html [--tags A,B]
    python3 -m accubench compare --ledger results.jsonl --tag A --against B
    python3 -m accubench validate --suite suites/code.json     # grader self-test

`validate` is the quality gate: it runs every task's grader against a known-good
and a known-bad output. A grader that passes bad output is a bug, not a feature.

## Task schema (JSON)

    {
      "id": "fizzbuzz-100",
      "category": "code",
      "prompt": "Write a Python function ... print fizzbuzz 1..100 ...",
      "max_tokens": 800,
      "grader": {
        "type": "code",              # exact|contains|regex|code|json
        "language": "python",
        "stdin": "",                 # optional
        "expect_stdout": "1 2 fizz ...",
        "timeout_s": 10
      }
    }

`code` grader: extract the *last* fenced ```python block from the reply, write
to temp dir, exec with `subprocess` + timeout, compare normalised stdout.
Normalisation = strip trailing whitespace per line + trailing newline.

## Per-task record (ledger line)

    {"ts": ..., "run_id": "...", "tag": "MAIN-iq4xs-mtp3", "task": "fizzbuzz-100",
     "category": "code", "pass": true, "wall_s": 12.4,
     "prompt_tokens": 210, "completion_tokens": 512,
     "tok_s": 94.1, "prompt_tok_s": 4200.0,
     "draft_n": 380, "draft_accepted": 290, "accept_pct": 76.3,
     "finish": "stop", "server": {"build": "b1-4df29be", "model": "Qwen3.8-27B-IQ4_XS"},
     "grader_detail": "stdout matched"}

## Aggregation

- raw_tps   = median(tok_s) over tasks
- pass_rate = passed / total
- eff_tps   = raw_tps × pass_rate        ← the headline number
- per category, plus overall; spec-decode accept% averaged
- comparison = same table for two tags + delta column

## Report (single HTML)

1. Header: run metadata (tags, date, server build/model, flags if known)
2. Headline cards: raw t/s, pass rate, effective t/s per tag
3. Grouped bar chart: raw vs effective per category per tag (inline SVG)
4. Scatter: accept% vs t/s (spec-decode health)
5. Full per-task table with pass/fail chips and grader detail
6. Footer: tool version, ledger path, reproducibility command line

## Tonight's dogfood plan (soak)

Loop until stopped, ~25 min/cycle: run all suites tagged `soak-N`, snapshot
/props + /health, append heartbeat line. Watchdog cron checks heartbeat age;
morning cron renders the report and lists anomalies (drift, failures, stalls).

## Out of scope for v1

Multi-server orchestration, LLM-judge tasks, token-level cost tracking,
Windows-native GPU counters. v1 must be excellent at one thing: measuring
effective t/s with full measurement.

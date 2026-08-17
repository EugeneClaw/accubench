# Contributing to

Thanks for your interest in `effbench`. This is a small tool with a small surface area; contributions are welcome but please keep them focused.

## Project structure

```
effbench/
├── effbench/             # the package itself
│   ├── __main__.py       # argparse + all subcommand dispatch
│   ├── client.py         # OpenAI-compatible HTTP client (stdlib only)
│   ├── tasks.py          # suite loader + validation
│   ├── verify.py         # the 6 grader types (exact/contains/json/code-exec/...)
│   ├── ledger.py         # JSONL append-only ledger + aggregation
│   ├── report.py         # self-contained HTML report (inline SVG, no CDNs)
│   ├── wizard.py         # the `effbench go` flow
│   ├── config.py         # ~/.effbench/config.json
│   ├── csv_export.py     # Sheets/Excel CSV writers
│   ├── share.py          # copy-pasteable Markdown
│   ├── explainer.py      # purpose + difficulty tags for every task
│   ├── expectations.py   # hardware-class inference + reference bands
│   └── expectations.json # the reference band library (edit this to add data)
├── suites/               # the task suites (JSON, each with good/bad fixtures)
│   ├── quick.json        # 12 tasks, ~10s per run
│   ├── seed.json         # the original 8 tasks
│   ├── reasoning.json    # 10 reasoning tasks
│   ├── code.json         # 10 code tasks (executed, not admired)
│   └── longform.json     # 8 structural-discipline tasks
├── tools/                # developer tools (not part of the package itself)
│   ├── selftest.py       # 29-check test suite
│   ├── soak.py           # overnight stability loop
│   ├── gen_tasks.py      # draft task banks with an LLM
│   └── adjudicate.py     # apply corrections before any draft ships
├── install.sh            # Mac / Linux one-line installer
├── install.ps1           # Windows PowerShell installer
├── README.md
├── CHANGELOG.md
└── ROADMAP.md
```

## Development setup

```bash
git clone https://github.com/EugeneClaw/effbench.git
cd effbench

# No venv needed (no pip deps). Just run:
python3 -m effbench validate --suite suites/quick.json
python3 tools/selftest.py
```

## Adding a task

Every task needs three things:

1. **`prompt`** — the question to the model.
2. **`grader`** — one of the 6 supported types: `exact`, `contains`, `contains_all`, `regex`, `code`, `json`.
3. **`good_output` and `bad_output`** — known-good and known-bad fixtures. **Your grader must pass the good fixture and fail the bad one. No exceptions.** `python3 -m effbench validate --suite suites/your-suite.json` proves this.

Add `purpose` (chat / code / reasoning / extract / structure / summarise) and `difficulty` (easy / medium / hard) if you're adding to `effbench/explainer.py`'s `TASK_PROFILES`. If you don't, the report will use the task ID and grader type to pick a default — but explicit is better.

Then add the new task to one of the suite files. **Never edit a suite to weaken a grader** (i.e. to make a known-bad output pass). That's the cardinal sin.

## Adding a grader type

If the 6 existing types don't cover your case, add a new one in `effbench/verify.py`. Each grader is a function: `grade(spec, content, reasoning) -> (bool, detail)`. Add a test case in `tools/selftest.py`. Make sure `good_output` and `bad_output` for at least one existing task still pass validation.

## Updating the expectations library

`effbench/expectations.json` holds known-good raw-t/s bands per (hardware class, model arch, quant). To add a new entry:

```json
{
  "hw_class": "desktop_gpu_high",
  "model_arch": "qwen3.27_b",
  "quant": "q5_k_m",
  "tok_s_lo": 100,
  "tok_s_hi": 170,
  "ref_url": "https://..."
}
```

The lookup is exact → relax-quant → relax-model → relax-hw. Add an entry rather than overwriting; new data is more useful than replacing a consensus number.

## Commit conventions

- One logical change per commit.
- Imperative subject line: `fix: …`, `feat: …`, `docs: …`, `chore: …`, `refactor: …`.
- Body explains *why*, not *what*.

## Releases

We tag each shippable state on `main` with `git tag vX.Y.Z`, then `gh release create` with release notes from `CHANGELOG.md`. New features = minor bump. Bug fixes = patch bump.

## Questions / issues

Open an issue on GitHub. Use the bug-report template for problems, the feature-request template for ideas.

## Code of conduct

Be kind. Assume good faith. The bar for "rude" is "would I be embarrassed if this showed up in a public screenshot?". The bar for "helpful disagreement" is "did I explain my reasoning?".
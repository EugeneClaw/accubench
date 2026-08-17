"""Persistent user config stored at ~/.effbench/config.json.

All customisations go here — no command-line defaults for things like
the server URL that vary per user. The installer doesn't write to this
file; only the first run of `effbench go` or `effbench setup` does.
"""
import json
import os

PATH = os.path.expanduser("~/.effbench/config.json")

DEFAULTS = {
    # Server URL. None means: ask on every run, don't assume.
    "url": None,
    # Suite to use for the wizard. None means: auto-detect (use quick).
    "suite": None,
    # Number of runs per task for the wizard.
    "runs": 3,
    # Default ledger path for write commands.
    "ledger": "effbench.jsonl",
    # Default HTML report path.
    "out": "effbench-report.html",
    # Open the report in the browser after rendering.
    "open": False,
}


def load():
    """Read config, falling back to defaults for any missing key."""
    out = dict(DEFAULTS)
    if not os.path.exists(PATH):
        return out
    try:
        with open(PATH) as f:
            saved = json.load(f)
        out.update({k: v for k, v in saved.items() if k in DEFAULTS})
    except (json.JSONDecodeError, OSError):
        pass
    return out


def save(cfg):
    """Persist the full config to disk."""
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def get(key):
    return load().get(key)


def set_value(key, value):
    cfg = load()
    cfg[key] = value
    save(cfg)


def resolve(key, cli_value=None):
    """CLI argument wins; otherwise config; otherwise DEFAULTS."""
    if cli_value is not None:
        return cli_value
    return get(key)
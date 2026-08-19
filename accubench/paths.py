"""Single source of truth for user-data paths.

The rename migration gives AccuBench one data directory (~/.accubench)
and a shim at the old location for the alias window. Everything that
touches the user data dir (config, keystore, ledger, reports) routes
through here so the three resolvers in the menu/config/keystore modules
can never disagree.
"""
import os


def data_dir():
    """Return the user data directory.

    Order:
      1. $ACCUBENCH_HOME (overrides for tests / power users)
      2. ~/.accubench
      3. ~/.effbench (alias window — older installs)
    """
    env = os.environ.get("ACCUBENCH_HOME")
    if env:
        return env
    new = os.path.expanduser("~/.accubench")
    if os.path.isdir(new):
        return new
    old = os.path.expanduser("~/.effbench")
    if os.path.isdir(old):
        return old
    return new


def config_path():
    return os.path.join(data_dir(), "config.json")


def keys_path():
    return os.path.join(data_dir(), "keys.json")


def ledger_path():
    return os.path.join(data_dir(), "ledger.jsonl")


def reports_dir():
    return os.path.join(data_dir(), "reports")


def data_dirs_to_migrate():
    """All candidate old-data dirs the one-time migrator should sweep.

    Today this is just ~/.effbench; if a future release moves again,
    append the older candidate here without changing call sites.
    """
    out = []
    new = os.path.expanduser("~/.accubench")
    old = os.path.expanduser("~/.effbench")
    if os.path.isdir(old) and os.path.realpath(old) != os.path.realpath(new):
        out.append(old)
    return out


def ensure_data_dir():
    os.makedirs(data_dir(), exist_ok=True)
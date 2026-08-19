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
    """Make sure the resolved data dir exists; no-op if it already does."""
    os.makedirs(data_dir(), exist_ok=True)


def migrate_old_data_dir():
    """One-shot copy of the old data dir into the resolved new one on
    first run after upgrade.

    Behaviour:
      * If the resolved new data dir already exists: do nothing (the
        new dir wins).
      * If the old data dir doesn't exist: do nothing (fresh install).
      * Otherwise: copy into a temp dir next to the new dir, write a
        `.migrated` stamp INSIDE the temp dir, then atomic rename into
        place. Old data dir is left untouched for instant rollback.
    Returns the path of the migrated-to directory, or None on no-op.
    Honours $ACCUBENCH_HOME for both source and target.
    """
    import shutil
    import tempfile

    new = os.environ.get("ACCUBENCH_HOME") or os.path.expanduser("~/.accubench")
    # An empty target dir is treated as "not yet created" — we still
    # own its contents in that case, so migrate proceeds. A non-empty
    # target dir means another install owns it; bail out.
    if os.path.isdir(new) and os.listdir(new):
        return None
    old = os.path.expanduser("~/.effbench")
    if not os.path.isdir(old):
        return None
    parent = os.path.dirname(new)
    os.makedirs(parent, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".accubench-migrate-", dir=parent) as tmp:
        # Copy first (succeeds or raises); stamp last so a partial copy
        # never looks like a completed migration to anything that looks
        # at `.migrated`.
        for entry in os.listdir(old):
            src = os.path.join(old, entry)
            dst = os.path.join(tmp, entry)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        # Stamp inside temp dir before rename (R4).
        with open(os.path.join(tmp, ".migrated"), "w", encoding="utf-8") as f:
            f.write("migrated from ~/.effbench\n")
        os.rename(tmp, new)
    return new
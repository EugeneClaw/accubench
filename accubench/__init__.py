"""accubench: quality-weighted benchmark for any OpenAI-compatible inference server.

effective t/s = raw t/s × task pass-rate
"""

__version__ = "0.9.23-dev"


def deprecate_alias_once():
    """Print a one-shot deprecation notice when invoked via the old name.

    QR condition: stderr-only, once per process, never UI, sunset date
    included. Idempotent within a process via a module-level guard.
    """
    if getattr(deprecate_alias_once, "_done", False):
        return
    deprecate_alias_once._done = True
    import sys
    print(
        "note: the 'effbench' command name is an alias for 'accubench'; "
        "the alias is removed in v1.0 — run `accubench` directly.",
        file=sys.stderr,
    )
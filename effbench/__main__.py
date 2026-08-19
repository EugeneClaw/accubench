#!/usr/bin/env python3
"""Compat shim for the v0.9.23 -> v1.0 alias window.

Old `python3 -m effbench ...` and old `.app`/`.lnk` wrappers route here.
Forward to accubench with a one-shot stderr deprecation line so pipes
and the web UI stay clean.
"""
import sys

from accubench.__main__ import main as _accubench_main  # noqa: E402

from accubench import deprecate_alias_once  # noqa: E402

deprecate_alias_once()


def main():
    return _accubench_main()


if __name__ == "__main__":
    sys.exit(main())
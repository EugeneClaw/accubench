"""Compat shim for the v0.9.23 -> v1.0 alias window.

Forwards to accubench and prints a one-shot stderr deprecation line.
"""
from accubench import deprecate_alias_once  # noqa: F401

deprecate_alias_once()
"""API-key storage for cloud endpoints.

A pasted key lives in ~/.effbench/keys.json (0600, user-only) — the same
trust level as any local tool's config dir. Config.json and the ledger
store only a reference, never the key itself. Users who prefer env vars
can ignore this entirely: an unset key here simply falls back to
os.environ at run time.
"""
import json
import os

_KEYS_PATH = os.path.join(os.path.expanduser("~"), ".effbench", "keys.json")


def save_key(endpoint_url, model, key):
    """Store key for this endpoint+model. Empty key removes the entry."""
    data = _load()
    ident = _ident(endpoint_url, model)
    if key:
        data[ident] = key
    else:
        data.pop(ident, None)
    os.makedirs(os.path.dirname(_KEYS_PATH), exist_ok=True)
    with open(_KEYS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    try:
        os.chmod(_KEYS_PATH, 0o600)
    except OSError:
        pass
    return True


def load_key(endpoint_url, model):
    return _load().get(_ident(endpoint_url, model), "")


def list_idents():
    """All stored identities (url::model), for the settings page."""
    return sorted(_load().keys())


def remove_key(endpoint_url, model):
    """Remove one stored key."""
    data = _load()
    ident = _ident(endpoint_url, model)
    if ident in data:
        del data[ident]
        _flush(data)
        return True
    return False


def wipe():
    """Remove ALL stored keys. Returns count removed."""
    data = _load()
    n = len(data)
    if n:
        _flush({})
    return n


def _ident(url, model):
    return (url or "").rstrip("/") + "::" + (model or "")


def _load():
    try:
        with open(_KEYS_PATH, encoding="utf-8") as f:
            v = json.load(f)
            return v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        return {}


def _flush(data):
    os.makedirs(os.path.dirname(_KEYS_PATH), exist_ok=True)
    with open(_KEYS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    try:
        os.chmod(_KEYS_PATH, 0o600)
    except OSError:
        pass


def clear_all():
    """Remove every stored key. Returns how many were removed."""
    data = _load()
    n = len(data)
    if n:
        _flush({})
    return n

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
    """Store key for this endpoint (provider-scoped; model ignored).
    Empty key removes the entry."""
    data = _load()
    ident = _ident(endpoint_url)
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


def load_key(endpoint_url, model=None):
    return _load().get(_ident(endpoint_url), "")


def list_idents():
    """All stored identities (provider URLs), for the settings page."""
    return sorted(_load().keys())


def remove_key(endpoint_url, model=None):
    """Remove one stored key (provider-scoped)."""
    data = _load()
    ident = _ident(endpoint_url)
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


def _ident(url, model=None):
    """Provider-scoped ident: bare URL. Legacy 'url::model' entries on disk
    are migrated to this form on load."""
    return (url or "").rstrip("/")


def _load():
    try:
        with open(_KEYS_PATH, encoding="utf-8") as f:
            v = json.load(f)
            if not isinstance(v, dict):
                return {}
            # migrate legacy "url::model" idents → provider-scoped bare URLs
            migrated = False
            for k in list(v.keys()):
                if "::" in k:
                    url = k.split("::", 1)[0]
                    if url not in v:
                        v[url] = v.pop(k)
                    else:
                        v.pop(k)  # provider entry already exists; drop dupe
                    migrated = True
            if migrated:
                _flush(v)
            return v
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

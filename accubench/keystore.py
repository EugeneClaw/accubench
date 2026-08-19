"""API-key storage for cloud endpoints.

A pasted key lives in ~/.accubench/keys.json (0600, user-only) — the same
trust level as any local tool's config dir. Config.json and the ledger
store only a reference, never the key itself. Users who prefer env vars
can ignore this entirely: an unset key here simply falls back to
os.environ at run time.
"""
import json
import os

from . import paths


def _keys_path():
    return paths.keys_path()


def save_key(endpoint_url, model, key):
    """Store key for this endpoint (provider-scoped; model ignored).
    Empty key removes the entry."""
    data = _load()
    ident = _ident(endpoint_url)
    if key:
        data[ident] = key
    else:
        data.pop(ident, None)
    _flush(data)
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
        with open(_keys_path(), encoding="utf-8") as f:
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
    """Atomic, umask-safe write of the keystore. File mode is 0600 from the
    moment the inode is created (no umask window between open and chmod)."""
    path = _keys_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        # Don't leave a half-written file behind on the user's disk
        try:
            os.remove(path)
        except OSError:
            pass
        raise

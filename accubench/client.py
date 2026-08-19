"""Minimal OpenAI-compatible HTTP client. Stdlib only (urllib)."""
import json
import urllib.request
import urllib.error

TIMEOUT = 1800  # long-form tasks can take minutes on big contexts


def normalise_url(url):
    """User-typed URLs often lack the scheme — add https:// so urllib
    accepts them. Idempotent; leaves everything else untouched."""
    u = (url or "").strip()
    if not u:
        return u
    if not (u.startswith("http://") or u.startswith("https://")):
        u = "https://" + u
    return u


def is_cloud_url(url):
    """Non-local endpoint = cloud (anything not localhost/LAN/loopback)."""
    u = normalise_url(url).lower()
    local_marks = ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "192.168.",
                   "10.", "172.16.", "172.17.", "172.18.", "172.19.",
                   "172.2", "172.30.", "172.31.", ".local", ".ts.net")
    if any(m in u for m in local_marks):
        return False
    return u.startswith("http://") or u.startswith("https://")


def make_client(url, model=None, key_env=None, name="", key=None):
    """Return a CloudClient for remote endpoints, ServerClient otherwise."""
    url = normalise_url(url)
    if is_cloud_url(url):
        from .cloud import CloudClient
        return CloudClient(url, model or "", key_env or "", name, key=key)
    return ServerClient(url)


class ServerClient:
    def __init__(self, url):
        self.url = url.rstrip("/")
        self._props = None

    def _get(self, path, timeout=10):
        req = urllib.request.Request(self.url + path)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def props(self):
        """GET /props. Raises on connection failure — callers can catch."""
        if self._props is None:
            self._props = self._get("/props")
        return self._props

    def health(self):
        """GET /health. Returns dict with status key (or raises)."""
        return self._get("/health", timeout=5)

    def chat(self, payload):
        """POST /v1/chat/completions. Returns (data, error)."""
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            self.url + "/v1/chat/completions", data=body,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode()[:400]
            except Exception:
                detail = ""
            return None, f"HTTP {e.code}: {detail}"
        except Exception as e:
            return None, str(e)[:400]
        # llama-server specific: surface spec-decode stats if present
        perf = data.get("perf_stats") or data.get("timings") or {}
        data["_perf"] = perf
        return data, None

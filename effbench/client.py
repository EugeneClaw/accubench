"""Minimal OpenAI-compatible HTTP client. Stdlib only (urllib)."""
import json
import urllib.request
import urllib.error

TIMEOUT = 1800  # long-form tasks can take minutes on big contexts


def is_cloud_url(url):
    """Non-local endpoint = cloud (anything not localhost/LAN/loopback)."""
    u = (url or "").lower()
    if u.startswith("https://"):
        return True
    local_marks = ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "192.168.",
                   "10.", "172.16.", "172.17.", "172.18.", "172.19.",
                   "172.2", "172.30.", "172.31.", ".local", ".ts.net")
    return not any(m in u for m in local_marks)


def make_client(url, model=None, key_env=None, name=""):
    """Return a CloudClient for remote endpoints, ServerClient otherwise."""
    if is_cloud_url(url):
        from .cloud import CloudClient
        return CloudClient(url, model or "", key_env or "", name)
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

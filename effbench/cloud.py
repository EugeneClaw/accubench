"""Cloud backends for effbench: OpenAI-compatible endpoints with an API key.

The key is read from an environment variable at run time and is never stored
by effbench — config holds only the variable NAME.

Timing model: cloud services deliver tokens in network bursts, so client-side
per-token timing is unreliable for short outputs. effbench reports wall tok/s
exactly as for local servers, and a generation figure derived from streamed
chunk arrival times, labelled estimated. Cloud reports carry a `cloud` source
label so local and cloud numbers are never silently mixed.
"""
import json
import os
import time
import urllib.request
import urllib.error

TIMEOUT = 1800

PRESETS = {
    "zai": {
        "base_url": "https://api.z.ai/api/coding/paas/v4",
        "key_env_default": "GLM_API_KEY",
        "note": "GLM models (z.ai coding plan endpoint)",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "key_env_default": "OPENAI_API_KEY",
        "note": "GPT models",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env_default": "OPENROUTER_API_KEY",
        "note": "Many providers, one key (incl. Claude, Llama, Gemini)",
    },
    "custom": {
        "base_url": "",
        "key_env_default": "",
        "note": "Any OpenAI-compatible /v1 endpoint",
    },
}


class CloudClient:
    """Speaks /v1/chat/completions + synthesised /props so run_task,
    wizard and report work unchanged."""

    def __init__(self, url, model, key_env, name=""):
        self.url = url.rstrip("/")
        self.model = model
        self.name = name
        self._key = os.environ.get(key_env, "")

    def props(self):
        return {
            "model_path": f"cloud::{self.name or self.url}::{self.model}",
            "build": "cloud",
            "total_slots": 1,
            "cloud": True,
            "cloud_name": self.name,
        }

    def health(self):
        return {"status": "ok"}

    def _sanitise_error(self, text):
        """Providers sometimes echo key/account details in error bodies.
        Keep status + first words only; never forward raw provider text."""
        text = (text or "").strip().replace("\n", " ")
        # strip anything that looks like a credential, in any error string
        import re as _re
        text = _re.sub(r"(sk-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._-]{8,}|"
                       r"eyJ[A-Za-z0-9_-]{10,})", "[redacted]", text)
        return text[:160]

    def chat(self, payload):
        body = dict(payload)
        body["model"] = self.model
        body["stream"] = True
        ctk = body.pop("chat_template_kwargs", None)
        if ".z.ai" in self.url and ctk is not None:
            # zai thinking models: translate llama.cpp no-think into zai's switch
            body["thinking"] = {"type": "disabled" if ctk.get("enable_thinking") is False else "enabled"}
        if body.get("max_tokens") is None:
            body["max_tokens"] = 4096
        data = json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if self._key:
            headers["Authorization"] = "Bearer " + self._key
        req = urllib.request.Request(
            self.url + "/chat/completions", data=data, headers=headers)
        content_parts = []
        usage = None
        finish = None
        ttft = None
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                buf = b""
                while True:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        line = line.strip()
                        if not line.startswith(b"data:"):
                            continue
                        raw = line[5:].strip()
                        if raw == b"[DONE]":
                            continue
                        try:
                            ev = json.loads(raw)
                        except ValueError:
                            continue
                        if ttft is None:
                            ch = ev.get("choices") or []
                            d = (ch[0].get("delta") or {}) if ch else {}
                            if d.get("content"):
                                ttft = time.time() - t0
                        if ev.get("usage"):
                            usage = ev["usage"]
                        ch = ev.get("choices") or []
                        if ch:
                            d = ch[0].get("delta") or {}
                            if d.get("content"):
                                content_parts.append(d["content"])
                            finish = ch[0].get("finish_reason") or finish
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode()[:400]
            except Exception:
                detail = ""
            return None, self._sanitise_error("HTTP {}: {}".format(e.code, detail))
        except Exception as e:
            return None, self._sanitise_error(type(e).__name__ + ": " + str(e))
        t_end = time.time()
        content = "".join(content_parts)
        n_completion = (usage or {}).get("completion_tokens")
        if not n_completion and content:
            n_completion = max(1, int(len(content) / 4))
        gen_s = max(0.01, t_end - t0 - (ttft or 0))
        out = {
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish,
            }],
            "usage": {
                "completion_tokens": n_completion,
                "prompt_tokens": (usage or {}).get("prompt_tokens"),
            },
        }
        out["_perf"] = {
            "predicted_per_second": (n_completion / gen_s) if gen_s > 0 else 0,
            "predicted_n": n_completion,
            "predicted_s": gen_s,
            "stream_ttft": ttft,
            "estimated": True,
        }
        return out, None

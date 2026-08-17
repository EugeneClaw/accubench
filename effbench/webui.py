"""Browser front end — a tiny localhost web server (stdlib only).

`effbench` (bare) or `effbench ui` starts this server on 127.0.0.1 and
opens the default browser. Everything the terminal menu does is here:
run quick/full benchmarks with live progress, view and compare past runs,
change settings. Reports are hosted at /report/<name> so results live in
the same front end that produced them.

The server binds 127.0.0.1 only — nothing on your network can reach it.
"""
import json
import os
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import __version__, config, wizard
from .client import ServerClient
from .ledger import append_record, load_ledger, aggregate, suite_of
from .report import render_report
from .expectations import (detect_hw_class, detect_model_arch, detect_quant,
                           lookup, classify_fit)
from .menu import (DATA_DIR, REPORTS_DIR, LEDGER, CANDIDATE_URLS,
                   _suite_path, _tags_summary)

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- shared run state ----------------------------------------------------

_state_lock = threading.Lock()
_state = {
    "running": False,
    "phase": "idle",        # idle | detecting | running | reporting | done | error
    "which": None,
    "tasks_done": 0,
    "tasks_total": 0,
    "current_task": "",
    "tag": None,
    "rows": [],            # per-task results for the live table
    "summary": None,       # final verdict dict
    "error": None,
}


def _set(**kw):
    with _state_lock:
        _state.update(kw)


def _detect_server():
    """Probe config/env/common URLs. Returns (url, props) or (None, [])."""
    tried = []
    candidates = []
    for url in [config.get("url"), os.environ.get("EFFBENCH_URL")] + CANDIDATE_URLS:
        if url and url not in candidates:
            candidates.append(url)
    for url in candidates:
        tried.append(url)
        try:
            props = ServerClient(url).props()
            if config.get("url") != url:
                config.set_value("url", url)
            return url, props, tried
        except Exception:
            continue
    return None, None, tried


def _worker(which):
    """Background benchmark run. One at a time (guarded by _state['running'])."""
    try:
        from .__main__ import run_task
        from .tasks import load_suite
        from types import SimpleNamespace

        _set(phase="detecting", error=None, rows=[], summary=None,
             tasks_done=0, tasks_total=0, current_task="", which=which)
        url, props, _ = _detect_server()
        if not url:
            _set(phase="error", error="No AI server found. Set the server URL in Settings "
                                       "(e.g. http://localhost:11434) and make sure it's running.")
            return

        suite = _suite_path(which)
        tasks = load_suite(suite)
        runs = 1 if which == "quick" else max(1, int(config.get("runs") or 1))
        tag = wizard._autotag(props)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        out = os.path.join(REPORTS_DIR, f"{tag}.html")

        _set(phase="running", tag=tag, tasks_total=len(tasks) * runs,
             model=os.path.basename(props.get("model_path", "?")),
             url=url)

        client = ServerClient(url)
        server = {
            "build": props.get("build", "?"),
            "total_slots": props.get("total_slots", "?"),
            "model_path": props.get("model_path", "?"),
        }
        import uuid
        run_id = uuid.uuid4().hex[:8]
        rows = []
        done = 0
        for ri in range(1, runs + 1):
            for t in tasks:
                _set(current_task=t["id"])
                ns = SimpleNamespace(think=False, tag=tag)
                rec = run_task(client, t, ns, server, run_id, ri)
                append_record(LEDGER, rec)
                done += 1
                rows.append({
                    "task": t["id"], "pass": bool(rec.get("pass")),
                    "tok_s": rec.get("tok_s") or 0,
                    "err": bool(rec.get("error")),
                })
                _set(tasks_done=done, rows=list(rows))

        _set(phase="reporting")
        hwc, klass, band = wizard._make_report(tag, LEDGER, props, out)
        bag = [r for r in load_ledger(LEDGER) if r.get("tag") == tag]
        agg = aggregate(bag)
        suite = suite_of(bag)
        rtps = agg.get("raw_tps") or 0
        summary = {
            "tag": tag,
            "report": f"/report/{os.path.basename(out)}",
            "suite": suite,
            "raw_tps": round(rtps, 1),
            "gen_tps": round(agg.get("gen_tps_median") or 0, 1),
            "peak_tps": round(agg.get("gen_tps_peak") or agg.get("peak_tps") or 0, 1),
            "p90": round(agg.get("p90_tps") or 0, 1),
            "pass_rate": agg.get("pass_rate") or 0,
            "eff_tps": round(agg.get("eff_tps") or rtps * (agg.get("pass_rate") or 0), 1),
            "n_tasks": agg.get("n", 0),
            "n_pass": agg.get("n_pass", 0),
            "fail_tasks": [r.get("task", "?") for r in bag if not r.get("pass")],
            "rows": [
                {"task": r.get("task", "?"), "pass": bool(r.get("pass"))}
                for r in sorted(bag, key=lambda r: r.get("i", 0))
            ],
            "hw_class": hwc,
            "fit": klass,
            "band": list(band[:2]) if band else None,
        }
        _set(phase="done", summary=summary)
        if config.get("open") is not False:
            try:
                webbrowser.open(f"file://{os.path.abspath(out)}")
            except Exception:
                pass
    except Exception as e:
        _set(phase="error", error=str(e)[:300])
    finally:
        _set(running=False)


def _start_run(which):
    with _state_lock:
        if _state["running"]:
            return False
        _state["running"] = True
    threading.Thread(target=_worker, args=(which,), daemon=True).start()
    return True


def _make_compare(tag_a, tag_b):
    recs = load_ledger(LEDGER)
    ra = [r for r in recs if r["tag"] == tag_a]
    rb = [r for r in recs if r["tag"] == tag_b]
    if not ra or not rb:
        return None
    props = None
    try:
        url = config.get("url")
        if url:
            props = ServerClient(url).props()
    except Exception:
        props = None
    model_path = (props or {}).get("model_path", "")
    obs = (aggregate(ra).get("raw_tps", 0) + aggregate(rb).get("raw_tps", 0)) / 2
    hwc = detect_hw_class(props or {}, observed_raw_tps=obs if obs else None)
    arch = detect_model_arch(model_path)
    quant = detect_quant(model_path)
    band_a = lookup(hwc, arch, quant) if props else None
    band_b = band_a
    if props:
        from .expectations import fit_for
        # suite-aware bands per side (quick runs get the ×0.89 scale)
        _, band_a, ka, _ = fit_for(ra, props)
        _, band_b, kb, _ = fit_for(rb, props)
    else:
        ka = classify_fit(aggregate(ra).get("raw_tps", 0), band_a)
        kb = classify_fit(aggregate(rb).get("raw_tps", 0), band_b)
    name = f"compare-{tag_a}-vs-{tag_b}.html"
    out = os.path.join(REPORTS_DIR, name)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    html = render_report([(tag_a, ra, band_a, ka, hwc), (tag_b, rb, band_b, kb, hwc)],
                         props=props, mode="compare")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return f"/report/{name}"


# ---- HTTP handler ---------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):        # silence request logging
        pass

    # -- helpers
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _file(self, path, content_type):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            self._json({"error": "not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- GET
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)

        if u.path in ("/", "/index.html"):
            self._file(os.path.join(HERE, "webui.html"), "text/html; charset=utf-8")

        elif u.path == "/api/state":
            with _state_lock:
                snap = dict(_state)
            snap["version"] = __version__
            snap["config"] = {
                "url": config.get("url"),
                "runs": config.get("runs"),
                "open": config.get("open") is not False,
            }
            self._json(snap)

        elif u.path == "/api/tags":
            self._json({"tags": _tags_summary()})

        elif u.path == "/api/reports":
            import glob as _g
            reps = sorted(_g.glob(os.path.join(REPORTS_DIR, "*.html")),
                          key=os.path.getmtime, reverse=True)
            self._json({"reports": [
                {"name": os.path.basename(r),
                 "when": time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(r)))}
                for r in reps[:50]]})

        elif u.path.startswith("/report/"):
            name = os.path.basename(u.path[len("/report/"):])
            if not name.endswith(".html"):
                self._json({"error": "not found"}, 404)
                return
            self._file(os.path.join(REPORTS_DIR, name), "text/html; charset=utf-8")

        elif u.path == "/api/detect":
            url, props, tried = _detect_server()
            self._json({"found": url, "tried": tried,
                        "model": os.path.basename((props or {}).get("model_path", "?")) if props else None})

        else:
            self._json({"error": "not found"}, 404)

    # -- POST
    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/run":
            body = self._body()
            which = body.get("which")
            if which not in ("quick", "full"):
                self._json({"error": "which must be quick|full"}, 400)
                return
            ok = _start_run(which)
            self._json({"started": ok}, 200 if ok else 409)

        elif u.path == "/api/compare":
            body = self._body()
            a, b = body.get("a"), body.get("b")
            if not a or not b or a == b:
                self._json({"error": "pick two different runs"}, 400)
                return
            path = _make_compare(a, b)
            if path:
                self._json({"report": path})
            else:
                self._json({"error": "runs not found in ledger"}, 404)

        elif u.path == "/api/config":
            body = self._body()
            for k, v in body.items():
                if k in ("url", "runs", "open"):
                    config.set_value(k, v)
            self._json({"ok": True, "config": config.load()})

        elif u.path == "/api/shutdown":
            self._json({"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        else:
            self._json({"error": "not found"}, 404)


def find_port(start=8765, tries=12):
    import socket
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return None


def launch(open_browser=True):
    port = find_port()
    if not port:
        print("effbench: no free port found (8765-8776) — close something and retry.")
        return 1
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print()
    print(f"  effbench {__version__} — web UI")
    print(f"  serving at {url}   (Ctrl-C to stop)")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0

"""Browser front end — a tiny localhost web server (stdlib only).

`effbench` (bare) or `effbench ui` starts this server on 127.0.0.1 and
opens the default browser. Everything the terminal menu does is here:
run quick/full benchmarks with live progress, view and compare past runs,
change settings. Reports are hosted at /report/<name> so results live in
the same front end that produced them.

The server binds 127.0.0.1 only — nothing on your network can reach it.
"""
import glob as _g
import json
import os
import threading
import time
from datetime import datetime
import webbrowser
from . import keystore
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import __version__, config, wizard
from .client import ServerClient, make_client
from .ledger import append_record, load_ledger, aggregate, suite_of
from .report import render_report
from .expectations import (detect_hw_class, detect_model_arch, detect_quant,
                           lookup, classify_fit)
from .__init__ import __version__ as __v__
from .menu import (DATA_DIR, REPORTS_DIR, LEDGER, CANDIDATE_URLS,
                   _suite_path, _tags_summary)

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- shared run state ----------------------------------------------------

_state_lock = threading.Lock()
_state = {
    "running": False,
    "cancel": False,        # set by /api/stop; worker checks between tasks
    "phase": "idle",        # idle | detecting | running | reporting | done | error | cancelled
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
            props = make_client(url).props()
            if config.get("url") != url:
                config.set_value("url", url)
            return url, props, tried
        except Exception:
            continue
    return None, None, tried


def _worker(which):
    """Thread entry: run one benchmark or a whole queue, sequentially."""
    try:
        _worker_inner(which)
    except Exception as e:
        _set(phase="error", error=str(e)[:300])
    finally:
        _set(running=False)


def _worker_inner(which):
    """One pass of the benchmark against the current target (queue-aware)."""
    from .__main__ import run_task
    from .tasks import load_suite
    from types import SimpleNamespace

    _state["cancel"] = False  # plain write; _set/_state_lock not needed
    _set(phase="detecting", error=None, rows=[], summary=None,
         tasks_done=0, tasks_total=0, current_task="", which=which,
         queue_len=len(_state.get("queue") or []))
    cloud = dict(config.get("cloud") or {})
    _q = _state.get("queue") or []
    _qi = _state.get("queue_idx", 0)
    if _q and _qi < len(_q):
        cloud.update(_q[_qi])
    if cloud and cloud.get("url") and cloud.get("model"):
        # cloud run: no local server needed
        from .cloud import CloudClient
        key = keystore.load_key(cloud["url"])
        client = CloudClient(cloud["url"], cloud["model"],
                             cloud.get("key_env", ""),
                             cloud.get("name", cloud.get("provider", "cloud")),
                             key=key or None)
        try:
            props = client.props()
        except Exception as e:
            _set(phase="error", error=f"Cloud endpoint failed: {e}")
            return
        url = cloud["url"]
    else:
        url, props, _ = _detect_server()
        if not url:
            _set(phase="error", error="No AI server found. Set the server URL in Settings "
                                      "(e.g. http://localhost:11434) and make sure it's running.")
            return
        client = make_client(url)

    suite = _suite_path(which)
    tasks = load_suite(suite)
    runs = 1 if which == "quick" else max(1, int(config.get("runs") or 1))
    if cloud and cloud.get("url") and cloud.get("model"):
        cname = cloud.get("name") or cloud.get("provider") or "cloud"
        tag = f"{cname}-{cloud['model']}-cloud-{datetime.now().strftime('%Y%m%d-%H%M%S')}".replace("/", "-").replace(" ", "-")
    else:
        tag = wizard._autotag(props)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    out = os.path.join(REPORTS_DIR, f"{tag}.html")

    _set(phase="running", tag=tag, tasks_total=len(tasks) * runs,
         model=os.path.basename(props.get("model_path", "?")),
         url=url)

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
            with _state_lock:
                cancelled = _state.get("cancel")
            if cancelled:
                _set(phase="cancelled")
                return
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
    from .grade import grade_run
    grade = grade_run(agg.get("n_pass", 0), agg.get("n", 0))
    rtps = agg.get("raw_tps") or 0
    summary = {
        "tag": tag,
        "grade": grade,
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
    # batch bookkeeping: record result, then advance or finish
    q = _state.get("queue") or []
    if q:
        with _state_lock:
            _state.setdefault("q_done", []).append({
                "tag": summary["tag"], "grade": summary.get("grade"),
                "pass_rate": summary.get("pass_rate"),
                "eff_tps": summary.get("eff_tps"),
            })
            idx = _state.get("queue_idx", 0) + 1
            _state["queue_idx"] = idx
        if idx < len(q):
            _set(phase="queue_next", queue_idx=idx)
            _worker_inner(which)  # same thread — sequential batch
            return
        # queue exhausted → full batch done
        with _state_lock:
            batch = list(_state.get("q_done") or [])
        _set(phase="done", summary=summary, batch=batch)
        return

    _set(phase="done", summary=summary)
    if config.get("open") is not False:
        try:
            webbrowser.open(f"file://{os.path.abspath(out)}")
        except Exception:
            pass


def _start_run(which, queue=None):
    with _state_lock:
        if _state["running"]:
            return False
        _state["running"] = True
        _state["queue"] = [dict(t) for t in queue] if queue else None
        _state["q_done"] = []
        _state["queue_idx"] = 0
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
            props = make_client(url).props()
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
        self.send_header("Cache-Control", "no-store, max-age=0")
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
                "cloud": config.get("cloud"),
                "runs": config.get("runs"),
                "open": config.get("open") is not False,
            }
            self._json(snap)

        elif u.path == "/api/tags":
            self._json({"tags": _tags_summary()})

        if u.path == "/api/export":
            recs = load_ledger(LEDGER)
            names = {}
            for f in _g.glob(os.path.join(REPORTS_DIR, "*.name")):
                with open(f, encoding="utf-8") as fh:
                    names[os.path.basename(f)[:-5]] = fh.read().strip()
            payload = {"format": "effbench-export", "version": __v__,
                       "names": names, "records": recs}
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Disposition",
                             'attachment; filename="effbench-results.json"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        elif u.path == "/api/leaderboard":
            import re as _re
            tags = _tags_summary()
            for t in tags:
                recs = [r for r in load_ledger(LEDGER) if r.get("tag") == t["tag"]]
                t["suite"] = suite_of(recs)
            models = {}
            for t in tags:
                base = _re.sub(r"-\d{8}-\d{6}$", "", t["tag"])
                key = (base, t.get("suite") or "unknown")
                m = models.setdefault(key, {"runs": 0, "best_pass": -1.0,
                                             "best_tps": 0.0, "best_eff": 0.0,
                                             "best_tag": t["tag"], "custom": t.get("custom")})
                m["runs"] += 1
                if (t.get("pass") or 0) > m["best_pass"]:
                    m["best_pass"] = t.get("pass") or 0
                    m["best_tps"] = t.get("tps") or 0
                    m["best_eff"] = t.get("eff_tps") or 0
                    m["best_tag"] = t["tag"]
                    m["custom"] = t.get("custom")
            out = []
            for (base, suite), m in models.items():
                suffix = " (quick)" if suite == "quick" else ""
                out.append({
                    "model": base + suffix,
                    "label": (m["custom"] or base) + suffix,
                    "suite": suite,
                    "runs": m["runs"],
                    "pass": m["best_pass"],
                    "tps": m["best_tps"],
                    "eff_tps": m["best_eff"],
                    "tag": m["best_tag"],
                    "where": "cloud" if "cloud" in base else "local",
                })
            suite_order = {"full": 0, "quick": 1}
            # position follows best pass-rate (user rule); suite stays as a label, tiebreak on eff t/s
            out.sort(key=lambda x: (-x["pass"], -(x.get("eff_tps") or 0)))
            for i, e in enumerate(out):
                e["rank"] = i + 1
            self._json({"entries": out})

        elif u.path == "/api/rename":
            body = self._body()
            name = os.path.basename(body.get("name") or "")
            if not name.endswith(".html"):
                self._json({"ok": False, "error": "bad name"}, 400)
                return
            custom = (body.get("custom") or "").strip()[:80]
            side = os.path.join(REPORTS_DIR, name[:-5] + ".name")
            try:
                if custom:
                    with open(side, "w", encoding="utf-8") as f:
                        f.write(custom)
                else:
                    if os.path.exists(side):
                        os.remove(side)
                self._json({"ok": True})
            except OSError as e:
                self._json({"ok": False, "error": str(e)}, 500)
            return

        elif u.path == "/api/reports":
            reps = sorted(_g.glob(os.path.join(REPORTS_DIR, "*.html")),
                          key=os.path.getmtime, reverse=True)
            out = []
            for r in reps[:50]:
                entry = {"name": os.path.basename(r),
                         "when": time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(r)))}
                side = r[:-5] + ".name"
                try:
                    with open(side, encoding="utf-8") as f:
                        entry["custom"] = f.read().strip() or None
                except OSError:
                    entry["custom"] = None
                out.append(entry)
            self._json({"reports": out})

        elif u.path.startswith("/report/"):
            name = os.path.basename(u.path[len("/report/"):])
            if not name.endswith(".html"):
                self._json({"error": "not found"}, 404)
                return
            path = os.path.join(REPORTS_DIR, name)
            # inject custom name into the served page if one exists
            side = path[:-5] + ".name"
            try:
                with open(side, encoding="utf-8") as f:
                    custom = f.read().strip()
                if custom:
                    import re as _re
                    with open(path, "rb") as f:
                        html = f.read()
                    html = _re.sub(rb"<h1>[^<]*</h1>",
                                   f"<h1>{custom}</h1>".encode(), html, count=1)
                    body = html
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
            except OSError:
                pass
            # HTML missing → regenerate from ledger (reports are derived data)
            if not os.path.exists(path):
                tag = name[:-5]
                if any(r.get("tag") == tag for r in load_ledger(LEDGER)):
                    try:
                        wizard._make_report(tag, LEDGER, {}, path)
                    except Exception:
                        pass
            if os.path.exists(path):
                self._file(path, "text/html; charset=utf-8")
            else:
                body = ("<!doctype html><meta charset=utf-8><body style=\"background:#07090D;"
                        "color:#C3CDD9;font:15px/1.6 -apple-system,sans-serif;padding:48px\">"
                        "<h2 style=\"color:#E8EDF4\">report not found</h2>"
                        "<p>No HTML for this run and no ledger records to rebuild it from "
                        "— the run was removed or never finished writing.</p></body>")
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body.encode())
            return

        elif u.path == "/api/cloud-models":
            from .cloud import CloudClient
            from .client import is_cloud_url, normalise_url
            q = parse_qs(u.query)
            curl = normalise_url((q.get("url") or [""])[0])
            model = (q.get("model") or [""])[0].strip()
            kenv = (q.get("key_env") or [""])[0].strip()
            pasted = (q.get("key") or [""])[0].strip()
            if not curl or not (curl.startswith("http://") or curl.startswith("https://")):
                self._json({"error": "not a cloud URL"}, 400)
                return
            key = pasted or keystore.load_key(curl)
            if not key:
                self._json({"error": "no key — paste it in the key field first"}, 400)
                return
            try:
                cc = CloudClient(curl, model, kenv, key=key)
                models = cc.list_models()
                self._json({"models": models})
            except Exception as e:
                self._json({"error": (type(e).__name__ + ": " + str(e))[:200]}, 502)

        elif u.path == "/api/key-status":
            u_ = parse_qs(u.query)
            kurl = (u_.get("url") or [""])[0]
            if not kurl:
                self._json({"saved": False}, 400)
                return
            self._json({"saved": bool(keystore.load_key(kurl))})

        elif u.path == "/api/keys":
            idents = keystore.list_idents()
            self._json({"idents": idents})

        elif u.path == "/api/detect":
            url, props, tried = _detect_server()
            self._json({"found": url, "tried": tried,
                        "model": os.path.basename((props or {}).get("model_path", "?")) if props else None})

        else:
            self._json({"error": "not found"}, 404)

    # -- POST
    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/stop":
            if _state.get("phase") not in ("running", "detecting"):
                self._json({"ok": False, "error": "no run in progress"}, 409)
                return
            with _state_lock:
                _state["cancel"] = True
            self._json({"ok": True, "acknowledged": True})
            return

        if u.path == "/api/run":
            body = self._body()
            which = body.get("which")
            if which not in ("quick", "full"):
                self._json({"error": "which must be quick|full"}, 400)
                return
            queue = body.get("queue") or []
            if queue and which != "full":
                self._json({"error": "batch queue requires full suite"}, 400)
                return
            ok = _start_run(which, queue=queue)
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

        elif u.path == "/api/cloud-test":
            body = self._body()
            from .cloud import CloudClient
            from .client import is_cloud_url, normalise_url
            curl = normalise_url(body.get("url") or "")
            model = (body.get("model") or "").strip()
            kenv = (body.get("key_env") or "").strip()
            pasted = (body.get("api_key") or "").strip()
            if not curl or not is_cloud_url(curl):
                self._json({"ok": False, "detail": "not a valid cloud URL"})
                return
            if not model:
                self._json({"ok": False, "detail": "model id is empty"})
                return
            # key resolution: pasted > saved > env var
            key = pasted or keystore.load_key(curl) or (os.environ.get(kenv) if kenv else None)
            if not key:
                self._json({"ok": False,
                            "detail": "no API key — paste one in the key field, or set the env var"})
                return
            try:
                cc = CloudClient(curl, model, kenv, key=key)
                txt, err = cc.chat({"messages": [{"role": "user", "content": "Say OK"}],
                                    "max_tokens": 40})
                if err:
                    self._json({"ok": False, "detail": err[:200]})
                else:
                    self._json({"ok": True, "detail": f"model replied ({len(txt or '')} chars)"})
            except Exception as e:
                self._json({"ok": False, "detail": (type(e).__name__ + ": " + str(e))[:200]})
            return
        elif u.path == "/api/key-remove":
            body = self._body()
            from .client import normalise_url
            url = normalise_url(body.get("url") or "")
            model = (body.get("model") or "").strip()
            if not url or not model:
                self._json({"ok": False, "error": "url and model required"}, 400)
                return
            gone = keystore.remove_key(url, model)
            self._json({"ok": gone})

        elif u.path == "/api/key-wipe":
            n = keystore.wipe()
            self._json({"ok": True, "removed": n})

        elif u.path == "/api/import":
            body = self._body()
            raw = (body.get("data") or "").strip()
            if not raw:
                self._json({"ok": False, "error": "empty import"}, 400)
                return
            try:
                doc = json.loads(raw)
                if isinstance(doc, dict) and doc.get("format") == "effbench-export":
                    incoming, in_names = doc.get("records", []), doc.get("names", {})
                else:
                    raise ValueError
            except ValueError:
                incoming = []
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        r = json.loads(line)
                        if isinstance(r, dict) and r.get("tag"):
                            incoming.append(r)
                    except ValueError:
                        pass
                in_names = {}
            if not incoming:
                self._json({"ok": False, "error": "no records found"}, 400)
                return
            existing = {(r.get("run_id"), r.get("task"), r.get("run_idx"), r.get("tag"))
                        for r in load_ledger(LEDGER)}
            added = 0
            new_tags = set()
            for r in incoming:
                k = (r.get("run_id"), r.get("task"), r.get("run_idx"), r.get("tag"))
                if k in existing:
                    continue
                append_record(LEDGER, r)
                existing.add(k)
                added += 1
                new_tags.add(r["tag"])
            reports = 0
            os.makedirs(REPORTS_DIR, exist_ok=True)
            for tag in sorted(new_tags):
                try:
                    wizard._make_report(tag, LEDGER, None,
                                        os.path.join(REPORTS_DIR, f"{tag}.html"))
                    reports += 1
                except Exception:
                    pass
                if in_names.get(tag):
                    with open(os.path.join(REPORTS_DIR, f"{tag}.name"), "w",
                              encoding="utf-8") as fh:
                        fh.write(in_names[tag])
            self._json({"ok": True, "added": added, "skipped": len(incoming) - added,
                        "reports": reports})

        elif u.path == "/api/report-delete":
            body = self._body()
            name = os.path.basename(body.get("name") or "")
            if not name.endswith(".html") or ".." in name:
                self._json({"ok": False, "error": "bad name"}, 400)
                return
            target = os.path.join(REPORTS_DIR, name)
            removed = []
            try:
                for suffix in (".html", ".name"):
                    p = target[:-5] + suffix if suffix == ".name" else target
                    if os.path.exists(p):
                        os.remove(p)
                        removed.append(os.path.basename(p))
                self._json({"ok": True, "removed": removed})
            except OSError as e:
                self._json({"ok": False, "error": str(e)}, 500)
            return

        elif u.path == "/api/key-reveal":
            body = self._body()
            url = (body.get("url") or "").strip()
            model = (body.get("model") or "").strip()
            if not url:
                self._json({"ok": False, "error": "url required"}, 400)
                return
                key = keystore.load_key(url)
            if key:
                self._json({"ok": True, "key": key, "len": len(key)})
            else:
                self._json({"ok": False, "error": "no key stored for this provider"})
            return

        elif u.path == "/api/config":
            body = self._body()
            # a pasted API key goes to the keystore (0600), never config.json
            cloud = body.get("cloud")
            pasted = ""
            if isinstance(cloud, dict):
                pasted = (cloud.get("api_key") or "").strip()
            pasted = pasted or (body.get("api_key") or "").strip()
            if isinstance(cloud, dict):
                cloud.pop("api_key", None)  # strip BEFORE persisting config
                from .client import normalise_url
                cloud["url"] = normalise_url(cloud.get("url") or "")
            for k, v in body.items():
                if k in ("url", "runs", "open", "cloud"):
                    if k == "url" and not (v or "").strip():
                        continue  # blank URL never overwrites a saved one
                    config.set_value(k, v)
            if isinstance(cloud, dict) and cloud.get("url") and cloud.get("model"):
                if pasted:
                    keystore.save_key(cloud["url"], cloud["model"], pasted)
                elif body.get("clear_key"):
                    keystore.save_key(cloud["url"], cloud["model"], "")
            elif body.get("clear_key") and cloud is None:
                # turning cloud off entirely → wipe saved keys too
                for ident in list(keystore._load()):
                    url, _, model = ident.partition("::")
                    keystore.save_key(url, model, "")
            self._json({"ok": True, "config": config.load(),
                        "key_saved": bool(pasted)})

        elif u.path == "/api/config-reset":
            body = self._body()
            removed = {"config": False, "keys": 0}
            try:
                if os.path.exists(config.PATH):
                    os.remove(config.PATH)
                    removed["config"] = True
            except OSError:
                pass
            if body.get("keys"):
                removed["keys"] = keystore.clear_all()
            self._json({"ok": True, **removed})

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


_BANNER = [
    r"                 _                 _    ",
    r" __ _ __ __ _  _| |__  ___ _ _  __| |_  ",
    r"/ _` / _/ _| || | '_ \/ -_) ' \/ _| ' \ ",
    r"\__,_\__\__|\_,_|_.__/\___|_||_\__|_||_|",
    r"                                        ",
]
_SPEED_LINES = [
    "        __         ",
    " -- ___/  \__      ",
    "   /         \___  ",
    "  _> O   O        >",
]


def _print_banner():
    import sys, time
    for line in _BANNER:
        print("\033[2m" + line + "\033[0m")
        sys.stdout.flush()
        time.sleep(0.05)
    for line in _SPEED_LINES:
        print("\033[1m\033[32m" + line + "\033[0m")
        sys.stdout.flush()
        time.sleep(0.12)
    print()


def launch(open_browser=True):
    port = find_port()
    if not port:
        print("effbench: no free port found (8765-8776) — close something and retry.")
        return 1
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)

    # browsers abort in-flight polls on refresh/close — not errors; stay quiet
    _orig_handle_error = srv.handle_error

    def _quiet_error(request, client_address):
        import sys
        et = sys.exc_info()[0]
        if et is None or issubclass(et, (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
            return
        _orig_handle_error(request, client_address)

    srv.handle_error = _quiet_error
    url = f"http://127.0.0.1:{port}/"
    try:
        _print_banner()
    except Exception:
        print()
    print(f"  AccuBench {__version__} (effbench) — web UI")
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

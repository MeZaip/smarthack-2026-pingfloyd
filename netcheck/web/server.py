"""Local server behind the desktop app. Standard library only.

Two listeners, same code:
  * the LOCAL one (127.0.0.1) is the app itself: pages, live data, scan, delete history;
  * the PHONE one ("Show on my phone") listens on the laptop's LAN address only while it is switched on
    (auto-off after 30 minutes). It is READ-ONLY and needs the secret key that is inside the QR code.

Security (the product is about security, so the app must be clean too):
  * every request must carry the exact Host of its listener (stops DNS-rebinding pages);
  * every POST needs the per-start token that only the local page receives (CSRF), and is refused on the phone listener;
  * live scans need confirm=true and still go through net.guardrail (own private subnet only, <= /22);
  * files are served from a fixed allow-list, never from a path in the request;
  * scan text reaches the page as JSON data and is inserted only with textContent (ui/app.js).
"""
from __future__ import annotations

import hmac
import json
import os
import secrets
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qs, urlparse

from .. import history
from ..core.analysis import analyze_file
from . import uidata

UI_DIR = uidata.ROOT / "ui"
STATIC = {   # published path -> (file in ui/, content type)
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}
MAX_JSON = 16 * 1024
PHONE_MINUTES = 30
DEFAULT_HOME = Path.home() / ".netcheck"


def _private_dir(p: Path) -> Path:
    if not p.exists():
        p.mkdir(mode=0o700, parents=True)   # scans are personal data: owner-only (NFR-02)
    return p


class App:
    """Everything one running app knows."""

    def __init__(self, scans_dir: Optional[Path] = None, db: Optional[str] = None,
                 detect: Optional[Callable] = None, scan_runner: Optional[Callable] = None):
        from ..net import netdetect, scanner
        self.token = secrets.token_urlsafe(32)        # CSRF token for the local page
        self.phone_key = None                         # secret inside the QR code, set while phone mode is on
        self.scans_dir = Path(scans_dir) if scans_dir else DEFAULT_HOME / "scans"
        self.db = db
        self.detect = detect or netdetect.detect
        self.scan_runner = scan_runner or scanner.run_scan_app
        self.find_nmap = scanner.find_nmap
        self.lock = threading.Lock()
        self.jobs: dict[str, dict] = {}
        self.local: Optional[ThreadingHTTPServer] = None
        self.phone: Optional[ThreadingHTTPServer] = None
        self.phone_until = 0.0
        self._phone_timer: Optional[threading.Timer] = None

    # ------------------------------------------------------------------ data
    def data_js(self) -> str:
        return uidata.to_js(uidata.live_data(self.scans_dir, self.db))

    def config_js(self, phone: bool) -> str:
        cfg = {"app": True, "phone": phone, "token": None if phone else self.token}
        return f"window.NETCHECK_APP = {json.dumps(cfg)};\n"

    def network(self) -> dict:
        from ..net import netdetect
        try:
            n = self.detect()
            return {"ok": True, "subnet": n.subnet, "ip": n.ip, "gateway": n.gateway or None, "interface": n.interface}
        except netdetect.NetworkDetectError as e:
            return {"ok": False, "error": str(e)}

    def state(self) -> dict:
        with self.lock:
            running = next(({"job": k, **v} for k, v in self.jobs.items() if v["state"] == "running"), None)
        phone = None
        if self.phone:
            host, port = self.phone.server_address[:2]
            phone = {"url": f"http://{host}:{port}/?k={self.phone_key}", "minutes_left": max(0, int((self.phone_until - time.time()) // 60))}
        return {"nmap": bool(self.find_nmap()), "network": self.network(), "scan": running, "phone": phone}

    # ------------------------------------------------------------------ actions
    def start_scan(self, mode: str) -> dict:
        from ..net import guardrail, netdetect
        if mode not in ("quick", "full"):
            raise ApiError(400, "bad mode")
        if not self.find_nmap():
            return {"started": False, "reason": "nmap", "message": "nmap is not installed on this computer."}
        try:
            net = self.detect()
            allow = guardrail.build_allowlist(net.subnet)
            target = guardrail.check_target(net.subnet, allow, confirmed=True)
        except guardrail.ScopeError as e:
            return {"started": False, "reason": "refused", "message": e.message("en")}
        except netdetect.NetworkDetectError as e:
            return {"started": False, "reason": "network", "message": f"Could not find your network: {e}"}
        with self.lock:
            if any(j["state"] == "running" for j in self.jobs.values()):
                return {"started": False, "reason": "busy", "message": "A check is already running."}
            job = uuid.uuid4().hex[:12]
            self.jobs[job] = {"state": "running", "target": target, "mode": mode, "started": time.time()}
        threading.Thread(target=self._scan, args=(job, target, mode), daemon=True).start()
        return {"started": True, "job": job, "target": target, "mode": mode}

    def _scan(self, job: str, target: str, mode: str) -> None:
        try:
            xml = self.scan_runner(target, _private_dir(self.scans_dir), mode)
            a = analyze_file(xml)
            if a.ok:
                with history.open_history(self.db) as conn:
                    history.save(conn, a)
            result = {"state": "done", "score": a.score if a.ok else None, "error": a.error}
        except Exception as e:  # shown to the user instead of failing silently
            result = {"state": "error", "message": str(e)[:300]}
        with self.lock:
            self.jobs[job] = {**self.jobs[job], **result}

    def delete_history(self) -> dict:
        deleted = history.delete_history(self.db)
        removed = 0
        if self.scans_dir.is_dir():
            for f in self.scans_dir.glob("scan_*.xml"):
                f.unlink()
                removed += 1
        return {"deleted": deleted or bool(removed), "scans_removed": removed}

    def phone_on(self) -> dict:
        from ..net import netdetect
        if self.phone:
            return self.state()["phone"]
        try:
            ip = self.detect().ip
        except netdetect.NetworkDetectError as e:
            raise ApiError(409, f"Could not find your network: {e}") from None
        self.phone_key = secrets.token_urlsafe(18)
        srv = ThreadingHTTPServer((ip, 0), make_handler(self, phone=True))
        srv.allowed_host = f"{ip}:{srv.server_address[1]}"
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.phone = srv
        self.phone_until = time.time() + PHONE_MINUTES * 60
        self._phone_timer = threading.Timer(PHONE_MINUTES * 60, self.phone_off)
        self._phone_timer.daemon = True
        self._phone_timer.start()
        return self.state()["phone"]

    def quit(self) -> None:
        self.phone_off()
        if self.local:
            threading.Thread(target=self.local.shutdown, daemon=True).start()

    def phone_off(self) -> dict:
        srv, self.phone, self.phone_key = self.phone, None, None
        if self._phone_timer:
            self._phone_timer.cancel()
        if srv:
            srv.shutdown()
            srv.server_close()
        return {"off": True}


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def make_handler(app: App, phone: bool):
    class Handler(BaseHTTPRequestHandler):
        server_version = "netcheck-app"
        sys_version = ""

        def log_message(self, fmt, *args):   # no request logs (privacy)
            pass

        def _send(self, status: int, body: bytes, ctype: str, extra: Optional[dict] = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, obj) -> None:
            self._send(status, json.dumps(obj).encode(), "application/json; charset=utf-8")

        def _host_ok(self) -> bool:
            return (self.headers.get("Host") or "").lower() == getattr(self.server, "allowed_host", "")

        def _phone_key_ok(self, q: dict) -> bool:
            key = app.phone_key or ""
            cookie = ""
            for part in (self.headers.get("Cookie") or "").split(";"):
                k, _, v = part.strip().partition("=")
                if k == "nck":
                    cookie = v
            given = q.get("k") or cookie
            return bool(key) and hmac.compare_digest(given, key)

        def do_GET(self):
            if not self._host_ok():
                return self._json(403, {"error": "forbidden host"})
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            extra = None
            if phone:
                if not self._phone_key_ok(q):
                    return self._send(403, b"This link has expired. Ask for a new QR code on the computer.",
                                      "text/plain; charset=utf-8")
                extra = {"Set-Cookie": f"nck={app.phone_key}; HttpOnly; SameSite=Strict; Path=/"}
            try:
                if url.path in ("/", "/index.html"):
                    html = (UI_DIR / "index.html").read_text(encoding="utf-8")
                    html = html.replace('<script src="data.js"></script>',
                                        '<script src="config.js"></script>\n  <script src="data.js"></script>')
                    return self._send(200, html.encode(), "text/html; charset=utf-8", extra)
                if url.path == "/config.js":
                    return self._send(200, app.config_js(phone).encode(), "text/javascript; charset=utf-8", extra)
                if url.path == "/data.js":
                    return self._send(200, app.data_js().encode(), "text/javascript; charset=utf-8", extra)
                if url.path in STATIC:
                    name, ctype = STATIC[url.path]
                    f = UI_DIR / name
                    if f.is_file():
                        return self._send(200, f.read_bytes(), ctype, extra)
                if phone:
                    return self._json(404, {"error": "not found"})
                if url.path == "/api/phone/qr.svg":
                    st = app.state()["phone"]
                    svg = qr_svg(st["url"]) if st else None
                    if not svg:
                        return self._json(404, {"error": "no QR"})
                    return self._send(200, svg, "image/svg+xml")
                routes = {
                    "/api/state": lambda: app.state(),
                    "/api/scan/status": lambda: _job(app, q.get("job")),
                }
                fn = routes.get(url.path)
                if not fn:
                    return self._json(404, {"error": "not found"})
                return self._json(200, fn())
            except ApiError as e:
                return self._json(e.status, {"error": str(e)})

        def do_POST(self):
            if phone or not self._host_ok():
                return self._json(403, {"error": "forbidden"})
            if not hmac.compare_digest(self.headers.get("X-Netcheck-Token", ""), app.token):
                return self._json(403, {"error": "missing or bad token"})
            try:
                body = self._body()
                path = urlparse(self.path).path
                if path == "/api/scan":
                    if body.get("confirm") is not True:
                        raise ApiError(400, "confirmation required")
                    return self._json(200, app.start_scan(str(body.get("mode", "quick"))))
                if path == "/api/history/delete":
                    if body.get("confirm") is not True:
                        raise ApiError(400, "confirmation required")
                    return self._json(200, app.delete_history())
                if path == "/api/quit":
                    threading.Timer(0.3, app.quit).start()
                    return self._json(200, {"bye": True})
                if path == "/api/phone":
                    return self._json(200, {"phone": app.phone_on()} if body.get("on") else app.phone_off())
                return self._json(404, {"error": "not found"})
            except ApiError as e:
                return self._json(e.status, {"error": str(e)})

        def _body(self) -> dict:
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                raise ApiError(415, "expected JSON")
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise ApiError(400, "bad length") from None
            if n < 0 or n > MAX_JSON:
                raise ApiError(413, "too large")
            try:
                obj = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                raise ApiError(400, "bad JSON") from None
            if not isinstance(obj, dict):
                raise ApiError(400, "bad JSON")
            return obj

    return Handler


def qr_svg(text: str) -> Optional[bytes]:
    """QR code as SVG (segno, pure Python). None if segno is not installed: the page then shows the link only."""
    try:
        import io
        import segno
    except ImportError:
        return None
    buf = io.BytesIO()
    segno.make(text, error="m").save(buf, kind="svg", scale=6, border=3, dark="#140c10", light="#ffffff",
                                     xmldecl=False, svgns=True, title="netcheck QR code")
    return buf.getvalue()


def _job(app: App, job) -> dict:
    with app.lock:
        j = app.jobs.get(str(job))
    if not j:
        raise ApiError(404, "unknown job")
    return j


def start(app: App, port: int = 8765) -> ThreadingHTTPServer:
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app, phone=False))
    except OSError:
        srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app, phone=False))   # port busy
    srv.allowed_host = f"127.0.0.1:{srv.server_address[1]}"
    app.local = srv
    return srv


def url_of(srv: ThreadingHTTPServer) -> str:
    return f"http://{srv.allowed_host}/"


def already_running(port: int) -> bool:
    """True if a netcheck app already answers on this port (second double-click: just reopen the page)."""
    import http.client
    try:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
        c.request("GET", "/api/state", headers={"Host": f"127.0.0.1:{port}"})
        r = c.getresponse()
        ok = r.status == 200 and r.getheader("Server", "").startswith("netcheck-app")
        c.close()
        return ok
    except OSError:
        return False


def serve(port: int = 8765, open_browser: bool = True, db: Optional[str] = None,
          scans_dir: Optional[str] = None) -> int:
    if already_running(port):
        if open_browser:
            import webbrowser
            webbrowser.open(f"http://127.0.0.1:{port}/")
        print(f"netcheck is already running at http://127.0.0.1:{port}/")
        return 0
    app = App(Path(scans_dir) if scans_dir else None, db)
    srv = start(app, port)
    url = url_of(srv)
    print(f"netcheck is running at {url}  (close this window or press Ctrl+C to stop)")
    if open_browser:
        import webbrowser
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.phone_off()
        srv.server_close()
    return 0


if os.name == "nt":   # Windows consoles: make sure printing a URL never crashes
    try:
        import sys as _sys
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

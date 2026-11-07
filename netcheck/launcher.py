"""`python -m netcheck app` - what the user's double-click starts (NetCheck.cmd on Windows).

* Starts the local agent (web UI + /api/v1) on a free port of 127.0.0.1, unprivileged.
* On the team's demo machine only: also starts the AI gateway if a key/model is configured locally.
  For real users the gateway is OUR server (NETCHECK_AI_URL=https://...), nothing to start here.
* Opens the UI as an app window: pywebview if installed, else Edge/Chrome in app mode
  (no address bar), else the default browser.
* Stops by itself when the user presses "Close" or closes the window (no heartbeat for 90 s).
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional

NO_WINDOW = 0x08000000


def _log_file() -> Path:
    home = Path(os.environ.get("NETCHECK_HOME") or Path.home() / ".netcheck")
    home.mkdir(parents=True, exist_ok=True)
    return home / "app.log"


def _no_console_safe() -> None:
    """pythonw.exe has no console: sys.stdout is None and any print() would crash. Log to a file instead."""
    if sys.stdout is None or sys.stderr is None:
        f = open(_log_file(), "a", encoding="utf-8", buffering=1)  # noqa: SIM115 - lives as long as the app
        sys.stdout = sys.stdout or f
        sys.stderr = sys.stderr or f


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _healthy(url: str, timeout: float = 6.0) -> bool:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    end = time.time() + timeout
    while time.time() < end:
        try:
            with opener.open(url, timeout=1) as r:
                if r.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(0.3)
    return False


def maybe_start_gateway() -> Optional[subprocess.Popen]:
    """Team demo machine only: start our AI gateway locally if it is configured here."""
    url = os.environ.get("NETCHECK_AI_URL", "")
    if url.startswith("https://") or os.environ.get("NETCHECK_LLM_PROVIDER") == "none":
        return None   # real deployment: the gateway runs on our server
    try:   # the gateway package decides; the app itself never reads an API key
        from gateway.config import Config
    except ImportError:
        return None   # client-only install: no gateway code here
    if not Config.from_env().ready():
        return None   # no key/model on this machine: the assistant uses the built-in texts
    port = free_port()
    log = open(_log_file(), "a", encoding="utf-8")  # noqa: SIM115
    kwargs = {"stdout": log, "stderr": log, "cwd": str(Path(__file__).resolve().parent.parent)}
    if os.name == "nt":
        kwargs["creationflags"] = NO_WINDOW
    proc = subprocess.Popen([sys.executable, "-m", "gateway", "--host", "127.0.0.1", "--port", str(port)], **kwargs)
    os.environ["NETCHECK_AI_URL"] = f"http://127.0.0.1:{port}"
    if not _healthy(f"http://127.0.0.1:{port}/health"):
        proc.terminate()
        os.environ["NETCHECK_LLM_PROVIDER"] = "none"
        return None
    return proc


_APP_BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]


def _app_browser() -> Optional[str]:
    if os.name == "nt":
        return next((p for p in _APP_BROWSERS if os.path.exists(p)), None)
    for name in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser"):
        if shutil.which(name):
            return shutil.which(name)
    return None


def open_window(url: str, mode: str) -> bool:
    """Show the UI. Returns True if this call blocks until the window is closed (pywebview)."""
    if mode in ("auto", "window"):
        try:
            import webview  # type: ignore  # optional: pip install pywebview
            webview.create_window("NetCheck", url, width=1150, height=850, min_size=(420, 600))
            webview.start()
            return True
        except Exception:  # noqa: BLE001 - not installed or no GUI backend: fall back
            pass
    if mode in ("auto", "window", "app"):
        exe = _app_browser()
        if exe:
            try:
                kwargs = {"creationflags": NO_WINDOW} if os.name == "nt" else {}
                subprocess.Popen([exe, f"--app={url}", "--window-size=1150,850"], **kwargs)
                return False
            except OSError:
                pass
    webbrowser.open(url)
    return False


def main(port: int = 0, lang: str = "ro", window: str = "auto", gateway: bool = True) -> int:
    _no_console_safe()
    from .ai.providers import load_dotenv
    load_dotenv()
    os.environ["NETCHECK_APP_MODE"] = "1"          # read when the web app is imported below
    gw = maybe_start_gateway() if gateway else None

    import uvicorn

    from .web import api_v1
    from .web.app import app

    port = port or free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning",
                                           log_config=None))
    api_v1.life.app_mode = True
    api_v1.life.on_stop(lambda: setattr(server, "should_exit", True))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    url = f"http://127.0.0.1:{port}/?lang={lang}"
    print(f"NetCheck: {url}")

    def watchdog():   # window closed without pressing "Close": stop after the page stops beating
        while not server.should_exit:
            time.sleep(5)
            if api_v1.life.idle():
                server.should_exit = True
    threading.Thread(target=watchdog, daemon=True).start()

    try:
        if open_window(url, window):          # pywebview: the window is closed now
            server.should_exit = True
        while thread.is_alive():
            thread.join(1)
    except KeyboardInterrupt:
        server.should_exit = True
    finally:
        if gw is not None:
            gw.terminate()
    return 0

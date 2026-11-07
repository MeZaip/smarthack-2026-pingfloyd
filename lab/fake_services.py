"""Hotspot-lab targets: FAKE services that only send a banner and hang up (brief: "simulate, do not expose").
There is no login, no shell, no data behind any of them. Run on a TARGET laptop joined to the team hotspot.

  python lab/fake_services.py            # "before": all weak services on
  python lab/fake_services.py --fixed    # "after": telnet + plain-HTTP admin + old FTP turned off

Expected findings when scanned:
  2323 telnet  -> TELNET_OPEN          2121 vsFTPd 2.3.4 -> FTP_CLEARTEXT + OUTDATED_SERVICE
  2222 OpenSSH_7.2 -> SSH_OPEN + OUTDATED_SERVICE      5901 RFB -> VNC_EXPOSED
  8080 http "Admin Login" -> HTTP_ADMIN_CLEARTEXT
Stop with Ctrl+C when you leave the venue.
"""
import argparse
import socketserver
import threading

TELNET = b"\xff\xfd\x01\xff\xfd\x1f\xff\xfd\x21\xff\xfb\x01\xff\xfb\x03"
# A well-known Server header so nmap -sV names the service "http" (an unknown banner on 8080
# would keep nmap's table name "http-proxy" and HTTP_ADMIN_CLEARTEXT would not be reported).
_BODY = b"<html><head><title>Admin Login</title></head><body>Lab page. No real login.</body></html>"
HTTP_PAGE = (b"HTTP/1.1 200 OK\r\nServer: lighttpd/1.4.59\r\nContent-Type: text/html\r\n"
             b"Content-Length: " + str(len(_BODY)).encode() + b"\r\nConnection: close\r\n\r\n" + _BODY)
SERVICES = {
    "telnet": (2323, TELNET, False),
    "ftp": (2121, b"220 (vsFTPd 2.3.4)\r\n", False),
    "ssh": (2222, b"SSH-2.0-OpenSSH_7.2p2 Ubuntu-4ubuntu2.8\r\n", True),
    "vnc": (5901, b"RFB 003.008\n", True),
    "http": (8080, None, False),
}


class Handler(socketserver.BaseRequestHandler):
    banner = b""
    is_http = False

    def handle(self):
        # nmap -sV first waits ~6 s for a banner (NULL probe) on the same connection; an HTTP
        # server that hangs up before that is reported as "tcpwrapped" instead of "http".
        self.request.settimeout(15 if self.is_http else 3)
        try:
            if self.is_http:
                self.request.recv(2048)       # read (and ignore) the request
                self.request.sendall(HTTP_PAGE)
            else:
                self.request.sendall(self.banner)
                self.request.recv(256)         # wait briefly, never interpret input
        except OSError:
            pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixed", action="store_true", help="simulate the AFTER state")
    a = ap.parse_args()
    off = {"telnet", "http", "ftp"} if a.fixed else set()
    for name, (port, banner, _) in SERVICES.items():
        if name in off:
            continue
        h = type(f"H_{name}", (Handler,), {"banner": banner or b"", "is_http": banner is None})
        srv = Server(("0.0.0.0", port), h)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print(f"fake {name:<6} listening on {port}")
    print("Ctrl+C to stop.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("stopped")


if __name__ == "__main__":
    main()

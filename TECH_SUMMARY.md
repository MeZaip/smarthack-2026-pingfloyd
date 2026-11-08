# SafeHouse — 1-page technical summary

**Lab setup.** One phone runs hotspot `RSH-PingFloyd` (WPA2/3). Scanner laptop joins only the hotspot. Target laptop runs
`lab/fake_services.py` (banner-only telnet, FTP vsFTPd 2.3.4, SSH OpenSSH 7.2, VNC, plain-HTTP "Admin Login") and optionally
Docker Redis / Mosquitto 1.6 / nginx admin page. ≥ 6 catalog finding types. Before/after: `--fixed` turns off telnet, FTP and HTTP admin.
Measured in our lab (iPhone hotspot `172.20.10.0/28`, MacBook scanner, Windows target; `tests/fixtures/lab/`): score **0 → 30 → 80** (all fake services + file sharing → `--fixed` → services and file sharing off).

**Architecture.** Python 3, one package, five layers:
`scanner (nmap, sudo only)` → `parser (defusedxml)` → `rules + score (deterministic)` → `explain (RO/EN JSON) / assistant (Claude, optional)` →
`history (SQLite) + SafeHouse web UI (FastAPI local agent, scan text inserted only as text) + CSV export`. CLI first, UI second; both call the same functions.

**Rules.** Literal implementation of the official catalog: only `state="open"`, decision by nmap service name, UPnP/SNMP only on UDP,
HTTP admin = service `http` without `tunnel="ssl"` and title containing login/admin/config/setup/router/settings,
SMB one finding per device (445 else 139), OUTDATED in addition to the service finding, UNKNOWN_DEVICE with empty port.
Score = max(0, 100 − Σ points). Validation Set: 24/24 rows, 0 extra, 8/8 scores (automated test).

**AI use (governed).** Findings, severities and scores never touch the LLM. The app holds **no API key**: it sends the question
plus a minimal scan context (device type, vendor, private IP, open ports, findings; never hostnames, MACs or raw XML) to our
stateless **AI gateway**, which holds the key and calls Claude Haiku 5.5 (optional: a local Ollama model). Gateway limits: strict
request contract, per-IP rate limit, daily cap, no logging of content. A **grounding validator** (in the gateway and again in the app)
drops any sentence naming an IP, port, CVE, link or phone number not in the scan; if nothing verified is left, the built-in text is shown instead.
Gateway down / no key / timeout → built-in answers, same UX. Conversations keep the last 6 turns in the app only.
"Exact steps for <maker>": the gateway lets Claude search **only the maker's official site** (any site, clearly flagged, for makers not on our list) for where the setting is,
sends no IP/MAC/hostname, checks the answer the same way and shows it with its sources; the built-in steps stay visible.
A technical report (.txt, nmap style) exports one check for an IT person (no AI).
The team also used Claude Code as a coding assistant during development (code, tests and reviews); every change was reviewed by the team and the validation tests had to stay green.

**Differentiators.** SafeHouse UI: a 3D house that is "inspected" by a real live scan, a network map of every device (this computer
marked), plain-language fixes; HMAC device IDs (no MAC stored); „Am reparat, verifică” one-click targeted re-check
(unprivileged `nmap -sT`, same rules);
„Paznic” unprivileged guard, a switch on Home: an unknown device on the Wi-Fi shows an alert within seconds (nmap host list + ARP table, no port scan; editable device list; it stops by itself on another network).

**Security & privacy.** One-click app (`SafeHouse.cmd`): the page is a thin client of a local agent on 127.0.0.1 (host check +
SameSite session cookie + origin check against CSRF/DNS rebinding); only nmap is elevated, via the OS permission dialog. Guardrail (allowlist = connected subnet, refuses public/CGNAT/oversized ranges, `--confirm`), rate ≤ 100 pps,
masked MACs, local-only history with one-click delete, hostile-input tests (XXE, entity bomb, XSS in titles), secrets only via env vars
(`gitleaks` clean).

**Assumptions.** Service names are taken exactly as nmap reports them (e.g. `http-proxy` is not `http`). Samba version ranges such as "3.X - 4.X"
are judged by their upper bound (not outdated) — to confirm with the mentors. A host with no MAC entry at all counts as "no MAC vendor". Only `.xml` files are analysed in batch mode (`--all-files` to override).

**Limitations / next steps.** Device-type guess is heuristic; filtered ports are not judged; maker-specific steps come from the
maker's site, not from the scan (shown with their sources). Next: a passive mDNS/SSDP listener and a signed PDF report.

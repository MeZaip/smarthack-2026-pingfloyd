# SafeHouse — Technical Summary

**Lab setup.** One phone runs hotspot `RSH-PingFloyd` (WPA2/3). Scanner laptop joins only the hotspot. Target laptop runs
`lab/fake_services.py` (banner-only telnet, FTP vsFTPd 2.3.4, SSH OpenSSH 7.2, VNC, plain-HTTP "Admin Login") and optionally
Docker Redis / Mosquitto 1.6 / nginx admin page. ≥ 6 catalog finding types. Before/after: `--fixed` turns off telnet, FTP and HTTP admin.
Measured in our lab (iPhone hotspot `172.20.10.0/28`, MacBook scanner, Windows target; `tests/fixtures/lab/`): score **0 → 30 → 80** (all fake services + file sharing → `--fixed` → services and file sharing off).

SafeHouse was designed and tested on a small, isolated Wi-Fi network owned by the
team. A phone hotspot provides the private subnet; a scanner laptop runs the
application; and a second laptop acts as the target. The target runs
[`lab/fake_services.py`](./lab/fake_services.py), which exposes banner-only
services and contains no login, shell, or real data: Telnet, FTP/vsftpd 2.3.4,
OpenSSH 7.2, VNC, and a plain-HTTP page titled “Admin Login”. Optional Docker
services add Redis, anonymous MQTT, and an nginx admin page
([`lab/docker-compose.yml`](./lab/docker-compose.yml)). The `--fixed` mode turns
off selected insecure services, providing a reproducible before/after experiment.
The checked-in lab fixtures contain at least five finding types and test that the
score improves across the repair steps.

Offline validation uses nmap XML fixtures, including home, smart-home, legacy,
non-standard-port, before/after, and malformed inputs. The golden tests compare
both missing and extra finding rows and exact network scores; malformed input
produces an `ERROR` row without stopping the batch.

<<<<<<< Updated upstream
**AI use (governed).** Findings, severities and scores never touch the LLM. The app holds **no API key**: it sends the question
plus a minimal scan context (device type, vendor, private IP, open ports, findings; never hostnames, MACs or raw XML) to our
stateless **AI gateway**, which holds the key and calls Claude Haiku 5.5 (optional: a local Ollama model). Gateway limits: strict
request contract, per-IP rate limit, daily cap, no logging of content. A **grounding validator** (in the gateway and again in the app)
drops any sentence naming an IP, port, CVE, link or phone number not in the scan; if nothing verified is left, the built-in text is shown instead.
Gateway down / no key / timeout → built-in answers, same UX. Conversations keep the last 6 turns in the app only.
"Exact steps for <maker>": the gateway lets Claude search **only the maker's official site** (any site, clearly flagged, for makers not on our list) for where the setting is,
sends no IP/MAC/hostname, checks the answer the same way and shows it with its sources; the built-in steps stay visible.
A technical report (.txt, nmap style) exports one check for an IT person (no AI).
<<<<<<< HEAD
=======
## Architecture
>>>>>>> Stashed changes
=======
The team also used Claude Code as a coding assistant during development (code, tests and reviews); every change was reviewed by the team and the validation tests had to stay green.
>>>>>>> ionut/extra-features

The implementation is a Python 3 application with a shared domain model:

```text
nmap (only privileged operation)
        ↓ XML
safe parser (defusedxml) → deterministic catalog rules and score
        ↓
SQLite history / CSV and technical report / FastAPI local agent / web UI
                                      ↓ optional
                              AI gateway → Claude or Ollama
```

The CLI and web UI call the same parser, analysis, rules, history, and reporting
functions. A live scan uses nmap service/version detection, HTTP page titles,
the top TCP ports, and a small UDP set. The guardrail permits only private,
connected, allowlisted networks, limits the range to 1,024 addresses, caps the
scan rate at 100 packets/second, and requires explicit confirmation. The Python
agent and UI run unprivileged on `127.0.0.1`; only nmap may request elevation.

The rule engine recognizes the official catalog (for example Telnet, exposed
databases, cleartext FTP/HTTP administration, SMB, MQTT, UPnP, SNMP, outdated
software, and unknown devices). Only ports whose nmap state is exactly `open`
are evaluated. The score is deterministic:
`max(0, 100 − sum(finding points))`. MAC addresses are masked before they enter
JSON, SQLite, reports, or the UI. History uses a keyed identifier to recognize a
device without storing its full MAC.

## Assumptions

Nmap service names and version evidence are treated as authoritative; therefore
`http-proxy` is not silently treated as `http`. HTTPS is identified through
Nmap’s `tunnel="ssl"` field. HTTP administration is reported only when the exact
service is `http`, TLS is absent, and the page title contains an administration
term such as “login”, “admin”, or “settings”. SMB creates one finding per
device,
preferring port 445. UDP-only findings require UDP. A version range such as
`3.X - 4.X` is judged by its upper major version. Device type is a heuristic
based on the available Nmap metadata, not an inventory guarantee.

## LLM use and safeguards

LLMs are optional enrichment, never the source of findings, severities, scores,
or built-in remediation text. The application sends a minimal context
(question, device type/vendor, private IP, open ports, and finding data) to a
stateless gateway; it does not send raw XML, full MAC addresses, or hostnames.
The API key exists only on the gateway. The default backend is Claude Haiku 5.5;
an Ollama backend is available for local execution. The gateway applies a
per-IP rate limit, daily request budget, bounded concurrency, request-size
limits, and timeouts, and does not log request bodies or client IPs.

Responses are checked both at the gateway and in the application. The grounding
validator rejects unobserved IPs, ports, CVEs, external links, and phone-like
numbers. If the gateway is unavailable, exceeds a limit, times out, or returns
ungrounded text, SafeHouse uses deterministic Romanian/English fallback text.
Maker-specific repair guidance may use Claude’s web search, restricted to the
maker’s official domains, and is displayed with sources.

## Limitations

The tool evaluates observed open ports, not filtered ports, vulnerabilities
behind authentication, or the complete device inventory. Service fingerprinting,
device classification, vendor identification, and page-title matching are
heuristics and can miss non-standard implementations. The live scan is limited
to the connected private subnet and requires nmap/Npcap plus suitable local
permissions. AI guidance depends on gateway/model availability and is advisory;
the deterministic report remains the authoritative result. Future work includes
passive mDNS/SSDP discovery, broader protocol-specific checks, and signed PDF
reports.

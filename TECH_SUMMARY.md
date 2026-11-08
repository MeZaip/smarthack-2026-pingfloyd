# SafeHouse: Technical Summary

## Lab setup

- **Network.** An iPhone runs the hotspot `RSH-PingFloyd` (WPA2/3, private subnet `172.20.10.0/28`). The scanner laptop joins only this hotspot. A Windows laptop is the target.
- **Target services.** The target runs `lab/fake_services.py`. It exposes banner-only services with no login, shell or real data behind them:
  - Telnet
  - FTP (vsFTPd 2.3.4)
  - OpenSSH 7.2
  - VNC
  - a plain-HTTP "Admin Login" page
- **Optional Docker services.** `lab/docker-compose.yml` adds Redis, anonymous MQTT and an nginx admin page.
- **Before/after experiment.** Windows file sharing stays on until the last step.

| Step | Target state | Score |
|---|---|---|
| Before | all fake services, file sharing on | 0 |
| Between | `--fixed`: Telnet, FTP and the admin page turned off | 30 |
| Final | services and file sharing off | 80 |

The three scans are in `tests/fixtures/lab/`. The official Validation Set is in `tests/fixtures/validation/`. A golden test checks both sets on every run: no missing rows, no extra rows, exact scores.

## Architecture

```
nmap (the only privileged step) --XML--> safe parser (defusedxml, size limits)
  --> deterministic rules + score --> SQLite history | CSV export | reports | local agent (FastAPI) --> web UI
                                                                                  \--optional--> AI gateway --> Claude / Ollama
```

**Single code path.** The CLI and the web UI share one Python package: parser, rules, score, history and reports. `netcheck analyze` and the UI's "Export CSV" produce identical `findings.csv` and `scores.csv`. An unreadable file gets `ERROR` and the batch continues.

**Live scan.** The live scan runs `nmap -sS -sU -sV --version-light --script http-title --max-rate 100`. It covers nmap's top 1000 TCP ports and UDP 53, 123, 161, 1900 and 5353.

**Guardrail.** Only the private subnet the computer is connected to is allowed. Public, carrier-NAT, loopback, multicast and link-local addresses, ranges larger than /22 and any scan without explicit confirmation are refused.

**Least privilege.** Only nmap is elevated, through the operating system's permission dialog (UAC, osascript or pkexec). The analyser, UI, assistant and guard run unprivileged.

**Local agent.** The agent listens on 127.0.0.1 only and checks the Host header against DNS rebinding. Requests that change state need a per-run SameSite cookie and a same-origin `Origin` header, so other websites cannot start a scan or delete data.

**Score.** `max(0, 100 - sum of finding points)`, from the official catalog. Only ports whose state is exactly `open` count.

**Privacy.**
- MACs are masked everywhere. Devices are recognised by a keyed HMAC of the MAC, never the MAC itself.
- History stays in `~/.netcheck/`, and "Delete all data" removes it.
- Scan text (banners, titles) is untrusted: it is inserted into the UI only as text.

**Beyond the brief.** A 3D house that reacts to a real scan; a network map; "I fixed it, check" (one-port re-check, no admin rights); a house guard that alerts within seconds when an unknown device joins the Wi-Fi; an nmap-style technical report with CIS Controls and OWASP IoT references; voice mode (browser speech recognition, answers spoken by Piper on the user's computer, browser voice as fallback).

## Assumptions

- **Service names.** Nmap service names are taken as reported, so `http-proxy` is not treated as `http`.
- **HTTPS.** HTTPS is recognised by `tunnel="ssl"`.
- **HTTP admin pages.** Reported only for service `http`, without TLS, with a page title containing an admin word (login, admin, settings).
- **SMB.** One SMB finding per device, preferring port 445.
- **Version ranges.** A range such as `3.X - 4.X` is judged by its upper major version.
- **Device type.** The device type is a heuristic based on nmap data and the MAC vendor.

## LLM use

**What the LLM never does.** It never produces findings, severities, scores or the built-in fix texts. Those come from fixed rules, identical on every run.

**What the assistant receives.** The assistant (chat and voice) only explains the results. The app holds no API key. It sends the question plus device type, vendor, private IP, open ports and findings to the team's stateless gateway; never hostnames, MACs, raw XML or history.

**Gateway.** The gateway holds the key and calls Claude Haiku 5.5, or Ollama locally. It enforces a strict request contract, a per-IP rate limit, a daily cap and timeouts, and does not log request content or client IPs.

**Grounding.** A grounding check runs in the gateway and again in the app. It removes any sentence that names an IP, port, CVE, link or phone number not present in the scan. If nothing verified is left, or the gateway is unreachable, SafeHouse shows its built-in Romanian/English texts and keeps working.

**Maker-specific steps.** "Exact steps for <maker>" lets Claude search only the maker's official site. Unknown makers are clearly flagged. The request sends only the maker, model, device type and problem code. The answer is shown with its sources.

**Development.** The team used Claude Code as a coding assistant (code, tests, reviews). Every change was reviewed by the team, and the validation tests had to stay green.

## Limitations and next steps

- **What is judged.** Only observed open ports are judged. Filtered ports, flaws behind a login and devices that do not answer are not covered.
- **Heuristics.** Fingerprinting, device type and vendor detection are heuristics.
- **Scope of the live scan.** The live scan needs nmap (and Npcap on Windows) and covers only the connected private subnet.
- **Assistant availability.** AI answers depend on the gateway being reachable. The rule-based report remains the authoritative result.
- **Next steps.** Device names through mDNS/SSDP, more protocol-specific checks, signed PDF reports.

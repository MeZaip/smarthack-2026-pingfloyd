# NetCheck — Secure Networks, Simply Explained

R Systems Hackathon 2026. A tool that scans a small network **you own**, explains every risk in plain
Romanian and English, tells you what to fix first, and proves the fix with before/after history.

## One-command setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
Live scans also need nmap (`brew install nmap` on macOS, `sudo apt install nmap` on Linux).
**Free local AI (recommended, do it at home — ~2–5 GB):** `brew install ollama`, `ollama serve`, `ollama pull qwen2.5:7b`
(weaker laptop: `ollama pull qwen2.5:3b` and `export NETCHECK_OLLAMA_MODEL=qwen2.5:3b`). Check with `python -m netcheck ai-status`.
No account, no key, and scan data never leaves the laptop. Without Ollama everything still works with built-in texts.
Claude is optional: `NETCHECK_LLM=anthropic` + `ANTHROPIC_API_KEY` in `.env` (**never commit `.env`**).

## Use it

| What | Command |
|---|---|
| Analyse a folder of nmap XML files → `findings.csv` + `scores.csv` (offline, no root) | `.venv/bin/python -m netcheck analyze <folder> --out results --history` |
| Show my network (interface, subnet, gateway) | `.venv/bin/python -m netcheck detect` |
| Live scan of my hotspot (guardrail + `--confirm` required) | `.venv/bin/python -m netcheck scan --confirm` |
| Talk to the assistant | `.venv/bin/python -m netcheck chat --scan scans/scan_01.xml` |
| Guided step-by-step check-up | `.venv/bin/python -m netcheck chat --guide` |
| Web UI (http://127.0.0.1:8000) | `.venv/bin/python -m netcheck serve` |
| List / delete local history | `.venv/bin/python -m netcheck history [--delete]` |
| „Dovedește!” — re-check one fixed problem (TCP: no root) | `.venv/bin/python -m netcheck verify <ip> <port> --confirm` |
| Signed before/after certificate / detect a forged one | `.venv/bin/python -m netcheck cert --before 3 --after 4` · `cert-verify certificate.json` |
| „Paznic” — notify me about new devices / open ports (no root) | `.venv/bin/python -m netcheck watch --confirm --interval 30` |
| Data contract JSON (`service_data_contracts.md`): §1 raw / §2 evaluated / §4 delta | `.venv/bin/python -m netcheck parse <file.xml>` · `analyze <folder> --contracts` · `diff a.xml b.xml --json` |
| Which AI is active | `.venv/bin/python -m netcheck ai-status` |
| Tests (Validation Set answer key, guardrail, hostile XML, XSS) | `.venv/bin/python -m pytest -q` |

Add `--lang en` before the sub-command for English output in the terminal, e.g. `python -m netcheck --lang en chat`.

### Test Set day (hour 20)
```bash
.venv/bin/python -m netcheck analyze /path/to/TestSet --out results/testset --history --source testset
```
Upload `results/testset/findings.csv` and `results/testset/scores.csv`, screenshot the **All files** page.
**Do not change code after uploading.** Then `git tag final`.

## What makes NetCheck different
> *Your home has doors. NetCheck shows them on a map, helps you close them, **proves** they are closed, and keeps watch afterwards.*

1. **Home map** — every device is a room, every open port a door (red = dangerous, icon + text, not colour only).
   The worst room says „👉 Începe aici”. Give rooms personal names („Camera bebelușului”); every explanation and the
   assistant use them. Devices are recognised across scans by an HMAC of the MAC with a local secret — the MAC itself is never stored.
2. **„Dovedește!”** — after a fix, one click re-checks just that IP:port in seconds (unprivileged TCP connect scan, same
   guardrail, same rules) and turns the door green. **Signed certificate**: before/after scores, resolved findings, SHA-256 of both
   scan files, Ed25519 signature. Change one digit and verification fails — something you can hand to an insurer or IT supplier.
3. **Paznic (guard)** — runs quietly without root, reads the ARP table after a rate-limited sweep, and sends a desktop
   notification when a new device joins or a new door opens (and says if it is dangerous). Pauses itself on a different network.
4. **Governed, free, local AI** — Ollama model on the laptop; every AI answer is checked against the scan: any IP, port,
   finding code, CVE, link or phone number not in the evidence → the answer is rejected and the verified text is shown.

## How the hotspot lab works (and where the data goes)

```
 [Phone A: hotspot RSH-<team>]  ← only the Wi-Fi "router". It does not collect or send anything to us.
        │ Wi-Fi
        ├── [Laptop 1: SCANNER]  runs NetCheck + nmap. nmap sends small probe packets over the Wi-Fi to
        │                        each device and writes the answers to scans/scan_*.xml ON THIS LAPTOP.
        ├── [Laptop 2: TARGET]   python lab/fake_services.py   (+ optional docker compose -f lab/docker-compose.yml up -d)
        └── [old phone / Pi]     optional extra target (e.g. an FTP server app)
```
Nothing has to be copied from the phone: the scanner laptop talks to the devices directly through the hotspot.
Check first that laptops see each other: `ping <other laptop IP>` (some phones isolate clients — try another
phone, or use the single-laptop Docker fallback, Setup D, and say so in the pitch).

Before/after demo: scan with `fake_services.py` → stop it, run `fake_services.py --fixed` → scan again.
The UI's History page shows the resolved findings and the score going up.

## Safety (rules of engagement)
* Guardrail: refuses public IPs, carrier-NAT (100.64/10), loopback/multicast, anything outside the allowlist
  (default = connected subnet; extra private ranges via `--allow` or `NETCHECK_ALLOWLIST`), anything bigger than /22,
  and any live scan without `--confirm`. Rate is capped at 100 packets/s.
* Only `nmap` runs with sudo; analyser, UI and assistant run unprivileged.
* MAC addresses are masked everywhere (`AA:BB:CC:XX:XX:XX`); history lives only in `~/.netcheck/history.db`;
  "Delete my history" button in the UI / `netcheck history --delete`.
* Scan files are treated as hostile: defusedxml (no XXE / entity bombs), 50 MB limit, all text escaped in the UI.
* No secrets in the repo: run `gitleaks detect --source .` (install: `brew install gitleaks`).

## Repository map
```
netcheck/parser.py     safe nmap XML parser        netcheck/rules.py     official catalog, literal rules
netcheck/analyzer.py   score, device type, CSV     netcheck/guardrail.py scope enforcement
netcheck/netdetect.py  interface/subnet/gateway    netcheck/scanner.py   nmap live scan
netcheck/explain/      RO/EN texts + fixes         netcheck/history.py   SQLite history, diff, alerts
netcheck/assistant.py  AI assistant + offline      netcheck/chat.py      terminal chat + guide mode
netcheck/web/          FastAPI UI                  lab/                  fake banner targets, docker targets
tests/fixtures/        validation answer key + synthetic validation files
```
Put the **official** Validation Set files into `tests/fixtures/validation/` at kickoff; the tests use it
automatically instead of the synthetic copies. Our own lab scans go into `tests/fixtures/lab/`.

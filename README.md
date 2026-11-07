# smarthack-2026-pingfloyd — netcheck

**Secure Networks, Simply Explained** — R Systems Hackathon 2026.
Scans a small network *you own*, explains the risks in plain Romanian/English and tells you exactly how to fix them.

## Setup

Python 3.10+. The core needs only the standard library.

```bash
pip install -r requirements.txt      # defusedxml (safer XML) + pytest
cp .env.example .env                 # optional: only if you change defaults (users need nothing)
```

## For users: one double-click (Windows)

1. Install [Nmap](https://nmap.org/download) (includes Npcap) and Python 3.10+ once.
2. Double-click **`NetCheck.cmd`**. The first start prepares everything (about a minute); then NetCheck opens
   in its own window, no terminal.
3. Press **„Verifică rețeaua mea”**, confirm the network is yours, press **Da** in the Windows permission
   dialog. The results appear in 1–3 minutes. **„Am reparat — verifică”** re-checks one fixed problem in seconds.
4. **„Închide”** stops NetCheck (it also stops by itself when the window is closed).

On Linux/macOS: `python -m netcheck app` (same app; the system password dialog replaces the Windows one).

**Team / development on Windows:** `.\run.ps1` (or `run.cmd` from cmd.exe) is the Windows version of `./run.sh`:
same options (`-Demo`, `-NoAI`, `-Port 9000`, `-App`), its own `.venv-windows`, gateway if a key is in `.env`,
UI on http://127.0.0.1:8000. Do not scan from WSL: WSL2 sits behind a NAT and cannot see the hotspot's
devices directly (no ARP/MACs, no SYN scan), even on a private network; run natively on Windows.

### How the pieces talk to each other

```
UI (page in an app window) ──/api/v1 JSON──▶ local agent (127.0.0.1, unprivileged) ──HTTPS──▶ our AI gateway
   only shows things and                       scans (only nmap is elevated, via the       stateless, holds the
   sends requests                              OS permission dialog), guardrail, analysis, API key, stores nothing
                                               local SQLite history (NFR-02: stays here)
```

* The page never chooses what to scan: the agent always checks the network it is connected to, after
  explicit consent, through `net/guardrail.py`.
* The agent only answers requests addressed to 127.0.0.1 (anti DNS-rebinding), and every state-changing
  request needs a per-run `SameSite=Strict` session cookie plus a same-origin `Origin` (anti CSRF): other
  websites open in the browser cannot start a scan or delete the history (`netcheck/web/security.py`).
* `/api/v1` is documented in `netcheck/web/api_v1.py` and `service_data_contracts.md` §5.

## Run the app (web UI)

```bash
./run.sh            # venv + requirements, AI gateway (if a key is set), UI on http://127.0.0.1:8000
./run.sh --demo     # same, with a separate demo history pre-loaded from the synthetic test scans
./run.sh --no-ai    # UI only; the assistant answers from the built-in texts
```

Or by hand: `python -m netcheck serve` (UI + JSON API) and, on the team machine, `python -m gateway`.
Upload nmap `.xml` files in the UI, or fill the history from the CLI (`netcheck history add`, `netcheck scan`).
The UI runs unprivileged and listens on 127.0.0.1 only.

JSON API (read-only, formats from `service_data_contracts.md`): `GET /api/scans`, `/api/scans/latest` (§2),
`/api/scans/{id}` (§2), `/api/scans/{id}/delta[?previous=<id>]` (§4).

## Analyse scan files (offline, no admin rights)

```bash
python -m netcheck analyze <folder-with-xml> --out results     # -> results/findings.csv, results/scores.csv
python -m netcheck report  scan.xml --lang ro                  # plain-language report
python -m netcheck ask     scan.xml "Ce să repar primul?"      # AI assistant (falls back to built-in text)
python -m netcheck chat    scan.xml                            # conversation with the assistant
python -m netcheck diff    before.xml after.xml                # what changed / what got fixed
```

Unreadable files get `ERROR` in `scores.csv`; the run continues with the other files.

## Scan history (score trend, before/after)

```bash
python -m netcheck history add scan_monday.xml scan_friday.xml   # save scans (alerts on new devices / new open ports)
python -m netcheck history list                                  # score trend
python -m netcheck history changes                               # before/after between the last two saved scans
python -m netcheck history delete                                # "Delete my history": removes the database file
```

Stored in SQLite at `~/.netcheck/history.sqlite` (override with `--db` or `NETCHECK_DB`), outside the repo,
owner-only permissions. Tables: `scans`, `devices`, `ports`, `findings` (children use `ON DELETE CASCADE`).
**The full MAC is never written to disk**: only the masked MAC (`XX:XX:XX:XX:1A:2B`, last two bytes only, for display)
and a keyed hash of the full MAC, used to recognise the same device across scans even when its IP changes
or two devices share a vendor. The hash key is random per history file and is deleted with it.

## Demo UI (HTML/CSS, no build step)

```bash
python tools/export_ui_data.py          # real tool output -> ui/data.js (scans, findings, texts, history)
python -m http.server 8000 -d ui        # then open http://localhost:8000  (or just open ui/index.html)
```

* **Look**: dark "security console" theme in black and red, no icons (devices are text tags like `[CAM]`,
  `[RTR]`; risk is always written in words). A slim text menu on the left (`01 HOME` … `05 ASK`) with live
  counters (score, devices, things to fix), a sliding red marker, keys `1`–`5` and ↑/↓; on phones it becomes
  a horizontal tab strip. A network card with a HUD score ring and a labelled traffic light, a "suggestion
  for today" card, device tiles that open a side/bottom sheet, fixes grouped by risk, an events timeline for
  history, and a terminal-style assistant chat. Only system fonts, so it works offline.
* **Home**: traffic-light score with the standard formula, and *“Do one thing today”*: the most dangerous
  device and its first fix, step by step (the jury's hands-on question), then every problem by risk.
* **Devices**, **Problems and fixes** (explanation, 1–5 steps, evidence, CIS/OWASP refs), **History**
  (score chart + before/after, *Delete my history*), **Ask** (grounded answers: every sentence cites
  its evidence; the demo switch slips in an invented claim and the checker blocks it).
* Written for **children and older people first**: plain words in RO/EN (`netcheck/explain/simple_texts.py`:
  title without jargon, ≤ 2 short sentences using the "your home has doors" picture, ≤ 3 steps, and who can do
  it: *you* / *ask someone who knows computers* / *ask the IT company*), a glossary, and text size buttons
  (A / A+ / A++). Devices and problems are simple cards: name/type, a 2-sentence explanation, numbered steps.
* Every score and risk shows icon + words, never colour alone: ❌ *Risc înalt / High risk*, ⚠️ *Risc mediu /
  Medium risk*, ✅ *Sigur / Safe*, on a traffic light. IP, ports, MAC, evidence and CIS/OWASP are one
  click away under *Details for people who know computers*.
* Checked in every view and both themes: no text under 16 px, every text/background pair ≥ 4.5:1 (WCAG AA),
  every button and card reachable by keyboard with a visible focus ring (NFR-08). RO/EN toggle (NFR-09).
  Scan text is inserted only as text, never as HTML (NFR-03).
* Deep links for the pitch: `#ask?q=first&hall=1`, `#home?lang=en&scan=V3_small_office.xml`, `#history?theme=light`.

## How it works

| Layer | What | LLM? |
|---|---|---|
| `netcheck/core/parser.py` | Safe nmap XML parsing: no DTD/entities, size limit, untrusted text clipped | no |
| `netcheck/core/rules.py` | Official finding catalog + detection rules, standard score | **no**: deterministic |
| `netcheck/core/diff.py` | Before/after comparison, new device / new port alerts | no |
| `netcheck/core/contract.py` | §2 Evaluated Scan Data + §4 History & Deltas JSON (data contract) | no |
| `netcheck/history.py` | Local SQLite history: trend, before/after, delete-my-history | no |
| `netcheck/web/` | FastAPI web UI (dashboard, house map, findings, history, report, Q&A) + read-only JSON API | no (the Q&A uses `netcheck/ai/`) |
| `netcheck/explain/texts.py` | Human-reviewed RO/EN explanations (max 2 sentences) + 1–5 fix steps, CIS/OWASP refs | no |
| `netcheck/ai/` | Q&A assistant client: sends a minimal, privacy-preserving context to our gateway; every answer is checked by a grounding guard (no IPs, ports, CVEs, links or phone numbers not in the scan) | yes, optional |
| `gateway/` | Team-hosted AI gateway: holds the API key, calls Claude Haiku 5.5 (or optional local Ollama); users configure nothing | yes |

Findings, severities and scores never come from the LLM. If the API is unavailable, slow, or an answer
fails the grounding check, the assistant returns a deterministic built-in answer.

### Rule assumptions (to confirm with mentors)
* Only ports with state exactly `open` count (`open|filtered` does not).
* `HTTP_ADMIN_CLEARTEXT` requires service name `http` without `tunnel="ssl"`.
* Samba ranges like `3.X - 4.X` are judged by the upper bound (not flagged).

## AI assistant: app → our gateway → Claude

```
netcheck app (user, no key) --HTTPS--> gateway (team machine, has the key) --HTTPS--> Claude API (Haiku 5.5)
     ^ falls back to built-in text if the gateway is down, over its limits, or the answer is not grounded
```

* **Users configure nothing and hold no key.** The app calls `NETCHECK_AI_URL` (default `http://127.0.0.1:8787`).
  For a distributed app, point the default at the gateway's public `https://` address.
* **The API key lives only on the gateway machine**, in `.env` (git-ignored). Tests check that the app code
  never reads a key and that the gateway never prints it.
* **Privacy:** only device type, vendor, private IP, open ports and findings are sent. Hostnames,
  MAC addresses, raw XML and history never leave the user's machine. The gateway whitelists fields
  and does not log request content or client IPs.
* **Cost / abuse protection:** per-IP rate limit, daily cap on model calls (`NETCHECK_GATEWAY_DAILY_LIMIT`),
  body limit, max 1024 output tokens (thinking off by default), strict request contract, `/health` never calls the model.
  A question costs roughly a tenth of a cent with Haiku 5.5; also set a spend limit in the Claude Console.
* **Grounding:** the gateway checks every answer (one retry), the app checks it again.
* **Conversations:** the gateway is stateless; the app keeps the last 6 question/answer pairs and sends
  them with each question (`Conversation` in `netcheck/ai/assistant.py`, `python -m netcheck chat`).
* **Errors:** model errors (bad key, no credits, unknown model) are printed in the gateway console and
  shown by the app with the reason; the key is never included.
* Optional: `NETCHECK_GATEWAY_BACKEND=ollama` runs a local model instead (no key needed).

### Run the gateway (team machine)

```powershell
copy .env.example .env        # put your key in ANTHROPIC_API_KEY=
powershell -ExecutionPolicy Bypass -File gateway\run.ps1      # or: python -m gateway
python -m netcheck ask tests\fixtures\synthetic\V2_smart_home.xml "Ce repar primul?"
python tools/eval_assistant.py                               # 10 fixed questions -> eval_results.md
```

To make it reachable for users on other machines, expose it through an HTTPS tunnel
(e.g. Cloudflare Tunnel) and set `NETCHECK_GATEWAY_TOKEN` + `NETCHECK_GATEWAY_TRUST_PROXY=1`.

## Tests

```bash
python tools/make_synthetic_fixtures.py   # synthetic look-alikes of the Validation Set
python -m pytest -q
```

Put the real Validation Set (with `expected_findings.csv` / `expected_scores.csv`) in
`tests/fixtures/validation/`; the golden test picks it up automatically.


## Live scan of your own network (Core Engine & CLI — `netcheck/net/`)

Needs nmap (`brew install nmap`) and the laptop connected **only** to the team hotspot.

```bash
python -m netcheck detect                         # interface, subnet, gateway (FR-01); --json = contract "network"
python -m netcheck scan --confirm                 # scan the connected subnet (FR-02/04); sudo only for nmap
python -m netcheck scan 8.8.8.8 --confirm         # ⛔ REFUZAT / REFUSED — guardrail demo (live check 4)
python -m netcheck parse scans/scan_x.xml         # §1 Raw Parsed Data JSON (service_data_contracts.md)
python -m netcheck verify scans/scan_x.xml 172.20.10.5 8080 --confirm   # „Dovedește!”: re-check one fix, no root
python -m netcheck watch --confirm --interval 30  # „Paznic”: desktop alert for a new device / newly opened port
```

Guardrail: refuses public IPs, carrier-NAT (100.64/10), loopback/multicast/link-local, ranges bigger than /22,
anything outside the allowlist (default = the connected subnet; extra *private* ranges via `--allow` or
`NETCHECK_ALLOWLIST`) and any live scan without `--confirm`. Rate ≤ 100 packets/s. Messages in RO (default) and EN (`--lang en`).
`scan` saves the XML + `<scan>.raw.json` in `scans/` (git-ignored: real network data) and adds the result to the history.
Lab targets (banner-only fake services, no real login behind them): `python lab/fake_services.py` (`--fixed` = the "after" state).

## Secrets check

```bash
gitleaks detect --source . -v
```

## Status

- [x] FR-05/06/09/15: analyser, catalog rules, standard score, CSV export
- [x] FR-07/08: RO/EN explanations and fixes
- [x] FR-10/13 (core): diff + alerts
- [x] FR-12: grounded AI assistant with fallback
- [x] FR-01/02/04: network detection, scope guardrail, live scan (`netcheck/net/`)
- [x] FR-11: web UI + history storage + "delete my history" (`netcheck serve`, `./run.sh`)

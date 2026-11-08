# smarthack-2026-pingfloyd — SafeHouse

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
2. Double-click **`SafeHouse.cmd`**. The first start prepares everything (about a minute); then SafeHouse opens
   in its own window, no terminal.
3. Press **„Verifică rețeaua mea”**, confirm the network is yours, press **Da** in the Windows permission
   dialog. The results appear in 1–3 minutes. **„Am reparat — verifică”** re-checks one fixed problem in seconds.
4. **„Închide”** stops SafeHouse (it also stops by itself when the window is closed).

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

The page at `/` is the **SafeHouse** UI (`ui/`) with live data: the scans saved on this computer, "Inspect house"
runs a real check of the network you are on (consent, then the system permission dialog, only nmap is elevated),
"Upload a check" analyses any nmap XML (a broken file shows a clear error and is not saved), "I fixed it, check"
re-tests one problem, "Ask" talks to the assistant (AI through the gateway, built-in texts as fallback) and
"Delete history" removes `~/.netcheck/history.sqlite`. The same page also works offline as a demo (below), with
fixed example data.

JSON API (read-only, formats from `service_data_contracts.md`): `GET /api/scans`, `/api/scans/latest` (§2),
`/api/scans/{id}` (§2), `/api/scans/{id}/delta[?previous=<id>]` (§4).

## Analyse scan files (offline, no admin rights)

```bash
python -m netcheck analyze <folder-with-xml> --out results     # -> results/findings.csv, results/scores.csv
python -m netcheck report  scan.xml --lang ro                  # plain-language report
python -m netcheck report  scan.xml --technical --out r.txt   # detailed technical report for IT (nmap style)
python -m netcheck ask     scan.xml "Ce să repar primul?"      # AI assistant (falls back to built-in text)
python -m netcheck chat    scan.xml                            # conversation with the assistant
python -m netcheck diff    before.xml after.xml                # what changed / what got fixed
```

Unreadable files get `ERROR` in `scores.csv`; the run continues with the other files.

The same export is in the app: **Export CSV** (Results tab) → choose a folder (or files) of nmap XML scans, or export
the checks saved on this computer. It runs the same code as `netcheck analyze` (identical `findings.csv` and
`scores.csv`, tested), downloads them as one ZIP and also saves them in `~/SafeHouse/exports/export_<date>/`.
Exporting never adds the files to the history. Files uploaded with "Upload a check" that cannot be read are kept by
name only (no content): they show as ERROR in the list and in Results, and "export the saved checks" writes them as ERROR. For the Test Set submission the CLI command above is the reference.

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

## Demo UI (HTML/CSS, no build step) - the same page as the app, with fixed example data

```bash
python tools/export_ui_data.py          # real tool output -> ui/data.js (scans, findings, texts, history)
python -m http.server 8000 -d ui        # then open http://localhost:8000  (or just open ui/index.html)
```

* **Safehouse3D** (Home, `ui/safehouse3d.js`): a real-time 3D scene with Three.js r159, bundled in `ui/vendor/`
  (MIT licence included; no CDN, works offline and from `file://`). A modern two-volume house (plaster + wood,
  big glass windows, flat roofs, hinged door) in a minimalist garden (lawn, stone path, hedge, stylised trees,
  bushes, grass tufts); textures are drawn in code. *Inspect house* sweeps a glowing laser grid from the roof
  to the ground in a loop (~4 s, three passes). **Safe**: the laser stops and the windows glow emerald (emissive
  glass + point lights inside). **Vulnerable**: the door swings open on an orange glow. A floating glass panel
  over the scene shows an icon and the result in both languages. Drag to turn the house. `buildHouse()` is the
  place to load a `.gltf` model later. Without WebGL the CSS house below is used.
* **Look** (Apple / Vercel style, dark by default; `#…?theme=light` for light): large whitespace, translucent
  hairline cards (radius 16px) that lift on hover, semantic colours (safe `#10B981`, warning `#F59E0B`, danger
  `#EF4444`) always paired with an SVG icon and words. Home = blended 3D house (edges fade into the page, glow
  tinted by the state, glass badge) next to one centred score card (glowing ring, status pills, gradient CTA),
  then **Uși lăsate deschise / Doors left open** (grid of fix cards, most dangerous marked *Start here*) and
  **Aparate găsite / Devices found** (grid of device cards: icon, name, IP, masked MAC).
* **Brand**: the official logo icon (`ui/assets/logo-icon.png`, cut from `ui/assets/logo-source.png` with
  `tools/extract_logo.py`; only the black background around it is made transparent, the dark inside of the
  shield and the glow are kept) is embedded as a data URI next to the HTML wordmark **Safe**House (Safe 800
  white, house 400 `#9ca3af`). It sits in the sidebar on computers and in the header on phones.
* **Icons**: every emoji was replaced by one SVG icon set (Lucide/Feather style, 2px strokes, `currentColor`),
  defined once as `<symbol>`s in `ui/index.html`; `tests/test_ui_assets.py` keeps emoji out of the UI.
* **SafeHouse** (fallback without WebGL): a CSS 3D house and an *Inspectează casa / Inspect house* button. Inspecting runs a scan
  bar down the house while the windows light up one by one, then shows one of two states, always icon + words:
  **safe** (green outline, door closes, ✅ *Casa este sigură / The house is safe*) or **vulnerable** (door opens
  on an orange doorway, pulsing ⚠️ *Atenție: O ușă este deschisă / Warning: A door is open*). The state comes from
  the real findings; other code can set it with `SafeHouse.setState("safe" | "vulnerable")` or run
  `SafeHouse.inspect()`. Below the house, device cards show icon, name, IP and a 2-sentence explanation in
  both languages. With *reduce motion* turned on, the result appears without animation.
* Layout and behaviour follow **Google Home** and **Fing**: navigation rail on computers and a bottom bar on
  phones, a greeting, a network card with a score ring and a labelled traffic light, a "suggestion for today"
  card, device tiles that open a side/bottom sheet, fixes grouped by risk like a security check, and an
  events timeline for history. The assistant is a chat with suggestion chips.
* **Home**: traffic-light score with the standard formula, and *“Do one thing today”*: the most dangerous
  device and its first fix, step by step (the jury's hands-on question), then every problem by risk.
* **Results**: every saved check in one table (number, date, file, standard score, safety rating, devices,
  problems - `scores.csv` on screen); tap a row to see what it found (device, IP, port, problem, severity, code -
  `findings.csv` on screen). Unreadable uploads show `ERROR`. "Export CSV" is right there.
* **Devices and fixes** (one place per device: every problem with its explanation, 1–5 steps, "I fixed it, check", evidence, CIS/OWASP refs), **History**
  (score chart + before/after, *Delete my history*), and the assistant as a **floating chat button**
  (bottom right; in the app: a conversation with the AI assistant, short and simple answers checked against the scan,
  in the language of the question; in the offline demo: answers from our own texts).
  On phones the menu becomes a bottom bar and the top bar keeps only icons.
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
* Deep links for the pitch: `#ask?q=first&hall=1`, `#home?lang=en&scan=V3_small_office.xml`, `#history?theme=light`, `#home?inspect=1`, `#home?state=vulnerable`.

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
* **Steps for your device's maker** (`POST /v1/guide`): "Exact steps for TP-Link" in a device's sheet, or a chat
  question like "How do I turn off UPnP on my TP-Link?", lets Claude search **only the maker's official site** (list in
  `netcheck/ai/guide.py`). Only the maker, the model the device announces (page title / product), the device type and
  the problem code are sent: no IP, MAC or hostname. The answer is checked like the chat (no IPs, ports, CVEs, phone
  numbers or links), keeps only sources on the maker's site and is shown with them. Needs web search enabled for the
  organisation in the Claude Console; without it (or with Ollama) the general built-in steps stay.
  Settings: `NETCHECK_GATEWAY_GUIDE_SEARCHES` (default 3), `NETCHECK_GATEWAY_GUIDE_TIMEOUT` (default 60 s).

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

In the app the same guard is a switch on Home, **„Paznicul casei” / House guard**: after the user confirms it is their
network, it looks every 20 s (`NETCHECK_GUARD_INTERVAL`) at who is connected (the hosts `nmap -sn` sees plus the ARP table,
no admin rights; ping sweep as fallback), tells about a new device at once ("It's mine" / "I don't know it", maker from
nmap's MAC list, private MACs shown as such) and, after an unprivileged top-100 connect check, about risky open doors.
Same guardrail as a check: only the connected network, it stops by itself on any other one; no admin rights; it waits while a full
check runs. What it remembers (HMAC of the MAC, masked MAC, open ports, the user's answer) lives in `~/.netcheck` and is
removed by "Delete all data".

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

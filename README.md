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
* Menu: **Home**, **Fixes**, **History**; the assistant is the **?** button next to the language.
  * **Home**: 3D house + score card, then the threat path and the network map of every device (FR-03: IP, masked
    MAC, maker), with *Show as a list* as the accessible version of the map (opens by itself past 14 devices).
    Old links `#devices?open=<IP>` open Home with that device's sheet.
  * **Fixes** (main work page): *One at a time* by default (the most dangerous thing first, with its device, steps
    and *Done, I fixed it*; a progress bar; the rest folded under *N more things*; *Fixed* list with undo; marks are
    kept only in this browser and the score changes only after a new check) and *See all* for experts (every
    problem by risk, evidence, CIS/OWASP refs). `#findings?view=all` opens the full list.
  * **Report for the IT company (FR-14)** on the Fixes page: *Save as PDF or print* and *Download the report
    (HTML)*: one self-contained A4 page (score, the first fix, every problem with place, evidence, refs, steps and
    status, the device table), built from DOM text nodes so scan text is escaped; it scales down to fit one page
    (never below 80 %). `SafeHouse.reportHtml()` returns the same page as a string.
  * **History**: score chart + before/after, *Delete my history*.
  * **? Ask** (chat panel, Esc closes, Enter sends, Shift+Enter new line, big suggested questions, "no passwords
    here" note): the answer comes from `window.SafeHouseAssistant.handler(question, {lang, scanFile, history})`
    if a page sets it, else `POST /api/v1/ask` (`service_data_contracts.md`) when served over http; with neither,
    or on error / 25 s timeout, the built-in grounded answers are used (every sentence cites its evidence; the
    demo switch slips in an invented claim and the checker blocks it). `#ask?q=first&hall=1` opens it.
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

# NetCheck — instructions for Claude Code (and humans)

R Systems Hackathon 2026, "Secure Networks, Simply Explained". Read `PLAN_ECHIPA.md` for who owns what.

## Golden rules
- **Never change findings/scores logic without a test.** `tests/test_validation.py` (golden answer key, no missing/extra rows,
  exact scores; uses `tests/fixtures/validation/` once the real set is there, else `fixtures/synthetic/`) must stay green.
  Test Set accuracy is 30% of the grade.
- Findings, severities and scores are deterministic code (`core/rules.py`, `core/analysis.py`). **No LLM there, ever.**
- Payloads between modules follow `service_data_contracts.md`: §1 in `net/contract.py`, §2/§4 in `core/contract.py`
  (checked by `tests/test_net.py` and `tests/test_web.py` against the JSON examples in that file).
- `netcheck/core/models.py` is the shared in-process contract (Host, Port, ScanResult, Finding). Changing a field = tell
  the team first; new fields need a default.
- Only `nmap` in `net/scanner.py` (and `verify --udp`) may run with sudo. Analyser, UI, assistant, gateway, watch run unprivileged.
- Every live scan target goes through `net/guardrail.py`. Never bypass it.
- No secrets in the repo. Config only via env vars (`.env.example`); the API key lives only on the gateway machine.
- MACs are always masked with `core/device.mask_mac()` (`XX:XX:XX:XX:1A:2B`); the raw MAC is never stored or shown.
- All user-facing text exists in Romanian AND English (`explain/texts.py`, `web/i18n.py`), ~12-year-old reading level.
- Scan file content is hostile: parse only via `core/parser.py`, never render it unescaped (Jinja autoescape stays on).

## Layout
| Module | Owner | Files (under `netcheck/` unless noted) |
|---|---|---|
| Core Engine & CLI | Ștefan (@Stevenenson) | `cli.py net/ lab/` |
| Rule & Scoring + Data Layer | see PLAN_ECHIPA.md | `core/ history.py tests/` |
| LLM Service | see PLAN_ECHIPA.md | `ai/ explain/ gateway/` (repo root) |
| Web API & Frontend | see PLAN_ECHIPA.md | `web/ run.sh` |
Edit files of another module only in coordination with its owner.

## Commands
```bash
./run.sh --demo                                     # venv + deps, gateway if configured, UI on http://127.0.0.1:8000
.venv/bin/python -m pytest -q                       # must be green before every merge
.venv/bin/python tools/make_synthetic_fixtures.py   # regenerate synthetic validation files
.venv/bin/python -m netcheck analyze tests/fixtures/synthetic --out results
.venv/bin/python -m netcheck serve                  # UI + JSON API on http://127.0.0.1:8000
.venv/bin/python -m gateway                         # AI gateway (needs ANTHROPIC_API_KEY in .env)
.venv/bin/python -m netcheck chat <scan.xml>        # assistant in the terminal (falls back to built-in text)
```

## Git workflow
- Branch per module (`stefan/cli`, `task/reguli-date`, `task/llm`, `task/web`), PR into the integration branch.
- Merge small and often (every 2–3 hours). CI (pytest + gitleaks) must be green.
- No code changes after the Test Set upload (hour 21); tag `final`.

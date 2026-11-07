# NetCheck — instructions for Claude Code (and humans)

R Systems Hackathon 2026, "Secure Networks, Simply Explained". Read `PLAN_ECHIPA.md` for who owns what.

## Golden rules
- **Never change findings/scores logic without a test.** `tests/test_netcheck.py::test_validation_set_matches_answer_key`
  must stay green (24 rows, 0 extra, 8 scores). Test Set accuracy is 30% of the grade.
- Findings, severities and scores are deterministic code (`rules.py`, `analyzer.py`). **No LLM there, ever.**
- `netcheck/models.py` is the shared contract (Finding, Device, ScanResult). Changing a field = tell the team first;
  new fields need a default so old history still loads.
- Only `nmap` in `scanner.py` (and `verify --udp`) may run with sudo. Analyser, UI, assistant, watch run unprivileged.
- Every live scan target goes through `guardrail.check_target()`. Never bypass it.
- No secrets in the repo. Config only via env vars (`.env.example`). MACs are always masked; raw MAC never stored.
- All user-facing text exists in Romanian AND English (`explain/texts.json`, `web/i18n.py`), ~12-year-old reading level.
- Scan file content is hostile: parse only via `parser.py` (defusedxml), never render it unescaped.

## Layout
| Module | Owner | Files |
|---|---|---|
| Core Engine & CLI | Ștefan (@Stevenenson) | `cli.py scanner.py guardrail.py netdetect.py parser.py verify.py watch.py lab/` |
| Rule & Scoring + Data Layer | see PLAN_ECHIPA.md | `rules.py analyzer.py models.py history.py identity.py certificate.py tests/` |
| LLM Service | see PLAN_ECHIPA.md | `llm.py assistant.py chat.py explain/` |
| Web API & Frontend | see PLAN_ECHIPA.md | `web/` |
Edit files of another module only in coordination with its owner.

## Commands
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                       # must be green before every merge
.venv/bin/python tests/fixtures/build_synthetic.py  # regenerate synthetic validation files
.venv/bin/python -m netcheck analyze tests/fixtures/validation_synthetic --out results
.venv/bin/python -m netcheck serve                  # UI on http://127.0.0.1:8000
.venv/bin/python -m netcheck chat --guide           # assistant (Ollama local, else offline)
```

## Git workflow
- Branch per module (`stefan/cli`, `task/reguli-date`, `task/llm`, `task/web`), PR into the integration branch.
- Merge small and often (every 2–3 hours). CI (pytest + gitleaks) must be green.
- No code changes after the Test Set upload (hour 21); tag `final`.

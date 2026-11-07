# Task-uri pe module

Aceeași listă există ca GitHub Issues (etichete `modul:*`). Fiecare își atribuie singur epic-ul modulului său.

## Core Engine & CLI — Ștefan (@Stevenenson)
Fișiere: `cli.py` `scanner.py` `guardrail.py` `netdetect.py` `parser.py` `verify.py` `watch.py` `lab/`  
Milestone: Ora 3: lab + 3 scanuri salvate · Ora 14: refuzul out-of-scope merge live

- [ ] [CLI] Mesajele guardrail-ului și în română _(must)_
- [ ] [CLI] Prima scanare live pe hotspot + timp sub 5 min pentru /24 _(must)_
- [ ] [CLI] Lab: ≥3 ținte, ≥5 tipuri de findings, pereche before/after _(must)_
- [ ] [CLI] Demo Paznic: telefon nou în hotspot → notificare _(bonus)_
- [ ] [CLI] gitleaks instalat + demo „no secrets” _(must)_

## Rule & Scoring + Data Layer — de ales (self-assign)
Fișiere: `rules.py` `analyzer.py` `models.py` `history.py` `identity.py` `certificate.py` `tests/`  
Milestone: Ora 10: Validation Set reprodus 24/24, 0 rânduri în plus, scoruri corecte

- [ ] [Reguli] Ora 0: Validation Set oficial în tests/fixtures/validation _(must)_
- [ ] [Reguli] Întrebări pentru mentori: Samba 3.X-4.X, http-proxy, host fără MAC _(must)_
- [ ] [Reguli] Reconciliere cu Base implementation de pe main _(must)_
- [ ] [Reguli] Procedura de la ora 20: Test Set + re-run identic _(must)_

## LLM Service — de ales (self-assign)
Fișiere: `llm.py` `assistant.py` `chat.py` `explain/texts.json`  
Milestone: Ora 12: toate codurile au text RO+EN verificat · Ora 16: chat --guide merge cap-coadă

- [ ] [LLM] Ollama + qwen2.5 local, test cu 10 întrebări în română _(must)_
- [ ] [LLM] Revizuire texts.json: ≤2 propoziții, nivel 12 ani _(must)_
- [ ] [LLM] Fals-pozitive în validatorul de grounding _(should)_
- [ ] [LLM] Test cu un non-tehnician (bonus juriu) _(bonus)_

## Web API & Frontend — de ales (self-assign)
Fișiere: `web/` (app, house, i18n, templates)  
Milestone: Ora 16: scor, findings, istoric vizibile · Ora 20: testul „juratul găsește singur”

- [ ] [Web] Verificare vizuală a hărții casei + lățime de telefon _(must)_
- [ ] [Web] Accesibilitate: tastatură, contrast AA, text ≥16px _(must)_
- [ ] [Web] Testul juratului: persoană străină găsește ce repară primul _(must)_
- [ ] [Web] Screenshot UI pentru upload-ul de la ora 21 _(must)_

## Toată echipa

- [ ] [Echipa] Pitch 5–7 min + TECH_SUMMARY completat


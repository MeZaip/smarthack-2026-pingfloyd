# Planul echipei (4 persoane, 5 module)

Prototipul complet e pe ramura `stefan/prototip-complet` (40 de teste verzi, Validation Set sintetic 24/24).
Fiecare om **deține un modul cap-coadă**: îl verifică pe date reale, îl îmbunătățește și îl prezintă la pitch.
Task-urile concrete sunt în **GitHub Issues** (etichete `modul:*`) și în `docs/issues.md`.

## Cine ce deține
| Modul | Om | Fișiere | Milestone din brief |
|---|---|---|---|
| **Core Engine & CLI**: scanare live, guardrail, parser XML sigur, verify, watch, lab | **Ștefan (@Stevenenson)** | `cli.py scanner.py guardrail.py netdetect.py parser.py verify.py watch.py lab/` | Ora 3: lab + 3 scanuri · Ora 14: refuz out-of-scope |
| **Rule & Scoring + Data Layer**: catalog, scor, CSV, istoric SQLite, certificat | _de ales_ | `rules.py analyzer.py models.py history.py identity.py certificate.py tests/` | Ora 10: 24/24 pe Validation Set |
| **LLM Service**: explicații RO/EN, asistent, grounding, Ollama | _de ales_ | `llm.py assistant.py chat.py explain/` | Ora 12: texte verificate · Ora 16: `chat --guide` |
| **Web API & Frontend**: dashboard, harta casei, istoric, certificat, accesibilitate | _de ales_ | `web/` | Ora 16: scor, findings, istoric vizibile |

Rule & Scoring și Data Layer sunt la același om: Data Layer e mic și depinde direct de modelul de date al regulilor.
Explicațiile de bază sunt **text fix, verificat**; LLM-ul doar personalizează și răspunde la întrebări (cu fallback).

**Puncte de contact** (se discută în grup înainte de orice schimbare):
- `models.py` (Finding/Device/ScanResult) e contractul comun. Câmpurile noi primesc o valoare implicită.
- `cli.py` apelează `chat.run_chat()`, `verify.verify()` și `watch.run()`; fiecare modul își deține interiorul.
- `web/app.py` doar apelează `history`, `verify`, `certificate`, `assistant`; nu le modifică.

## Cum comunicăm
1. **Grup de chat** (WhatsApp/Discord): „am dat push”, link-uri, erori. La eveniment, vorbim direct la masă.
2. **Stand-up de 5 minute la orele 3, 6, 10, 13, 16, 19**: ce am terminat / ce urmează / unde m-am blocat.
3. **GitHub Issues** = tabla de task-uri. Îți atribui singur issue-ul când începi și scrii în comentarii ce ai aflat.
4. **Ramuri**: `stefan/cli`, `task/reguli-date`, `task/llm`, `task/web`, toate pornite din `stefan/prototip-complet`.
   Faci PR înapoi în ramura de integrare, mic și des (la 2–3 ore).
5. **Înainte de merge**: `python -m pytest -q` verde local. CI-ul (pytest + gitleaks) trebuie să fie verde pe PR.
6. **`CLAUDE.md`**: dacă folosești Claude Code, el citește automat regulile proiectului, ca să nu strice codul altui modul.

## Ce facem ACASĂ, înainte de eveniment
`brew install nmap ollama gitleaks` · `ollama pull qwen2.5:7b` (sau `qwen2.5:3b`) · `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` · `.venv/bin/python -m pytest -q`

## Ce ne face diferiți (de prezentat la pitch)
> „Casa ta are uși. SafeHouse ți le arată pe o hartă, te ajută să le închizi, **dovedește** că s-au închis și păzește casa după aceea.”

| Funcție | Modul | Demo în 30 de secunde |
|---|---|---|
| 🏠 Harta casei + nume personale | Web | Juratul vede „👉 Începe aici”; redenumim „Camera bebelușului” și apare peste tot |
| 🔍 „Dovedește!” | CLI + Web | `fake_services.py --fixed`, apoi „Am reparat — verifică!”, iar ușa devine verde |
| 📜 Certificat semnat | Reguli & date | Schimbăm o cifră în JSON, iar `cert-verify` arată ⛔ falsificat |
| 🛡️ Paznic | CLI | `watch --interval 20`, un telefon intră în hotspot → notificare |
| 🤖 AI local, verificat | LLM | Întrebare-capcană → AI-ul răspunde din scan sau e respins de validator |

## Cele 7 verificări live (în ordine)
1. Re-rulare pe un fișier din Test Set: `python -m netcheck analyze <fișier> --out results/rerun` → identic cu upload-ul. *(Reguli)*
2. Juratul folosește UI-ul singur → „Repară primul” + „Începe aici”. *(Web)*
3. Explicație + fix pentru 3 coduri → cardurile de findings / `chat`. *(LLM)*
4. Guardrail: `python -m netcheck scan 8.8.8.8 --confirm` și pe subnetul locației → ⛔ REFUSED. *(CLI)*
5. Fișier stricat → `analyze V7_broken.xml` → ERROR, fără crash; în UI un card roșu cu explicație. *(CLI)*
6. Before/after din lab → pagina Istoric (grafic + ✔ rezolvate) + certificat. *(CLI + Web)*
7. `gitleaks detect --source .` → curat. *(CLI)*

## Ora 20–21 (Test Set)
```bash
.venv/bin/python -m netcheck analyze /cale/TestSet --out results/testset --history --source testset
```
Verificăm: un rând ERROR pentru fișierul stricat, perechea before/after în Istoric, nimic ciudat → upload → `git tag final`.
**Zero modificări de cod după upload.**

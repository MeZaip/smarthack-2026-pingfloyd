/* netcheck UI - for parents, grandparents and children.
 * Patterns borrowed from Google Home (greeting, suggestion card, device tiles that open a sheet,
 * navigation rail / bottom bar) and Fing (network card with score ring, security checks grouped by
 * risk, events timeline). Data: window.NETCHECK_DATA from tools/export_ui_data.py (real analyser).
 * Security (NFR-03): scan text is untrusted and only ever inserted as text, never innerHTML.
 */
"use strict";

(function () {
  const D = window.NETCHECK_DATA;
  if (!D) {
    document.getElementById("main").textContent = "Lipsește ui/data.js. Rulează: python tools/export_ui_data.py";
    return;
  }

  // ---------------------------------------------------------------- words (RO / EN, ~12-year-old level)
  const T = {
    ro: {
      skip: "Sari la conținut", close: "Închide", scanFile: "Verificarea afișată",
      navHome: "Acasă", navDevices: "Aparate", navFindings: "Reparații", navHistory: "Istoric", navAsk: "Întreabă",
      footer: "Nu păstrăm nimic pe internet: tot ce vezi rămâne pe acest calculator. Adresele aparatelor sunt ascunse pe jumătate, ca să-ți protejăm intimitatea.",
      hello: "Bună! 👋", helloSub: "Apasă butonul și verificăm împreună dacă rețeaua din casa ta e sigură.",
      inspect: "Inspectează casa", inspectAgain: "Inspectează din nou",
      stIdleT: "Casa ta digitală", stIdleS: "Apasă „Inspectează casa” ca să verificăm fiecare ușă.",
      stScanT: "Inspectez casa…", stScanS: "Verific fiecare aparat și fiecare ușă. Durează câteva secunde.",
      stSafeT: "Casa este sigură", stSafeS: "Toate ușile sunt închise. Nu ai nimic de reparat.",
      stVulnT: "Atenție: O ușă este deschisă", stVulnS: "Am găsit {n} lucruri de reparat. Mai jos vezi ce poți face.", stVulnS1: "Am găsit un lucru de reparat. Mai jos vezi ce poți face.",
      stErrT: "Nu am putut citi verificarea", stErrS: "Fișierul verificării e stricat. Alege altă verificare din lista de sus.",
      houseLabel: "Desen cu o casă. Ferestrele se aprind când o verificăm.",
      devicesFound: "Aparatele găsite ({n})", ipLabel: "IP", otherLang: "EN", whatToDo: "Ce pot face",
      netTitle: "Rețeaua de acasă",
      scoreOf: "din 100",
      band_red: "Risc înalt", band_amber: "Risc mediu", band_green: "Sigur",
      lampGreen: "Sigur", lampAmber: "Risc mediu", lampRed: "Risc înalt",
      summary: "{d} aparate verificate · {f} lucruri de reparat",
      summaryOne: "{d} aparate verificate · un lucru de reparat",
      summaryNone: "{d} aparate verificate · nimic de reparat",
      scoreMeaning: "Verde înseamnă sigur, galben înseamnă că trebuie reparat ceva, roșu înseamnă că trebuie reparat repede.",
      seeFixes: "Vezi ce trebuie reparat", seeDevices: "Vezi aparatele",
      suggestTitle: "Sugestie pentru azi", suggestSub: "Nu trebuie să repari tot deodată. Începe cu asta:",
      mostDangerous: "Aparatul cu cea mai mare problemă", thisDevice: "Aparatul",
      doThis: "Ce faci",
      btnDone: "Am făcut asta", btnSkip: "Arată-mi altceva",
      progress: "Lucrul {i} din {n}",
      doneNote: "✔ Bravo! Ai rezolvat: {title}. Verifică din nou rețeaua mai târziu ca să vezi scorul nou.",
      allDone: "Ai trecut prin toate. Verifică din nou rețeaua ca să vezi cât de sigură e acum.",
      restart: "Ia-o de la capăt",
      noProblems: "Nu am găsit nimic de reparat. Felicitări! Verifică din nou din când în când.",
      helpNote: "Ești copil? Arată această pagină unui părinte înainte să schimbi ceva. Nu te descurci? Arată-o cuiva de încredere: un nepot, un prieten sau firma care ți-a pus internetul.",
      yourDevices: "Aparatele tale", seeAll: "Vezi toate",
      glossaryTitle: "Cuvinte utile",
      devicesTitle: "Aparatele mele", devicesSub: "Toate aparatele conectate la internetul tău. Apasă pe un aparat ca să vezi ce are și ce poți face.",
      fAll: "Toate ({n})", fProblems: "Cu probleme ({n})", fSafe: "Sigure ({n})",
      devOk: "Sigur", devProblems: "{n} lucruri de reparat", devProblem: "Un lucru de reparat",
      devOkExplain: "Nu am găsit nicio problemă la acest aparat. Ușile lui sunt bine încuiate.",
      devOkSteps: ["Instalează actualizările când aparatul ți le cere.", "Folosește o parolă lungă, pe care n-o mai ai în altă parte."],
      keepSafe: "Ca să rămână sigur",
      otherProblems: "Alte lucruri de reparat la acest aparat",
      findingsTitle: "Ce trebuie reparat", findingsSub: "Verificarea de securitate, de la cel mai periculos la cel mai puțin periculos. Fiecare card îți spune ce faci, pas cu pas.",
      sumHigh: "Risc înalt", sumMedium: "Risc mediu", sumLow: "Risc mic", sumInfo: "Doar de știut",
      cardHint: "Apasă Enter ca să vezi detaliile tehnice.",
      codeLabel: "Cod",
      techMore: "Detalii pentru cine se pricepe (sau pentru firma IT)",
      techTitle: "Numele tehnic", techSteps: "Pași detaliați", techWhere: "Unde (adresă și ușă)",
      evidence: "Ce a văzut verificarea", refs: "Standarde de securitate",
      ip: "Adresă (IP)", mac: "Adresă fizică (MAC, ascunsă pe jumătate)", vendor: "Producător", hostname: "Nume în rețea",
      ports: "Uși deschise (porturi)", none: "niciuna", unknown: "nu știm",
      errorTitle: "Nu am putut citi această verificare",
      errorBody: "Fișierul verificării este stricat sau incomplet, așa că nu arătăm nimic pentru el. Alege altă verificare din lista de sus sau fă una nouă.",
      errorDetail: "Detaliu tehnic",
      historyTitle: "A devenit rețeaua mai sigură?", historySub: "Verificările salvate pe acest calculator, înainte și după ce ai reparat lucrurile.",
      before: "Înainte", now: "Acum",
      bravo: "🎉 Bravo! Ai reparat {n} lucruri.", bravoOne: "🎉 Bravo! Ai reparat un lucru.",
      worse: "⚠️ Atenție: scorul a scăzut. Uită-te la lucrurile noi de reparat.", same: "Scorul a rămas la fel.",
      events: "Ce s-a întâmplat",
      evFixed: "Ai reparat: {title}", evNew: "Lucru nou de reparat: {title}",
      evSecured: "Setările se deschid acum pe drumul sigur", evSecuredSub: "Din ușa {from} în ușa sigură {to}",
      evNewDev: "Aparat nou în rețea", evGoneDev: "Un aparat nu mai e în rețea",
      evQuiet: "Niciun aparat nou și nicio ușă nouă periculoasă",
      evFirst: "Verificarea de dinainte: scor {s}, {f} lucruri de reparat",
      chartTitle: "Scorul la fiecare verificare", chartLabel: "Grafic cu scorul la fiecare verificare salvată",
      colScan: "Verificare", colScore: "Scor", colFindings: "De reparat",
      deleteTitle: "Istoricul tău", deleteSub: "Poți șterge oricând tot ce am salvat pe acest calculator.",
      deleteBtn: "Șterge tot ce am salvat",
      deleteConfirm: "Sigur ștergi toate verificările salvate pe acest calculator? Nu le mai poți aduce înapoi.",
      deleteYes: "Da, șterge tot", deleteNo: "Nu, lasă-le",
      deleted: "Gata, am șters tot ce era salvat pe acest calculator.",
      deletedTech: "În aplicație, asta șterge fișierul ~/.netcheck/history.sqlite.",
      restore: "Adu înapoi datele demo",
      askTitle: "Întreabă", askSub: "Îți răspund doar cu ce am văzut în verificare. Lângă fiecare propoziție scrie de unde știu. Dacă o propoziție nu are dovadă, o tai.",
      botName: "Asistentul SafeHouse",
      botHello: "Salut! Sunt aici să te ajut. Alege o întrebare de mai jos sau scrie-mi una.",
      q1: "Ce repar prima dată?", q2: "Ce aparate am acasă?", q3: "E periculoasă imprimanta mea?",
      askPlaceholder: "De exemplu: Ce repar prima dată?", askBtn: "Trimite", askLabel: "Întrebarea ta",
      proof: "de unde știu",
      noAnswer: "Verificarea nu-mi arată asta, așa că nu pot să-ți răspund sigur. Încearcă una dintre întrebările de mai sus.",
      hallToggle: "Pentru prezentare: arată cum oprim o informație inventată",
      hallSwitch: "Strecoară în răspuns o afirmație inventată",
      blocked: "Am tăiat-o: {r}.",
      rPort: "ușa {port} nu e deschisă pe {ip} în această verificare", rIp: "adresa {ip} nu apare în dovezi",
      rCve: "{cve} nu apare în verificare", rNoCite: "nu are nicio dovadă din verificare",
      verified: "{ok} propoziții verificate, {bad} tăiate",
      demoNote: "Aici răspunsurile vin din textele noastre. În aplicație le scrie inteligența artificială, iar același verificator taie orice propoziție fără dovadă.",
      aFirst1: "Cea mai mare problemă este la: {name}.", aFirst2: "Începe cu asta: {title}.", aFirst3: "Primul pas: {step}",
      aDevCount: "Am găsit {n} aparate conectate la rețeaua ta.", aDev: "{name}.",
      aPrinterYes: "Da, puțin: oricine din rețea poate trimite documente la imprimanta ta, prin ușa 9100.",
      aPrinterFix: "Ce poți face: {step}", aPrinterNo: "Verificarea nu-mi arată o imprimantă cu problema asta.",
      aClean: "Verificarea nu arată nimic de reparat. Totul e bine!",
      hall: "Routerul are și ușa Telnet deschisă (portul {port}), deci schimbă-i parola imediat.",
    },
    en: {
      skip: "Skip to content", close: "Close", scanFile: "Check shown",
      navHome: "Home", navDevices: "Devices", navFindings: "Fixes", navHistory: "History", navAsk: "Ask",
      footer: "We keep nothing on the internet: everything you see stays on this computer. Device addresses are half hidden to protect your privacy.",
      hello: "Hi! 👋", helloSub: "Press the button and we will check together if the network in your home is safe.",
      inspect: "Inspect house", inspectAgain: "Inspect again",
      stIdleT: "Your digital home", stIdleS: "Press “Inspect house” so we can check every door.",
      stScanT: "Inspecting the house…", stScanS: "Checking every device and every door. It takes a few seconds.",
      stSafeT: "The house is safe", stSafeS: "All doors are closed. You have nothing to fix.",
      stVulnT: "Warning: A door is open", stVulnS: "We found {n} things to fix. See below what you can do.", stVulnS1: "We found one thing to fix. See below what you can do.",
      stErrT: "We could not read the check", stErrS: "The check file is broken. Pick another check from the list at the top.",
      houseLabel: "Drawing of a house. The windows light up when we check it.",
      devicesFound: "Devices found ({n})", ipLabel: "IP", otherLang: "RO", whatToDo: "What I can do",
      netTitle: "Home network",
      scoreOf: "out of 100",
      band_red: "High risk", band_amber: "Medium risk", band_green: "Safe",
      lampGreen: "Safe", lampAmber: "Medium risk", lampRed: "High risk",
      summary: "{d} devices checked · {f} things to fix",
      summaryOne: "{d} devices checked · one thing to fix",
      summaryNone: "{d} devices checked · nothing to fix",
      scoreMeaning: "Green means safe, yellow means something needs fixing, red means fix it soon.",
      seeFixes: "See what needs fixing", seeDevices: "See the devices",
      suggestTitle: "Suggestion for today", suggestSub: "You do not have to fix everything at once. Start with this:",
      mostDangerous: "The device with the biggest problem", thisDevice: "Device",
      doThis: "What to do",
      btnDone: "I did this", btnSkip: "Show me something else",
      progress: "Thing {i} of {n}",
      doneNote: "✔ Well done! You fixed: {title}. Check the network again later to see the new score.",
      allDone: "You went through everything. Check the network again to see how safe it is now.",
      restart: "Start again",
      noProblems: "We found nothing to fix. Congratulations! Check again from time to time.",
      helpNote: "Are you a child? Show this page to a parent before you change anything. Finding it hard? Show it to someone you trust: a grandchild, a friend or the company that set up your internet.",
      yourDevices: "Your devices", seeAll: "See all",
      glossaryTitle: "Useful words",
      devicesTitle: "My devices", devicesSub: "All the devices connected to your internet. Tap a device to see what it has and what you can do.",
      fAll: "All ({n})", fProblems: "With problems ({n})", fSafe: "Safe ({n})",
      devOk: "Safe", devProblems: "{n} things to fix", devProblem: "One thing to fix",
      devOkExplain: "We found no problem on this device. Its doors are locked well.",
      devOkSteps: ["Install updates when the device asks you to.", "Use a long password that you do not use anywhere else."],
      keepSafe: "To keep it safe",
      otherProblems: "Other things to fix on this device",
      findingsTitle: "What needs fixing", findingsSub: "The security check, from most to least dangerous. Each card tells you what to do, step by step.",
      sumHigh: "High risk", sumMedium: "Medium risk", sumLow: "Low risk", sumInfo: "Just so you know",
      cardHint: "Press Enter to see the technical details.",
      codeLabel: "Code",
      techMore: "Details for people who know computers (or for the IT company)",
      techTitle: "Technical name", techSteps: "Detailed steps", techWhere: "Where (address and door)",
      evidence: "What the check saw", refs: "Security standards",
      ip: "Address (IP)", mac: "Physical address (MAC, half hidden)", vendor: "Maker", hostname: "Network name",
      ports: "Open doors (ports)", none: "none", unknown: "we don't know",
      errorTitle: "We could not read this check",
      errorBody: "The check file is broken or incomplete, so we show nothing for it. Pick another check from the list at the top or make a new one.",
      errorDetail: "Technical detail",
      historyTitle: "Has the network become safer?", historySub: "The checks saved on this computer, before and after you fixed things.",
      before: "Before", now: "Now",
      bravo: "🎉 Well done! You fixed {n} things.", bravoOne: "🎉 Well done! You fixed one thing.",
      worse: "⚠️ Careful: the score went down. Look at the new things to fix.", same: "The score stayed the same.",
      events: "What happened",
      evFixed: "You fixed: {title}", evNew: "New thing to fix: {title}",
      evSecured: "The settings now open on the safe road", evSecuredSub: "From door {from} to safe door {to}",
      evNewDev: "New device on the network", evGoneDev: "A device is no longer on the network",
      evQuiet: "No new device and no dangerous new door",
      evFirst: "The check before: score {s}, {f} things to fix",
      chartTitle: "The score at each check", chartLabel: "Chart of the score at each saved check",
      colScan: "Check", colScore: "Score", colFindings: "To fix",
      deleteTitle: "Your history", deleteSub: "You can delete everything we saved on this computer at any time.",
      deleteBtn: "Delete everything saved",
      deleteConfirm: "Delete all checks saved on this computer? You cannot get them back.",
      deleteYes: "Yes, delete everything", deleteNo: "No, keep them",
      deleted: "Done, we deleted everything that was saved on this computer.",
      deletedTech: "In the app, this removes the file ~/.netcheck/history.sqlite.",
      restore: "Bring back the demo data",
      askTitle: "Ask", askSub: "I answer only with what I saw in the check. Next to each sentence it says how I know. If a sentence has no proof, I cross it out.",
      botName: "SafeHouse assistant",
      botHello: "Hi! I am here to help. Pick a question below or write me one.",
      q1: "What do I fix first?", q2: "Which devices do I have at home?", q3: "Is my printer dangerous?",
      askPlaceholder: "For example: What do I fix first?", askBtn: "Send", askLabel: "Your question",
      proof: "how I know",
      noAnswer: "The check does not show me that, so I cannot answer for sure. Try one of the questions above.",
      hallToggle: "For the presentation: show how we stop an invented claim",
      hallSwitch: "Slip an invented claim into the answer",
      blocked: "Crossed out: {r}.",
      rPort: "door {port} is not open on {ip} in this check", rIp: "address {ip} is not in the proof",
      rCve: "{cve} is not in the check", rNoCite: "it has no proof from the check",
      verified: "{ok} sentences checked, {bad} crossed out",
      demoNote: "Here the answers come from our own texts. In the app, artificial intelligence writes them and the same checker crosses out any sentence without proof.",
      aFirst1: "The biggest problem is on: {name}.", aFirst2: "Start with this: {title}.", aFirst3: "First step: {step}",
      aDevCount: "We found {n} devices connected to your network.", aDev: "{name}.",
      aPrinterYes: "A little: anyone on the network can send documents to your printer, through door 9100.",
      aPrinterFix: "What you can do: {step}", aPrinterNo: "The check does not show me a printer with this problem.",
      aClean: "The check shows nothing to fix. All good!",
      hall: "The router also has the Telnet door open (port {port}), so change its password right away.",
    },
  };

  // Risk words with icons (never colour alone).
  const RISK = {
    high: { ro: "Risc înalt", en: "High risk", icon: "❌", tone: "red" },
    medium: { ro: "Risc mediu", en: "Medium risk", icon: "⚠️", tone: "amber" },
    low: { ro: "Risc mic", en: "Low risk", icon: "ℹ️", tone: "low" },
    info: { ro: "Doar de știut", en: "Just so you know", icon: "ℹ️", tone: "info" },
  };
  const BAND_ICON = { red: "❌", amber: "⚠️", green: "✅" };
  const DEVICE_ICON = { router: "📶", camera: "📷", printer: "🖨️", nas: "🗄️", iot: "💡", tv: "📺", phone: "📱", computer: "💻", server: "🖥️", unknown: "❓" };
  const SIZES = ["100%", "115%", "130%"];
  const TABS = ["home", "devices", "findings", "history", "ask"];

  // ---------------------------------------------------------------- state
  const store = {
    get(k) { try { return window.localStorage.getItem("netcheck." + k); } catch (e) { return null; } },
    set(k, v) { try { window.localStorage.setItem("netcheck." + k, v); } catch (e) { /* private mode */ } },
  };
  const state = {
    lang: store.get("lang") === "en" ? "en" : "ro",
    size: Math.min(2, Math.max(0, Number(store.get("size")) || 0)),
    scan: Math.max(0, D.scans.findIndex((s) => s.file === "V2_smart_home.xml")),
    tab: "home",
    devFilter: "all",
    cursor: {}, lastDone: {},
    historyDeleted: store.get("historyDeleted") === "1",
    confirmDelete: false,
    hallucinate: false,
    chat: [],            // [{kind, text}]
    inspected: {},       // scan file -> true once the house was inspected
    scanning: false,
  };

  // ---------------------------------------------------------------- helpers
  function t(key, vars) {
    let s = (T[state.lang] && T[state.lang][key]) || T.ro[key] || key;
    if (vars && typeof s === "string") for (const k of Object.keys(vars)) s = s.split("{" + k + "}").join(String(vars[k]));
    return s;
  }
  function h(tag, props) {
    const el = document.createElement(tag);
    if (props) for (const [k, v] of Object.entries(props)) {
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (let i = 2; i < arguments.length; i++) append(el, arguments[i]);
    return el;
  }
  function append(el, c) {
    if (c == null || c === false) return;
    if (Array.isArray(c)) { c.forEach((x) => append(el, x)); return; }
    el.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
  }
  function svg(tag, attrs) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
    return el;
  }
  const scan = () => D.scans[state.scan];
  const bandOf = (score) => (score >= 80 ? "green" : score >= 50 ? "amber" : "red");
  const simple = (code) => (D.simple[code] && D.simple[code][state.lang]) || { title: code, explain: "", steps: [] };
  const whoOf = (code) => (D.simple[code] && D.simple[code].who) || "helper";
  const detailed = (code) => (D.texts[code] && D.texts[code][state.lang]) || { title: code, explain: "", steps: [] };
  const refs = (code) => (D.texts[code] && D.texts[code].refs) || [];
  const where = (f) => (f.port == null ? f.ip : `${f.ip}:${f.port}`);
  const deviceByIp = (s, ip) => s.devices.find((d) => d.ip === ip);
  const deviceLabel = (type) => (D.deviceLabels[type] || D.deviceLabels.unknown)[state.lang];
  const plural = (n, one, many) => (n === 1 ? t(one) : t(many, { n }));
  const problemsOf = (s, d) => s.findings.filter((f) => f.ip === d.ip && f.severity !== "info");
  const toneOf = (sev) => RISK[sev].tone;

  function shortVendor(v) {
    if (!v) return "";
    return v.replace(/\b(Technologies|Technology|Incorporated|Inc\.?|Industries|Electronics|Foundation|Corporation|Corp\.?|Co\.?|Ltd\.?|Hangzhou|International)\b/gi, "").replace(/\s+/g, " ").trim();
  }
  function deviceName(d) {
    if (!d) return deviceLabel("unknown");
    const v = shortVendor(d.vendor);
    return deviceLabel(d.type) + (v ? ` (${v})` : "");
  }
  const riskPill = (sev) => h("span", { class: "pill p-" + sev }, h("span", { "aria-hidden": "true", text: RISK[sev].icon }), RISK[sev][state.lang]);
  function bandPill(score) {
    const b = bandOf(score);
    return h("span", { class: "pill p-" + b }, h("span", { "aria-hidden": "true", text: BAND_ICON[b] }), t("band_" + b));
  }
  function devIco(type, tone, big) {
    return h("div", { class: "dev-ico" + (big ? " lg" : "") + (tone ? " " + tone : ""), "aria-hidden": "true", text: DEVICE_ICON[type] || DEVICE_ICON.unknown });
  }
  function whoLine(code) {
    const w = D.who[whoOf(code)];
    return h("p", { class: "who" }, h("span", { "aria-hidden": "true", text: w.icon }), w[state.lang]);
  }
  const steps = (list) => h("ol", { class: "steps" }, list.map((x) => h("li", { text: x })));
  function techBox(children) {
    return h("details", { class: "tech" }, h("summary", null, h("span", { "aria-hidden": "true", text: "🔧" }), t("techMore")), h("div", null, children));
  }
  function techFor(f) {
    const d = detailed(f.code);
    return techBox([
      h("dl", { class: "meta" },
        h("dt", { text: t("techTitle") }), h("dd", { text: d.title }),
        h("dt", { text: t("techWhere") }), h("dd", { class: "mono", text: where(f) }),
        h("dt", { text: t("codeLabel") }), h("dd", { class: "mono", text: f.code })),
      h("p", { text: d.explain }),
      h("strong", { text: t("techSteps") }),
      h("ol", { class: "plain" }, d.steps.map((x) => h("li", { text: x }))),
      h("div", { class: "muted", text: t("evidence") }),
      h("div", { class: "evidence mono", text: f.evidence }),
      refs(f.code).length ? h("div", { class: "tags" }, h("span", { class: "muted", text: t("refs") + ":" }), refs(f.code).map((r) => h("span", { class: "tag", text: r }))) : null,
    ]);
  }
  function pageHead(title, sub) {
    return h("div", { class: "page-head" }, h("h2", { text: title }), sub ? h("p", { text: sub }) : null);
  }
  function focusSel(sel) { const el = document.querySelector(sel); if (el) el.focus(); }

  // Score ring (Fing) + labelled traffic light.
  function ring(score, small) {
    const b = bandOf(score), r = 52, c = 2 * Math.PI * r;
    const s = svg("svg", { viewBox: "0 0 120 120", "aria-hidden": "true" });
    s.append(svg("circle", { class: "track", cx: 60, cy: 60, r, fill: "none", "stroke-width": 12 }));
    s.append(svg("circle", { class: "val-" + b, cx: 60, cy: 60, r, fill: "none", "stroke-width": 12, "stroke-linecap": "round",
      "stroke-dasharray": `${(score / 100) * c} ${c}` }));
    return h("div", { class: "ring" + (small ? " small" : ""), role: "img", "aria-label": `${score} ${t("scoreOf")}, ${t("band_" + b)}` },
      s, h("div", { class: "ring-center", "aria-hidden": "true" }, h("div", { class: "ring-num", text: String(score) }), h("div", { class: "ring-of", text: t("scoreOf") })));
  }
  function traffic(score) {
    const b = bandOf(score);
    const lamp = (tone, key) => h("span", { class: "lamp " + tone + (b === tone ? " on" : "") },
      h("span", { class: "dot", "aria-hidden": "true" }), b === tone ? [h("span", { "aria-hidden": "true", text: BAND_ICON[tone] }), t(key)] : t(key));
    return h("div", { class: "traffic", role: "img", "aria-label": t("band_" + b) },
      lamp("green", "lampGreen"), lamp("amber", "lampAmber"), lamp("red", "lampRed"));
  }

  // ---------------------------------------------------------------- "one thing today" queue
  function mostDangerous(s) {
    const d = s.devices.slice().sort((a, b) => b.risk_points - a.risk_points)[0];
    return d && d.risk_points > 0 ? d : null;
  }
  function queue(s) {
    const top = mostDangerous(s);
    const real = s.findings.filter((f) => f.severity !== "info");
    return top ? real.filter((f) => f.ip === top.ip).concat(real.filter((f) => f.ip !== top.ip)) : real;
  }

  function errorBox(s) {
    return h("div", { class: "error", role: "alert" },
      h("h2", null, h("span", { "aria-hidden": "true", text: "😕 " }), t("errorTitle")),
      h("p", { class: "lead", text: t("errorBody") }),
      techBox(h("p", null, t("errorDetail") + ": ", h("span", { class: "mono", text: s.file + " — " + s.error }))));
  }

  // ---------------------------------------------------------------- HOME: SafeHouse
  const SCAN_MS = 2600;
  const reducedMotion = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const resultOf = (s) => (s.error ? "error" : s.findings.some((f) => f.severity !== "info") ? "vulnerable" : "safe");
  const STATUS = {
    idle: { icon: "🏠", title: "stIdleT", sub: "stIdleS" },
    scanning: { icon: "🔎", title: "stScanT", sub: "stScanS" },
    safe: { icon: "✅", title: "stSafeT", sub: "stSafeS" },
    vulnerable: { icon: "⚠️", title: "stVulnT", sub: "stVulnS" },
    error: { icon: "❌", title: "stErrT", sub: "stErrS" },
  };

  function houseScene() {
    const f = (cls, kids) => h("div", { class: "face " + cls }, kids);
    return h("div", { class: "house-stage", role: "img", "aria-label": t("houseLabel") },
      h("div", { class: "scanbar", "aria-hidden": "true" }),
      h("div", { class: "house-wrap", "aria-hidden": "true" },
        h("div", { class: "house" },
          f("f-back"), f("f-left"),
          f("f-right", [h("div", { class: "win w3" }), h("div", { class: "win w4" })]),
          f("f-gable back"), f("chimney"), f("f-roof b"), f("f-roof a"), f("f-gable"),
          f("f-front", [h("div", { class: "win w1" }), h("div", { class: "win w2" }), h("div", { class: "doorway" }), h("div", { class: "door" })]))));
  }

  // Puts the hero in one state; colour is never alone, every state has an icon + words.
  function applyHouseState(st) {
    const hero = document.querySelector(".hero");
    if (!hero || !STATUS[st]) return false;
    const s = scan(), cfg = STATUS[st], toFix = s.error ? 0 : s.findings.filter((x) => x.severity !== "info").length;
    hero.dataset.state = st;
    hero.querySelector(".hs-icon").textContent = cfg.icon;
    hero.querySelector(".hs-title").textContent = t(cfg.title);
    hero.querySelector(".hs-sub").textContent = st === "vulnerable" && toFix ? (toFix === 1 ? t("stVulnS1") : t("stVulnS", { n: toFix })) : t(cfg.sub);
    const btn = hero.querySelector(".inspect-btn");
    btn.setAttribute("aria-busy", String(st === "scanning"));
    btn.disabled = st === "scanning";
    return true;
  }

  function inspect() {
    const s = scan();
    if (state.scanning) return;
    state.scanning = true;
    applyHouseState("scanning");
    setTimeout(() => {
      state.scanning = false;
      state.inspected[s.file] = true;
      render();
      focusSel(".inspect-btn");
    }, reducedMotion() ? 0 : SCAN_MS);
  }

  function renderHome(root) {
    const s = scan();
    const done = !!state.inspected[s.file];
    const st = state.scanning ? "scanning" : done ? resultOf(s) : "idle";
    root.append(pageHead(t("hello"), t("helloSub")));

    const toFix = s.error ? 0 : s.findings.filter((f) => f.severity !== "info").length;
    const side = h("div", { class: "hero-side" },
      h("div", { class: "house-status", role: "status", "aria-live": "polite" },
        h("div", { class: "hs-icon", "aria-hidden": "true" }),
        h("div", null, h("p", { class: "hs-title" }), h("p", { class: "hs-sub" }))),
      done && !s.error ? h("div", { class: "hero-score" }, ring(s.score, true),
        h("div", null, traffic(s.score),
          h("p", { class: "lead", style: "margin:.6rem 0 0", text: toFix === 0 ? t("summaryNone", { d: s.devices.length }) : toFix === 1 ? t("summaryOne", { d: s.devices.length }) : t("summary", { d: s.devices.length, f: toFix }) }))) : null,
      h("div", { class: "actions" },
        h("button", { type: "button", class: "btn btn-filled inspect-btn", onclick: inspect }, h("span", { "aria-hidden": "true", text: "🔎 " }), done ? t("inspectAgain") : t("inspect")),
        done && toFix ? h("button", { type: "button", class: "btn", onclick: () => setTab("findings") }, "🛡️ " + t("seeFixes")) : null));
    root.append(h("section", { class: "hero", "data-state": st, "aria-label": "SafeHouse" }, houseScene(), side));
    applyHouseState(st);

    if (!done) return;                       // results appear after the house is inspected
    if (s.error) { root.append(h("div", { class: "section" }, errorBox(s))); return; }

    root.append(h("div", { class: "section" },
      h("div", { class: "section-head" }, h("h3", { text: t("devicesFound", { n: s.devices.length }) })),
      deviceCards(s)));
    root.append(h("div", { class: "section" }, h("div", { class: "section-head" }, h("h3", { text: "⭐ " + t("suggestTitle") })), suggestion(s)));
    root.append(h("div", { class: "section glossary" }, h("div", { class: "section-head" }, h("h3", { text: "📖 " + t("glossaryTitle") })),
      h("dl", null, D.glossary[state.lang].map((g) => h("div", { class: "g" }, h("dt", { text: g.term }), h("dd", { text: g.meaning }))))));
  }

  // Device cards: icon, name, IP and a very simple explanation (max 2 sentences) in both languages.
  function explainIn(lang, d, worst) {
    return worst ? D.simple[worst.code][lang].explain : T[lang].devOkExplain;
  }
  function deviceCards(s) {
    const other = state.lang === "ro" ? "en" : "ro";
    return h("div", { class: "dcards" }, s.devices.slice().sort((a, b) => b.risk_points - a.risk_points).map((d) => {
      const probs = problemsOf(s, d), worst = probs[0], vendor = shortVendor(d.vendor);
      const name = deviceLabel(d.type) + (vendor ? " " + vendor : "");
      const card = h("article", { class: "dcard", tabindex: "0", "aria-label": `${name}, ${t("ipLabel")} ${d.ip}. ${worst ? RISK[worst.severity][state.lang] : t("devOk")}.` },
        h("div", { class: "dcard-head" }, devIco(d.type, worst ? toneOf(worst.severity) : "green"),
          h("div", null, h("h3", { text: name }), h("div", { class: "dcard-ip" }, t("ipLabel") + ": ", h("span", { class: "mono", text: d.ip })))),
        worst ? riskPill(worst.severity) : h("span", { class: "pill p-green" }, h("span", { "aria-hidden": "true", text: "✅" }), t("devOk")),
        h("p", { lang: state.lang, style: "margin-top:.8rem", text: explainIn(state.lang, d, worst) }),
        h("p", { class: "other", lang: other }, h("span", { class: "lang-tag", text: t("otherLang") + ":" }), explainIn(other, d, worst)),
        h("button", { type: "button", class: "btn btn-text", onclick: (e) => { e.stopPropagation(); openDevice(d, card); } }, t("whatToDo") + " ›"));
      card.addEventListener("click", () => openDevice(d, card));
      card.addEventListener("keydown", (e) => { if (e.target === card && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); openDevice(d, card); } });
      return card;
    }));
  }

  function suggestion(s) {
    const q = queue(s);
    const card = h("div", { class: "suggest", "aria-live": "polite" });
    if (!q.length) { card.append(h("p", { class: "lead", style: "margin:0", text: "✅ " + t("noProblems") })); return card; }
    const i = state.cursor[s.file] || 0;
    if (state.lastDone[s.file]) card.append(h("div", { class: "note ok", text: t("doneNote", { title: state.lastDone[s.file] }) }));
    if (i >= q.length) {
      card.append(h("p", { class: "lead", text: t("allDone") }),
        h("button", { type: "button", class: "btn btn-tonal", onclick: () => { state.cursor[s.file] = 0; state.lastDone[s.file] = null; render(); } }, t("restart")));
      return card;
    }
    const f = q[i], tx = simple(f.code), dev = deviceByIp(s, f.ip), top = mostDangerous(s);
    card.append(
      h("p", { class: "muted", text: t("suggestSub") }),
      h("div", { class: "suggest-top" }, devIco(dev ? dev.type : "unknown", toneOf(f.severity), true),
        h("div", { class: "grow" },
          h("div", { class: "muted", text: top && top.ip === f.ip ? t("mostDangerous") : t("thisDevice") }),
          h("strong", { style: "font-size:1.3rem", text: deviceName(dev) })),
        riskPill(f.severity)),
      h("h3", { text: tx.title }),
      h("p", { class: "lead", text: tx.explain }),
      h("h4", { text: t("doThis") + ":" }),
      steps(tx.steps),
      whoLine(f.code),
      h("div", { class: "actions" },
        h("button", { type: "button", class: "btn btn-filled", onclick: () => { state.lastDone[s.file] = tx.title; state.cursor[s.file] = i + 1; render(); focusSel(".suggest button"); } }, "✔ " + t("btnDone")),
        q.length > 1 ? h("button", { type: "button", class: "btn", onclick: () => { state.lastDone[s.file] = null; state.cursor[s.file] = (i + 1) % q.length; render(); focusSel(".suggest button"); } }, t("btnSkip")) : null,
        h("span", { class: "progress", text: t("progress", { i: i + 1, n: q.length }) })),
      h("p", { class: "note" }, h("span", { "aria-hidden": "true", text: "👨‍👩‍👧 " }), t("helpNote")),
      techFor(f));
    return card;
  }

  // ---------------------------------------------------------------- DEVICES (tiles + sheet)
  function tiles(s, list) {
    return h("div", { class: "tiles" }, list.map((d) => {
      const probs = problemsOf(s, d), worst = probs[0];
      const tone = worst ? toneOf(worst.severity) : "green";
      const status = worst ? `${RISK[worst.severity].icon} ${RISK[worst.severity][state.lang]} · ${plural(probs.length, "devProblem", "devProblems")}` : `✅ ${t("devOk")}`;
      const vendor = shortVendor(d.vendor);
      return h("button", { type: "button", class: "tile " + tone, onclick: (e) => openDevice(d, e.currentTarget),
        "aria-label": `${deviceLabel(d.type)}${vendor ? ", " + vendor : ""}. ${status.replace(/^\S+\s/, "")}` },
        devIco(d.type),
        h("div", null, h("div", { class: "tile-name", text: deviceLabel(d.type) }), vendor ? h("div", { class: "tile-sub", text: vendor }) : null),
        h("div", { class: "tile-status", text: status }));
    }));
  }

  function renderDevices(root) {
    const s = scan();
    root.append(pageHead(t("devicesTitle"), t("devicesSub")));
    if (s.error) { root.append(errorBox(s)); return; }
    const withP = s.devices.filter((d) => problemsOf(s, d).length);
    const safe = s.devices.filter((d) => !problemsOf(s, d).length);
    const chip = (key, label) => h("button", { type: "button", class: "chip-btn", "aria-pressed": String(state.devFilter === key),
      onclick: () => { state.devFilter = key; render(); focusSel(`.chip-btn[aria-pressed="true"]`); } }, label);
    root.append(h("div", { class: "chips", style: "margin-bottom:20px", role: "group" },
      chip("all", t("fAll", { n: s.devices.length })), chip("problems", "⚠️ " + t("fProblems", { n: withP.length })), chip("safe", "✅ " + t("fSafe", { n: safe.length }))));
    const list = (state.devFilter === "problems" ? withP : state.devFilter === "safe" ? safe : s.devices)
      .slice().sort((a, b) => b.risk_points - a.risk_points);
    root.append(tiles(s, list));
  }

  // The device card (name/type, 2-sentence explanation, numbered steps) shown in a sheet.
  let lastOpener = null;
  function openDevice(d, opener) {
    const s = scan(), probs = problemsOf(s, d), worst = probs[0];
    const tx = worst ? simple(worst.code) : null, vendor = shortVendor(d.vendor);
    const risky = new Set(probs.filter((f) => f.port != null).map((f) => f.port));
    const body = document.getElementById("sheet-body");
    body.replaceChildren(h("div", null,
      h("div", { class: "sheet-head" }, devIco(d.type, worst ? toneOf(worst.severity) : "green", true),
        h("div", null, h("h2", { id: "sheet-title", text: deviceLabel(d.type) }), vendor ? h("div", { class: "muted", text: vendor }) : null)),
      worst ? riskPill(worst.severity) : h("span", { class: "pill p-green" }, h("span", { "aria-hidden": "true", text: "✅" }), t("devOk")),
      worst ? h("h3", { style: "margin-top:1rem", text: tx.title }) : null,
      h("p", { class: "lead", style: "margin-top:.6rem", text: worst ? tx.explain : t("devOkExplain") }),
      h("h4", { text: (worst ? t("doThis") : t("keepSafe")) + ":" }),
      steps(worst ? tx.steps : t("devOkSteps")),
      worst ? whoLine(worst.code) : null,
      probs.length > 1 ? [h("h4", { text: t("otherProblems") + ":" }),
        h("div", { class: "chips" }, probs.slice(1).map((f) => h("button", { type: "button", class: "chip-btn",
          onclick: () => { closeSheet(); setTab("findings"); openFinding(s.findings.indexOf(f)); } }, `${RISK[f.severity].icon} ${simple(f.code).title} ›`)))] : null,
      techBox([
        h("dl", { class: "meta" },
          h("dt", { text: t("ip") }), h("dd", { class: "mono", text: d.ip }),
          h("dt", { text: t("mac") }), h("dd", { class: "mono", text: d.mac || t("unknown") }),
          h("dt", { text: t("vendor") }), h("dd", { text: d.vendor || t("unknown") }),
          h("dt", { text: t("hostname") }), h("dd", { text: d.hostname || t("unknown") })),
        h("div", { class: "muted", style: "margin-bottom:.4rem", text: t("ports") }),
        d.open_ports.length ? h("div", { class: "tags" }, d.open_ports.map((p) => h("span", { class: "port" + (risky.has(p.port) ? " risk" : "") },
          (risky.has(p.port) ? "⚠️ " : "") + `${p.port}/${p.protocol} ${p.service}${p.tls ? " (TLS)" : ""}`))) : h("span", { text: t("none") }),
        worst ? [h("h4", { text: t("techTitle") + ": " + detailed(worst.code).title }), h("div", { class: "evidence mono", text: worst.evidence }),
          h("span", { class: "code-tag", text: `${t("codeLabel")}: ${worst.code}` })] : null,
      ])));
    lastOpener = opener || null;
    const dlg = document.getElementById("sheet");
    if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", "");
    document.getElementById("sheet-close").focus();
  }
  function closeSheet() {
    const dlg = document.getElementById("sheet");
    if (dlg.open) { if (typeof dlg.close === "function") dlg.close(); else dlg.removeAttribute("open"); }
  }

  // ---------------------------------------------------------------- FIXES (Fing-style security check)
  function renderFindings(root) {
    const s = scan();
    root.append(pageHead(t("findingsTitle"), t("findingsSub")));
    if (s.error) { root.append(errorBox(s)); return; }
    if (!s.findings.length) { root.append(h("div", { class: "suggest" }, h("p", { class: "lead", style: "margin:0", text: "✅ " + t("noProblems") }))); return; }
    const sums = { high: "sumHigh", medium: "sumMedium", low: "sumLow", info: "sumInfo" };
    root.append(h("div", { class: "chips" }, Object.keys(RISK).filter((k) => s.findings.some((f) => f.severity === k))
      .map((k) => h("span", { class: "pill p-" + k }, h("span", { "aria-hidden": "true", text: RISK[k].icon }), `${t(sums[k])}: ${s.findings.filter((f) => f.severity === k).length}`))));
    Object.keys(RISK).forEach((sev) => {
      const group = s.findings.map((f, i) => ({ f, i })).filter((x) => x.f.severity === sev);
      if (!group.length) return;
      root.append(h("section", { class: "group" },
        h("div", { class: "group-head" }, h("h3", null, h("span", { "aria-hidden": "true", text: RISK[sev].icon + " " }), `${RISK[sev][state.lang]} (${group.length})`)),
        h("div", { class: "checks" }, group.map(({ f, i }) => checkCard(s, f, i)))));
    });
  }
  function checkCard(s, f, i) {
    const tx = simple(f.code), dev = deviceByIp(s, f.ip) || { type: "unknown" }, vendor = shortVendor(dev.vendor);
    const card = h("article", { class: "check", id: "finding-" + i, tabindex: "0",
      "aria-label": `${RISK[f.severity][state.lang]}. ${tx.title}. ${deviceLabel(dev.type)}. ${t("cardHint")}` },
      h("div", { class: "check-head" }, devIco(dev.type, toneOf(f.severity)),
        h("div", { class: "grow" }, h("h3", { style: "margin:0;font-size:1.2rem", text: deviceLabel(dev.type) }), vendor ? h("div", { class: "sub", text: vendor }) : null),
        riskPill(f.severity)),
      h("h4", { class: "title", text: tx.title }),
      h("p", { text: tx.explain }),
      h("h4", { text: t("doThis") + ":" }),
      steps(tx.steps),
      h("div", { class: "foot-row" }, whoLine(f.code), h("span", { class: "code-tag", text: `${t("codeLabel")}: ${f.code}` })),
      techFor(f));
    card.addEventListener("keydown", (e) => {
      if (e.target !== card || (e.key !== "Enter" && e.key !== " ")) return;
      e.preventDefault();
      const d = card.querySelector("details.tech");
      d.open = !d.open;
    });
    return card;
  }
  function openFinding(i) {
    const el = document.getElementById("finding-" + i);
    if (!el) return;
    el.focus({ preventScroll: true });
    el.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  // ---------------------------------------------------------------- HISTORY (compare + events timeline)
  function renderHistory(root) {
    root.append(pageHead(t("historyTitle"), t("historySub")));
    if (state.historyDeleted) {
      root.append(h("div", { class: "suggest" }, h("p", { class: "lead", role: "status", text: "🗑 " + t("deleted") }),
        h("p", { class: "muted", text: t("deletedTech") }),
        h("button", { type: "button", class: "btn btn-tonal", onclick: () => { state.historyDeleted = false; store.set("historyDeleted", "0"); render(); } }, t("restore"))));
      return;
    }
    const ch = D.history.changes, trend = D.history.trend;
    const fixed = ch.resolved_findings.length;
    const verdict = ch.score_change > 0 ? (fixed === 1 ? t("bravoOne") : t("bravo", { n: fixed })) : ch.score_change < 0 ? t("worse") : t("same");

    const compare = h("div", { class: "suggest" },
      h("div", { class: "compare" },
        h("div", { class: "compare-col" }, h("strong", { text: t("before") }), ring(ch.score_before, true), bandPill(ch.score_before)),
        h("div", { class: "compare-arrow", "aria-hidden": "true", text: "→" }),
        h("div", { class: "compare-col" }, h("strong", { text: t("now") }), ring(ch.score_after, true), bandPill(ch.score_after))),
      h("p", { class: "verdict", text: verdict }),
      h("h3", { style: "margin-top:1.5rem", text: t("events") }),
      timeline(ch, trend));

    const chartCard = h("div", { class: "suggest" }, h("h3", { text: t("chartTitle") }), chart(trend),
      h("table", { class: "data" },
        h("thead", null, h("tr", null, ["colScan", "colScore", "colFindings"].map((k) => h("th", { scope: "col", text: t(k) })))),
        h("tbody", null, trend.map((r, i) => h("tr", null,
          h("td", { text: i === 0 ? t("before") : i === trend.length - 1 ? t("now") : "#" + r.scan_id }),
          h("td", null, `${r.network_score} `, bandPill(r.network_score)),
          h("td", { text: String(r.findings) }))))),
      techBox(h("p", { class: "mono", text: `${ch.before_file} → ${ch.after_file}` })));

    root.append(h("div", { class: "two" }, compare, chartCard));

    const del = h("div", { class: "suggest", style: "margin-top:20px" },
      h("h3", { text: t("deleteTitle") }), h("p", { class: "muted", text: t("deleteSub") }),
      h("button", { type: "button", class: "btn btn-danger", onclick: () => { state.confirmDelete = true; render(); focusSel(".confirm button"); } }, "🗑 " + t("deleteBtn")));
    if (state.confirmDelete) {
      del.append(h("div", { class: "confirm", role: "alertdialog", "aria-label": t("deleteBtn") },
        h("p", { class: "lead", text: t("deleteConfirm") }),
        h("div", { class: "actions" },
          h("button", { type: "button", class: "btn btn-danger", onclick: () => { state.historyDeleted = true; state.confirmDelete = false; store.set("historyDeleted", "1"); render(); } }, t("deleteYes")),
          h("button", { type: "button", class: "btn", onclick: () => { state.confirmDelete = false; render(); } }, t("deleteNo")))));
    }
    root.append(del);
  }

  function timeline(ch, trend) {
    const ev = (tone, icon, title, sub) => h("li", null, h("span", { class: "t-ico " + tone, "aria-hidden": "true", text: icon }),
      h("div", { class: "t-text" }, h("strong", { text: title }), sub ? h("span", { class: "muted", text: sub }) : null));
    const after = [];
    ch.resolved_findings.forEach((f) => after.push(ev("green", "✅", t("evFixed", { title: simple(f.code).title }), null)));
    ch.secured_ports.forEach((u) => after.push(ev("blue", "🔒", t("evSecured"), t("evSecuredSub", { from: u.from_port, to: u.to_port }))));
    ch.new_findings.forEach((f) => after.push(ev("amber", "⚠️", t("evNew", { title: simple(f.code).title }), null)));
    ch.new_devices.forEach((ip) => after.push(ev("red", "🆕", t("evNewDev"), ip)));
    ch.removed_devices.forEach((ip) => after.push(ev("", "👋", t("evGoneDev"), ip)));
    if (!ch.alerts) after.push(ev("green", "👍", t("evQuiet"), null));
    const first = trend[0];
    return h("div", null,
      h("div", { class: "t-when", text: t("now") }),
      h("ul", { class: "timeline" }, after),
      h("div", { class: "t-when", text: t("before") }),
      h("ul", { class: "timeline" }, ev(bandOf(first.network_score) === "red" ? "red" : "amber", BAND_ICON[bandOf(first.network_score)],
        t("evFirst", { s: first.network_score, f: first.findings }), null)));
  }

  function chart(trend) {
    const panelW = document.getElementById("panel-history").clientWidth || 1000;
    const W = Math.round(Math.max(300, Math.min(560, (panelW > 900 ? panelW * 0.46 : panelW) - 56)));
    const H = 250, L = 44, R = 12, TOP = 32, B = 44, innerW = W - L - R, innerH = H - TOP - B;
    const y = (v) => TOP + innerH - (v / 100) * innerH, slot = innerW / trend.length, bw = Math.min(84, slot * 0.55);
    const wrap = h("div", { class: "chart-wrap" });
    const s = svg("svg", { class: "chart", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": t("chartLabel") });
    [0, 50, 80, 100].forEach((v) => {
      s.append(svg("line", { class: "grid-line", x1: L, x2: W - R, y1: y(v), y2: y(v) }));
      const lab = svg("text", { class: "axis-text", x: L - 8, y: y(v) + 5, "text-anchor": "end" }); lab.textContent = String(v); s.append(lab);
    });
    const tip = h("div", { class: "tooltip", hidden: true });
    trend.forEach((r, i) => {
      const cx = L + slot * i + slot / 2, x = cx - bw / 2, top = y(r.network_score), base = y(0), band = bandOf(r.network_score), rr = Math.min(6, (base - top) / 2);
      s.append(svg("path", { class: "bar-" + band, d: `M${x},${base} V${top + rr} Q${x},${top} ${x + rr},${top} H${x + bw - rr} Q${x + bw},${top} ${x + bw},${top + rr} V${base} Z` }));
      const v = svg("text", { class: "value-text", x: cx, y: top - 8, "text-anchor": "middle" }); v.textContent = `${BAND_ICON[band]} ${r.network_score}`; s.append(v);
      const name = i === 0 ? t("before") : i === trend.length - 1 ? t("now") : `#${r.scan_id}`;
      const lab = svg("text", { class: "axis-text", x: cx, y: H - B + 24, "text-anchor": "middle" }); lab.textContent = name; s.append(lab);
      const label = `${name}: ${r.network_score} ${t("scoreOf")}, ${t("band_" + band)}`;
      const hit = svg("rect", { class: "hit", x: cx - slot / 2, y: TOP - 24, width: slot, height: innerH + 24, tabindex: "0", "aria-label": label });
      const show = () => { tip.textContent = label; tip.hidden = false; const k = s.getBoundingClientRect().width / W; tip.style.left = cx * k + "px"; tip.style.top = top * k + "px"; };
      hit.addEventListener("mouseenter", show); hit.addEventListener("focus", show);
      hit.addEventListener("mouseleave", () => { tip.hidden = true; }); hit.addEventListener("blur", () => { tip.hidden = true; });
      s.append(hit);
    });
    wrap.append(s, tip);
    return wrap;
  }

  // ---------------------------------------------------------------- ASK (grounded chat, NFR-06 / FR-12)
  const RX_IP = /\b(?:\d{1,3}\.){3}\d{1,3}\b/g;
  const RX_CVE = /\bCVE-\d{4}-\d{3,}\b/gi;
  const RX_PORTS = [/(?:\bport(?:ul|urile|uri|s)?|\bușa|\bdoor)\s+(\d{1,5})\b/gi, /\b(\d{1,5})\s*\/\s*(?:tcp|udp)\b/gi, /(?:\d{1,3}\.){3}\d{1,3}:(\d{1,5})\b/g];
  function check(sentence, s) {
    if (!sentence.cites || !sentence.cites.length) return { ok: false, reason: t("rNoCite") };
    const citedIps = new Set(sentence.cites.includes("scan") ? s.devices.map((d) => d.ip) : sentence.cites.map((c) => c.split(":")[0]));
    const devices = s.devices.filter((d) => citedIps.has(d.ip));
    for (const ip of sentence.text.match(RX_IP) || []) if (!citedIps.has(ip) || !deviceByIp(s, ip)) return { ok: false, reason: t("rIp", { ip }) };
    for (const rx of RX_PORTS) for (const m of sentence.text.matchAll(rx)) {
      const port = Number(m[1]);
      if (!devices.some((d) => d.open_ports.some((p) => p.port === port))) return { ok: false, reason: t("rPort", { port, ip: devices.map((d) => d.ip).join(", ") || "?" }) };
    }
    const evidence = s.findings.map((f) => f.evidence).join(" ").toUpperCase();
    for (const cve of sentence.text.match(RX_CVE) || []) if (!evidence.includes(cve.toUpperCase())) return { ok: false, reason: t("rCve", { cve }) };
    return { ok: true };
  }
  function answer(kind, s) {
    const out = [];
    if (kind === "first") {
      const q = queue(s);
      if (!q.length) return [{ text: t("aClean"), cites: ["scan"] }];
      const f = q[0], tx = simple(f.code), c = where(f);
      out.push({ text: t("aFirst1", { name: deviceName(deviceByIp(s, f.ip)) }), cites: [f.ip] });
      out.push({ text: t("aFirst2", { title: tx.title }), cites: [c] });
      if (tx.steps[0]) out.push({ text: t("aFirst3", { step: tx.steps[0] }), cites: [c] });
    } else if (kind === "devices") {
      out.push({ text: t("aDevCount", { n: s.devices.length }), cites: ["scan"] });
      s.devices.forEach((d) => out.push({ text: t("aDev", { name: deviceName(d) }), cites: [d.ip] }));
    } else if (kind === "printer") {
      const f = s.findings.find((x) => x.code === "PRINTER_RAW_EXPOSED" && x.port === 9100);
      if (!f) return [{ text: t("aPrinterNo"), cites: ["scan"] }];
      out.push({ text: t("aPrinterYes"), cites: [`${f.ip}:9100`] });
      const st = simple(f.code).steps[0];
      if (st) out.push({ text: t("aPrinterFix", { step: st }), cites: [`${f.ip}:9100`] });
    } else return [{ text: t("noAnswer"), cites: ["scan"] }];
    if (state.hallucinate) {
      const router = s.devices.find((d) => d.type === "router") || s.devices[0];
      if (router) {
        const port = [23, 2323, 3389, 5900].find((p) => !router.open_ports.some((x) => x.port === p));
        out.splice(1, 0, { text: t("hall", { port }), cites: [router.ip] });
      }
    }
    return out;
  }
  function classify(q) {
    const s = q.toLowerCase();
    if (/(repar|primul|prima|întâi|intai|fix|first|start)/.test(s)) return "first";
    if (/(imprimant|printer|9100)/.test(s)) return "printer";
    if (/(aparat|dispozitiv|device|ce am|what do i have|conectat|connected)/.test(s)) return "devices";
    return "unknown";
  }
  function renderAsk(root) {
    const s = scan();
    root.append(pageHead(t("askTitle"), t("askSub")));
    if (s.error) { root.append(errorBox(s)); return; }
    const card = h("div", { class: "suggest chat" });
    card.append(h("div", { class: "bot-name", text: "🤖 " + t("botName") }), h("div", { class: "bubble bot", text: t("botHello") }));
    state.chat.forEach((m) => {
      card.append(h("div", { class: "bubble me", text: m.text }));
      const res = answer(m.kind, s).map((x) => ({ x, r: check(x, s) }));
      card.append(h("div", { class: "bot-name", text: "🤖 " + t("botName") }));
      res.forEach(({ x, r }) => card.append(h("div", { class: "bubble bot" + (r.ok ? "" : " blocked") },
        h("span", { class: "txt", text: x.text }),
        x.cites.filter((c) => c !== "scan").map((c) => h("span", { class: "proof", title: t("proof") }, h("span", { "aria-hidden": "true", text: "🔎" }), h("span", { class: "sr", text: t("proof") + ": " }), c)),
        r.ok ? null : h("span", { class: "why" }, h("span", { "aria-hidden": "true", text: "✂️ " }), t("blocked", { r: r.reason })))));
      const bad = res.filter((z) => !z.r.ok).length;
      card.append(h("div", { class: "muted", style: "margin-left:6px", text: t("verified", { ok: res.length - bad, bad }) }));
    });
    const ask = (kind, text) => { state.chat.push({ kind, text }); if (state.chat.length > 4) state.chat.shift(); render(); focusSel("#ask-input"); };
    card.append(h("div", { class: "chips", style: "margin-top:.5rem" },
      [["first", "q1"], ["devices", "q2"], ["printer", "q3"]].map(([k, key]) => h("button", { type: "button", class: "chip-btn", onclick: () => ask(k, t(key)) }, "💬 " + t(key)))));
    const input = h("input", { type: "text", id: "ask-input", placeholder: t("askPlaceholder"), maxlength: "200", "aria-label": t("askLabel") });
    card.append(h("form", { class: "composer", onsubmit: (e) => { e.preventDefault(); const q = input.value.trim(); if (q) ask(classify(q), q); } },
      input, h("button", { type: "submit", class: "btn btn-filled" }, t("askBtn"), h("span", { "aria-hidden": "true", text: " ➤" }))));
    card.append(h("details", { class: "tech", open: state.hallucinate }, h("summary", null, h("span", { "aria-hidden": "true", text: "🎤" }), t("hallToggle")),
      h("div", null,
        h("label", { class: "switch" }, h("input", { type: "checkbox", checked: state.hallucinate,
          onchange: (e) => { state.hallucinate = e.target.checked; render(); focusSel(".switch input"); } }), t("hallSwitch")),
        h("p", { class: "muted", text: t("demoNote") }))));
    root.append(card);
  }

  // ---------------------------------------------------------------- shell
  const RENDER = { home: renderHome, devices: renderDevices, findings: renderFindings, history: renderHistory, ask: renderAsk };
  function setTab(name) {
    state.tab = name;
    TABS.forEach((n) => { document.getElementById("panel-" + n).hidden = n !== name; });
    document.querySelectorAll(".nav-item").forEach((b) => { if (b.dataset.tab === name) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current"); });
    render();
    window.scrollTo({ top: 0 });
  }
  function render() {
    document.documentElement.lang = state.lang;
    document.documentElement.style.fontSize = SIZES[state.size];
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.getElementById("lang-ro").setAttribute("aria-pressed", String(state.lang === "ro"));
    document.getElementById("lang-en").setAttribute("aria-pressed", String(state.lang === "en"));
    [0, 1, 2].forEach((i) => document.getElementById("size-" + i).setAttribute("aria-pressed", String(state.size === i)));
    document.getElementById("size-group").setAttribute("aria-label", state.lang === "en" ? "Text size" : "Mărimea textului");
    const sel = document.getElementById("scan-select");
    sel.setAttribute("aria-label", t("scanFile"));
    sel.replaceChildren(...D.scans.map((s, i) => h("option", { value: String(i), selected: i === state.scan }, s.error ? `${s.file} — ❌` : `${s.file} — ${s.score}/100`)));
    const panel = document.getElementById("panel-" + state.tab);
    panel.replaceChildren();
    RENDER[state.tab](panel);
  }

  document.getElementById("scan-select").addEventListener("change", (e) => { state.scan = Number(e.target.value); state.chat = []; render(); });
  ["ro", "en"].forEach((l) => document.getElementById("lang-" + l).addEventListener("click", () => { state.lang = l; store.set("lang", l); render(); }));
  [0, 1, 2].forEach((i) => document.getElementById("size-" + i).addEventListener("click", () => { state.size = i; store.set("size", String(i)); render(); }));
  document.querySelectorAll(".nav-item").forEach((b) => b.addEventListener("click", () => { setTab(b.dataset.tab); document.getElementById("main").focus({ preventScroll: true }); }));
  const dlg = document.getElementById("sheet");
  document.getElementById("sheet-close").addEventListener("click", closeSheet);
  dlg.addEventListener("close", () => { if (lastOpener && document.body.contains(lastOpener)) lastOpener.focus(); });
  dlg.addEventListener("click", (e) => { if (e.target === dlg) closeSheet(); });   // tap outside the sheet

  // Deep links for the pitch: #ask?q=first&hall=1, #home?lang=en&scan=V3_small_office.xml, #history?theme=light&size=2, #devices?open=192.168.1.40
  (function applyHash() {
    const [tab, query] = location.hash.slice(1).split("?");
    const p = new URLSearchParams(query || "");
    if (p.get("lang") === "en" || p.get("lang") === "ro") state.lang = p.get("lang");
    if (["0", "1", "2"].includes(p.get("size"))) state.size = Number(p.get("size"));
    const i = D.scans.findIndex((s) => s.file === p.get("scan"));
    if (i >= 0) state.scan = i;
    if (p.get("hall") === "1") state.hallucinate = true;
    if (p.get("inspect") === "1") state.inspected[scan().file] = true;
    if (p.get("theme") === "light" || p.get("theme") === "dark") document.documentElement.dataset.theme = p.get("theme");
    const q = { first: "q1", devices: "q2", printer: "q3" }[p.get("q")];
    if (q) state.chat = [{ kind: p.get("q"), text: t(q) }];
    setTab(TABS.includes(tab) ? tab : "home");
    if (p.get("state")) applyHouseState(p.get("state"));
    const open = p.get("open");
    if (open && !scan().error) { const d = deviceByIp(scan(), open); if (d) openDevice(d); }
  })();

  // SafeHouse.setState("safe" | "vulnerable" | "idle" | "scanning" | "error") and SafeHouse.inspect()
  window.SafeHouse = {
    setState(st) { if (state.tab !== "home") setTab("home"); return applyHouseState(st); },
    inspect() { if (state.tab !== "home") setTab("home"); inspect(); },
  };

  let resizeTimer = null;
  window.addEventListener("resize", () => { if (state.tab !== "history") return; clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 150); });
})();

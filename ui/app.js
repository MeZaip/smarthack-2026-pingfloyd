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
  // LIVE: the page is served by the local agent (netcheck app / serve): real scans from this computer's
  // history, a real check of the network, the AI assistant and "I fixed it - check". Otherwise it is the
  // offline demo built by tools/export_ui_data.py and everything works as a prototype.
  const LIVE = !!D.live;

  // ---------------------------------------------------------------- words (RO / EN, ~12-year-old level)
  const T = {
    ro: {
      skip: "Sari la conținut", close: "Închide", scanFile: "Verificarea afișată",
      navHome: "Acasă", navDevices: "Aparate", navResults: "Rezultate", navFindings: "Reparații", navHistory: "Istoric", navAsk: "Întreabă",
      footer: "Verificările tale rămân pe acest calculator. Adresele aparatelor sunt ascunse parțial, pentru intimitatea ta.",
      hello: "Bună!", helloSub: "Apasă butonul și verificăm împreună dacă rețeaua din casa ta e sigură.",
      inspect: "Inspectează casa", inspectAgain: "Inspectează din nou",
      topoCore: "Casa ta", topoGateway: "Poarta spre internet", topoHint: "Apasă pe un aparat ca să vezi detaliile.",
      topoNet: "Rețea", topoWhy: "Ce înseamnă", closeEsc: "Închide (Esc)", portOpen: "Deschis", portVuln: "Vulnerabil", portSecure: "criptat",
      netTitle: "Rețeaua ta ({n} aparate)", netSub: "{n} aparate au uși deschise. Începe cu cel mai periculos sau apasă pe orice aparat.", netSub1: "Un aparat are uși deschise. Începe cu el sau apasă pe orice aparat.",
      topoMore: "+{n} mai multe", fixNow: "Repară acum", moreProbs: "+{n} alte probleme", moreProb1: "+1 altă problemă", devDetails: "Vezi detalii", topoBack: "Toată rețeaua", topoShow: "Filtrează după risc", topoSearch: "Caută IP sau nume", topoResults: "{n} rezultate", topoResult1: "Un rezultat", topoNoResults: "Niciun aparat găsit",
      topoStart: "Începe cu cel mai periculos", topoPrev: "Aparatul anterior", topoNext: "Următorul", topoFound: "Ce am găsit",
      tourStep: "Aparatul {i} din {n}", tourPort: "port {p}", tourFirst: "Primul pas",
      tourEndT: "Ai parcurs tot traseul", tourEndS1: "Un aparat are uși deschise. Reparațiile, pas cu pas:", tourEndS: "{n} aparate au uși deschise. Reparațiile, pas cu pas:",
      stIdleT: "Casa ta digitală", stIdleS: "Apasă „Inspectează casa” ca să verificăm fiecare ușă.",
      stScanT: "Inspectez casa…", stScanS: "Verific fiecare aparat și fiecare ușă. Durează câteva secunde.",
      stSafeT: "Casa este sigură", stSafeS: "Toate ușile sunt închise. Nu ai nimic de reparat.",
      stVulnT: "Atenție: o ușă e deschisă", stVulnS: "Am găsit {n} lucruri de reparat. Mai jos vezi ce poți face.", stVulnS1: "Am găsit un lucru de reparat. Mai jos vezi ce poți face.",
      stErrT: "Nu am putut citi verificarea", stErrS: "Fișierul verificării e stricat. Alege altă verificare din lista de sus.",
      houseLabel: "Casă 3D într-o grădină. Când o verificăm, o lumină trece peste ea, iar la final ferestrele se aprind.", errorWord: "EROARE",
      devicesFound: "Aparate găsite ({n})", ipLabel: "IP", macLabel: "MAC", otherLang: "EN", whatToDo: "Ce poți face",
      doorsOpen: "Uși lăsate deschise ({n})", doorsSub: "Fiecare card spune ce s-a întâmplat și ce faci, pas cu pas. Cel mai periculos e primul.",
      doorsNone: "Nicio ușă lăsată deschisă. Toate aparatele tale sunt în siguranță.",
      devicesSub2: "Toate aparatele conectate la rețeaua ta. Apasă pe un aparat ca să vezi ce poți face.",
      trendUp: "Scorul a crescut cu {pts}", trendDown: "Scorul a scăzut cu {pts}",
      trendSame: "Scorul a rămas la fel ca data trecută", trendFirst: "Prima verificare salvată pentru această rețea",
      trendNone: "Încă nu avem o verificare anterioară, ca să comparăm scorul",
      newDev1: "1 aparat nou", newDevN: "{n} aparate noi", newDev0: "Niciun aparat nou",
      delHistory: "Șterge istoricul", delHistoryAsk: "Ștergi toate verificările salvate pe acest calculator? Nu le mai poți aduce înapoi.",
      histGone: "Istoricul a fost șters de pe acest calculator.",
      startHere: "Începe de aici", scoreTitle: "Scorul casei tale", scorePending: "Apasă butonul ca să verificăm casa și să afli scorul.",
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
      progress: "Reparația {i} din {n}",
      doneNote: "Bravo! Ai rezolvat: {title}. Verifică din nou rețeaua mai târziu ca să vezi scorul nou.",
      allDone: "Ai trecut prin toate. Verifică din nou rețeaua ca să vezi cât de sigură e acum.",
      restart: "Ia-o de la capăt",
      noProblems: "Nu am găsit nimic de reparat. Felicitări! Verifică din nou din când în când.",
      helpNote: "Dacă ești copil, arată pagina unui părinte înainte să schimbi ceva. Dacă ți se pare greu, cere ajutorul cuiva de încredere.",
      yourDevices: "Aparatele tale", seeAll: "Vezi toate",
      glossaryTitle: "Cuvinte utile",
      devicesTitle: "Aparate și reparații", devicesSub: "Toate aparatele din rețeaua ta, cel mai periculos primul. Apasă pe un aparat ca să vezi ce problemă are și cum o repari, pas cu pas.",
      fAll: "Toate ({n})", fProblems: "Cu probleme ({n})", fSafe: "Sigure ({n})",
      devOk: "Sigur", devProblems: "{n} lucruri de reparat", devProblem: "Un lucru de reparat",
      devOkExplain: "Nu am găsit nicio problemă la acest aparat. Ușile lui sunt bine încuiate.",
      devOkSteps: ["Instalează actualizările când aparatul ți le cere.", "Folosește o parolă lungă, pe care n-o mai ai în altă parte."],
      keepSafe: "Ca să rămână sigur",
      otherProblems: "Alte lucruri de reparat la acest aparat", problemN: "Problema {i} din {n}", justKnow: "Doar de știut",
      findingsTitle: "Ce trebuie reparat", findingsSub: "Verificarea de securitate, de la cel mai periculos la cel mai puțin periculos. Fiecare card îți spune ce faci, pas cu pas.",
      sumHigh: "Risc înalt", sumMedium: "Risc mediu", sumLow: "Risc mic", sumInfo: "Doar de știut",
      cardHint: "Apasă Enter ca să vezi detaliile tehnice.",
      codeLabel: "Cod",
      techMore: "Detalii avansate",
      techTitle: "Numele tehnic", techSteps: "Pași detaliați", techWhere: "Unde",
      evidence: "Ce a văzut verificarea", refs: "Standarde de securitate",
      ip: "Adresă IP", mac: "Adresă MAC", vendor: "Producător", hostname: "Nume în rețea",
      ports: "Porturi deschise", none: "niciunul", unknown: "necunoscut",
      errorTitle: "Nu am putut citi această verificare",
      errorBody: "Fișierul verificării este stricat sau incomplet, așa că nu arătăm nimic pentru el. Alege altă verificare din lista de sus sau fă una nouă.",
      errorDetail: "Detaliu tehnic",
      historyTitle: "A devenit rețeaua mai sigură?", historySub: "Verificările salvate pe acest calculator, înainte și după ce ai reparat lucrurile.",
      before: "Înainte", now: "Acum",
      bravo: "Bravo! Ai reparat {n} lucruri.", bravoOne: "Bravo! Ai reparat un lucru.",
      worse: "Atenție: scorul a scăzut. Uită-te la lucrurile noi de reparat.", same: "Scorul a rămas la fel.",
      events: "Ce s-a întâmplat",
      evFixed: "Ai reparat: {title}", evNew: "Lucru nou de reparat: {title}",
      evSecured: "Pagina de setări folosește acum legătura sigură", evSecuredSub: "Ușa {from} a fost înlocuită cu ușa sigură {to}",
      evNewDev: "Aparat nou în rețea", evGoneDev: "Un aparat nu mai e în rețea",
      evQuiet: "Niciun aparat nou și nicio ușă nouă periculoasă",
      evFirst: "Verificarea de dinainte: scor {s}, {f} lucruri de reparat",
      chartTitle: "Scorul la fiecare verificare", chartLabel: "Grafic cu scorul la fiecare verificare salvată",
      colScan: "Verificare", colScore: "Scor", colFindings: "De reparat",
      cyLog: "Jurnal de sistem", cyDevices: "Aparate", cyCompare: "Scorul casei", cyWhen: "Verificarea",
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
      blocked: "Am tăiat-o: {r}.",
      rPort: "ușa {port} nu e deschisă pe {ip} în această verificare", rIp: "adresa {ip} nu apare în dovezi",
      rCve: "{cve} nu apare în verificare", rNoCite: "nu are nicio dovadă din verificare",
      verified: "{ok} propoziții verificate, {bad} tăiate",
      aFirst1: "Cea mai mare problemă este la: {name}.", aFirst2: "Începe cu asta: {title}.", aFirst3: "Primul pas: {step}",
      aDevCount: "Am găsit {n} aparate conectate la rețeaua ta.", aDev: "{name}.",
      aPrinterYes: "Da, puțin: oricine din rețea poate trimite documente la imprimanta ta, prin ușa 9100.",
      aPrinterFix: "Ce poți face: {step}", aPrinterNo: "Verificarea nu-mi arată o imprimantă cu problema asta.",
      aClean: "Verificarea nu arată nimic de reparat. Totul e bine!",
      // live app (local agent)
      noScan: "Încă nu ai verificat casa", needScan: "Încă nu avem nicio verificare. Verifică acum rețeaua la care ești conectat sau încarcă o verificare.", goHome: "Mergi la Acasă", scanNow: "Verifică rețeaua acum",
      cfTitle: "Verificăm rețeaua ta?", cfNet: "Ești conectat la:", cfAsk: "Este rețeaua ta, de acasă sau a echipei? Verificăm doar rețeaua la care ești conectat acum.",
      cfYes: "Da, e rețeaua mea", cfNo: "Nu, renunț", cfPrep: "Mă pregătesc…",
      cfPerm: "Calculatorul îți va cere permisiunea. Apasă „Da”: o primește doar programul de verificare, Nmap, și doar pentru această verificare.",
      scanElapsed: "A trecut {t}. De obicei durează 1–3 minute.",
      probT: "Verificarea nu s-a putut face", tryAgain: "Încearcă din nou",
      nmapT: "Lipsește programul de verificare", nmapLink: "Deschide pagina de descărcare Nmap",
      upload: "Încarcă o verificare", uploading: "Se încarcă…", uploadBad: "Fișierul nu poate fi citit: e stricat sau nu e o verificare Nmap.",
      verifyBtn: "Am reparat, verifică", verifying: "Verific…",
      histNeedTwo: "Avem o singură verificare. Repară un lucru, apoi apasă din nou „Inspectează casa” ca să vedem dacă rețeaua a devenit mai sigură.",
      thinking: "Mă gândesc…", newChat: "Conversație nouă",
      mode_ai: "Răspuns scris de inteligența artificială, doar din ce a văzut verificarea.",
      mode_offline: "Asistentul online nu e disponibil acum, așa că îți răspund din textele noastre.",
      mode_rejected: "Răspunsul inteligenței artificiale nu a trecut verificarea, așa că îți arăt textele noastre.",
      closeApp: "Închide aplicația", closedApp: "Aplicația s-a închis. Poți închide această fereastră.",
      thisPc: "acest calculator", connErr: "Nu pot vorbi cu aplicația. Reîncarcă pagina și încearcă din nou.", oldApp: "Aplicația care rulează e mai veche decât această pagină. Închide SafeHouse și pornește-l din nou.",
      askSubLive: "Îți răspund scurt, doar pe baza verificării afișate sus. Trimit întrebarea și un rezumat al verificării, fără să păstrăm nimic.",
      resTitle: "Toate verificările", resSub: "Fiecare verificare salvată pe acest calculator, cu scorul și cât de sigură e rețeaua. Apasă pe un rând ca să vezi tot ce a găsit.",
      colNo: "Nr.", colWhen: "Verificare", colFile: "Fișier", colRating: "Siguranță", colDevices: "Aparate", colProblems: "Probleme",
      resFindings: "Ce a găsit verificarea", colIp: "Adresă IP", colPort: "Port", colCode: "Cod", colSeverity: "Gravitate",
      colProblem: "Problema", colDevice: "Aparat", resNone: "Verificarea nu a găsit nimic de reparat.", resOpen: "Arată pe Acasă", techReport: "Raport tehnic", guideBtn: "Pași exacți pentru {v}", guideWait: "Caut pe site-ul {v} pașii pentru aparatul tău…", guideT: "Pași pentru {v}", guideNote: "Găsiți de asistent pe site-ul oficial {v}. Meniurile pot diferi puțin de la un model la altul.", guideNoteWeb: "Găsiți de asistent pe internet, pentru că nu avem site-ul oficial {v} în listă. Verifică sursele de mai sus înainte să schimbi ceva.", guideSrc: "Sursa", guideNone: "Asistentul nu a dat surse, așa că urmează pașii cu grijă.", techReporting: "Pregătesc raportul tehnic…", techReportDoneT: "Gata, raportul tehnic e descărcat", techReportDone: "Un fișier text cu toate aparatele, porturile, versiunile și problemele găsite, pe care îl poți trimite unui specialist IT.", techReportWhere: "L-am salvat și aici:",
      resNoDetail: "Detaliile acestei verificări vechi nu mai apar aici. Exportă CSV-ul ca să le vezi.",
      resDelete: "Șterge toate datele", resDeleteAsk: "Ștergi toate verificările și rezultatele salvate pe acest calculator? Nu le mai poți aduce înapoi. Fișierele CSV și rapoartele tehnice exportate deja rămân.",
      exportBtn: "Exportă CSV", exportT: "Exportă rezultatele în CSV",
      exportS: "Fac cele două fișiere standard, findings.csv și scores.csv, pentru un folder întreg de verificări Nmap (.xml). Un fișier care nu poate fi citit primește ERROR.",
      exportFolder: "Alege un folder", exportFiles: "Alege fișiere", exportSaved: "Exportă verificările salvate ({n})",
      exporting: "Pregătesc fișierele…", exportDoneT: "Gata, fișierele CSV sunt descărcate",
      exportDone: "{f} fișiere analizate, {e} cu ERROR, {k} probleme găsite.", exportWhere: "Le-am salvat și aici:",
      exportSkipped: "Am sărit {n} fișiere care nu sunt .xml.", exportNone: "Nu am găsit fișiere .xml în ce ai ales.",
      guardT: "Paznicul casei", guardOffS: "Te anunț imediat ce se conectează la Wi-Fi-ul tău un aparat pe care nu-l cunosc.",
      guardStart: "Pornește paznicul", guardStop: "Oprește paznicul",
      guardLearning: "Caut aparatele din rețea…", guardWaiting: "Aștept să se termine verificarea casei…", guardMoved: "M-am oprit pentru că ai schimbat rețeaua. Pornește-mă din nou când ești pe rețeaua ta.", gdNet: "Rețeaua păzită", gdTimes: "Ultima trecere", gdKnown: "cunoscute", gOff: "oprit", guardOffShort: "Te anunț când apare un aparat nou.", gStart: "Pornește", gsMoved: "Oprit: ai schimbat rețeaua.", gsWaiting: "Aștept verificarea casei…", gsLearning: "Caut aparatele…", gsPaused: "Pauză: nu ești pe nicio rețea.", gsError: "Nu văd rețeaua acum.", gsEmpty: "Nu văd alte aparate.", gsWatching: "{n} aparate · {ago}", gDetails: "Detalii", gNothing: "Încă n-am văzut nimic nou. Te anunț imediat ce apare ceva.", gForget: "Uită toate aparatele", gDevices: "Aparatele din rețeaua ta ({n})", gDevicesS: "„Uită” îl scoate din listă: dacă e încă conectat, te anunț din nou. Ca să scoți un străin din rețea, schimbă parola Wi-Fi.", gOnline: "acum în rețea", gSeen: "văzut {ago}", gForgetOne: "Uită", gdNow: "acum", gdHow: "Cum caut aparatele", gdSeen: "Aparate văzute", gdErr: "Mesaj de la Nmap",
      guardEmpty: "Nu văd niciun alt aparat în rețea. Dacă știi că sunt aparate conectate, acest calculator nu poate citi lista lor.", guardWatching: "Păzesc rețeaua · {n} aparate cunoscute · m-am uitat {ago}",
      guardWatching0: "Păzesc rețeaua · m-am uitat {ago}", guardPaused: "Pauză: nu ești conectat la nicio rețea acum.",
      guardError: "Paznicul nu poate vedea rețeaua acum. Mai încerc.", guardAskT: "Pornim paznicul?",
      guardAsk: "La fiecare {s} secunde mă uit cine e conectat la rețeaua ta. Doar la rețeaua la care ești conectat acum și fără drepturi de administrator.",
      guardAsk2: "Este rețeaua ta?", guardYes: "Da, păzește-o",
      agoNow: "chiar acum", agoS: "acum {n} secunde", agoM: "acum {n} minute", agoM1: "acum un minut",
      gNewDevT: "Aparat nou în Wi-Fi-ul tău", gPrivate: "Telefon sau laptop (adresă privată)", gUnknownDev: "Aparat necunoscut",
      gKnow: "Îl cunoști?", gMine: "E al meu", gStranger: "Nu-l cunosc",
      gWasMine: "e al tău", gWasStranger: "nu-l cunoști", gRecent: "Ce a văzut paznicul",
      gStrangerT: "Un aparat pe care nu-l cunoști", gStrangerS: "S-ar putea să fie al unui vecin sau al cuiva care îți folosește Wi-Fi-ul. Iată ce faci:",
    },
    en: {
      skip: "Skip to content", close: "Close", scanFile: "Check shown",
      navHome: "Home", navDevices: "Devices", navResults: "Results", navFindings: "Fixes", navHistory: "History", navAsk: "Ask",
      footer: "Your checks stay on this computer. Device addresses are partly hidden, for your privacy.",
      hello: "Hi!", helloSub: "Press the button and we will check together if the network in your home is safe.",
      inspect: "Inspect the house", inspectAgain: "Inspect again",
      topoCore: "Your home", topoGateway: "Gateway to the internet", topoHint: "Tap a device to see its details.",
      topoNet: "Network", topoWhy: "What it means", closeEsc: "Close (Esc)", portOpen: "Open", portVuln: "Vulnerable", portSecure: "encrypted",
      netTitle: "Your network ({n} devices)", netSub: "{n} devices have open doors. Start with the most dangerous one or tap any device.", netSub1: "One device has open doors. Start with it or tap any device.",
      topoMore: "+{n} more", fixNow: "Fix it now", moreProbs: "+{n} more problems", moreProb1: "+1 more problem", devDetails: "See details", topoBack: "Whole network", topoShow: "Filter by risk", topoSearch: "Search IP or name", topoResults: "{n} results", topoResult1: "One result", topoNoResults: "No device found",
      topoStart: "Start with the most dangerous", topoPrev: "Previous device", topoNext: "Next", topoFound: "What we found",
      tourStep: "Device {i} of {n}", tourPort: "port {p}", tourFirst: "First step",
      tourEndT: "That's the whole path", tourEndS1: "One device has open doors. The fixes, step by step:", tourEndS: "{n} devices have open doors. The fixes, step by step:",
      stIdleT: "Your digital home", stIdleS: "Press “Inspect the house” so we can check every door.",
      stScanT: "Inspecting the house…", stScanS: "Checking every device and every door. It takes a few seconds.",
      stSafeT: "The house is safe", stSafeS: "All doors are closed. You have nothing to fix.",
      stVulnT: "Warning: a door is open", stVulnS: "We found {n} things to fix. See below what you can do.", stVulnS1: "We found one thing to fix. See below what you can do.",
      stErrT: "We could not read the check", stErrS: "The check file is broken. Pick another check from the list at the top.",
      houseLabel: "3D house in a garden. When we check it, a light passes over it and at the end the windows light up.", errorWord: "ERROR",
      devicesFound: "Devices found ({n})", ipLabel: "IP", macLabel: "MAC", otherLang: "RO", whatToDo: "What you can do",
      doorsOpen: "Doors left open ({n})", doorsSub: "Each card says what is wrong and what to do, step by step. The most dangerous one comes first.",
      doorsNone: "No door left open. All your devices are safe.",
      devicesSub2: "All the devices connected to your network. Tap a device to see what you can do.",
      trendUp: "Score improved by {pts}", trendDown: "Score dropped by {pts}",
      trendSame: "Score is the same as last time", trendFirst: "First saved check for this network",
      trendNone: "No earlier check yet to compare the score with",
      newDev1: "1 new device", newDevN: "{n} new devices", newDev0: "No new devices",
      delHistory: "Delete history", delHistoryAsk: "Delete all checks saved on this computer? You cannot get them back.",
      histGone: "History was deleted from this computer.",
      startHere: "Start here", scoreTitle: "Your home's score", scorePending: "Press the button so we can check the house and show your score.",
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
      progress: "Fix {i} of {n}",
      doneNote: "Well done! You fixed: {title}. Check the network again later to see the new score.",
      allDone: "You went through everything. Check the network again to see how safe it is now.",
      restart: "Start again",
      noProblems: "We found nothing to fix. Congratulations! Check again from time to time.",
      helpNote: "If you are a child, show this page to a parent before you change anything. If it feels hard, ask someone you trust for help.",
      yourDevices: "Your devices", seeAll: "See all",
      glossaryTitle: "Useful words",
      devicesTitle: "Devices and fixes", devicesSub: "Every device on your network, the most dangerous first. Tap a device to see its problem and how to fix it, step by step.",
      fAll: "All ({n})", fProblems: "With problems ({n})", fSafe: "Safe ({n})",
      devOk: "Safe", devProblems: "{n} things to fix", devProblem: "One thing to fix",
      devOkExplain: "We found no problem on this device. Its doors are locked well.",
      devOkSteps: ["Install updates when the device asks you to.", "Use a long password that you do not use anywhere else."],
      keepSafe: "To keep it safe",
      otherProblems: "Other things to fix on this device", problemN: "Problem {i} of {n}", justKnow: "Just so you know",
      findingsTitle: "What needs fixing", findingsSub: "The security check, from most to least dangerous. Each card tells you what to do, step by step.",
      sumHigh: "High risk", sumMedium: "Medium risk", sumLow: "Low risk", sumInfo: "Just so you know",
      cardHint: "Press Enter to see the technical details.",
      codeLabel: "Code",
      techMore: "Advanced details",
      techTitle: "Technical name", techSteps: "Detailed steps", techWhere: "Where",
      evidence: "What the check saw", refs: "Security standards",
      ip: "IP address", mac: "MAC address", vendor: "Maker", hostname: "Network name",
      ports: "Open ports", none: "none", unknown: "unknown",
      errorTitle: "We could not read this check",
      errorBody: "The check file is broken or incomplete, so we show nothing for it. Pick another check from the list at the top or make a new one.",
      errorDetail: "Technical detail",
      historyTitle: "Has the network become safer?", historySub: "The checks saved on this computer, before and after you fixed things.",
      before: "Before", now: "Now",
      bravo: "Well done! You fixed {n} things.", bravoOne: "Well done! You fixed one thing.",
      worse: "Careful: the score went down. Look at the new things to fix.", same: "The score stayed the same.",
      events: "What happened",
      evFixed: "You fixed: {title}", evNew: "New thing to fix: {title}",
      evSecured: "The settings page now uses the secure connection", evSecuredSub: "Door {from} was replaced by the secure door {to}",
      evNewDev: "New device on the network", evGoneDev: "A device is no longer on the network",
      evQuiet: "No new device and no dangerous new door",
      evFirst: "The check before: score {s}, {f} things to fix",
      chartTitle: "The score at each check", chartLabel: "Chart of the score at each saved check",
      colScan: "Check", colScore: "Score", colFindings: "To fix",
      cyLog: "System log", cyDevices: "Devices", cyCompare: "Home score", cyWhen: "Check",
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
      blocked: "Crossed out: {r}.",
      rPort: "door {port} is not open on {ip} in this check", rIp: "address {ip} is not in the proof",
      rCve: "{cve} is not in the check", rNoCite: "it has no proof from the check",
      verified: "{ok} sentences checked, {bad} crossed out",
      aFirst1: "The biggest problem is on: {name}.", aFirst2: "Start with this: {title}.", aFirst3: "First step: {step}",
      aDevCount: "We found {n} devices connected to your network.", aDev: "{name}.",
      aPrinterYes: "A little: anyone on the network can send documents to your printer, through door 9100.",
      aPrinterFix: "What you can do: {step}", aPrinterNo: "The check does not show me a printer with this problem.",
      aClean: "The check shows nothing to fix. All good!",
      // live app (local agent)
      noScan: "You have not checked the house yet", needScan: "There is no check yet. Check the network you are connected to now, or upload a check.", goHome: "Go to Home", scanNow: "Check my network now",
      cfTitle: "Shall we check your network?", cfNet: "You are connected to:", cfAsk: "Is this your network, at home or your team's? We only check the network you are connected to right now.",
      cfYes: "Yes, it is my network", cfNo: "No, cancel", cfPrep: "Getting ready…",
      cfPerm: "The computer will ask for permission. Press “Yes”: only the checking program, Nmap, gets it, and only for this check.",
      scanElapsed: "{t} so far. It usually takes 1–3 minutes.",
      probT: "The check could not be done", tryAgain: "Try again",
      nmapT: "The checking program is missing", nmapLink: "Open the Nmap download page",
      upload: "Upload a check", uploading: "Uploading…", uploadBad: "The file cannot be read: it is broken or not an Nmap check.",
      verifyBtn: "I fixed it, check", verifying: "Checking…",
      histNeedTwo: "We have only one check. Fix one thing, then press “Inspect the house” again to see if the network got safer.",
      thinking: "Thinking…", newChat: "New conversation",
      mode_ai: "Answer written by artificial intelligence, only from what the check saw.",
      mode_offline: "The online assistant is not available right now, so I answer from our own texts.",
      mode_rejected: "The AI answer did not pass the check, so I show you our own texts.",
      closeApp: "Close the app", closedApp: "The app is closed. You can close this window.",
      thisPc: "this computer", connErr: "I cannot reach the app. Reload the page and try again.", oldApp: "The running app is older than this page. Close SafeHouse and start it again.",
      askSubLive: "I answer briefly, only from the check shown at the top. I send your question and a summary of the check, and we keep nothing.",
      resTitle: "All checks", resSub: "Every check saved on this computer, with its score and how safe the network is. Tap a row to see everything it found.",
      colNo: "No.", colWhen: "Check", colFile: "File", colRating: "Safety", colDevices: "Devices", colProblems: "Problems",
      resFindings: "What the check found", colIp: "IP address", colPort: "Port", colCode: "Code", colSeverity: "Severity",
      colProblem: "Problem", colDevice: "Device", resNone: "The check found nothing to fix.", resOpen: "Show on Home", techReport: "Technical report", guideBtn: "Exact steps for {v}", guideWait: "Looking on the {v} website for the steps for your device…", guideT: "Steps for {v}", guideNote: "Found by the assistant on the official {v} website. Menus can differ a little from model to model.", guideNoteWeb: "Found by the assistant on the web, because the official {v} website is not on our list. Check the sources above before you change anything.", guideSrc: "Source", guideNone: "The assistant gave no sources, so follow the steps carefully.", techReporting: "Preparing the technical report…", techReportDoneT: "Done, the technical report is downloaded", techReportDone: "A text file with every device, port, version and problem found, ready to send to an IT specialist.", techReportWhere: "I also saved it here:",
      resNoDetail: "The details of this older check are not shown here. Export the CSV to see them.",
      resDelete: "Delete all data", resDeleteAsk: "Delete all checks and results saved on this computer? You cannot get them back. CSV files and technical reports you already exported stay.",
      exportBtn: "Export CSV", exportT: "Export the results as CSV",
      exportS: "I make the two standard files, findings.csv and scores.csv, for a whole folder of Nmap checks (.xml). A file that cannot be read gets ERROR.",
      exportFolder: "Choose a folder", exportFiles: "Choose files", exportSaved: "Export the saved checks ({n})",
      exporting: "Preparing the files…", exportDoneT: "Done, the CSV files are downloaded",
      exportDone: "{f} files analysed, {e} with ERROR, {k} problems found.", exportWhere: "I also saved them here:",
      exportSkipped: "I skipped {n} files that are not .xml.", exportNone: "I found no .xml files in what you chose.",
      guardT: "House guard", guardOffS: "I tell you as soon as a device I do not know joins your Wi-Fi.",
      guardStart: "Turn on the guard", guardStop: "Turn off the guard",
      guardLearning: "Looking for the devices on the network…", guardWaiting: "Waiting for the house check to finish…", guardMoved: "I stopped because you changed networks. Turn me on again when you are on your own network.", gdNet: "Guarded network", gdTimes: "Last look", gdKnown: "known", gOff: "off", guardOffShort: "I tell you when a new device appears.", gStart: "Turn on", gsMoved: "Off: you changed networks.", gsWaiting: "Waiting for the house check…", gsLearning: "Looking for devices…", gsPaused: "Paused: no network.", gsError: "Cannot see the network now.", gsEmpty: "I see no other devices.", gsWatching: "{n} devices · {ago}", gDetails: "Details", gNothing: "Nothing new so far. I will tell you as soon as something appears.", gForget: "Forget all devices", gDevices: "The devices on your network ({n})", gDevicesS: "“Forget” removes it from the list: if it is still connected, I will tell you again. To get a stranger off the network, change the Wi-Fi password.", gOnline: "on the network now", gSeen: "seen {ago}", gForgetOne: "Forget", gdNow: "now", gdHow: "How I look for devices", gdSeen: "Devices seen", gdErr: "Message from Nmap",
      guardEmpty: "I see no other device on the network. If you know devices are connected, this computer cannot read their list.", guardWatching: "Guarding the network · {n} known devices · looked {ago}",
      guardWatching0: "Guarding the network · looked {ago}", guardPaused: "Paused: you are not connected to any network right now.",
      guardError: "The guard cannot see the network right now. I keep trying.", guardAskT: "Turn on the guard?",
      guardAsk: "Every {s} seconds I look at who is connected to your network. Only the network you are connected to right now, and without administrator rights.",
      guardAsk2: "Is this your network?", guardYes: "Yes, guard it",
      agoNow: "just now", agoS: "{n} seconds ago", agoM: "{n} minutes ago", agoM1: "a minute ago",
      gNewDevT: "New device on your Wi-Fi", gPrivate: "Phone or laptop (private address)", gUnknownDev: "Unknown device",
      gKnow: "Do you know it?", gMine: "It's mine", gStranger: "I don't know it",
      gWasMine: "yours", gWasStranger: "you don't know it", gRecent: "What the guard saw",
      gStrangerT: "A device you don't know", gStrangerS: "It might belong to a neighbour or someone using your Wi-Fi. Here is what to do:",
    },
  };

  // Risk words with icons (never colour alone).
  const RISK = {
    high: { ro: "Risc înalt", en: "High risk", icon: "octagon", tone: "red" },
    medium: { ro: "Risc mediu", en: "Medium risk", icon: "alert", tone: "amber" },
    low: { ro: "Risc mic", en: "Low risk", icon: "info", tone: "low" },
    info: { ro: "Doar de știut", en: "Just so you know", icon: "info", tone: "info" },
  };
  const BAND_ICON = { red: "octagon", amber: "alert", green: "check" };
  const DEVICE_ICON = { router: "router", camera: "video", printer: "printer", nas: "drive", iot: "bulb", tv: "tv", phone: "phone", computer: "laptop", server: "server", unknown: "help" };
  const TABS = ["home", "devices", "history", "results"];   // "Devices" also holds every fix; the assistant is a floating chat

  // ---------------------------------------------------------------- state
  const store = {
    get(k) { try { return window.localStorage.getItem("netcheck." + k); } catch (e) { return null; } },
    set(k, v) { try { window.localStorage.setItem("netcheck." + k, v); } catch (e) { /* private mode */ } },
  };
  const state = {
    lang: store.get("lang") === "en" ? "en" : "ro",
    scan: LIVE ? 0 : Math.max(0, D.scans.findIndex((s) => s.file === "V2_smart_home.xml")),   // live: newest first
    tab: "home",
    devFilter: "all",
    cursor: {}, lastDone: {},
    historyDeleted: store.get("historyDeleted") === "1",
    confirmDelete: false,
    chat: [],            // [{kind, text}]
    inspected: {},       // scan file -> true once the house was inspected
    scanning: false,
    // live app
    broken: [],          // uploaded files that could not be read: shown as an error, never saved
    job: null,           // running check: {id, elapsed}
    busy: false,         // a chat answer is on its way
    chatOpen: false,     // the floating assistant panel
    resSel: null,        // Results tab: the check whose findings are shown
    verify: {},          // "ip|port|code" -> {status, message}
    guides: {},          // "scan|ip|code" -> {status, answer?, sources?, message?}
    justDeleted: false,
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
  // One SVG icon from the sprite in index.html (2px strokes, currentColor, aligned with text by flexbox).
  function icon(name, cls) {
    const el = svg("svg", { class: "ico" + (cls ? " " + cls : ""), "aria-hidden": "true", focusable: "false" });
    el.append(svg("use", { href: "#i-" + name }));
    return el;
  }
  // live: uploaded files that could not be read come first (shown as an error), then the saved scans
  const allScans = () => (LIVE ? state.broken.concat(D.scans) : D.scans);
  const EMPTY = { file: "", label: "", devices: [], findings: [], empty: true };   // live, nothing saved yet
  const scan = () => allScans()[state.scan] || EMPTY;
  const isInspected = (s) => !s.empty && (LIVE || !!state.inspected[s.file]);
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
    return deviceLabel(d.type) + (v ? ` (${v})` : "") + (d.me ? ` · ${t("thisPc")}` : "");
  }
  const meSuffix = (d) => (d && d.me ? ` · ${t("thisPc")}` : "");   // the computer this app runs on
  const riskPill = (sev) => h("span", { class: "pill p-" + sev }, icon(RISK[sev].icon), RISK[sev][state.lang]);
  function bandPill(score) {
    const b = bandOf(score);
    return h("span", { class: "pill p-" + b }, icon(BAND_ICON[b]), t("band_" + b));
  }
  // Risk colour of the 3D model's LED and rim light: red high, amber medium, blue low, green safe.
  const MODEL_TONE = { red: "red", high: "red", amber: "amber", medium: "amber", low: "blue", info: "green", green: "green" };
  // Which 3D model a device gets: the model of its type, or a variant when its name or maker says more (a MacBook,
  // an iMac, an iPhone, a Raspberry Pi; ui/assets/models/procedural/). Every phone that is not an iPhone gets the
  // standard Android model. A variant without a model falls back to its type in device3d.js.
  function modelOf(d) {
    if (!d) return "unknown";
    const type = DEVICE_ICON[d.type] ? d.type : "unknown";
    const name = String(d.hostname || "").toLowerCase(), vendor = String(d.vendor || "").toLowerCase();
    const apple = vendor.includes("apple");
    if (type === "computer") {
      if (name.includes("imac")) return "computer-imac";
      if (apple || /macbook|\bmbp\b|\bmac\b/.test(name)) return "computer-macbook";
    }
    if (type === "phone") return apple || /iphone|ipad/.test(name) ? "phone-iphone" : "phone-android";
    if (type === "iot" && vendor.includes("raspberry")) return "iot-raspberrypi";
    return type;
  }
  function devIco(type, tone, big, d) {
    const t = DEVICE_ICON[type] ? type : "unknown";
    return h("div", { class: "dev-ico dev3d" + (big ? " lg" : "") + (tone ? " " + tone : ""), "aria-hidden": "true",
      "data-type": t, "data-model": d ? modelOf(d) : t, "data-tone": MODEL_TONE[tone] || "green" }, icon(DEVICE_ICON[t]));
  }
  function whoLine(code) {
    const w = D.who[whoOf(code)];
    return h("p", { class: "who" }, icon(w.icon), w[state.lang]);
  }
  const steps = (list) => h("ol", { class: "steps" }, list.map((x) => h("li", { text: x })));
  function techBox(children) {
    return h("details", { class: "tech" }, h("summary", null, icon("code"), h("span", { text: t("techMore") })), h("div", null, children));
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

  // ---------------------------------------------------------------- LIVE: talking to the local agent (/api/v1)
  // Same-origin calls only; the agent checks the session cookie and the origin (netcheck/web/security.py).
  async function api(method, path, body) {
    const opts = { method, credentials: "same-origin", headers: {} };
    if (body instanceof FormData) opts.body = body;
    else if (body !== undefined) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
    let r;
    try { r = await fetch(path + (path.includes("?") ? "&" : "?") + "lang=" + state.lang, opts); }
    catch (e) { return { ok: false, status: 0, data: {} }; }
    let data = {};
    try { data = await r.json(); } catch (e) { /* not JSON */ }
    return { ok: r.ok, status: r.status, data };
  }
  // a 404/405 without our error body: the page is newer than the running app (it was not restarted after an update)
  const errText = (res) => (res.data && res.data.error && res.data.error.message)
    || (res.status === 404 || res.status === 405 ? t("oldApp") : t("connErr"));
  // Fresh data after a check, an upload or a delete; keeps the scan on screen when it still exists.
  async function reloadData(selectId) {
    const keep = selectId != null ? selectId : scan().scan_id;
    const res = await api("GET", "/api/v1/ui-data");
    if (!res.ok) return false;
    Object.assign(D, res.data);
    const i = allScans().findIndex((s) => s.scan_id != null && s.scan_id === keep);
    state.scan = i >= 0 ? i : 0;
    return true;
  }
  // shown on every page when nothing is saved yet (first start, or after "delete everything")
  function needScanBox() {
    return h("div", { class: "suggest" }, h("p", { class: "lead with-ico", style: "margin:0 0 1rem" }, icon("home"), h("span", { text: t("needScan") })),
      h("button", { type: "button", class: "btn btn-cta", onclick: () => { if (state.chatOpen) closeChat(); setTab("home"); inspect(); } }, icon("search"), t("scanNow")));
  }
  // The side/bottom sheet, also used for the check flow (consent, problems).
  let lastOpener = null;
  function showSheet(content, opener) {
    document.getElementById("sheet-body").replaceChildren(content);
    lastOpener = opener || document.activeElement || null;
    const dlg = document.getElementById("sheet");
    if (!dlg.open) { if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", ""); }
  }
  function problemSheet(title, message, detail, retry) {
    showSheet(h("div", { role: "alert" },
      h("div", { class: "sheet-head" }, h("div", { class: "dev-ico red", "aria-hidden": "true" }, icon("alert")), h("h2", { id: "sheet-title", text: title })),
      h("p", { class: "lead", style: "margin-top:.6rem", text: message }),
      detail ? techBox(h("p", { class: "evidence mono", text: detail })) : null,
      h("div", { class: "actions" },
        retry ? h("button", { type: "button", class: "btn btn-cta", onclick: retry }, icon("refresh"), t("tryAgain")) : null,
        h("button", { type: "button", class: "btn", onclick: closeSheet }, t("close")))));
    focusSel("#sheet .actions .btn");
  }
  function nmapSheet(message) {
    showSheet(h("div", { role: "alert" },
      h("div", { class: "sheet-head" }, h("div", { class: "dev-ico amber", "aria-hidden": "true" }, icon("alert")), h("h2", { id: "sheet-title", text: t("nmapT") })),
      h("p", { class: "lead", style: "margin-top:.6rem", text: message }),
      h("div", { class: "actions" },
        h("a", { class: "btn btn-cta", href: "https://nmap.org/download.html", target: "_blank", rel: "noopener noreferrer" }, icon("arrow"), t("nmapLink")),
        h("button", { type: "button", class: "btn", onclick: () => { closeSheet(); liveInspect(); } }, icon("refresh"), t("tryAgain")))));
  }

  // "Inspect house" in the app: consent -> one elevated nmap run on THIS network -> results.
  async function liveInspect() {
    if (state.scanning) return;
    showSheet(h("div", { class: "lead", role: "status", text: t("cfPrep") }));
    const res = await api("GET", "/api/v1/status");
    if (!res.ok) return problemSheet(t("probT"), errText(res), null, liveInspect);
    const st = res.data;
    if (st.scan) { closeSheet(); return followJob(st.scan); }
    if (!st.network.ok) return problemSheet(t("probT"), st.network.message, null, liveInspect);
    if (!st.nmap) return nmapSheet(state.lang === "en"
      ? "To check the network we need Nmap, a free program. Install it (press Next until it finishes), then try again."
      : "Ca să verificăm rețeaua avem nevoie de Nmap, un program gratuit. Instalează-l (apasă Next până termină), apoi încearcă din nou.");
    const net = st.network;
    showSheet(h("div", null,
      h("div", { class: "sheet-head" }, h("div", { class: "dev-ico", "aria-hidden": "true" }, icon("wifi")), h("h2", { id: "sheet-title", text: t("cfTitle") })),
      h("p", { class: "muted", style: "margin-top:.8rem", text: t("cfNet") }),
      h("p", { class: "lead" }, h("strong", { text: net.wifi || t("topoNet") }), h("span", { class: "mono", text: "  ·  " + net.subnet })),
      h("p", { text: t("cfAsk") }),
      h("p", { class: "note with-ico" }, icon("lock"), h("span", { text: t("cfPerm") })),
      h("div", { class: "actions" },
        h("button", { type: "button", class: "btn btn-cta", id: "cf-yes", onclick: startLiveScan }, icon("shield"), t("cfYes")),
        h("button", { type: "button", class: "btn", onclick: closeSheet }, t("cfNo")))));
    focusSel("#cf-yes");
  }
  async function startLiveScan() {
    const res = await api("POST", "/api/v1/scan", { confirm: true });
    if (!res.ok) return problemSheet(t("probT"), errText(res), null, liveInspect);
    closeSheet();
    followJob(res.data);
  }
  const mmss = (sec) => `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
  function showElapsed() {
    if (!state.job) return;
    const el = document.querySelector(".hero .sc-lead");
    if (el) el.textContent = t("scanElapsed", { t: mmss(state.job.elapsed || 0) });
  }
  let jobTimer = null;
  function followJob(job) {
    state.scanning = true;
    state.job = { id: job.id, elapsed: job.elapsed || 0 };
    if (state.tab === "home") { render(); } else setTab("home");
    clearInterval(jobTimer);
    jobTimer = setInterval(async () => {
      const res = await api("GET", "/api/v1/scan/" + encodeURIComponent(job.id));
      if (!res.ok) { stopJob(); return problemSheet(t("probT"), errText(res), null, liveInspect); }
      const j = res.data;
      state.job.elapsed = j.elapsed;
      showElapsed();
      if (j.status === "done") {
        stopJob();
        state.justDeleted = false;
        state.chat = [];
        await reloadData(j.scan_id);
        render();
        focusSel(".inspect-btn");
      } else if (j.status === "error") {
        stopJob();
        render();
        problemSheet(t("probT"), j.error.message, j.error.detail, liveInspect);
      }
    }, 1500);
  }
  function stopJob() { clearInterval(jobTimer); state.scanning = false; state.job = null; }

  // "I fixed it - check": re-tests one problem without a full scan (TCP ports, no admin rights needed).
  const canVerify = (s, f) => LIVE && s.scan_id != null && f.port != null && f.protocol === "tcp";
  function verifyRow(s, f) {
    if (!canVerify(s, f)) return null;
    const key = `${f.ip}|${f.port}|${f.code}`, v = state.verify[key];
    const out = h("p", { class: "verify-out" + (v ? " note with-ico" + (v.status === "resolved" ? " ok" : "") : ""), role: "status", "aria-live": "polite" },
      v ? [icon(v.status === "resolved" ? "check" : v.status === "pending" ? "search" : "alert"), h("span", { text: v.message })] : null);
    const btn = h("button", { type: "button", class: "btn btn-tonal", disabled: v && v.status === "pending",
      onclick: async (e) => {
        e.stopPropagation();
        state.verify[key] = { status: "pending", message: t("verifying") };
        refreshVerify(key, s, f);
        const res = await api("POST", "/api/v1/verify", { scan_id: s.scan_id, ip: f.ip, port: f.port, code: f.code });
        state.verify[key] = res.ok ? { status: res.data.status, message: res.data.message } : { status: "error", message: errText(res) };
        refreshVerify(key, s, f);
      } }, icon("refresh"), t("verifyBtn"));
    return h("div", { class: "verify-row", "data-verify": key, style: "margin-top:1rem" }, btn, out);
  }
  function refreshVerify(key, s, f) {
    document.querySelectorAll(`[data-verify="${CSS.escape(key)}"]`).forEach((el) => {
      const fresh = verifyRow(s, f);
      if (fresh) swapKeepFocus(el, fresh);
    });
  }
  // replace a block that may hold the keyboard focus: the focus moves to the new block (its button, else the block)
  function swapKeepFocus(el, fresh) {
    const had = el.contains(document.activeElement);
    el.replaceWith(fresh);
    if (!had) return;
    const target = fresh.querySelector("button:not([disabled])") || fresh;
    if (target === fresh) fresh.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
  }

  // Score ring (Fing) + labelled traffic light.
  function traffic(score) {
    const b = bandOf(score);
    const lamp = (tone, key) => h("span", { class: "lamp " + tone + (b === tone ? " on" : "") },
      h("span", { class: "dot", "aria-hidden": "true" }), b === tone ? [icon(BAND_ICON[tone]), t(key)] : t(key));
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
      h("h2", { class: "with-ico" }, icon("x-circle", "lg"), h("span", { text: t("errorTitle") })),
      h("p", { class: "lead", text: t("errorBody") }),
      techBox(h("p", null, t("errorDetail") + ": ", h("span", { class: "mono", text: s.file + " — " + s.error }))));
  }

  // ---------------------------------------------------------------- HOME: SafeHouse
  const SCAN_MS = 4000;      // the laser sweeps roof-to-ground about three times
  const reducedMotion = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const resultOf = (s) => (s.error ? "error" : s.findings.some((f) => f.severity !== "info") ? "vulnerable" : "safe");
  const STATUS = {
    idle: { icon: "home", title: "stIdleT", sub: "stIdleS" },
    scanning: { icon: "search", title: "stScanT", sub: "stScanS" },
    safe: { icon: "shield", title: "stSafeT", sub: "stSafeS" },
    vulnerable: { icon: "alert", title: "stVulnT", sub: "stVulnS" },
    error: { icon: "x-circle", title: "stErrT", sub: "stErrS" },
  };

  // Floating glass panel over the house: icon + the result in both languages (always icon + words).
  function glassPanel() {
    return h("div", { class: "glass", "aria-hidden": "true" },
      h("div", { class: "glass-ico" }),
      h("div", null, h("p", { class: "glass-main" })));
  }
  function houseScene() {
    if (window.Safehouse3D && window.Safehouse3D.supported) {
      const mountEl = h("div", { class: "house3d-mount" });
      return h("div", { class: "house-stage is3d", role: "img", "aria-label": t("houseLabel") }, mountEl, glassPanel());
    }
    const f = (cls, kids) => h("div", { class: "face " + cls }, kids);
    return h("div", { class: "house-stage", role: "img", "aria-label": t("houseLabel") }, glassPanel(),
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
    const wrap = hero.querySelector(".stage-wrap");
    if (wrap) wrap.classList.toggle("is-scanning", st === "scanning");   // starts / stops the yoyo scanline
    hero.querySelector(".hs-icon").replaceChildren(icon(cfg.icon, "lg"));
    hero.querySelector(".glass-ico").replaceChildren(icon(cfg.icon, "lg"));
    hero.querySelector(".glass-main").textContent = t(cfg.title);
    if (window.Safehouse3D) window.Safehouse3D.setState(st);
    hero.querySelector(".hs-title").textContent = t(cfg.title);
    hero.querySelector(".hs-sub").textContent = st === "vulnerable" && toFix ? (toFix === 1 ? t("stVulnS1") : t("stVulnS", { n: toFix })) : t(cfg.sub);
    const btn = hero.querySelector(".inspect-btn");
    btn.setAttribute("aria-busy", String(st === "scanning"));
    btn.disabled = st === "scanning";
    return true;
  }

  function inspect() {
    if (LIVE) { liveInspect(); return; }
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

  // Points in words: Romanian needs "de" for 20+ ("40 de puncte"), not for 1-19 ("5 puncte").
  function points(n) {
    n = Math.abs(n);
    if (state.lang === "en") return n === 1 ? "1 point" : `${n} points`;
    const r = n % 100;
    return n === 1 ? "1 punct" : (r >= 1 && r <= 19 ? `${n} puncte` : `${n} de puncte`);
  }
  // What the saved history says about the scan on screen. Only real data, never invented numbers.
  function historyFor(s) {
    if (LIVE) {                              // every saved scan carries its change since the one before it
      if (s.empty || s.error) return { kind: "none" };
      if (s.changes) return { kind: "delta", delta: s.changes.score_change, newDevices: s.changes.new_devices.length };
      return D.history.trend.length && D.history.trend[0].scan_id === s.scan_id ? { kind: "first" } : { kind: "none" };
    }
    if (state.historyDeleted || !D.history || !D.history.trend.length) return { kind: "none" };
    const i = D.history.trend.findIndex((r) => r.file === s.file);
    if (i < 0) return { kind: "none" };
    if (i === 0) return { kind: "first" };
    const ch = D.history.changes;
    if (!ch || ch.after_file !== s.file) return { kind: "none" };
    return { kind: "delta", delta: ch.score_change, newDevices: ch.new_devices.length };
  }
  function trendRow(s) {
    const hs = historyFor(s);
    if (hs.kind !== "delta") return h("p", { class: "trend neutral" }, icon("info"), h("span", { text: hs.kind === "first" ? t("trendFirst") : t("trendNone") }));
    const up = hs.delta > 0, down = hs.delta < 0;
    return h("p", { class: "trend " + (up ? "up" : down ? "down" : "neutral") },
      icon(up ? "trend-up" : down ? "trend-down" : "info"),
      h("span", { text: up ? t("trendUp", { pts: points(hs.delta) }) : down ? t("trendDown", { pts: points(hs.delta) }) : t("trendSame") }));
  }
  function newDeviceBadge(s) {
    const hs = historyFor(s);
    if (hs.kind !== "delta") return null;
    const n = hs.newDevices;
    if (!n) return h("span", { class: "newdev none" }, icon("check"), t("newDev0"));
    return h("span", { class: "newdev", role: "status" }, h("span", { class: "pulse-dot", "aria-hidden": "true" }), icon("plus"), n === 1 ? t("newDev1") : t("newDevN", { n }));
  }
  // NFR-02: one-click "delete my history", with an inline confirmation (no browser dialog).
  // live: really deletes ~/.netcheck/history.sqlite through the agent, then shows the empty house
  async function liveDelete() {
    const res = await api("DELETE", "/api/v1/history");
    state.confirmDelete = false;
    if (!res.ok) { problemSheet(t("probT"), errText(res)); return; }
    state.broken = []; state.chat = []; state.verify = {}; state.guides = {}; state.justDeleted = true;
    await reloadData(-1);
    render();
  }
  function privacyRow() {
    if (LIVE) {
      if (state.justDeleted && !D.scans.length) return h("div", { class: "privacy" }, h("p", { class: "with-ico muted", role: "status", style: "margin:0" }, icon("trash"), h("span", { text: t("histGone") })));
      if (!D.scans.length) return null;
      if (state.confirmDelete) {
        return h("div", { class: "privacy confirm-inline", role: "alertdialog", "aria-label": t("delHistory") },
          h("p", { style: "margin:0", text: t("delHistoryAsk") }),
          h("div", { class: "actions" },
            h("button", { type: "button", class: "btn btn-danger", onclick: liveDelete }, icon("trash"), t("deleteYes")),
            h("button", { type: "button", class: "btn", onclick: () => { state.confirmDelete = false; render(); focusSel(".btn-delete"); } }, t("deleteNo"))));
      }
      return h("div", { class: "privacy" }, h("button", { type: "button", class: "btn-delete", onclick: () => { state.confirmDelete = true; render(); focusSel(".confirm-inline .btn-danger"); } }, icon("trash"), t("delHistory")));
    }
    if (state.historyDeleted) {
      return h("div", { class: "privacy" }, h("p", { class: "with-ico muted", role: "status", style: "margin:0" }, icon("trash"), h("span", { text: t("histGone") })),
        h("button", { type: "button", class: "btn-link", onclick: () => { state.historyDeleted = false; store.set("historyDeleted", "0"); render(); } }, t("restore")));
    }
    if (state.confirmDelete) {
      return h("div", { class: "privacy confirm-inline", role: "alertdialog", "aria-label": t("delHistory") },
        h("p", { style: "margin:0", text: t("delHistoryAsk") }),
        h("div", { class: "actions" },
          h("button", { type: "button", class: "btn btn-danger", onclick: () => { state.historyDeleted = true; state.confirmDelete = false; store.set("historyDeleted", "1"); render(); focusSel(".privacy .btn-link"); } }, icon("trash"), t("deleteYes")),
          h("button", { type: "button", class: "btn", onclick: () => { state.confirmDelete = false; render(); focusSel(".btn-delete"); } }, t("deleteNo"))));
    }
    return h("div", { class: "privacy" }, h("button", { type: "button", class: "btn-delete", onclick: () => { state.confirmDelete = true; render(); focusSel(".confirm-inline .btn-danger"); } }, icon("trash"), t("delHistory")));
  }

  const SEV_RANK = { high: 0, medium: 1, low: 2 };

  function renderHome(root) {
    const s = scan();
    const done = isInspected(s) && !state.scanning;
    const st = state.scanning ? "scanning" : done ? resultOf(s) : "idle";
    const toFix = s.error ? 0 : s.findings.filter((f) => f.severity !== "info").length;
    root.append(pageHead(t("hello"), t("helloSub")));

    // right column: score, status pills and the call to action, centred in one card
    // the score as a dial (ui/assets/score-ring/): segmented track, glowing line and end cap, counting up from 0 the
    // first time a scan is shown; before the house is inspected the same dial, empty
    const scoreDial = () => window.ScoreRing.create(s.score, { of: t("scoreOf"), key: s.file,
      aria: `${s.score} ${t("scoreOf")}, ${t("band_" + bandOf(s.score))}` });
    const pendingRing = window.ScoreRing.pending(t("scoreOf"));
    pendingRing.setAttribute("aria-hidden", "true");
    const scoreCard = h("div", { class: "score-card" },
      h("p", { class: "eyebrow muted", text: t("scoreTitle") }),
      done && !s.error ? scoreDial() : pendingRing,
      done && !s.error ? traffic(s.score) : null,
      h("p", { class: "lead sc-lead", text: state.scanning && state.job ? t("scanElapsed", { t: mmss(state.job.elapsed || 0) })
        : !done || s.error ? (s.error && done ? t("stErrS") : t("scorePending"))
        : toFix === 0 ? t("summaryNone", { d: s.devices.length }) : toFix === 1 ? t("summaryOne", { d: s.devices.length }) : t("summary", { d: s.devices.length, f: toFix }) }),
      done && !s.error ? h("div", { class: "changes" }, trendRow(s), newDeviceBadge(s)) : null,
      h("div", { class: "actions" },
        h("button", { type: "button", class: "btn btn-cta inspect-btn", onclick: inspect }, icon(done ? "refresh" : "search"), done ? t("inspectAgain") : t("inspect")),
        done && toFix ? h("button", { type: "button", class: "btn", onclick: () => showFixes() }, icon("shield"), t("seeFixes")) : null),
      LIVE ? guardRow() : null,
      privacyRow(),
      // screen-reader status (the glass badge over the house is the visible one)
      h("div", { class: "house-status sr", role: "status", "aria-live": "polite" },
        h("div", { class: "hs-icon" }), h("div", null, h("p", { class: "hs-title" }), h("p", { class: "hs-sub" }))));

    root.append(h("section", { class: "hero premium", "data-state": st, "aria-label": "SafeHouse" },
      h("div", { class: "stage-wrap" }, houseScene(), h("div", { class: "scanline", "aria-hidden": "true" })), scoreCard));
    const mountEl = root.querySelector(".house3d-mount");
    if (mountEl) window.Safehouse3D.mount(mountEl);
    applyHouseState(st);

    if (!done) return;                       // results appear after the house is inspected
    if (s.error) { root.append(h("div", { class: "section" }, errorBox(s))); return; }

    // Rețeaua ta: one tree for every device (router -> risk branches -> devices); the threat path lives in its panel
    const vuln = s.devices.filter((d) => problemsOf(s, d).length).length;
    const topo = topology(s);
    root.append(h("section", { class: "section" },
      h("div", { class: "section-head" }, h("h3", { class: "with-ico" }, icon("wifi", "lg"), h("span", { text: t("netTitle", { n: s.devices.length }) }))),
      h("p", { class: "section-sub", text: vuln === 0 ? t("doorsNone") : vuln === 1 ? t("netSub1") : t("netSub", { n: vuln }) }),
      topo));
    startTopology(topo, s);
  }

  // ---------------------------------------------------------------- HOME: the network map
  // The whole network on one map, however many devices it has: the router (gateway) in the middle and the devices
  // scattered around it at random (seeded by their address, so the same network always looks the same), each one
  // wired straight to the router. The risk chips above the map (High / Medium / Low / Safe) filter it; the overview
  // shows the most dangerous devices of every risk level plus a "+N more" node, a filtered view shows all of them
  // and turns into glowing dots past 24 devices. The map is only as tall as its devices need. Phones show one level.
  // The threat path lives in the details panel: "Start with the most dangerous" and Previous / Next walk through
  // every device with open doors, riskiest first, while a packet runs from the device up its branch to the router.
  const TOPO_SEVS = ["high", "medium", "low", "safe"];
  const PKT_DUR = { high: 1.4, medium: 2.2, low: 2.8, safe: 3.6 };
  const TOPO_K = 4;          // devices per branch in the overview, before "+N more"
  const TOPO_DOTS = 24;      // more visible devices than this -> glowing dots (and no 3D models)
  let topoUid = 0;
  function topology(s) {
    const svgEl = svg("svg", { class: "topo-svg", "aria-hidden": "true" });
    return h("div", { class: "topo" },
      h("div", { class: "topo-main" },
        h("div", { class: "topo-bar" }),
        h("div", { class: "topo-legend", role: "group", "aria-label": t("topoShow") }),
        h("div", { class: "topo-graph" }, h("div", { class: "topo-radar", "aria-hidden": "true" }), svgEl)),
      h("aside", { class: "topo-panel grunge", "aria-live": "polite", "aria-label": t("topoNet") }));
  }
  function startTopology(root, s) {
    const graph = root.querySelector(".topo-graph"), svgEl = graph.querySelector(".topo-svg"), panel = root.querySelector(".topo-panel");
    const bar = root.querySelector(".topo-bar"), legend = root.querySelector(".topo-legend"), radar = graph.querySelector(".topo-radar");
    const uid = "topo" + ++topoUid, still = reducedMotion();
    const sevOf = (probs) => (probs.length ? probs[0].severity : "safe");
    const sevLabel = (k) => (k === "safe" ? t("devOk") : RISK[k][state.lang]);
    const sevIcon = (k) => (k === "safe" ? "check" : RISK[k].icon);
    const rank = (x) => (x.probs.length ? SEV_RANK[x.probs[0].severity] : 9);
    const byRisk = (a, b) => rank(a) - rank(b) || b.d.risk_points - a.d.risk_points;
    const entry = (d) => { const probs = problemsOf(s, d); return { d, probs, sev: sevOf(probs) }; };

    const gw = s.devices.find((d) => d.type === "router") || null;
    const gwItem = gw ? entry(gw) : null;
    const items = s.devices.filter((d) => d !== gw).map(entry).sort(byRisk);
    // the risk chips count the router too (it stays in the middle of the map; its chip lights it up instead of a branch)
    const hubs = TOPO_SEVS.map((k) => ({ k, list: items.filter((x) => x.sev === k), gw: !!gwItem && gwItem.sev === k }))
      .filter((x) => x.list.length || x.gw);
    const hubN = (hb) => hb.list.length + (hb.gw ? 1 : 0);
    // the threat path: every device with open doors (the router too), most dangerous first
    const trail = (gwItem ? [gwItem, ...items] : items).filter((x) => x.probs.length).sort(byRisk);

    let mode = { kind: "all" }, query = "", narrow = graph.clientWidth > 0 && graph.clientWidth < 600, dots = false;
    let selected = null, vis = [], mores = [], trace = null, tracePkt = null, openK = null;
    const elOf = new Map();

    function nodeBtn(it, core, dot) {
      const d = it.d, sev = it.sev, vendor = shortVendor(d.vendor), ico = DEVICE_ICON[d.type] || DEVICE_ICON.unknown;
      const b = h("button", { type: "button", class: `topo-node sev-${sev}${core ? " core" : ""}${dot ? " dot" : ""}`,
          "aria-label": `${vendor || deviceLabel(d.type)}, ${deviceLabel(d.type)}, ${d.ip}. ${sevLabel(sev)}`, "aria-pressed": "false" },
        h("span", { class: "topo-orb" }, dot ? icon(ico)
          : h("span", { class: "dev3d topo-model", "aria-hidden": "true", "data-type": DEVICE_ICON[d.type] ? d.type : "unknown",
              "data-model": modelOf(d), "data-tone": MODEL_TONE[sev] || "green", "data-float": "" }, icon(ico))),
        h("span", { class: "topo-label" }, h("strong", { text: vendor || deviceLabel(d.type) }),
          h("span", { text: (core ? t("topoGateway") : sevLabel(sev)) + meSuffix(d) })));
      b.addEventListener("click", () => select(it));
      elOf.set(it, b);
      return b;
    }
    const coreEl = gwItem ? nodeBtn(gwItem, true, false)
      : h("div", { class: "topo-node core sev-safe" }, h("span", { class: "topo-orb" }, icon("home")), h("span", { class: "topo-label" }, h("strong", { text: t("topoCore") })));
    graph.append(coreEl);

    // top bar: search, "back to the whole network", start of the threat path
    const search = h("input", { type: "search", class: "topo-search-in", placeholder: t("topoSearch"), "aria-label": t("topoSearch"), autocomplete: "off", spellcheck: "false" });
    const status = h("span", { class: "topo-status", role: "status", "aria-live": "polite" });
    const back = h("button", { type: "button", class: "btn-hud topo-back", hidden: true, onclick: () => setMode({ kind: "all" }) }, icon("chevron", "back"), h("span", { text: t("topoBack") }));
    // filter: a network with nothing to fix has no "start" button, and append(null) would print "null"
    bar.append(...[items.length > 1 ? h("label", { class: "topo-search" }, icon("search"), search) : null, status, back,
      trail.length ? h("button", { type: "button", class: "btn-hud primary start", onclick: () => goTo(0) }, icon("shield"), h("span", { text: t("topoStart") }), icon("chevron", "go")) : null].filter(Boolean));
    let searchTimer;
    const applySearch = () => { clearTimeout(searchTimer); query = search.value.trim().toLowerCase(); setMode(query ? { kind: "search" } : { kind: "all" }); };
    search.addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(applySearch, 120); });
    search.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); applySearch(); if (mode.kind === "search" && vis[0]) select(vis[0].it, true); }
      if (e.key === "Escape" && search.value) { e.stopPropagation(); search.value = ""; applySearch(); }
    });
    const matches = () => items.filter((x) => [x.d.ip, x.d.hostname, x.d.vendor, x.d.mac, deviceLabel(x.d.type)]
      .some((v) => v && String(v).toLowerCase().includes(query)));

    function packet(id, sev, i, cls) {
      const dur = PKT_DUR[sev] || 1.6;
      const c = svg("circle", { class: "topo-pkt sev-" + sev + (cls ? " " + cls : ""), r: cls ? 4.5 : 3.5 });
      const m = svg("animateMotion", { dur: dur + "s", repeatCount: "indefinite", begin: `-${((i * 0.37) % dur).toFixed(2)}s`,
        keyPoints: "1;0", keyTimes: "0;1", calcMode: "linear" });                         // from the device towards the router
      const mp = svg("mpath", { href: "#" + id });
      mp.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", "#" + id);
      m.append(mp); c.append(m); svgEl.append(c);
      return c;
    }

    // build the nodes and wires for the current view (positions come from layout())
    function render() {
      graph.querySelectorAll(".topo-node:not(.core), .topo-more").forEach((n) => n.remove());
      svgEl.replaceChildren(); legend.replaceChildren();
      elOf.clear(); if (gwItem) elOf.set(gwItem, coreEl);
      vis = []; mores = [];
      const firstHub = hubs.find((x) => x.list.length) || hubs[0];
      const view = narrow && mode.kind === "all" ? { kind: "branch", k: firstHub && firstHub.k } : mode;   // phones: one branch at a time
      openK = view.kind === "branch" ? view.k : null;
      let shown;
      if (view.kind === "all") shown = hubs.flatMap((hb) => (hb.list.length <= TOPO_K + 1 ? hb.list : hb.list.slice(0, TOPO_K)).map((it) => ({ it, hub: hb.k })));
      else if (view.kind === "branch") shown = ((hubs.find((x) => x.k === view.k) || { list: [] }).list).map((it) => ({ it, hub: view.k }));
      else shown = matches().map((it) => ({ it, hub: it.sev }));
      dots = shown.length > TOPO_DOTS;
      root.classList.toggle("is-branch", view.kind !== "all");
      // a risk chip open: the router glows when it belongs to that risk level and fades back when it does not
      const gwIn = !!gwItem && openK != null && gwItem.sev === openK;
      coreEl.classList.toggle("is-match", gwIn);
      coreEl.classList.toggle("is-other", openK != null && !gwIn);
      back.hidden = narrow || mode.kind === "all";
      status.textContent = mode.kind === "search" ? (shown.length === 1 ? t("topoResult1") : shown.length ? t("topoResults", { n: shown.length }) : t("topoNoResults")) : "";

      hubs.forEach((hb) => {
        const on = openK === hb.k;
        const b = h("button", { type: "button", class: `btn-hud chip topo-hub sev-${hb.k}${view.kind !== "all" && !on ? " is-off" : ""}`,
            "aria-pressed": String(on), "aria-label": `${sevLabel(hb.k)}: ${hubN(hb)}` },
          h("span", { class: "hub-top" }, icon(sevIcon(hb.k)), h("span", { class: "chip-n", text: String(hubN(hb)) })), h("span", { class: "hub-word", text: sevLabel(hb.k) }));
        b.addEventListener("click", () => setMode(on && !narrow ? { kind: "all" } : { kind: "branch", k: hb.k }));
        legend.append(b);
      });
      if (view.kind === "all") hubs.forEach((hb) => {
        if (hb.list.length <= TOPO_K + 1) return;
        const m = h("button", { type: "button", class: `btn-hud chip topo-more sev-${hb.k}`, onclick: () => setMode({ kind: "branch", k: hb.k }) },
          icon("plus"), h("span", { text: t("topoMore", { n: hb.list.length - TOPO_K }) }));
        const p = svg("path", { class: `topo-link sev-${hb.k}` });
        svgEl.append(p); graph.append(m); mores.push({ k: hb.k, el: m, path: p });
      });
      shown.forEach(({ it, hub }, i) => {
        const el = nodeBtn(it, false, dots), p = svg("path", { class: "topo-link sev-" + it.sev, id: `${uid}-l${i}` });
        svgEl.append(p); graph.append(el); vis.push({ it, el, hub, path: p });
      });
      trace = svg("path", { class: "topo-trace", id: `${uid}-trace` });
      svgEl.append(trace);
      tracePkt = null;
      if (!still) {
        vis.forEach((v, i) => { if (!dots && v.it.sev !== "safe") packet(`${uid}-l${i}`, v.it.sev, i); });
        tracePkt = packet(`${uid}-trace`, "high", 0, "topo-trace-pkt");
      }
      if (window.Device3D && !dots) window.Device3D.scan(graph);
    }

    const place = (el, x, y) => { el.style.left = x + "px"; el.style.top = y + "px"; };
    // a small seeded random generator: the same device always gets the same spot on a map of the same width
    const hash = (str) => { let x = 2166136261; for (let i = 0; i < str.length; i++) { x ^= str.charCodeAt(i); x = Math.imul(x, 16777619); } return x >>> 0; };
    const rng = (seed) => () => { seed = (seed + 0x6d2b79f5) | 0; let r = Math.imul(seed ^ (seed >>> 15), 1 | seed); r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r; return ((r ^ (r >>> 14)) >>> 0) / 4294967296; };
    // the centre of a node's circle, measured from the centre of the node (the label hangs under the circle)
    const orbDy = (el) => { const o = el.querySelector(".topo-orb"); return o ? o.offsetTop + o.offsetHeight / 2 - el.offsetHeight / 2 : 0; };
    const curve = (x1, y1, x2, y2, bend) => {                    // soft curve, not a straight wire
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
      return `M${x1.toFixed(1)},${y1.toFixed(1)} Q${(mx - (y2 - y1) * bend).toFixed(1)},${(my + (x2 - x1) * bend).toFixed(1)} ${x2.toFixed(1)},${y2.toFixed(1)}`;
    };
    // drop every node at a random free spot around the router; the map starts as small as the nodes allow and only
    // grows (12% at a time) when they do not fit. "Free" means: room around the box, no wire crossing a device, no
    // two devices on (almost) the same line from the router, and of a few random free spots the airiest one wins.
    // Small networks (up to 8 devices) always keep every rule and grow the map instead; big ones cannot keep them on
    // a compact map, so at every size they try every rule, then without the wire rule, then with half the angle, and
    // only on a crowded map boxes only (they never overlap).
    const bendOf = (key) => (hash(key) % 2 ? 1 : -1) * 0.14;
    function wirePts(x1, y1, x2, y2, bend) {                   // points along the curve(), for the crossing checks
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, qx = mx - (y2 - y1) * bend, qy = my + (x2 - x1) * bend, pts = [];
      for (let t = 0.1; t < 0.95; t += 0.06) pts.push({ x: (1 - t) * (1 - t) * x1 + 2 * (1 - t) * t * qx + t * t * x2, y: (1 - t) * (1 - t) * y1 + 2 * (1 - t) * t * qy + t * t * y2 });
      return pts;
    }
    function scatter(W, boxes) {
      const n = boxes.length, airy = !dots;                           // dots: only keep them apart, there are too many wires
      const PAD = narrow ? 10 : 18, gap = dots ? (narrow ? 16 : 26) : narrow ? 22 : n <= 8 ? 40 : 28;
      const cw = coreEl.offsetWidth + (narrow ? 24 : 64), ch = coreEl.offsetHeight + (narrow ? 20 : 32);
      const coreY = (H) => (narrow ? PAD + ch / 2 : H / 2);         // phones: the router on top, the devices under it
      const coreDy = orbDy(coreEl);
      const sizes = boxes.map((b) => ({ w: b.el.offsetWidth + gap, h: b.el.offsetHeight + gap, rw: b.el.offsetWidth + 12, rh: b.el.offsetHeight + 12,
        dy: b.more ? 0 : orbDy(b.el), bend: bendOf(b.key) }));
      const area = sizes.reduce((a, s) => a + s.w * s.h, cw * ch);
      const minAng = airy && n > 1 ? Math.min(26, (0.6 * (narrow ? 180 : 360)) / n) * (Math.PI / 180) : 0;
      // with the details panel open (computer) the map is at least as tall as a comfortable panel, which scrolls inside
      const minH = root.classList.contains("open") && !narrow ? 560 : narrow ? 280 : 300;
      const inBox = (p, b) => Math.abs(p.x - b.x) * 2 < b.rw && Math.abs(p.y - b.y) * 2 < b.rh;

      // one attempt at height H with the rules of `level` (3: every rule, 2: no wire rule, 1: half the angle, 0: boxes only)
      function attempt(H, level, seed) {
        const cx = W / 2, cy = coreY(H), sx = cx, sy = cy + coreDy, core = { x: cx, y: cy, w: cw, h: ch }, placed = [];
        const free = (c) => {
          if (Math.abs(core.x - c.x) * 2 < core.w + c.w && Math.abs(core.y - c.y) * 2 < core.h + c.h) return false;
          if (placed.some((p) => Math.abs(p.x - c.x) * 2 < p.w + c.w && Math.abs(p.y - c.y) * 2 < p.h + c.h)) return false;
          if (level === 0) return true;
          const a = level === 1 ? minAng / 2 : minAng;
          if (a && placed.some((p) => { const d = Math.abs(p.ang - c.ang); return Math.min(d, 2 * Math.PI - d) < a; })) return false;
          if (level < 3) return true;
          if (c.pts.some((q) => placed.some((p) => inBox(q, p)))) return false;          // my wire through a device
          return !placed.some((p) => p.pts.some((q) => inBox(q, c)));                    // a wire through me
        };
        for (let i = 0; i < n; i++) {
          const s = sizes[i], rnd = rng(hash(boxes[i].key) + seed * 7919 + level * 131);
          let best = null, bestScore = -Infinity;
          const consider = (x, y) => {
            const ey = y + s.dy, c = { x, y, w: s.w, h: s.h, rw: s.rw, rh: s.rh, ang: Math.atan2(ey - sy, x - sx),
              pts: level === 3 ? wirePts(sx, sy, x, ey, s.bend).filter((q) => !inBox(q, { x, y, rw: s.rw, rh: s.rh })) : [] };
            if (!free(c)) return false;
            // the airiest spot wins; boxes-only is the last resort for crowded maps: pack close to the router instead
            const score = level === 0 ? -Math.hypot(x - cx, (y - cy) * 1.4) : Math.min(Math.hypot(x - cx, y - cy) * 0.8, ...placed.map((p) => Math.hypot(p.x - x, p.y - y)));
            if (score > bestScore) { bestScore = score; best = c; }
            return true;
          };
          const x0 = PAD + s.w / 2, y0 = PAD + s.h / 2, xs = Math.max(0, W - 2 * PAD - s.w), ys = Math.max(0, H - 2 * PAD - s.h);
          for (let k = 0, found = 0; k < 300 && found < (airy ? 8 : 3); k++) if (consider(x0 + rnd() * xs, y0 + rnd() * ys)) found++;
          if (!best) {                                              // random spots all taken: every free spot on a fine grid
            const st = dots ? 8 : 14, ox = rnd() * st, oy = rnd() * st;
            for (let y = y0 + oy; y <= y0 + ys; y += st) for (let x = x0 + ox; x <= x0 + xs; x += st) consider(x, y);
          }
          if (!best) return null;
          placed.push(best);
        }
        return { H, out: placed, cy };
      }

      let H = Math.max(ch + 2 * PAD, minH, Math.ceil((area * 1.45) / Math.max(1, W - 2 * PAD)));
      for (let tries = 0; tries < 18; tries++, H = Math.ceil(H * 1.12)) {
        const levels = !airy ? [0] : tries === 17 ? [3, 2, 1, 0] : n <= 8 ? [3] : tries < 3 ? [3, 2] : tries < 6 ? [3, 2, 1] : [3, 2, 1, 0];
        for (const level of levels) for (let k = 0; k < (level ? 3 : 1); k++) { const r = attempt(H, level, tries * 3 + k); if (r) return r; }
      }
      return { H, out: [], cy: coreY(H) };
    }
    function layout() {
      const W = graph.clientWidth;
      if (!W) return;
      if ((W < 600) !== narrow) { narrow = W < 600; render(); restoreSel(); }
      const boxes = [...vis.map((v, i) => ({ el: v.el, path: v.path, key: v.it.d.ip || v.it.d.mac || "n" + i })),
        ...mores.map((m) => ({ el: m.el, path: m.path, key: "more-" + m.k, more: true }))];
      const { H, out, cy } = scatter(W, boxes);
      const cx = W / 2, coreOy = cy + orbDy(coreEl);
      place(coreEl, cx, cy);
      place(radar, cx, coreOy);
      radar.style.width = radar.style.height = Math.min(narrow ? 260 : 340, H * 0.95) + "px";
      boxes.forEach((b, i) => {
        const p = out[i];
        if (!p) return;
        place(b.el, p.x, p.y);
        const ty = b.more ? p.y : p.y + orbDy(b.el), bend = bendOf(b.key);
        b.path.setAttribute("d", curve(cx, coreOy, p.x, ty, bend));       // from the router to the device
      });
      graph.style.height = H + "px";
      svgEl.style.height = H + "px";
      svgEl.setAttribute("viewBox", `0 0 ${W} ${H}`);
      updateTrace();
    }

    // the selected device lights up its wire to the router
    function updateTrace() {
      if (!trace) return;
      const v = selected && vis.find((x) => x.it === selected.it);
      const d = (v && v.path.getAttribute("d")) || "";
      trace.setAttribute("d", d || "M0,0");
      trace.setAttribute("class", "topo-trace" + (d ? " is-on sev-" + v.it.sev : ""));
      if (tracePkt) tracePkt.setAttribute("class", "topo-pkt topo-trace-pkt" + (d ? " is-on sev-" + v.it.sev : ""));
      vis.forEach((x) => x.path.classList.toggle("is-on", !!d && x === v));
    }

    function setMode(m) {
      mode = m;
      if (m.kind !== "search" && search.value) { search.value = ""; query = ""; }
      render();
      restoreSel();
      layout();
      // a risk level where only the router is: open the router's details, there is no branch to show
      const hb = m.kind === "branch" && hubs.find((x) => x.k === m.k);
      if (hb && hb.gw && !hb.list.length && !selected) select(gwItem);
    }
    // after a re-render the selected device keeps its panel if it is still on screen
    function restoreSel() {
      if (!selected) return;
      const b = elOf.get(selected.it);
      if (!b) { close(true); return; }
      selected.btn = b;
      b.setAttribute("aria-pressed", "true");
      graph.querySelectorAll(".topo-node").forEach((n) => n.classList.toggle("is-dim", n !== b && !n.classList.contains("core")));
    }
    // walk the threat path; a device hidden behind "+N" opens its branch first
    function goTo(i) {
      const it = trail[i];
      if (!it) return;
      if (!elOf.has(it)) setMode({ kind: "branch", k: it.sev });
      select(it, true);
      const nx = panel.querySelector(".topo-next") || elOf.get(it);
      if (nx) nx.focus({ preventScroll: true });
      const el = elOf.get(it);
      if (el && el.scrollIntoView) el.scrollIntoView({ block: "nearest", behavior: still ? "auto" : "smooth" });
    }

    function navRow(it) {
      const ti = trail.indexOf(it);
      if (!trail.length) return null;
      if (ti < 0) return h("div", { class: "topo-nav", style: "--i:1" },
        h("button", { type: "button", class: "btn-hud topo-next", onclick: () => goTo(0) }, h("span", { text: t("topoStart") }), icon("chevron", "go")));
      const last = ti === trail.length - 1;
      return h("div", { class: "topo-nav", style: "--i:1" },
        h("button", { type: "button", class: "btn-hud icon topo-prev", "aria-label": t("topoPrev"), title: t("topoPrev"), disabled: ti === 0, onclick: () => goTo(ti - 1) }, icon("chevron", "back")),
        h("span", { class: "topo-step", text: t("tourStep", { i: ti + 1, n: trail.length }) }),
        last ? h("button", { type: "button", class: "btn-hud topo-next", onclick: () => showFixes() }, icon("shield"), h("span", { text: t("seeFixes") }))
          : h("button", { type: "button", class: "btn-hud topo-next", onclick: () => goTo(ti + 1) }, h("span", { text: t("topoNext") }), icon("chevron", "go")));
    }
    function select(it, fromNav) {
      const btn = elOf.get(it);
      if (!btn) return;
      if (selected && selected.it === it && !fromNav) { close(); return; }
      if (selected && selected.btn) selected.btn.setAttribute("aria-pressed", "false");
      selected = { it, btn };
      btn.setAttribute("aria-pressed", "true");
      const d = it.d, probs = it.probs, worst = probs[0], vendor = shortVendor(d.vendor), sev = it.sev;
      // kept short on purpose: who it is, how bad, what we found (titles only) and one clear button to fix it.
      // The technical part (IP, MAC, ports) and every step live in the device sheet behind the button.
      const SHOW = 3, more = probs.length - SHOW;
      const name = (vendor ? `${vendor} · ${deviceLabel(d.type)}` : deviceLabel(d.type)) + meSuffix(d);
      panel.className = `topo-panel grunge sev-${sev}`;
      panel.replaceChildren(...[                // filter: replaceChildren() would print a skipped part as "null"
        h("div", { class: "topo-ph", style: "--i:0" }, devIco(d.type, worst ? toneOf(worst.severity) : "green", false, d),
          h("div", { class: "grow" }, h("h4", { text: name }),
            h("div", { class: "topo-risk" }, worst ? riskPill(worst.severity) : h("span", { class: "pill p-green" }, icon("check"), t("devOk")))),
          h("button", { type: "button", class: "btn-hud icon topo-x", "aria-label": t("closeEsc"), title: t("closeEsc"), onclick: () => close() }, icon("x"))),
        h("p", { class: "topo-why", style: "--i:1", text: worst ? simple(worst.code).explain : t("devOkExplain") }),
        // every problem: icon + title, so the colour is never the only sign of how bad it is (NFR-08)
        probs.length ? h("ul", { class: "topo-finds", style: "--i:2" }, probs.slice(0, SHOW).map((f) =>
          h("li", { class: "sev-" + f.severity, "aria-label": `${RISK[f.severity][state.lang]}: ${simple(f.code).title}` },
            h("span", { class: "topo-fline" }, icon(RISK[f.severity].icon), h("strong", { text: simple(f.code).title }))))) : null,
        more > 0 ? h("p", { class: "topo-more-probs", style: "--i:2", text: more === 1 ? t("moreProb1") : t("moreProbs", { n: more }) }) : null,
        worst ? h("button", { type: "button", class: "btn-hud primary topo-cta", style: "--i:3", onclick: (e) => openDevice(d, e.currentTarget) },
            icon("shield"), h("span", { class: "grow", text: t("fixNow") }), icon("chevron", "go"))
          : h("button", { type: "button", class: "btn-hud topo-cta topo-cta-soft", style: "--i:3", onclick: (e) => openDevice(d, e.currentTarget) },
            h("span", { class: "grow", text: t("devDetails") }), icon("chevron", "go")),
        navRow(it),
        h("div", { class: "topo-scan", "aria-hidden": "true" })].filter(Boolean));
      if (window.Device3D) window.Device3D.scan(panel);     // 3D model in the panel header
      // replay the reveal (scan line + boxes one by one) for every device that is opened
      if (!still) { void panel.offsetWidth; panel.classList.add("is-revealing"); }
      panel.scrollTop = 0;
      root.classList.add("open");
      graph.querySelectorAll(".topo-node").forEach((n) => n.classList.toggle("is-dim", n !== btn && !n.classList.contains("core")));
      updateTrace();
      requestAnimationFrame(layout);
    }
    function close(silent) {
      if (!selected) return;
      const btn = selected.btn;
      btn.setAttribute("aria-pressed", "false");
      selected = null;
      root.classList.remove("open");
      graph.querySelectorAll(".topo-node").forEach((n) => n.classList.remove("is-dim"));
      updateTrace();
      requestAnimationFrame(layout);
      if (!silent && btn.isConnected) btn.focus({ preventScroll: true });
    }
    root.addEventListener("keydown", (e) => {
      if (e.target === search) return;
      if (e.key === "Escape") { close(); return; }
      const ti = selected ? trail.indexOf(selected.it) : -1;
      if (ti < 0) return;
      if (e.key === "ArrowRight" && ti < trail.length - 1) { e.preventDefault(); goTo(ti + 1); }
      if (e.key === "ArrowLeft" && ti > 0) { e.preventDefault(); goTo(ti - 1); }
    });
    render();
    // re-layout when the graph area changes size (window resize, panel opening)
    new ResizeObserver(() => layout()).observe(graph);
    requestAnimationFrame(layout);
  }

  function suggestion(s) {
    const q = queue(s);
    const card = h("div", { class: "suggest", "aria-live": "polite" });
    if (!q.length) { card.append(h("p", { class: "lead with-ico", style: "margin:0" }, icon("check", "ok"), h("span", { text: t("noProblems") }))); return card; }
    const i = state.cursor[s.file] || 0;
    if (state.lastDone[s.file]) card.append(h("div", { class: "note ok with-ico" }, icon("check"), h("span", { text: t("doneNote", { title: state.lastDone[s.file] }) })));
    if (i >= q.length) {
      card.append(h("p", { class: "lead", text: t("allDone") }),
        h("button", { type: "button", class: "btn btn-tonal", onclick: () => { state.cursor[s.file] = 0; state.lastDone[s.file] = null; render(); } }, t("restart")));
      return card;
    }
    const f = q[i], tx = simple(f.code), dev = deviceByIp(s, f.ip), top = mostDangerous(s);
    card.append(
      h("p", { class: "muted", text: t("suggestSub") }),
      h("div", { class: "suggest-top" }, devIco(dev ? dev.type : "unknown", toneOf(f.severity), true, dev),
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
        h("button", { type: "button", class: "btn btn-filled", onclick: () => { state.lastDone[s.file] = tx.title; state.cursor[s.file] = i + 1; render(); focusSel(".suggest button"); } }, icon("tick"), t("btnDone")),
        q.length > 1 ? h("button", { type: "button", class: "btn", onclick: () => { state.lastDone[s.file] = null; state.cursor[s.file] = (i + 1) % q.length; render(); focusSel(".suggest button"); } }, t("btnSkip")) : null,
        h("span", { class: "progress", text: t("progress", { i: i + 1, n: q.length }) })),
      h("p", { class: "note with-ico" }, icon("users"), h("span", { text: t("helpNote") })),
      techFor(f));
    return card;
  }

  // ---------------------------------------------------------------- DEVICES (tiles + sheet)
  function tiles(s, list) {
    return h("div", { class: "tiles" }, list.map((d) => {
      const probs = problemsOf(s, d), worst = probs[0];
      const tone = worst ? toneOf(worst.severity) : "green";
      const status = worst ? `${RISK[worst.severity][state.lang]} · ${plural(probs.length, "devProblem", "devProblems")}` : t("devOk");
      const vendor = shortVendor(d.vendor);
      return h("button", { type: "button", class: "tile " + tone, onclick: (e) => openDevice(d, e.currentTarget),
        "aria-label": `${deviceLabel(d.type)}${vendor ? ", " + vendor : ""}. ${status}` },
        devIco(d.type, tone === "green" ? "green" : worst.severity, false, d),
        h("div", null, h("div", { class: "tile-name", text: deviceLabel(d.type) }), vendor || d.me ? h("div", { class: "tile-sub", text: (vendor || "") + (vendor ? meSuffix(d) : t("thisPc")) }) : null),
        h("div", { class: "tile-meta" }, h("span", { class: "mono", text: `${t("ipLabel")} ${d.ip}` }), h("span", { class: "mono", text: `${t("macLabel")} ${d.mac || t("unknown")}` })),
        h("div", { class: "tile-status" }, icon(worst ? RISK[worst.severity].icon : "check"), h("span", { text: status })));
    }));
  }

  function renderDevices(root) {
    const s = scan();
    root.append(pageHead(t("devicesTitle"), t("devicesSub")));
    if (s.empty) { root.append(needScanBox()); return; }
    if (s.error) { root.append(errorBox(s)); return; }
    const withP = s.devices.filter((d) => problemsOf(s, d).length);
    const safe = s.devices.filter((d) => !problemsOf(s, d).length);
    const chip = (key, label) => h("button", { type: "button", class: "chip-btn", "aria-pressed": String(state.devFilter === key),
      onclick: () => { state.devFilter = key; render(); focusSel(`.chip-btn[aria-pressed="true"]`); } }, label);
    const sums = { high: "sumHigh", medium: "sumMedium", low: "sumLow" };
    const real = s.findings.filter((f) => f.severity !== "info");
    if (real.length) root.append(h("div", { class: "chips", style: "margin-bottom:12px" }, Object.keys(sums).filter((k) => real.some((f) => f.severity === k))
      .map((k) => h("span", { class: "pill p-" + k }, icon(RISK[k].icon), `${t(sums[k])}: ${real.filter((f) => f.severity === k).length}`))));
    root.append(h("div", { class: "chips", style: "margin-bottom:20px", role: "group" },
      chip("all", t("fAll", { n: s.devices.length })), chip("problems", [icon("alert"), t("fProblems", { n: withP.length })]), chip("safe", [icon("check"), t("fSafe", { n: safe.length })])));
    const list = (state.devFilter === "problems" ? withP : state.devFilter === "safe" ? safe : s.devices)
      .slice().sort((a, b) => b.risk_points - a.risk_points);
    root.append(tiles(s, list));
  }

  // The device sheet: what it is, then EVERY problem it has with its fix, step by step (the former
  // "Fixes" tab lives here now: one place per device, no repetition), then the technical details.
  function fixBlock(s, f, i, n) {
    const tx = simple(f.code);
    return h("section", { class: "fix-block", style: i ? "margin-top:1.6rem;padding-top:1.4rem;border-top:1px solid var(--line, rgba(255,255,255,.08))" : "margin-top:1rem" },
      h("div", { class: "chips", style: "align-items:center" }, f.severity === "info" ? h("span", { class: "pill p-info" }, icon("info"), t("justKnow")) : riskPill(f.severity),
        n > 1 ? h("span", { class: "muted", text: t("problemN", { i: i + 1, n }) }) : null),
      h("h3", { style: "margin-top:.8rem", text: tx.title }),
      h("p", { class: "lead", style: "margin-top:.5rem", text: tx.explain }),
      tx.steps.length ? [h("h4", { text: t("doThis") + ":" }), steps(tx.steps)] : null,
      f.severity !== "info" ? whoLine(f.code) : null,
      guideRow(s, f),
      verifyRow(s, f),
      techFor(f));
  }
  // "Exact steps for TP-Link": the assistant looks on the maker's official site (live app, known maker only)
  function guideRow(s, f) {
    const d = LIVE && f.severity !== "info" && s.scan_id != null ? deviceByIp(s, f.ip) : null;
    if (!d || !d.guide) return null;
    const key = `${s.scan_id}|${f.ip}|${f.code}`, g = state.guides[key], v = d.guide;
    const wrap = h("div", { class: "guide-row", "data-guide": key, style: "margin-top:1rem" });
    if (!g || g.status === "error") {
      wrap.append(h("button", { type: "button", class: "btn btn-tonal", onclick: async (e) => {
        e.stopPropagation();
        state.guides[key] = { status: "pending" }; refreshGuide(key, s, f);
        const res = await api("POST", "/api/v1/guide", { scan_id: s.scan_id, ip: f.ip, code: f.code });
        state.guides[key] = res.ok ? { status: "ok", answer: res.data.answer, sources: res.data.sources || [], official: res.data.official !== false } : { status: "error", message: errText(res) };
        refreshGuide(key, s, f);
      } }, icon("bot"), t("guideBtn", { v })));
      if (g) wrap.append(h("p", { class: "note with-ico", role: "status" }, icon("info"), h("span", { text: g.message })));
    } else if (g.status === "pending") {
      wrap.append(h("p", { class: "note with-ico", role: "status" }, icon("search"), h("span", { text: t("guideWait", { v }) })));
    } else {
      wrap.append(h("div", { class: "guide-box", role: "status" },
        h("h4", { class: "with-ico" }, icon("bot"), h("span", { text: t("guideT", { v }) })),
        h("p", { class: "guide-text", text: g.answer }),
        g.sources.length ? h("ul", { class: "guide-src" }, g.sources.map((x) => h("li", null, h("span", { text: t("guideSrc") + ": " }),
          h("a", { href: x.url, target: "_blank", rel: "noopener noreferrer", text: x.title })))) : h("p", { class: "muted", text: t("guideNone") }),
        h("p", { class: "muted guide-note", text: t(g.official ? "guideNote" : "guideNoteWeb", { v }) })));
    }
    return wrap;
  }
  function refreshGuide(key, s, f) {
    document.querySelectorAll(`[data-guide="${CSS.escape(key)}"]`).forEach((el) => { const fresh = guideRow(s, f); if (fresh) swapKeepFocus(el, fresh); });
  }
  function openDevice(d, opener) {
    const s = scan(), probs = problemsOf(s, d), worst = probs[0], vendor = shortVendor(d.vendor);
    const all = probs.concat(s.findings.filter((f) => f.ip === d.ip && f.severity === "info"));
    const risky = new Set(probs.filter((f) => f.port != null).map((f) => f.port));
    const body = document.getElementById("sheet-body");
    body.replaceChildren(h("div", null,
      h("div", { class: "sheet-head" }, devIco(d.type, worst ? toneOf(worst.severity) : "green", true, d),
        h("div", null, h("h2", { id: "sheet-title", text: deviceLabel(d.type) }), vendor || d.me ? h("div", { class: "muted", text: (vendor || "") + (vendor ? meSuffix(d) : t("thisPc")) }) : null)),
      worst ? h("p", { class: "muted", style: "margin:.6rem 0 0", text: plural(probs.length, "devProblem", "devProblems") }) : null,
      all.length ? all.map((f, i) => fixBlock(s, f, i, all.length)) : null,
      worst ? null : [h("span", { class: "pill p-green", style: "margin-top:1rem" }, icon("check"), t("devOk")),
        h("p", { class: "lead", style: "margin-top:.6rem", text: t("devOkExplain") }),
        h("h4", { text: t("keepSafe") + ":" }), steps(t("devOkSteps"))],
      techBox([
        h("dl", { class: "meta" },
          h("dt", { text: t("ip") }), h("dd", { class: "mono", text: d.ip }),
          h("dt", { text: t("mac") }), h("dd", { class: "mono", text: d.mac || t("unknown") }),
          h("dt", { text: t("vendor") }), h("dd", { text: d.vendor || t("unknown") }),
          h("dt", { text: t("hostname") }), h("dd", { text: d.hostname || t("unknown") })),
        h("div", { class: "muted", style: "margin-bottom:.4rem", text: t("ports") }),
        d.open_ports.length ? h("div", { class: "tags" }, d.open_ports.map((p) => h("span", { class: "port" + (risky.has(p.port) ? " risk" : "") },
          risky.has(p.port) ? icon("alert") : null, `${p.port}/${p.protocol} ${p.service}${p.tls ? " (TLS)" : ""}`))) : h("span", { text: t("none") }),
      ])));
    lastOpener = opener || null;
    const dlg = document.getElementById("sheet");
    if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", "");
    if (window.Device3D) window.Device3D.scan(body);
    body.scrollTop = 0;
    document.getElementById("sheet-close").focus();
  }
  // "See what needs fixing": the devices with problems, the most dangerous one opened
  function showFixes() {
    state.devFilter = "problems";
    closeSheet();
    setTab("devices");
    const s = scan(), top = mostDangerous(s);
    if (top) openDevice(top);
  }
  function closeSheet() {
    const dlg = document.getElementById("sheet");
    if (dlg.open) { if (typeof dlg.close === "function") dlg.close(); else dlg.removeAttribute("open"); }
  }

  // ---------------------------------------------------------------- HISTORY (compare + events timeline)
  // ---------------------------------------------------------------- HISTORY: cyber data dashboard
  // The History tab as a dark command console: glass panels with a thin neon edge whose colour follows the state of the
  // network like a traffic light (green safe, yellow medium risk, red high risk: the colours everyone already knows),
  // white text on a near-solid background, large type, so it reads easily at 80 too. The Before / Now scores as the same
  // dial as Home (ui/assets/score-ring/), the score at each check as a glowing line chart (pure SVG built here: no chart library,
  // the app has to work offline) and the events as a system log. Only real data from the saved history; every
  // animation stops with reduced motion, and every chart point is reachable with the keyboard.
  const NEON = { green: "ok", amber: "warn", red: "bad" };
  const neonOf = (score) => NEON[bandOf(score)] || "ok";
  let cyUid = 0;
  const when = (sec) => (sec ? new Date(sec * 1000).toLocaleString(state.lang === "ro" ? "ro-RO" : "en-GB",
    { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "");
  const scanName = (trend, i) => (i === 0 ? t("before") : i === trend.length - 1 ? t("now") : `#${trend[i].scan_id}`);

  function cyPanel(title, cls, ...kids) {
    return h("section", { class: "cy-panel" + (cls ? " " + cls : "") },
      title ? h("h3", { class: "cy-title" }, h("span", { class: "cy-slash", "aria-hidden": "true", text: "//" }), h("span", { text: title })) : null, kids);
  }

  function renderHistory(root) {
    root.append(pageHead(t("historyTitle"), t("historySub")));
    if (state.historyDeleted) {
      root.append(h("div", { class: "suggest" }, h("p", { class: "lead with-ico", role: "status" }, icon("trash"), h("span", { text: t("deleted") })),
        h("p", { class: "muted", text: t("deletedTech") }),
        h("button", { type: "button", class: "btn btn-tonal", onclick: () => { state.historyDeleted = false; store.set("historyDeleted", "0"); render(); } }, t("restore"))));
      return;
    }
    if (LIVE && !D.scans.length) { root.append(needScanBox()); return; }
    // live: the scan on screen compared with the one saved just before it
    const cur = scan();
    const ch = LIVE ? (cur.error ? D.history.changes : cur.changes || null) : D.history.changes, trend = D.history.trend;
    const lastScore = ch ? ch.score_after : trend.length ? trend[trend.length - 1].network_score : cur.score;
    const deck = h("div", { class: "cyber n-" + neonOf(lastScore == null ? 100 : lastScore) });
    root.append(deck);
    if (!ch) {
      deck.append(h("div", { class: "cy-grid" },
        cyPanel(null, "cy-note", h("p", { class: "with-ico" }, icon("info", "lg"), h("span", { text: t("histNeedTwo") }))),
        trend.length ? cyPanel(t("chartTitle"), null, cyChart(trend)) : null));
      if (LIVE) deck.append(cyPanel(t("deleteTitle"), "cy-danger", h("p", { class: "cy-muted", text: t("deleteSub") }), privacyRow()));
      return;
    }
    const fixed = ch.resolved_findings.length;
    const verdict = ch.score_change > 0 ? (fixed === 1 ? t("bravoOne") : t("bravo", { n: fixed })) : ch.score_change < 0 ? t("worse") : t("same");
    const dial = (label, score, id) => window.ScoreRing.create(score, { of: t("scoreOf"), key: `history|${label}|${id}`,
      aria: `${label}: ${score} ${t("scoreOf")}, ${t("band_" + bandOf(score))}` });
    const col = (label, score, id) => h("div", { class: "cy-col" }, h("span", { class: "cy-col-k", text: label }), dial(label, score, id),
      h("span", { class: "cy-band n-" + neonOf(score) }, icon(BAND_ICON[bandOf(score)]), t("band_" + bandOf(score))));
    const compare = cyPanel(t("cyCompare"), null,
      h("div", { class: "cy-compare" }, col(t("before"), ch.score_before, ch.before_scan_id ?? ch.before_file),
        h("div", { class: "cy-arrow", "aria-hidden": "true" }, h("span"), h("span"), h("span")),
        col(t("now"), ch.score_after, ch.after_scan_id ?? ch.after_file)),
      h("p", { class: "cy-verdict n-" + (ch.score_change < 0 ? "bad" : ch.score_change > 0 ? "ok" : "warn") },
        icon(ch.score_change > 0 ? "sparkles" : ch.score_change < 0 ? "alert" : "info", "lg"), h("span", { text: verdict })));
    const log = cyPanel(t("events"), null, cyLog(ch, trend));
    const chartPanel = cyPanel(t("chartTitle"), null, cyChart(trend), cyTable(trend),
      techBox(h("p", { class: "mono", text: `${ch.before_file} → ${ch.after_file}` })));
    deck.append(h("div", { class: "cy-grid" }, h("div", { class: "cy-stack" }, compare, log), chartPanel));

    const del = cyPanel(t("deleteTitle"), "cy-danger", h("p", { class: "cy-muted", text: t("deleteSub") }),
      h("button", { type: "button", class: "btn btn-danger", onclick: () => { state.confirmDelete = true; render(); focusSel(".confirm button"); } }, icon("trash"), t("deleteBtn")));
    if (state.confirmDelete) {
      del.append(h("div", { class: "confirm", role: "alertdialog", "aria-label": t("deleteBtn") },
        h("p", { class: "lead", text: t("deleteConfirm") }),
        h("div", { class: "actions" },
          h("button", { type: "button", class: "btn btn-danger", onclick: LIVE ? liveDelete : () => { state.historyDeleted = true; state.confirmDelete = false; store.set("historyDeleted", "1"); render(); } }, t("deleteYes")),
          h("button", { type: "button", class: "btn", onclick: () => { state.confirmDelete = false; render(); } }, t("deleteNo")))));
    }
    deck.append(del);
  }

  // The score at each saved check: a smooth glowing line over a gradient area, a fine precision grid, hexagon points
  // in the colour of each check's state (the latest one pulses), and a technical tooltip on hover / keyboard focus.
  function cyChart(trend) {
    const panelW = document.getElementById("panel-history").clientWidth || 1000;
    const W = Math.round(Math.max(300, Math.min(640, (panelW > 900 ? panelW * 0.5 : panelW) - 72)));
    const H = 330, L = 48, R = 22, TOP = 44, B = 52, iw = W - L - R, ih = H - TOP - B, uid = "cy" + ++cyUid, n = trend.length;
    const y = (v) => TOP + ih - (v / 100) * ih;
    const x = (i) => (n === 1 ? L + iw / 2 : L + 30 + (i * (iw - 60)) / (n - 1));
    const pts = trend.map((r, i) => [x(i), y(r.network_score)]);
    const s = svg("svg", { class: "cy-chart", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": t("chartLabel") });
    const defs = svg("defs");
    const area = svg("linearGradient", { id: uid + "-area", x1: "0", y1: "0", x2: "0", y2: "1" });
    area.append(svg("stop", { offset: "0", class: "cy-stop-a", "stop-opacity": "0.55" }), svg("stop", { offset: "0.55", class: "cy-stop-a", "stop-opacity": "0.14" }),
      svg("stop", { offset: "1", class: "cy-stop-a", "stop-opacity": "0" }));
    const glow = svg("filter", { id: uid + "-glow", x: "-30%", y: "-30%", width: "160%", height: "160%" });
    const merge = svg("feMerge");
    merge.append(svg("feMergeNode", { in: "blur" }), svg("feMergeNode", { in: "SourceGraphic" }));
    glow.append(svg("feGaussianBlur", { stdDeviation: "3.2", result: "blur" }), merge);
    defs.append(area, glow);
    s.append(defs);
    // precision grid: a fine line every 10 points, labelled dashed lines at the band limits, a faint column per check
    for (let v = 0; v <= 100; v += 10) s.append(svg("line", { class: [0, 50, 80, 100].includes(v) ? "cy-grid-major" : "cy-grid-minor", x1: L, x2: W - R, y1: y(v), y2: y(v) }));
    [0, 50, 80, 100].forEach((v) => { const lab = svg("text", { class: "cy-axis", x: L - 10, y: y(v) + 6, "text-anchor": "end" }); lab.textContent = String(v); s.append(lab); });
    pts.forEach(([px]) => s.append(svg("line", { class: "cy-grid-v", x1: px, x2: px, y1: TOP, y2: TOP + ih })));
    // the line: a smooth curve through the points that never overshoots the 0-100 range
    let d = "";
    if (n > 1) {
      const c = (v) => Math.max(TOP, Math.min(TOP + ih, v));
      d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
      for (let i = 1; i < n; i++) {
        const p0 = pts[i - 2] || pts[i - 1], p1 = pts[i - 1], p2 = pts[i], p3 = pts[i + 1] || p2, k = 0.18;
        d += ` C${(p1[0] + (p2[0] - p0[0]) * k).toFixed(1)},${c(p1[1] + (p2[1] - p0[1]) * k).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) * k).toFixed(1)},${c(p2[1] - (p3[1] - p1[1]) * k).toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
      }
      s.append(svg("path", { class: "cy-area", fill: `url(#${uid}-area)`, d: `${d} L${pts[n - 1][0].toFixed(1)},${y(0)} L${pts[0][0].toFixed(1)},${y(0)} Z` }));
      s.append(svg("path", { class: "cy-line", d, pathLength: "1", filter: `url(#${uid}-glow)` }));
    }
    const hex = (cx, cy, r) => Array.from({ length: 6 }, (_, i) => { const a = Math.PI / 6 + (i * Math.PI) / 3; return `${(cx + Math.cos(a) * r).toFixed(1)},${(cy + Math.sin(a) * r).toFixed(1)}`; }).join(" ");
    const tip = h("div", { class: "cy-tip", hidden: true, role: "status" });
    trend.forEach((r, i) => {
      const [px, py] = pts[i], tone = neonOf(r.network_score), last = i === n - 1, name = scanName(trend, i);
      const g = svg("g", { class: "cy-node n-" + tone, style: `--i:${i}` });
      if (last) g.append(svg("circle", { class: "cy-pulse", cx: px, cy: py, r: 12 }));
      g.append(svg("polygon", { class: "cy-pt" + (last ? " is-last" : ""), points: hex(px, py, last ? 11 : 9), filter: `url(#${uid}-glow)` }));
      const v = svg("text", { class: "cy-val", x: px, y: py - 20, "text-anchor": "middle" }); v.textContent = String(r.network_score); g.append(v);
      const lab = svg("text", { class: "cy-axis cy-x", x: px, y: H - B + 32, "text-anchor": "middle" }); lab.textContent = name; g.append(lab);
      s.append(g);
      const band = t("band_" + bandOf(r.network_score));
      const label = `${name}: ${r.network_score} ${t("scoreOf")}, ${band}`;
      const slot = n === 1 ? iw : (iw - 60) / (n - 1);
      const hit = svg("rect", { class: "cy-hit", x: px - slot / 2, y: TOP - 24, width: slot, height: ih + 24, tabindex: "0", "aria-label": label });
      const show = () => {
        tip.replaceChildren(
          h("div", { class: "cy-tip-head" }, h("b", { text: `${t("cyWhen")} ${name}` }), r.scanned_at ? h("span", { text: when(r.scanned_at) }) : null),
          h("div", null, h("span", { text: t("colScore") + " " }), h("b", { text: `${r.network_score}/100` }), h("span", { text: ` · ${band}` })),
          h("div", null, h("span", { text: `${t("colFindings")} ` }), h("b", { text: String(r.findings) }),
            r.devices != null ? h("span", { text: ` · ${t("cyDevices")} ${r.devices}` }) : null));
        tip.className = "cy-tip n-" + tone;
        tip.hidden = false;
        const k = s.getBoundingClientRect().width / W;
        tip.style.left = Math.max(130, Math.min(W * k - 130, px * k)) + "px"; tip.style.top = py * k + "px";
        g.classList.add("is-on");
      };
      const hide = () => { tip.hidden = true; g.classList.remove("is-on"); };
      hit.addEventListener("mouseenter", show); hit.addEventListener("focus", show);
      hit.addEventListener("mouseleave", hide); hit.addEventListener("blur", hide);
      s.append(hit);
    });
    return h("div", { class: "cy-chart-wrap" }, s, tip);
  }

  // The checks as a data table in the console style (the same numbers as the chart, for screen readers and exact values).
  function cyTable(trend) {
    return h("table", { class: "cy-table" },
      h("thead", null, h("tr", null, ["colScan", "colScore", "colFindings"].map((k) => h("th", { scope: "col", text: t(k) })))),
      h("tbody", null, trend.map((r, i) => h("tr", { class: "n-" + neonOf(r.network_score) },
        h("td", null, h("span", { class: "cy-dot", "aria-hidden": "true" }), scanName(trend, i), r.scanned_at ? h("span", { class: "cy-when", text: when(r.scanned_at) }) : null),
        h("td", null, h("b", { text: String(r.network_score) }), h("span", { class: "cy-muted", text: "/100" }),
          h("span", { class: "sr", text: ", " + t("band_" + bandOf(r.network_score)) })),     // the dot's colour says the band
        h("td", { text: String(r.findings) })))));
  }

  // What happened between the two checks, as a system log: glowing status icons, thin luminous separators, alerts that
  // pulse, a blinking cursor at the end.
  function cyLog(ch, trend) {
    let i = 0;
    const line = (tone, name, title, sub, stamp) => h("li", { class: "cy-log-line t-" + tone, style: `--i:${i++}` },
      h("span", { class: "cy-stamp", text: stamp }),
      h("span", { class: "cy-log-ico", "aria-hidden": "true" }, icon(name)),
      h("div", { class: "cy-log-text" }, h("strong", { text: title }), sub ? h("span", { class: "cy-log-sub", text: sub }) : null));
    const now = `[${t("now").toUpperCase()}]`, before = `[${t("before").toUpperCase()}]`;
    const after = [];
    ch.resolved_findings.forEach((f) => after.push(line("green", "check", t("evFixed", { title: simple(f.code).title }), null, now)));
    ch.secured_ports.forEach((u) => after.push(line("info", "lock", t("evSecured"), t("evSecuredSub", { from: u.from_port, to: u.to_port }), now)));
    ch.new_findings.forEach((f) => after.push(line("amber", "alert", t("evNew", { title: simple(f.code).title }), null, now)));
    ch.new_devices.forEach((ip) => after.push(line("red", "plus", t("evNewDev"), ip, now)));
    ch.removed_devices.forEach((ip) => after.push(line("neutral", "leave", t("evGoneDev"), ip, now)));
    if (!ch.alerts) after.push(line("green", "shield", t("evQuiet"), null, now));
    const first = (ch.before_scan_id != null && trend.find((r) => r.scan_id === ch.before_scan_id)) || trend[0];
    const firstLine = line(bandOf(first.network_score) === "red" ? "red" : "amber", BAND_ICON[bandOf(first.network_score)],
      t("evFirst", { s: first.network_score, f: first.findings }), first.scanned_at ? when(first.scanned_at) : null, before);
    return h("div", { class: "cy-term" },
      h("div", { class: "cy-term-bar", "aria-hidden": "true" }, h("i"), h("i"), h("i"), h("span", { text: `safehouse ~ ${t("cyLog").toLowerCase()}` })),
      h("ul", { class: "cy-log" }, after, firstLine),
      h("div", { class: "cy-cursor", "aria-hidden": "true", text: ">" }));
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
    return out;
  }
  function classify(q) {
    const s = q.toLowerCase();
    if (/(repar|primul|prima|întâi|intai|fix|first|start)/.test(s)) return "first";
    if (/(imprimant|printer|9100)/.test(s)) return "printer";
    if (/(aparat|dispozitiv|device|ce am|what do i have|conectat|connected)/.test(s)) return "devices";
    return "unknown";
  }
  // live: a real conversation with the assistant (AI through the team gateway, built-in texts as fallback).
  // Findings and scores never come from the AI; it only explains what this scan shows (NFR-06).
  async function liveAsk(q) {
    q = (q || "").trim().slice(0, 500);
    const s = scan();
    if (!q || state.busy || s.empty || s.error) return;
    const turns = [];
    state.chat.filter((m) => m.source === "ai").slice(-6).forEach((m) => turns.push({ role: "user", content: m.q }, { role: "assistant", content: m.a }));
    const item = { q, a: null, mode: null, source: null };
    state.chat.push(item);
    if (state.chat.length > 20) state.chat.shift();
    state.busy = true;
    renderChatPanel();
    const res = await api("POST", "/api/v1/ask", { question: q, scan_id: s.scan_id, history: turns });
    state.busy = false;
    if (res.ok) Object.assign(item, { a: res.data.answer, mode: res.data.mode, source: res.data.source, sources: res.data.sources || [], vendor: res.data.vendor, official: res.data.official !== false });
    else Object.assign(item, { a: errText(res), mode: "error", source: "error" });
    renderChatPanel();
    if (state.chatOpen) focusSel("#ask-input");
  }
  function renderChat(root) {
    const s = scan();
    root.append(h("p", { class: "muted chat-sub", text: LIVE ? t("askSubLive") : t("askSub") }));
    if (s.empty) { root.append(needScanBox()); return; }
    if (s.error) { root.append(errorBox(s)); return; }
    const card = h("div", { class: "chat" });
    card.append(h("div", { class: "bot-name with-ico" }, icon("bot"), h("span", { text: t("botName") })), h("div", { class: "bubble bot", text: t("botHello") }));
    state.chat.forEach((m) => {
      if (m.q !== undefined) {               // live answer
        card.append(h("div", { class: "bubble me", text: m.q }));
        card.append(h("div", { class: "bot-name with-ico" }, icon("bot"), h("span", { text: t("botName") })));
        card.append(h("div", { class: "bubble bot", "aria-busy": String(m.a == null) }, h("span", { class: "txt", style: "white-space:pre-line", text: m.a == null ? t("thinking") : m.a }),
          m.sources && m.sources.length ? h("ul", { class: "guide-src" }, m.sources.map((x) => h("li", null, h("span", { text: t("guideSrc") + ": " }),
            h("a", { href: x.url, target: "_blank", rel: "noopener noreferrer", text: x.title })))) : null));
        if (m.mode === "guide") card.append(h("div", { class: "muted", style: "margin-left:6px", text: t(m.official ? "guideNote" : "guideNoteWeb", { v: m.vendor || "" }) }));
        else if (m.mode && m.mode !== "error") card.append(h("div", { class: "muted", style: "margin-left:6px", text: t("mode_" + m.mode) }));
        return;
      }
      card.append(h("div", { class: "bubble me", text: m.text }));
      const res = answer(m.kind, s).map((x) => ({ x, r: check(x, s) }));
      card.append(h("div", { class: "bot-name with-ico" }, icon("bot"), h("span", { text: t("botName") })));
      res.forEach(({ x, r }) => card.append(h("div", { class: "bubble bot" + (r.ok ? "" : " blocked") },
        h("span", { class: "txt", text: x.text }),
        x.cites.filter((c) => c !== "scan").map((c) => h("span", { class: "proof", title: t("proof") }, icon("search"), h("span", { class: "sr", text: t("proof") + ": " }), c)),
        r.ok ? null : h("span", { class: "why" }, icon("scissors"), h("span", { text: t("blocked", { r: r.reason }) })))));
      const bad = res.filter((z) => !z.r.ok).length;
      card.append(h("div", { class: "muted", style: "margin-left:6px", text: t("verified", { ok: res.length - bad, bad }) }));
    });
    // offline demo (no local agent): answers from our own texts, checked sentence by sentence
    const demoAsk = (kind, text) => { state.chat.push({ kind, text }); if (state.chat.length > 4) state.chat.shift(); renderChatPanel(); focusSel("#ask-input"); };
    const useLive = LIVE;
    const ask = (kind, text) => (useLive ? liveAsk(text) : demoAsk(kind, text));
    card.append(h("div", { class: "chips", style: "margin-top:.5rem" },
      [["first", "q1"], ["devices", "q2"], ["printer", "q3"]].map(([k, key]) => h("button", { type: "button", class: "chip-btn", disabled: useLive && state.busy, onclick: () => ask(k, t(key)) }, icon("message"), t(key))),
      LIVE && state.chat.length ? h("button", { type: "button", class: "chip-btn", onclick: () => { state.chat = []; renderChatPanel(); focusSel("#ask-input"); } }, icon("refresh"), t("newChat")) : null));
    const input = h("input", { type: "text", id: "ask-input", placeholder: t("askPlaceholder"), maxlength: useLive ? "500" : "200", "aria-label": t("askLabel") });
    root.append(card);
    root.append(h("form", { class: "composer", onsubmit: (e) => { e.preventDefault(); const q = input.value.trim(); if (q) ask(classify(q), q); } },
      input, h("button", { type: "submit", class: "btn btn-filled", "aria-label": t("askBtn"), disabled: useLive && state.busy }, h("span", { class: "btn-label", text: t("askBtn") }), icon("send"))));
  }

  // ---------------------------------------------------------------- RESULTS: every check in a table (scores.csv + findings.csv on screen)
  let openExport = null;                               // set by the live app ("Export CSV")
  function renderResults(root) {
    root.append(pageHead(t("resTitle"), t("resSub")));
    // one row per check, in the order they were saved (like scores.csv); unreadable uploads at the end with ERROR
    const rows = LIVE
      ? (D.history.all || D.history.trend).map((r, i) => {
          const x = D.scans.find((y) => y.scan_id === r.scan_id) || null;
          return { no: i + 1, key: "id" + r.scan_id, s: x, label: (x && x.label) || r.file, when: (x && x.when) || "",
            file: r.file, score: r.network_score, error: !!r.error, devices: r.devices, problems: r.findings };
        })
      : D.scans.map((x, i) => ({ no: i + 1, key: "f" + i, s: x, label: x.file, file: x.file, score: x.score, error: !!x.error,
          devices: x.devices.length, problems: x.findings.length }));
    if (!rows.length) {
      root.append(needScanBox());
      return;
    }
    const cur = scan();
    // one selection for the whole app: a row picked here is also the check shown in the top bar (and on Home)
    const sel = rows.find((r) => r.key === state.resSel) || rows.find((r) => r.s && r.s === cur) || rows[rows.length - 1];
    const pick = (r) => {
      const i = r.s ? allScans().indexOf(r.s) : -1;
      if (i >= 0) { if (i !== state.scan) { state.scan = i; state.chat = []; state.verify = {}; } state.resSel = null; }
      else state.resSel = r.key;                       // an old check without details: shown here only
      state.confirmDelete = false;
      render();
      focusSel(`tr[data-key="${r.key}"]`);
    };
    const rating = (r) => r.error ? h("span", { class: "pill p-red" }, icon("x-circle"), t("errorWord")) : bandPill(r.score);
    const table = h("table", { class: "data results" },
      h("thead", null, h("tr", null, ["colNo", "colWhen", "colFile", "colScore", "colRating", "colDevices", "colProblems"]
        .map((k) => h("th", { scope: "col", class: "c-" + k, text: t(k) })))),
      h("tbody", null, rows.map((r) => {
        const tr = h("tr", { tabindex: "0", "data-key": r.key, class: r === sel ? "is-sel" : "", "aria-selected": String(r === sel) },
          h("td", { class: "c-colNo mono", text: String(r.no) }),
          h("td", { class: "c-colWhen" }, h("span", { text: r.when || r.label }),
            r.when && !/^scan_\d{8}_\d{6}\.xml$/.test(r.file) ? h("span", { class: "mob-file mono", text: r.file }) : null),
          h("td", { class: "c-colFile mono", text: r.file }),
          h("td", { class: "c-colScore" }, h("strong", { text: r.error ? "ERROR" : String(r.score) })),
          h("td", { class: "c-colRating" }, rating(r)),
          h("td", { class: "c-colDevices", text: r.error ? "–" : String(r.devices) }),
          h("td", { class: "c-colProblems", text: r.error ? "–" : String(r.problems) }));
        tr.addEventListener("click", () => pick(r));
        tr.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(r); } });
        return tr;
      })));
    root.append(h("div", { class: "suggest" }, h("div", { class: "table-wrap" }, table),
      LIVE ? h("div", { class: "actions" },
        openExport ? h("button", { type: "button", class: "btn", onclick: () => openExport() }, icon("chart"), t("exportBtn")) : null,
        h("button", { type: "button", class: "btn btn-danger res-delete", onclick: () => { state.confirmDelete = true; render(); focusSel(".res-confirm .btn-danger"); } }, icon("trash"), t("resDelete"))) : null,
      LIVE && state.confirmDelete ? h("div", { class: "confirm res-confirm", role: "alertdialog", "aria-label": t("resDelete") },
        h("p", { class: "lead", text: t("resDeleteAsk") }),
        h("div", { class: "actions" },
          h("button", { type: "button", class: "btn btn-danger", onclick: liveDelete }, icon("trash"), t("deleteYes")),
          h("button", { type: "button", class: "btn", onclick: () => { state.confirmDelete = false; render(); focusSel(".res-delete"); } }, t("deleteNo")))) : null));

    // the findings of the selected check (findings.csv on screen)
    const x = sel.s;
    const box = h("div", { class: "suggest", style: "margin-top:20px" },
      h("h3", { class: "with-ico" }, icon("search", "lg"), h("span", { text: `${t("resFindings")} · ${sel.label}` })));
    if (sel.error) box.append(errorBox(x || { file: sel.file, error: "" }));
    else if (!x) box.append(h("p", { class: "muted", text: t("resNoDetail") }));
    else if (!x.findings.length) box.append(h("p", { class: "lead with-ico" }, icon("check", "ok"), h("span", { text: t("resNone") })));
    else box.append(h("div", { class: "table-wrap" }, h("table", { class: "data results findings-table" },
      h("thead", null, h("tr", null, ["colDevice", "colIp", "colPort", "colProblem", "colSeverity", "colCode"].map((k) => h("th", { scope: "col", class: "c-" + k, text: t(k) })))),
      h("tbody", null, x.findings.map((f) => {
        const dev = deviceByIp(x, f.ip);
        return h("tr", null,
          h("td", { class: "c-colDevice", text: deviceName(dev) }),
          h("td", { class: "c-colIp mono", text: f.ip }),
          h("td", { class: "c-colPort mono", text: f.port == null ? "–" : `${f.port}/${f.protocol}` }),
          h("td", { class: "c-colProblem", text: simple(f.code).title }),
          h("td", { class: "c-colSeverity" }, f.severity === "info" ? h("span", { class: "pill p-info" }, icon("info"), t("justKnow")) : riskPill(f.severity)),
          h("td", { class: "c-colCode mono", text: f.code }));
      })))));
    if (x && !sel.error) box.append(h("div", { class: "actions" }, h("button", { type: "button", class: "btn btn-tonal", onclick: () => {
      const i = allScans().indexOf(x); if (i >= 0) { state.scan = i; state.chat = []; } setTab("home"); } }, icon("home"), t("resOpen")),
      LIVE && x.scan_id != null ? h("button", { type: "button", class: "btn", onclick: () => techReport(x.scan_id) }, icon("code"), t("techReport")) : null));
    root.append(box);
  }

  // the technical report of one saved check (.txt, nmap style): downloaded and also kept on disk by the agent
  async function techReport(scanId) {
    showSheet(h("p", { class: "lead", role: "status", text: t("techReporting") }));
    let r;
    try { r = await fetch(`/api/v1/report/${scanId}?lang=${state.lang}`, { method: "POST", credentials: "same-origin" }); }
    catch (e) { problemSheet(t("techReport"), t("connErr")); return; }
    if (!r.ok) { let data = {}; try { data = await r.json(); } catch (e) { /* not JSON */ } problemSheet(t("techReport"), errText({ data, status: r.status })); return; }
    const blob = await r.blob();
    const name = ((r.headers.get("Content-Disposition") || "").match(/filename="([^"]+)"/) || [])[1] || "safehouse_report.txt";
    const a = h("a", { href: URL.createObjectURL(blob), download: name, style: "display:none" });
    document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000);
    let where = "";
    try { where = decodeURIComponent(r.headers.get("X-SafeHouse-Saved-To") || ""); } catch (e) { /* keep empty */ }
    showSheet(h("div", { role: "status" },
      h("div", { class: "sheet-head" }, h("div", { class: "dev-ico green", "aria-hidden": "true" }, icon("check")), h("h2", { id: "sheet-title", text: t("techReportDoneT") })),
      h("p", { class: "lead", style: "margin-top:.6rem", text: t("techReportDone") }),
      where ? [h("p", { class: "muted", text: t("techReportWhere") }), h("p", { class: "evidence mono", text: where })] : null,
      h("div", { class: "actions" }, h("button", { type: "button", class: "btn", onclick: closeSheet }, t("close")))));
  }

  // ---------------------------------------------------------------- „Păzește casa": the guard
  // A card on Home (on / off, what it is doing, the last things it saw) and, while it is on, a small alert in the
  // corner for every new device or newly opened door, with "It's mine" / "I don't know it". The page asks the
  // local agent every few seconds; the agent does the looking (no admin rights, only this network).
  const guardSt = { data: null, timer: null, shown: new Set() };
  const ago = (ts) => {
    const n = Math.max(0, Math.round(Date.now() / 1000 - ts));
    return n < 5 ? t("agoNow") : n < 60 ? t("agoS", { n }) : n < 120 ? t("agoM1") : t("agoM", { n: Math.round(n / 60) });
  };
  const gName = (e) => shortVendor(e.vendor) || (e.private_mac ? t("gPrivate") : t("gUnknownDev"));
  function guardLine(g) {
    if (g && !g.on && g.state === "moved") return t("guardMoved");
    if (!g || !g.on) return t("guardOffS");
    if (g.phase === "waiting") return t("guardWaiting");
    if (g.state === "learning") return t("guardLearning");
    if (g.state === "paused") return t("guardPaused");
    if (g.state === "error") return t("guardError") + (g.error ? ` (${g.error})` : "");
    if (!g.known && !g.seen && g.last_check) return t("guardEmpty");
    const a = g.last_check ? ago(g.last_check) : t("agoNow");
    return g.known ? t("guardWatching", { n: g.known, ago: a }) : t("guardWatching0", { ago: a });
  }
  // the same, in a few words, for the row in the score card (the full sentence is in the sheet)
  function guardShort(g) {
    if (g && !g.on && g.state === "moved") return t("gsMoved");
    if (!g || !g.on) return t("guardOffShort");
    if (g.phase === "waiting") return t("gsWaiting");
    if (g.state === "learning") return t("gsLearning");
    if (g.state === "paused") return t("gsPaused");
    if (g.state === "error") return t("gsError");
    if (!g.known && !g.seen && g.last_check) return t("gsEmpty");
    return t("gsWatching", { n: g.known, ago: g.last_check ? ago(g.last_check) : t("agoNow") });
  }
  // a compact row in the score card (between the house and the network map nothing changes); the details in a sheet
  function guardRow() {
    const g = guardSt.data, on = !!(g && g.on);
    const fresh = on && g.events.filter((e) => e.status === "new").length;
    return h("div", { class: "guard-row" + (on ? " is-on" : "") },
      h("span", { class: "guard-dot", "aria-hidden": "true" }, icon("shield")),
      h("div", { class: "grow" },
        h("strong", { text: t("guardT") + (on ? "" : " · " + t("gOff")) }),
        h("p", { class: "muted guard-line", role: "status", "aria-live": "polite", text: guardShort(g) })),
      on ? h("button", { type: "button", class: "btn btn-text guard-more", "aria-haspopup": "dialog", onclick: (e) => guardSheet(e.currentTarget) },
            fresh ? h("span", { class: "badge", text: String(fresh) }) : null, t("gDetails"))
        : h("button", { type: "button", class: "btn btn-text", id: "guard-start", "aria-label": t("guardStart"), onclick: guardAsk }, t("gStart")));
  }
  function guardSheetBody() {
    const g = guardSt.data || { events: [] }, on = !!g.on, d = g.diag || {};
    return h("div", { class: "guard-sheet" },
      h("div", { class: "sheet-head" }, h("div", { class: "dev-ico" + (on ? " green" : ""), "aria-hidden": "true" }, icon("shield")),
        h("div", null, h("h2", { id: "sheet-title", text: t("guardT") }), h("p", { class: "muted", role: "status", text: guardLine(g) }))),
      g.events.length ? [h("h4", { text: t("gRecent") + ":" }),
        h("ul", { class: "guard-recent" }, g.events.slice(0, 10).map((e) => h("li", null,
          icon(e.kind === "new_device" ? "plus" : "door"),
          h("span", { text: `${t("gNewDevT")}: ${gName(e)} · ${e.ip}` +
            (e.status === "mine" ? ` · ${t("gWasMine")}` : e.status === "stranger" ? ` · ${t("gWasStranger")}` : "") }),
          h("span", { class: "muted", text: ago(e.when) }))))]
        : h("p", { class: "lead", style: "margin-top:1rem", text: t("gNothing") }),
      g.devices && g.devices.length ? [h("h4", { text: t("gDevices", { n: g.devices.length }) }),
        h("p", { class: "muted", style: "margin:.2rem 0 .6rem", text: t("gDevicesS") }),
        h("ul", { class: "guard-devices" }, g.devices.map((d) => h("li", { class: d.mine === false ? "is-stranger" : "" },
          h("span", { class: "gd-ico" + (d.online ? " on" : ""), "aria-hidden": "true" }, icon(d.mine === false ? "alert" : "wifi")),
          h("div", { class: "grow" },
            h("strong", { text: `${gName(d)} · ${d.ip}` }),
            h("span", { class: "muted", text: [d.online ? t("gOnline") : d.last_seen ? t("gSeen", { ago: ago(d.last_seen) }) : "",
              d.mine === true ? t("gWasMine") : d.mine === false ? t("gWasStranger") : ""].filter(Boolean).join(" · ") })),
          h("div", { class: "gd-actions" },
            d.mine !== true ? h("button", { type: "button", class: "btn btn-text", onclick: () => guardDevice(d.id, "mine") }, t("gMine")) : null,
            d.mine !== false ? h("button", { type: "button", class: "btn btn-text", onclick: () => guardDevice(d.id, "stranger") }, t("gStranger")) : null,
            h("button", { type: "button", class: "btn btn-text", "aria-label": `${t("gForgetOne")}: ${gName(d)} ${d.ip}`, onclick: () => guardDevice(d.id, "forget") }, icon("trash"), t("gForgetOne"))))))] : null,
      techBox(h("dl", { class: "meta" },
        h("dt", { text: t("gdNet") }), h("dd", { class: "mono", text: `${g.subnet || "–"} · ${t("gdNow")}: ${d.net_now || "–"}` }),
        h("dt", { text: t("gdHow") }), h("dd", { class: "mono", text: d.how ? `${d.how} · nmap ${d.nmap_rc ?? "–"}` : "–" }),
        h("dt", { text: t("gdTimes") }), h("dd", { class: "mono", text: `#${d.looks ?? 0} · nmap ${d.nmap_s ?? "–"}s · ping ${d.ping_s ?? "–"}s` }),
        h("dt", { text: t("gdSeen") }), h("dd", { class: "mono", text: `nmap: ${d.from_nmap ?? "–"} / ${d.nmap_up ?? "–"} up · ARP: ${d.arp ?? "–"} · ${t("gdKnown")}: ${g.known ?? 0}` }),
        d.nmap_err ? [h("dt", { text: t("gdErr") }), h("dd", { class: "mono", text: d.nmap_err })] : null,
        g.error ? [h("dt", { text: t("gdErr") }), h("dd", { class: "mono", text: g.error })] : null)),
      h("div", { class: "actions" },
        on ? h("button", { type: "button", class: "btn", onclick: guardForget }, icon("refresh"), t("gForget")) : null,
        on ? h("button", { type: "button", class: "btn btn-danger", onclick: () => { closeSheet(); guardSwitch(false); } }, t("guardStop"))
          : h("button", { type: "button", class: "btn btn-cta", onclick: guardAsk }, icon("shield"), t("guardStart")),
        h("button", { type: "button", class: "btn", onclick: closeSheet }, t("close"))));
  }
  async function guardDevice(id, action) {
    const res = await api("POST", "/api/v1/guard/device", { id, action });
    if (res.ok) { guardSt.data = res.data; refreshGuardCard(); }
    if (action === "stranger") strangerSheet();
  }
  async function guardForget() {
    const res = await api("POST", "/api/v1/guard/forget");
    if (res.ok) { guardSt.data = res.data; refreshGuardCard(); guardSchedule(); }
  }
  function guardSheet(opener) {
    showSheet(guardSheetBody(), opener);
    focusSel("#sheet .actions .btn");
  }
  function refreshGuardCard() {
    const swap = (old, fresh) => {
      const det = fresh.querySelector("details");
      if (old.querySelector("details[open]") && det) det.open = true;      // keep "Advanced details" open
      if (fresh.innerHTML !== old.innerHTML || fresh.className !== old.className) swapKeepFocus(old, fresh);
    };
    const row = document.querySelector(".guard-row");
    if (row) swap(row, guardRow());
    const sheet = document.querySelector("#sheet[open] .guard-sheet");
    if (sheet) swap(sheet, guardSheetBody());
  }
  async function guardAsk() {
    showSheet(h("div", { class: "lead", role: "status", text: t("cfPrep") }));
    const res = await api("GET", "/api/v1/status");
    if (!res.ok) return problemSheet(t("probT"), errText(res));
    const net = res.data.network;
    if (!net.ok) return problemSheet(t("probT"), net.message);
    showSheet(h("div", null,
      h("div", { class: "sheet-head" }, h("div", { class: "dev-ico", "aria-hidden": "true" }, icon("shield")), h("h2", { id: "sheet-title", text: t("guardAskT") })),
      h("p", { class: "muted", style: "margin-top:.8rem", text: t("cfNet") }),
      h("p", { class: "lead" }, h("strong", { text: net.wifi || t("topoNet") }), h("span", { class: "mono", text: "  ·  " + net.subnet })),
      h("p", { text: t("guardAsk", { s: (guardSt.data && guardSt.data.interval) || 20 }) }),
      h("p", { class: "lead", text: t("guardAsk2") }),
      h("div", { class: "actions" },
        h("button", { type: "button", class: "btn btn-cta", id: "guard-yes", onclick: () => { closeSheet(); guardSwitch(true); } }, icon("shield"), t("guardYes")),
        h("button", { type: "button", class: "btn", onclick: closeSheet }, t("cfNo")))));
    focusSel("#guard-yes");
  }
  async function guardSwitch(on) {
    const res = await api("POST", "/api/v1/guard", { on, confirm: on });
    if (!res.ok) return problemSheet(t("probT"), errText(res));
    guardSt.data = res.data;
    if (on) res.data.events.forEach((e) => guardSt.shown.add(e.id));   // only what happens from now on
    refreshGuardCard(); guardSchedule();
  }
  function guardSchedule() {
    clearTimeout(guardSt.timer);
    if (guardSt.data && guardSt.data.on) guardSt.timer = setTimeout(guardPoll, 4000);
  }
  async function guardPoll() {
    const res = await api("GET", "/api/v1/guard");
    if (res.ok) {
      guardSt.data = res.data;
      refreshGuardCard();
      renderGuardToasts();
    }
    guardSchedule();
  }
  // the alerts in the corner: one per new event, until the user answers or closes it
  const toastBox = h("div", { class: "guard-toasts", "aria-live": "assertive", "aria-relevant": "additions" });
  document.body.append(toastBox);
  function renderGuardToasts() {
    const evs = (guardSt.data ? guardSt.data.events : []).filter((e) => e.status === "new" && !guardSt.shown.has(e.id)).slice(0, 3);
    const want = new Set(evs.map((e) => e.id));
    toastBox.querySelectorAll(".guard-toast").forEach((el) => { if (!want.has(el.dataset.id)) el.remove(); });
    evs.forEach((e) => {
      const old = toastBox.querySelector(`[data-id="${CSS.escape(e.id)}"]`);
      const fresh = guardToast(e);
      if (old) { if (old.dataset.sig !== fresh.dataset.sig) old.replaceWith(fresh); } else toastBox.append(fresh);
    });
  }
  function guardToast(e) {
    const close = () => { guardSt.shown.add(e.id); renderGuardToasts(); };
    const answer = async (mine) => {
      guardSt.shown.add(e.id); renderGuardToasts();
      await api("POST", "/api/v1/guard/ack", { id: e.id, mine });
      if (!mine) strangerSheet();
      guardPoll();
    };
    // only devices: what doors it has open is for "Inspect the house"
    const el = h("div", { class: "guard-toast", role: "alert", "data-id": e.id, "data-sig": e.status },
      h("div", { class: "gt-head" }, icon("wifi"), h("strong", { text: t("gNewDevT") }),
        h("button", { type: "button", class: "icon-btn gt-x", "aria-label": t("close"), title: t("close"), onclick: close }, icon("x"))),
      h("p", { class: "gt-name", text: `${gName(e)} · ${e.ip}` }),
      h("p", { class: "gt-q", text: t("gKnow") }),
      h("div", { class: "actions" },
        h("button", { type: "button", class: "btn btn-tonal", onclick: () => answer(true) }, icon("check"), t("gMine")),
        h("button", { type: "button", class: "btn", onclick: () => answer(false) }, icon("alert"), t("gStranger"))));
    return el;
  }
  function strangerSheet() {
    const tx = simple("UNKNOWN_DEVICE");
    showSheet(h("div", null,
      h("div", { class: "sheet-head" }, h("div", { class: "dev-ico red", "aria-hidden": "true" }, icon("alert")), h("h2", { id: "sheet-title", text: t("gStrangerT") })),
      h("p", { class: "lead", style: "margin-top:.6rem", text: t("gStrangerS") }),
      steps(tx.steps),
      h("div", { class: "actions" }, h("button", { type: "button", class: "btn", onclick: closeSheet }, t("close")))));
    focusSel("#sheet .actions .btn");
  }

  // ---------------------------------------------------------------- the assistant: a floating button + chat panel
  const chatFab = h("button", { type: "button", class: "chat-fab", id: "chat-fab", "aria-haspopup": "dialog", "aria-controls": "chat-panel",
    onclick: () => openChat() }, icon("message"), h("span", { class: "chat-fab-label" }));
  const chatPanel = h("section", { class: "chat-panel", id: "chat-panel", role: "dialog", "aria-labelledby": "chat-title", hidden: true },
    h("header", { class: "chat-head" }, icon("bot"), h("h2", { id: "chat-title" }),
      h("button", { type: "button", class: "icon-btn chat-close", onclick: () => closeChat() }, icon("x"), h("span", { class: "sr" }))),
    h("div", { class: "chat-body" }));
  chatPanel.addEventListener("keydown", (e) => { if (e.key === "Escape") { e.stopPropagation(); closeChat(); } });
  document.body.append(chatFab, chatPanel);
  function renderChatPanel() {
    chatFab.querySelector(".chat-fab-label").textContent = t("askTitle");
    chatFab.setAttribute("aria-label", t("askTitle"));
    chatFab.title = t("askTitle");
    chatPanel.querySelector("#chat-title").textContent = t("botName");
    chatPanel.querySelector(".chat-close .sr").textContent = t("close");
    chatFab.hidden = state.chatOpen;
    chatPanel.hidden = !state.chatOpen;
    if (!state.chatOpen) return;
    const body = chatPanel.querySelector(".chat-body");
    body.replaceChildren();
    renderChat(body);
    body.scrollTop = body.scrollHeight;              // newest message in view
  }
  function openChat() {
    state.chatOpen = true;
    renderChatPanel();
    focusSel("#ask-input");
  }
  function closeChat() {
    state.chatOpen = false;
    renderChatPanel();
    chatFab.focus();
  }

  // ---------------------------------------------------------------- shell
  const RENDER = { home: renderHome, devices: renderDevices, history: renderHistory, results: renderResults };
  function setTab(name) {
    state.tab = name;
    state.confirmDelete = false;                       // a delete question never follows you to another tab
    TABS.forEach((n) => { document.getElementById("panel-" + n).hidden = n !== name; });
    document.querySelectorAll(".nav-item").forEach((b) => { if (b.dataset.tab === name) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current"); });
    render();
    window.scrollTo({ top: 0 });
  }
  function render() {
    document.documentElement.lang = state.lang;
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.getElementById("lang-ro").setAttribute("aria-pressed", String(state.lang === "ro"));
    document.getElementById("lang-en").setAttribute("aria-pressed", String(state.lang === "en"));
    const sel = document.getElementById("scan-select");
    sel.setAttribute("aria-label", t("scanFile"));
    const list = allScans();
    sel.disabled = !list.length;
    sel.replaceChildren(...(list.length ? list.map((s, i) => h("option", { value: String(i), selected: i === state.scan },
      s.error ? `${s.label || s.file} — ${t("errorWord")}` : `${s.label || s.file} — ${s.score}/100`)) : [h("option", { value: "0" }, t("noScan"))]));
    // top-bar actions: the words are hidden on small screens, so they are also the button's name and tooltip
    const label = (sel, text) => { const b = document.querySelector(sel); if (!b) return; b.querySelector("span").textContent = text; b.setAttribute("aria-label", text); b.title = text; };
    label(".upload-btn", state.uploading ? t("uploading") : t("upload"));
    label("#close-app", t("closeApp"));
    const panel = document.getElementById("panel-" + state.tab);
    panel.replaceChildren();
    RENDER[state.tab](panel);
    renderChatPanel();
    if (window.Device3D) window.Device3D.scan(panel);       // 3D models into every .dev3d slot
  }

  document.getElementById("scan-select").addEventListener("change", (e) => { state.scan = Number(e.target.value); state.chat = []; state.confirmDelete = false; state.resSel = null; render(); });

  // ---------------------------------------------------------------- LIVE: upload a file, close the app, heartbeat
  if (LIVE) {
    // "Upload a check": any nmap XML (e.g. from the lab or the Test Set). Readable files are saved to the history;
    // a broken file is shown with a clear error and is never saved (live check 5).
    const file = h("input", { type: "file", accept: ".xml,text/xml", multiple: true, class: "sr", tabindex: "-1" });
    const upBtn = h("button", { type: "button", class: "btn btn-text upload-btn", onclick: () => file.click() }, icon("plus"), h("span", { text: t("upload") }));
    file.addEventListener("change", async () => {
      if (!file.files.length) return;
      const fd = new FormData();
      Array.from(file.files).forEach((f) => fd.append("files", f, f.name));
      file.value = "";
      state.uploading = true; render();
      const res = await api("POST", "/api/v1/upload", fd);
      state.uploading = false;
      if (!res.ok) { render(); problemSheet(t("probT"), errText(res)); return; }
      // unreadable files are kept by the agent too (shown and exported with ERROR)
      const bad = res.data.errors || [];
      const saved = res.data.saved || [];
      state.justDeleted = false; state.chat = [];
      await reloadData(saved.length ? saved[saved.length - 1] : bad.length ? bad[bad.length - 1].scan_id : -1);
      setTab("home");
      if (bad.length) problemSheet(t("errorTitle"), t("uploadBad"), bad.map((b) => `${b.file}: ${b.error}`).join("\n"));
    });
    // "Export CSV" (FR-15): findings.csv + scores.csv for a whole folder, written by the same code as
    // `python -m netcheck analyze <folder>`; downloaded as one ZIP and also saved under ~/SafeHouse/exports.
    const pickFolder = h("input", { type: "file", multiple: true, webkitdirectory: true, class: "sr", tabindex: "-1" });
    const pickFiles = h("input", { type: "file", multiple: true, accept: ".xml,text/xml", class: "sr", tabindex: "-1" });
    const isXml = (f) => /\.xml$/i.test(f.name) && !f.name.startsWith(".");
    pickFolder.addEventListener("change", () => {
      const all = Array.from(pickFolder.files).filter((f) => !f.name.startsWith("."));
      pickFolder.value = "";
      runExport(all.filter(isXml), all.filter((f) => !isXml(f)).length);
    });
    pickFiles.addEventListener("change", () => { const all = Array.from(pickFiles.files); pickFiles.value = ""; runExport(all, 0); });
    openExport = () => exportSheet();
    function exportSheet() {
      showSheet(h("div", null,
        h("div", { class: "sheet-head" }, h("div", { class: "dev-ico", "aria-hidden": "true" }, icon("chart")), h("h2", { id: "sheet-title", text: t("exportT") })),
        h("p", { class: "lead", style: "margin-top:.6rem", text: t("exportS") }),
        h("div", { class: "actions" },
          h("button", { type: "button", class: "btn btn-cta", id: "ex-folder", onclick: () => pickFolder.click() }, icon("drive"), t("exportFolder")),
          h("button", { type: "button", class: "btn", onclick: () => pickFiles.click() }, icon("plus"), t("exportFiles"))),
        D.scans.length ? h("div", { class: "actions" },
          h("button", { type: "button", class: "btn btn-text", onclick: () => runExport(null, 0) }, icon("chart"), t("exportSaved", { n: D.scans.length }))) : null));
      focusSel("#ex-folder");
    }
    async function runExport(files, skipped) {
      if (files && !files.length) { problemSheet(t("exportT"), t("exportNone")); return; }
      showSheet(h("p", { class: "lead", role: "status", text: t("exporting") }));
      let body;
      if (files) { body = new FormData(); files.forEach((f) => body.append("files", f, f.name)); }
      let r;
      try {
        r = await fetch((files ? "/api/v1/export" : "/api/v1/export/history") + "?lang=" + state.lang,
          { method: "POST", credentials: "same-origin", body });
      } catch (e) { problemSheet(t("exportT"), t("connErr")); return; }
      if (!r.ok) { let data = {}; try { data = await r.json(); } catch (e) { /* not JSON */ } problemSheet(t("exportT"), errText({ data, status: r.status })); return; }
      const blob = await r.blob();
      const name = ((r.headers.get("Content-Disposition") || "").match(/filename="([^"]+)"/) || [])[1] || "safehouse_results.zip";
      const a = h("a", { href: URL.createObjectURL(blob), download: name, style: "display:none" });
      document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000);
      const n = (k) => Number(r.headers.get("X-SafeHouse-" + k) || 0);
      let where = "";
      try { where = decodeURIComponent(r.headers.get("X-SafeHouse-Saved-To") || ""); } catch (e) { /* keep empty */ }
      showSheet(h("div", { role: "status" },
        h("div", { class: "sheet-head" }, h("div", { class: "dev-ico green", "aria-hidden": "true" }, icon("check")), h("h2", { id: "sheet-title", text: t("exportDoneT") })),
        h("p", { class: "lead", style: "margin-top:.6rem", text: t("exportDone", { f: n("Files"), e: n("Errors"), k: n("Findings") }) }),
        skipped ? h("p", { class: "note with-ico" }, icon("info"), h("span", { text: t("exportSkipped", { n: skipped }) })) : null,
        where ? [h("p", { class: "muted", text: t("exportWhere") }), h("p", { class: "evidence mono", text: where })] : null,
        h("div", { class: "actions" }, h("button", { type: "button", class: "btn", onclick: closeSheet }, t("close")))));
    }
    // actions on the right of the top bar (icons only on phones, see styles.css); the file pickers stay hidden
    document.querySelector(".appbar-actions").prepend(upBtn);       // "Export CSV" lives in the Results tab
    document.body.append(file, pickFolder, pickFiles);
    if (D.app_mode) {
      const close = h("button", { type: "button", class: "btn", id: "close-app" }, icon("x"), h("span", { text: t("closeApp") }));
      close.addEventListener("click", async () => {
        await api("POST", "/api/v1/shutdown");
        document.body.replaceChildren(h("p", { class: "lead", style: "padding:3rem;text-align:center", text: t("closedApp") }));
        window.close();
      });
      document.querySelector(".appbar-actions").append(close);
      const beat = () => api("POST", "/api/v1/heartbeat");
      beat(); setInterval(beat, 20000);
    }
    // a check already running (e.g. the page was reloaded): follow it
    api("GET", "/api/v1/status").then((res) => { if (res.ok && res.data.scan && res.data.scan.status === "running") followJob(res.data.scan); });
    // the guard may already be on (page reloaded): show its state, alerts only for what happens from now on
    api("GET", "/api/v1/guard").then((res) => {
      if (!res.ok) return;
      guardSt.data = res.data; res.data.events.forEach((e) => guardSt.shown.add(e.id));
      refreshGuardCard(); guardSchedule();
    });
  }
  ["ro", "en"].forEach((l) => document.getElementById("lang-" + l).addEventListener("click", () => { state.lang = l; store.set("lang", l); render(); }));
  document.querySelectorAll(".nav-item").forEach((b) => b.addEventListener("click", () => { setTab(b.dataset.tab); document.getElementById("main").focus({ preventScroll: true }); }));
  // the SafeHouse logo (side bar on computers, top bar on phones) always goes back to Home
  document.querySelectorAll(".nav-brand, .logo").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    closeSheet();
    setTab("home");
    document.getElementById("main").focus({ preventScroll: true });
  }));
  const dlg = document.getElementById("sheet");
  document.getElementById("sheet-close").addEventListener("click", closeSheet);
  dlg.addEventListener("close", () => { if (lastOpener && document.body.contains(lastOpener)) lastOpener.focus(); });
  dlg.addEventListener("click", (e) => { if (e.target === dlg) closeSheet(); });   // tap outside the sheet

  // Deep links for the pitch: #ask?q=first, #home?lang=en&scan=V3_small_office.xml, #history?theme=light, #devices?open=192.168.1.40
  (function applyHash() {
    const [tab, query] = location.hash.slice(1).split("?");
    const p = new URLSearchParams(query || "");
    const qs = new URLSearchParams(location.search);          // the app window opens /?lang=ro|en
    if (!store.get("lang") && (qs.get("lang") === "en" || qs.get("lang") === "ro")) state.lang = qs.get("lang");
    if (p.get("lang") === "en" || p.get("lang") === "ro") state.lang = p.get("lang");
    const i = allScans().findIndex((s) => s.file === p.get("scan"));
    if (i >= 0) state.scan = i;
    if (p.get("inspect") === "1") state.inspected[scan().file] = true;
    if (p.get("theme") === "light" || p.get("theme") === "dark") document.documentElement.dataset.theme = p.get("theme");
    const q = { first: "q1", devices: "q2", printer: "q3" }[p.get("q")];
    if (q) state.chat = [{ kind: p.get("q"), text: t(q) }];
    if (tab === "findings") { state.devFilter = "problems"; setTab("devices"); }       // old "Fixes" links
    else setTab(TABS.includes(tab) ? tab : "home");
    if (tab === "ask") openChat();                                                        // the assistant
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

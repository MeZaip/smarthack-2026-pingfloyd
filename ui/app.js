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
      hello: "Bună!", helloSub: "Apasă butonul și verificăm împreună dacă rețeaua din casa ta e sigură.",
      homeTitle: "Casa ta digitală", ebHome: "Starea rețelei", ebActive: "Activ", ebDevices: "Aparate", ebOnline: "{n} online",
      ebFindings: "Reparații", ebHistory: "Istoric", ebSaved: "{n} salvate", ebAsk: "Asistent", ebGrounded: "Doar din dovezi",
      hudGateway: "Router", hudOnline: "{n} online", hudPorts: "{n} porturi deschise", hudPort1: "1 port deschis", hudFix: "{n} de reparat", hudFix0: "Nimic de reparat",
      act_red: "Trebuie să acționezi", act_amber: "Merită verificat", act_green: "Totul e în regulă", sevBar: "Nivel de risc",
      fixOne: "Unul pe rând", fixAll: "Vezi toate", fixViewLabel: "Cum vrei să vezi reparațiile",
      fixProgress: "{d} din {n} reparate", fixProgressLabel: "Reparații făcute", fixNow: "Începe cu asta", fixNext: "Următorul lucru",
      btnFixed: "Gata, l-am reparat", moreLeft: "Mai ai {n} lucruri", moreLeft1: "Mai ai un lucru", doneList: "Reparate ({n})", undo: "Anulează",
      markedFixed: "Reparat", markFixed: "Am reparat asta", allFixedT: "Ai reparat tot!", allFixedS: "Inspectează casa din nou ca să vezi cât de sigură e acum.",
      infoNote: "Mai sunt {n} lucruri doar de știut, care nu trebuie reparate. Le vezi la „Vezi toate”.", infoNote1: "Mai e un lucru doar de știut, care nu trebuie reparat. Îl vezi la „Vezi toate”.",
      fixOneSub: "Începem cu lucrul cel mai periculos. Urmează pașii, apasă „Gata, l-am reparat” și trecem la următorul.",
      helpBtn: "Întreabă", helpAria: "Întreabă asistentul: deschide chatul",
      chatSub: "Îți răspund doar cu ce am văzut în verificarea ta.", chatPrivacy: "Nu scrie aici parole sau date personale.",
      chatTyping: "Asistentul se gândește…", chatSuggest: "Poți începe cu una dintre aceste întrebări:", chatMore: "Alte întrebări",
      chatYou: "Tu", chatAi: "Răspuns de la asistentul AI, verificat cu datele din verificare.",
      chatOffline: "Răspuns din textele pregătite de noi (asistentul AI nu e conectat acum).",
      chatRejected: "Asistentul AI a spus ceva ce nu apare în verificare, așa că îți dau răspunsul sigur.",
      chatNew: "Începe din nou", chatTooLong: "Scrie mai scurt, te rog (cel mult 500 de semne).",
      repTitle: "Raport pentru firma IT", repSub: "O pagină cu tot ce am găsit, ca s-o trimiți cuiva care se pricepe la calculatoare.",
      repPdf: "Salvează ca PDF sau tipărește", repHtml: "Descarcă raportul (HTML)", repHint: "La „Salvează ca PDF” alege „Salvează ca PDF” în fereastra de tipărire.",
      repDocTitle: "Raport de securitate a rețelei", repGenerated: "Generat", repScan: "Verificarea", repScore: "Scor",
      repTop: "Pe scurt", repDevices: "Aparate găsite", repFindings: "Probleme găsite", repSev: "Risc", repWhere: "Unde", repProblem: "Problema",
      repFix: "Ce trebuie făcut", repStatus: "Stare", repToDo: "De reparat", repFixedByUser: "Marcat reparat de utilizator", repInfoOnly: "Doar informativ",
      repDevice: "Aparat", repVendor: "Producător", repPorts: "Porturi deschise", repEvidence: "Dovadă", repNone: "Nicio problemă găsită.",
      repNote: "Adresele MAC sunt mascate (se văd doar ultimii 2 octeți). Raportul a fost făcut pe acest calculator; nimic nu a fost trimis pe internet.",
      repFirst: "Primul lucru de reparat",
      showList: "Vezi ca listă", hideList: "Ascunde lista", listTitle: "Lista aparatelor",
      inspect: "Inspectează casa", inspectAgain: "Inspectează din nou",
      topoCore: "Casa ta", topoGateway: "Poarta spre internet", topoHint: "Apasă pe un aparat ca să vezi detaliile.",
      topoNet: "Rețea", topoWhy: "Ce înseamnă", topoAll: "Toate", topoShow: "Arată:", closeEsc: "Închide (Esc)", portOpen: "Deschis", portVuln: "Vulnerabil", portSecure: "criptat",
      tourTitle: "Traseul amenințărilor", tourSub: "Dă scroll: urmărim datele de la un aparat la altul, începând cu cel mai periculos.",
      tourStep: "Aparatul {i} din {n}", tourPort: "port {p}", tourFirst: "Primul pas",
      tourEndT: "Ai parcurs tot traseul", tourEndS1: "Un aparat are uși deschise. Reparațiile, pas cu pas:", tourEndS: "{n} aparate au uși deschise. Reparațiile, pas cu pas:",
      stIdleT: "Casa ta digitală", stIdleS: "Apasă „Inspectează casa” ca să verificăm fiecare ușă.",
      stScanT: "Inspectez casa…", stScanS: "Verific fiecare aparat și fiecare ușă. Durează câteva secunde.",
      stSafeT: "Casa este sigură", stSafeS: "Toate ușile sunt închise. Nu ai nimic de reparat.",
      stVulnT: "Atenție: O ușă este deschisă", stVulnS: "Am găsit {n} lucruri de reparat. Mai jos vezi ce poți face.", stVulnS1: "Am găsit un lucru de reparat. Mai jos vezi ce poți face.",
      stErrT: "Nu am putut citi verificarea", stErrS: "Fișierul verificării e stricat. Alege altă verificare din lista de sus.",
      houseLabel: "Casă 3D într-o grădină. Când o verificăm, o lumină trece peste ea, iar la final ferestrele se aprind.", errorWord: "EROARE",
      devicesFound: "Aparate găsite ({n})", ipLabel: "IP", macLabel: "MAC", otherLang: "EN", whatToDo: "Ce pot face",
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
      progress: "Lucrul {i} din {n}",
      doneNote: "Bravo! Ai rezolvat: {title}. Verifică din nou rețeaua mai târziu ca să vezi scorul nou.",
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
      bravo: "Bravo! Ai reparat {n} lucruri.", bravoOne: "Bravo! Ai reparat un lucru.",
      worse: "Atenție: scorul a scăzut. Uită-te la lucrurile noi de reparat.", same: "Scorul a rămas la fel.",
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
      hello: "Hi!", helloSub: "Press the button and we will check together if the network in your home is safe.",
      homeTitle: "Your Digital Home", ebHome: "Network status", ebActive: "Active", ebDevices: "Devices", ebOnline: "{n} online",
      ebFindings: "Fixes", ebHistory: "History", ebSaved: "{n} saved", ebAsk: "Assistant", ebGrounded: "Evidence only",
      hudGateway: "Router", hudOnline: "{n} online", hudPorts: "{n} open ports", hudPort1: "1 open port", hudFix: "{n} to fix", hudFix0: "Nothing to fix",
      act_red: "Action required", act_amber: "Worth a look", act_green: "All good", sevBar: "Risk level",
      fixOne: "One at a time", fixAll: "See all", fixViewLabel: "How to show the fixes",
      fixProgress: "{d} of {n} fixed", fixProgressLabel: "Fixes done", fixNow: "Start with this", fixNext: "Next thing",
      btnFixed: "Done, I fixed it", moreLeft: "{n} more things to do", moreLeft1: "One more thing to do", doneList: "Fixed ({n})", undo: "Undo",
      markedFixed: "Fixed", markFixed: "I fixed this", allFixedT: "You fixed everything!", allFixedS: "Inspect the house again to see how safe it is now.",
      infoNote: "There are {n} more things just to know, nothing to fix. See them under “See all”.", infoNote1: "There is one more thing just to know, nothing to fix. See it under “See all”.",
      fixOneSub: "We start with the most dangerous thing. Follow the steps, press “Done, I fixed it” and we move on to the next one.",
      helpBtn: "Ask", helpAria: "Ask the assistant: opens the chat",
      chatSub: "I answer only with what I saw in your check.", chatPrivacy: "Do not write passwords or personal details here.",
      chatTyping: "The assistant is thinking…", chatSuggest: "You can start with one of these questions:", chatMore: "Other questions",
      chatYou: "You", chatAi: "Answer from the AI assistant, checked against the data from your check.",
      chatOffline: "Answer from our ready-made texts (the AI assistant is not connected right now).",
      chatRejected: "The AI assistant said something that is not in the check, so here is the safe answer.",
      chatNew: "Start over", chatTooLong: "Please write a shorter question (at most 500 characters).",
      repTitle: "Report for your IT company", repSub: "One page with everything we found, to send to someone who knows computers.",
      repPdf: "Save as PDF or print", repHtml: "Download the report (HTML)", repHint: "For a PDF, choose “Save as PDF” in the print window.",
      repDocTitle: "Network security report", repGenerated: "Generated", repScan: "Check", repScore: "Score",
      repTop: "In short", repDevices: "Devices found", repFindings: "Problems found", repSev: "Risk", repWhere: "Where", repProblem: "Problem",
      repFix: "What to do", repStatus: "Status", repToDo: "To fix", repFixedByUser: "Marked fixed by the user", repInfoOnly: "Information only",
      repDevice: "Device", repVendor: "Maker", repPorts: "Open ports", repEvidence: "Evidence", repNone: "No problems found.",
      repNote: "MAC addresses are masked (only the last 2 bytes are shown). This report was made on this computer; nothing was sent to the internet.",
      repFirst: "First thing to fix",
      showList: "Show as a list", hideList: "Hide the list", listTitle: "List of devices",
      inspect: "Inspect house", inspectAgain: "Inspect again",
      topoCore: "Your home", topoGateway: "Gateway to the internet", topoHint: "Tap a device to see its details.",
      topoNet: "Network", topoWhy: "What it means", topoAll: "All", topoShow: "Show:", closeEsc: "Close (Esc)", portOpen: "Open", portVuln: "Vulnerable", portSecure: "encrypted",
      tourTitle: "Threat path", tourSub: "Scroll: we follow the data from one device to the next, starting with the most dangerous.",
      tourStep: "Device {i} of {n}", tourPort: "port {p}", tourFirst: "First step",
      tourEndT: "That's the whole path", tourEndS1: "One device has open doors. The fixes, step by step:", tourEndS: "{n} devices have open doors. The fixes, step by step:",
      stIdleT: "Your digital home", stIdleS: "Press “Inspect house” so we can check every door.",
      stScanT: "Inspecting the house…", stScanS: "Checking every device and every door. It takes a few seconds.",
      stSafeT: "The house is safe", stSafeS: "All doors are closed. You have nothing to fix.",
      stVulnT: "Warning: A door is open", stVulnS: "We found {n} things to fix. See below what you can do.", stVulnS1: "We found one thing to fix. See below what you can do.",
      stErrT: "We could not read the check", stErrS: "The check file is broken. Pick another check from the list at the top.",
      houseLabel: "3D house in a garden. When we check it, a light passes over it and at the end the windows light up.", errorWord: "ERROR",
      devicesFound: "Devices found ({n})", ipLabel: "IP", macLabel: "MAC", otherLang: "RO", whatToDo: "What I can do",
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
      progress: "Thing {i} of {n}",
      doneNote: "Well done! You fixed: {title}. Check the network again later to see the new score.",
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
      bravo: "Well done! You fixed {n} things.", bravoOne: "Well done! You fixed one thing.",
      worse: "Careful: the score went down. Look at the new things to fix.", same: "The score stayed the same.",
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
    high: { ro: "Risc înalt", en: "High risk", icon: "octagon", tone: "red" },
    medium: { ro: "Risc mediu", en: "Medium risk", icon: "alert", tone: "amber" },
    low: { ro: "Risc mic", en: "Low risk", icon: "info", tone: "low" },
    info: { ro: "Doar de știut", en: "Just so you know", icon: "info", tone: "info" },
  };
  const BAND_ICON = { red: "octagon", amber: "alert", green: "check" };
  const DEVICE_ICON = { router: "router", camera: "video", printer: "printer", nas: "drive", iot: "bulb", tv: "tv", phone: "phone", computer: "laptop", server: "server", unknown: "help" };
  const SIZES = ["100%", "115%", "130%"];
  const TABS = ["home", "findings", "history"];

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
    fixView: store.get("fixView") === "all" ? "all" : "one",   // Fixes: one thing at a time (default) or the full list
    fixed: {}, pick: {},  // scan file -> Set of fixed keys (saved on this computer) / the thing chosen to show now
    homeList: null,      // Home: device list open? (null = open by itself past 14 devices, when the map gets dense)
    cursor: {}, lastDone: {},
    historyDeleted: store.get("historyDeleted") === "1",
    confirmDelete: false,
    hallucinate: false,
    chat: [],            // [{role: "user", text, kind} | {role: "bot", parts: [{text, cites, ok, reason}] | null, text?, mode}]
    chatBusy: false,
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
  // One SVG icon from the sprite in index.html (2px strokes, currentColor, aligned with text by flexbox).
  function icon(name, cls) {
    const el = svg("svg", { class: "ico" + (cls ? " " + cls : ""), "aria-hidden": "true", focusable: "false" });
    el.append(svg("use", { href: "#i-" + name }));
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
  const riskPill = (sev) => h("span", { class: "pill p-" + sev }, icon(RISK[sev].icon), RISK[sev][state.lang]);
  function bandPill(score) {
    const b = bandOf(score);
    return h("span", { class: "pill p-" + b }, icon(BAND_ICON[b]), t("band_" + b));
  }
  // Risk colour of the 3D model's LED and rim light: red high, amber medium, blue low, green safe.
  const MODEL_TONE = { red: "red", high: "red", amber: "amber", medium: "amber", low: "blue", info: "green", green: "green" };
  function devIco(type, tone, big) {
    const t = DEVICE_ICON[type] ? type : "unknown";
    return h("div", { class: "dev-ico dev3d" + (big ? " lg" : "") + (tone ? " " + tone : ""), "aria-hidden": "true",
      "data-type": t, "data-tone": MODEL_TONE[tone] || "green" }, icon(DEVICE_ICON[t]));
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
  function pageHead(title, sub, eyebrow, tone) {
    return h("div", { class: "page-head hud-head" },
      eyebrow ? h("p", { class: "eyebrow-badge" + (tone ? " t-" + tone : "") }, h("span", { class: "pulse-dot", "aria-hidden": "true" }), h("span", { text: eyebrow })) : null,
      h("h2", { text: title }), sub ? h("p", { class: "page-sub", text: sub }) : null);
  }
  // One clear status badge under the score ring + a thin 3-segment severity bar (icon + words, never colour alone).
  function statusBadge(score) {
    const b = bandOf(score);
    return h("p", { class: "status-badge sb-" + b }, icon(BAND_ICON[b]), h("span", { text: `${t("band_" + b)} · ${t("act_" + b)}` }));
  }
  function sevBar(score) {
    const b = bandOf(score), lit = { green: 1, amber: 2, red: 3 }[b];
    return h("div", { class: "sev-bar sv-" + b, "aria-hidden": "true" }, [1, 2, 3].map((i) => h("span", { class: i <= lit ? "on" : "" })));
  }
  // Quick network facts under the 3D house (gateway, devices online, open ports, things to fix).
  function hudChips(s, done) {
    const gw = s.devices.find((d) => d.type === "router");
    const ports = s.devices.reduce((n, d) => n + d.open_ports.length, 0);
    const toFix = s.findings.filter((f) => f.severity !== "info").length;
    const chip = (name, text, cls) => h("li", { class: "hud-chip" + (cls ? " " + cls : "") }, icon(name), h("span", { text }));
    return h("ul", { class: "hud-chips", "aria-label": t("ebHome") },
      chip("wifi", `${t("hudGateway")} ${gw ? gw.ip : "–"}`, "mono-chip"),
      chip("phone", t("hudOnline", { n: s.devices.length })),
      chip("door", ports === 1 ? t("hudPort1") : t("hudPorts", { n: ports })),
      done ? chip(toFix ? "alert" : "check", toFix ? t("hudFix", { n: toFix }) : t("hudFix0"), toFix ? "warn" : "ok") : null);
  }
  function focusSel(sel) { const el = document.querySelector(sel); if (el) el.focus(); }

  // Score ring (Fing) + labelled traffic light.
  function ring(score, small) {
    const b = bandOf(score), r = 52, c = 2 * Math.PI * r;
    const s = svg("svg", { viewBox: "0 0 120 120", "aria-hidden": "true" });
    s.append(svg("circle", { class: "track", cx: 60, cy: 60, r, fill: "none", "stroke-width": 12 }));
    s.append(svg("circle", { class: "val-" + b, cx: 60, cy: 60, r, fill: "none", "stroke-width": 12, "stroke-linecap": "round",
      "stroke-dasharray": `${(score / 100) * c} ${c}` }));
    return h("div", { class: "ring b-" + b + (small === "lg" ? " lg" : small ? " small" : ""), role: "img", "aria-label": `${score} ${t("scoreOf")}, ${t("band_" + b)}` },
      s, h("div", { class: "ring-center", "aria-hidden": "true" }, h("div", { class: "ring-num", text: String(score) }), h("div", { class: "ring-of", text: t("scoreOf") })));
  }
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
      h("div", null, h("p", { class: "glass-main" }), h("p", { class: "glass-alt" })));
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
    const other = state.lang === "ro" ? "en" : "ro";
    hero.querySelector(".glass-ico").replaceChildren(icon(cfg.icon, "lg"));
    hero.querySelector(".glass-main").textContent = t(cfg.title);
    hero.querySelector(".glass-alt").textContent = T[other][cfg.title];
    hero.querySelector(".glass-alt").setAttribute("lang", other);
    if (window.Safehouse3D) window.Safehouse3D.setState(st);
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

  // Points in words: Romanian needs "de" for 20+ ("40 de puncte"), not for 1-19 ("5 puncte").
  function points(n) {
    n = Math.abs(n);
    if (state.lang === "en") return n === 1 ? "1 point" : `${n} points`;
    const r = n % 100;
    return n === 1 ? "1 punct" : (r >= 1 && r <= 19 ? `${n} puncte` : `${n} de puncte`);
  }
  // What the saved history says about the scan on screen. Only real data, never invented numbers.
  function historyFor(s) {
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
  function privacyRow() {
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

  // ---------------------------------------------------------------- HOME: threat path (scroll-telling)
  // The vulnerable devices, most dangerous first, zig-zag down the page on isometric platforms. A data line
  // leaves each device, goes down, turns 90 degrees and reaches the next one. The line is drawn while you
  // scroll (stroke-dashoffset = the "drawSVG" effect), a packet rides on its tip, and the device nearest the
  // middle of the screen is in focus: its platform lights up and its vulnerability card is revealed.
  // Plain JS (scroll + requestAnimationFrame), no GSAP: the app has to work offline on the hotspot.
  const SEV_RANK = { high: 0, medium: 1, low: 2 };
  function threatTour(s) {
    const list = s.devices.map((d) => ({ d, probs: problemsOf(s, d) })).filter((x) => x.probs.length)
      .sort((a, b) => SEV_RANK[a.probs[0].severity] - SEV_RANK[b.probs[0].severity] || b.d.risk_points - a.d.risk_points);
    if (!list.length) return null;
    const stage = (type, tone, label) => h("div", { class: "tour-stage", "aria-hidden": "true" },
      h("div", { class: "iso" }, h("div", { class: "iso-plate p3" }), h("div", { class: "iso-plate p2" }), h("div", { class: "iso-plate p1" }), h("div", { class: "iso-ring" })),
      type ? h("div", { class: "iso-device dev3d", "data-type": type, "data-tone": MODEL_TONE[tone] || "green", "data-float": "" }, icon(DEVICE_ICON[type] || DEVICE_ICON.unknown))
           : h("div", { class: "iso-device" }, icon("shield")),
      label ? h("span", { class: "tour-num", text: label }) : null);
    const nodes = list.map(({ d, probs }, i) => h("li", { class: `tour-node sev-${probs[0].severity} ${i % 2 ? "right" : "left"}` },
      stage(DEVICE_ICON[d.type] ? d.type : "unknown", probs[0].severity, String(i + 1).padStart(2, "0")),
      h("article", { class: "tour-card" },
        h("p", { class: "tour-eyebrow", text: t("tourStep", { i: i + 1, n: list.length }) }),
        h("h4", { text: deviceName(d) }),
        h("p", { class: "tour-ip", text: d.ip }),
        riskPill(probs[0].severity),
        h("ul", { class: "tour-probs" }, probs.map((f) => {
          const tx = simple(f.code);
          return h("li", { class: "sev-" + f.severity },
            h("strong", { text: tx.title }),
            f.port != null ? h("span", { class: "tour-port", text: t("tourPort", { p: `${f.port}/${f.protocol}` }) }) : null,
            tx.steps[0] ? h("p", { class: "tour-fix" }, h("b", { text: t("tourFirst") + ": " }), tx.steps[0]) : null);
        })))));
    const end = h("li", { class: `tour-node end ${list.length % 2 ? "right" : "left"}` }, stage(null),
      h("article", { class: "tour-card" },
        h("h4", { text: t("tourEndT") }),
        h("p", { text: list.length === 1 ? t("tourEndS1") : t("tourEndS", { n: list.length }) }),
        h("button", { type: "button", class: "btn btn-filled", onclick: () => setTab("findings") }, icon("shield"), t("seeFixes"))));
    const svgEl = svg("svg", { class: "tour-svg", "aria-hidden": "true" });
    ["tour-base", "tour-glow", "tour-line"].forEach((c) => svgEl.append(svg("path", { class: c })));
    svgEl.append(svg("circle", { class: "tour-packet", r: 6 }));
    return h("section", { class: "section tour", "aria-labelledby": "tour-title" },
      h("div", { class: "section-head" }, h("h3", { id: "tour-title", class: "with-ico" }, icon("wifi", "lg"), h("span", { text: t("tourTitle") }))),
      h("p", { class: "section-sub", text: t("tourSub") }),
      h("div", { class: "tour-map" }, svgEl, h("ol", { class: "tour-nodes" }, nodes, end)));
  }

  let tourState = null;
  function startTour(section) {
    const map = section.querySelector(".tour-map"), svgEl = map.querySelector(".tour-svg");
    const [base, glow, line] = svgEl.querySelectorAll("path"), packet = svgEl.querySelector(".tour-packet");
    const nodes = [...map.querySelectorAll(".tour-node")];
    const st = { map, nodes, len: 0, y0: 0, y1: 1, ticking: false };
    tourState = st;
    function layout() {                       // the path from node to node: down, 90-degree turn, down
      const mr = map.getBoundingClientRect();
      const pts = nodes.map((n) => {
        const r = n.querySelector(".iso-device").getBoundingClientRect(), p = n.querySelector(".iso").getBoundingClientRect();
        return { x: r.left + r.width / 2 - mr.left, top: r.top - mr.top - 6, bottom: p.bottom - mr.top - 10 };
      });
      let d = `M${pts[0].x.toFixed(1)},${pts[0].bottom.toFixed(1)}`;
      for (let i = 1; i < pts.length; i++) {
        const a = pts[i - 1], b = pts[i], mid = (a.bottom + b.top) / 2;
        d += ` V${mid.toFixed(1)} H${b.x.toFixed(1)} V${b.top.toFixed(1)}`;
        if (i < pts.length - 1) d += ` M${b.x.toFixed(1)},${b.bottom.toFixed(1)}`;   // the line passes behind the device
      }
      svgEl.setAttribute("width", mr.width); svgEl.setAttribute("height", mr.height);
      svgEl.setAttribute("viewBox", `0 0 ${mr.width} ${mr.height}`);
      [base, glow, line].forEach((pth) => pth.setAttribute("d", d));
      st.len = line.getTotalLength();
      [glow, line].forEach((pth) => { pth.style.strokeDasharray = `${st.len} ${st.len}`; });
      st.y0 = pts[0].bottom; st.y1 = pts[pts.length - 1].top;
      update();
    }
    function update() {
      st.ticking = false;
      if (!map.isConnected) return;
      const mr = map.getBoundingClientRect(), vh = window.innerHeight, still = reducedMotion();
      // how far the middle of the screen has travelled between the first and the last device -> line drawn
      const tip = vh * 0.55 - mr.top;
      const p = still ? 1 : Math.max(0, Math.min(1, (tip - st.y0) / Math.max(1, st.y1 - st.y0)));
      const drawn = st.len * p;
      [glow, line].forEach((pth) => { pth.style.strokeDashoffset = String(st.len - drawn); });
      const pt = line.getPointAtLength(drawn);
      packet.setAttribute("cx", pt.x); packet.setAttribute("cy", pt.y);
      packet.style.opacity = p > 0.002 && p < 0.998 ? "1" : "0";
      // focus: the device nearest the middle of the screen
      let best = -1, bestD = Infinity;
      nodes.forEach((n, i) => {
        const r = n.querySelector(".tour-stage").getBoundingClientRect(), c = r.top + r.height / 2, dist = c - vh * 0.5;
        if (Math.abs(dist) < bestD) { bestD = Math.abs(dist); best = i; }
        n.style.setProperty("--dist", still ? "0" : (dist / vh).toFixed(3));          // parallax of the platforms
      });
      nodes.forEach((n, i) => {
        n.classList.toggle("is-active", still || i === best);
        n.classList.toggle("is-done", !still && i < best);
      });
      map.style.setProperty("--py", still ? "0px" : `${(-mr.top * 0.15).toFixed(1)}px`);   // background drifts slower
    }
    st.layout = layout;
    st.onScroll = () => { if (!st.ticking) { st.ticking = true; requestAnimationFrame(update); } };
    requestAnimationFrame(layout);
  }
  window.addEventListener("scroll", () => { if (tourState) tourState.onScroll(); }, { passive: true });
  window.addEventListener("resize", () => { if (tourState && tourState.map.isConnected) tourState.layout(); });

  function renderHome(root) {
    const s = scan();
    const done = !!state.inspected[s.file];
    const st = state.scanning ? "scanning" : done ? resultOf(s) : "idle";
    const toFix = s.error ? 0 : s.findings.filter((f) => f.severity !== "info").length;

    // right column: score, status pills and the call to action, centred in one card
    const pendingRing = h("div", { class: "ring b-none lg", "aria-hidden": "true" },
      (() => { const g = svg("svg", { viewBox: "0 0 120 120" }); g.append(svg("circle", { class: "track", cx: 60, cy: 60, r: 52, fill: "none", "stroke-width": 12 })); return g; })(),
      h("div", { class: "ring-center" }, h("div", { class: "ring-num", text: "–" }), h("div", { class: "ring-of", text: t("scoreOf") })));
    const scoreCard = h("div", { class: "score-card" },
      h("p", { class: "eyebrow muted", text: t("scoreTitle") }),
      done && !s.error ? ring(s.score, "lg") : pendingRing,
      done && !s.error ? statusBadge(s.score) : null,
      done && !s.error ? sevBar(s.score) : null,
      h("p", { class: "lead", text: !done || s.error ? (s.error && done ? t("stErrS") : t("scorePending"))
        : toFix === 0 ? t("summaryNone", { d: s.devices.length }) : toFix === 1 ? t("summaryOne", { d: s.devices.length }) : t("summary", { d: s.devices.length, f: toFix }) }),
      done && !s.error ? h("div", { class: "changes" }, trendRow(s), newDeviceBadge(s)) : null,
      h("div", { class: "actions" },
        // with things to fix, "See what needs fixing" is the main action and "Inspect again" the quiet one
        done && toFix ? h("button", { type: "button", class: "btn btn-cta fix-btn", onclick: () => setTab("findings") },
          icon("shield"), h("span", { text: t("seeFixes") }), h("span", { class: "count-badge", "aria-hidden": "true", text: String(toFix) })) : null,
        h("button", { type: "button", class: "btn inspect-btn " + (done && toFix ? "btn-ghost" : "btn-cta"), onclick: inspect }, icon(done ? "refresh" : "search"), done ? t("inspectAgain") : t("inspect"))),
      privacyRow(),
      // screen-reader status (the glass badge over the house is the visible one)
      h("div", { class: "house-status sr", role: "status", "aria-live": "polite" },
        h("div", { class: "hs-icon" }), h("div", null, h("p", { class: "hs-title" }), h("p", { class: "hs-sub" }))));

    const band = done && !s.error ? bandOf(s.score) : "none";
    root.append(h("section", { class: "hero premium bento", "data-state": st, "data-band": band, "aria-label": "SafeHouse" },
      h("div", { class: "stage-col" },
        pageHead(t("homeTitle"), t("helloSub"), `${t("ebHome")} · ${t("ebActive")}`, band),
        h("div", { class: "stage-wrap" }, houseScene(), h("div", { class: "scanline", "aria-hidden": "true" })),
        s.error ? null : hudChips(s, done)),
      scoreCard));
    const mountEl = root.querySelector(".house3d-mount");
    if (mountEl) window.Safehouse3D.mount(mountEl);
    applyHouseState(st);

    if (!done) return;                       // results appear after the house is inspected
    if (s.error) { root.append(h("div", { class: "section" }, errorBox(s))); return; }

    // Traseul amenințărilor: the vulnerable devices one after another, revealed while scrolling
    const tour = threatTour(s);
    root.append(tour || h("section", { class: "section" },
      h("div", { class: "section-head" }, h("h3", { class: "with-ico" }, icon("door", "lg"), h("span", { text: t("doorsOpen", { n: 0 }) }))),
      h("div", { class: "suggest" }, h("p", { class: "lead with-ico", style: "margin:0" }, icon("check", "ok"), h("span", { text: t("doorsNone") })))));
    if (tour) startTour(tour);

    // Aparate găsite: network topology (gateway in the middle, devices around it, click = details panel)
    const topo = topology(s), list = deviceList(s);
    root.append(h("section", { class: "section", id: "devices" },
      h("div", { class: "section-head" }, h("h3", { class: "with-ico" }, icon("wifi", "lg"), h("span", { text: t("devicesFound", { n: s.devices.length }) })), list.btn),
      h("p", { class: "section-sub", text: t("topoHint") }),
      topo, list.box));
    startTopology(topo, s);
  }

  // ---------------------------------------------------------------- HOME: network topology graph
  // The router is the glowing core (gateway) with a radar sweep around it; every other device is a node on rings
  // around it, joined by a thin data line (cyan = safe, orange = medium, red = high risk) with a packet travelling
  // along it (faster on riskier links). A legend above the graph filters the devices by risk. Rings fill up from
  // the inside, riskiest first, and get more room the further out they are, so the same layout holds up to ~200
  // devices (past 14 devices the nodes shrink to glowing dots with the name on hover/focus). Clicking a node
  // slides in a translucent glass panel with a subtle grunge texture: name, IP + MAC (masked), risk badge, open
  // ports, a plain explanation and "What I can do"; its boxes appear one by one behind a scan line.
  const TOPO_SEVS = ["high", "medium", "low", "safe"];
  const PKT_DUR = { high: 1.4, medium: 2.2, low: 2.8, safe: 3.6 };
  let topoUid = 0;
  function topology(s) {
    const svgEl = svg("svg", { class: "topo-svg", "aria-hidden": "true" });
    return h("div", { class: "topo" },
      h("div", { class: "topo-main" },
        h("div", { class: "topo-bar", role: "group", "aria-label": t("topoShow") }),
        h("div", { class: "topo-graph" }, h("div", { class: "topo-radar", "aria-hidden": "true" }), svgEl)),
      h("aside", { class: "topo-panel grunge", "aria-live": "polite", "aria-label": t("topoNet") }));
  }
  function startTopology(root, s) {
    const graph = root.querySelector(".topo-graph"), svgEl = graph.querySelector(".topo-svg"), panel = root.querySelector(".topo-panel");
    const bar = root.querySelector(".topo-bar"), radar = graph.querySelector(".topo-radar");
    const uid = "topo" + ++topoUid, still = reducedMotion();
    const gw = s.devices.find((d) => d.type === "router") || null;
    const others = s.devices.filter((d) => d !== gw).map((d) => ({ d, probs: problemsOf(s, d) }))
      .sort((a, b) => (a.probs.length ? SEV_RANK[a.probs[0].severity] : 9) - (b.probs.length ? SEV_RANK[b.probs[0].severity] : 9) || b.d.risk_points - a.d.risk_points);
    const sevOf = (probs) => (probs.length ? probs[0].severity : "safe");
    const sevLabel = (k) => (k === "safe" ? t("devOk") : RISK[k][state.lang]);
    const sevIcon = (k) => (k === "safe" ? "check" : RISK[k].icon);
    const small = others.length > 14;
    let selected = null, filter = null;

    function nodeBtn(d, probs, core) {
      const sev = sevOf(probs), vendor = shortVendor(d.vendor);
      const b = h("button", { type: "button", class: `topo-node sev-${sev}${core ? " core" : ""}${small && !core ? " dot" : ""}`,
          "aria-label": `${vendor || deviceLabel(d.type)}, ${deviceLabel(d.type)}, ${d.ip}. ${sevLabel(sev)}`, "aria-pressed": "false" },
        h("span", { class: "topo-orb" }, small && !core ? icon(DEVICE_ICON[d.type] || DEVICE_ICON.unknown)
          : h("span", { class: "dev3d topo-model", "aria-hidden": "true", "data-type": DEVICE_ICON[d.type] ? d.type : "unknown",
              "data-tone": MODEL_TONE[sev] || "green", "data-float": "" }, icon(DEVICE_ICON[d.type] || DEVICE_ICON.unknown))),
        h("span", { class: "topo-label" }, h("strong", { text: vendor || deviceLabel(d.type) }),
          h("span", { text: core ? t("topoGateway") : sevLabel(sev) })));
      b.addEventListener("click", () => select(d, b));
      return b;
    }
    const coreEl = gw ? nodeBtn(gw, problemsOf(s, gw), true)
      : h("div", { class: "topo-node core sev-safe" }, h("span", { class: "topo-orb" }, icon("home")), h("span", { class: "topo-label" }, h("strong", { text: t("topoCore") })));
    const items = others.map(({ d, probs }) => ({ d, probs, sev: sevOf(probs), el: nodeBtn(d, probs, false) }));
    graph.append(coreEl, ...items.map((x) => x.el));
    const gRings = svg("g", { class: "topo-rings" });
    svgEl.append(gRings);
    const paths = items.map((x, i) => { const p = svg("path", { class: "topo-link sev-" + x.sev, id: `${uid}-l${i}` }); svgEl.append(p); return p; });

    // data packets: one per link, from the device towards the gateway (only the risky links when there are many
    // devices); none at all with reduced motion
    const pkts = [];
    if (!still) items.forEach((x, i) => {
      if (small && x.sev === "safe") return;
      const dur = PKT_DUR[x.sev];
      const c = svg("circle", { class: "topo-pkt sev-" + x.sev, r: small ? 2.5 : 3.5 });
      const m = svg("animateMotion", { dur: dur + "s", repeatCount: "indefinite", begin: `-${((i * 0.37) % dur).toFixed(2)}s`,
        keyPoints: "1;0", keyTimes: "0;1", calcMode: "linear" });
      const mp = svg("mpath", { href: `#${uid}-l${i}` });
      mp.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", `#${uid}-l${i}`);
      m.append(mp); c.append(m); svgEl.append(c); pkts.push({ c, i });
    });

    // legend = filter: "All" + one chip per risk level that is present, each with icon, words and a count
    const counts = { high: 0, medium: 0, low: 0, safe: 0 };
    items.forEach((x) => { counts[x.sev]++; });
    const chips = [h("button", { type: "button", class: "btn-hud chip all", "data-f": "", "aria-pressed": "true" },
      h("span", { text: t("topoAll") }), h("span", { class: "chip-n", text: String(items.length) }))];
    TOPO_SEVS.filter((k) => counts[k]).forEach((k) => chips.push(h("button", { type: "button", class: `btn-hud chip sev-${k}`, "data-f": k, "aria-pressed": "false" },
      icon(sevIcon(k)), h("span", { text: sevLabel(k) }), h("span", { class: "chip-n", text: String(counts[k]) }))));
    if (items.length) bar.append(h("span", { class: "topo-bar-k", text: t("topoShow") }), ...chips);
    chips.forEach((c) => c.addEventListener("click", () => setFilter(c.dataset.f && c.dataset.f !== filter ? c.dataset.f : null)));
    function setFilter(f) {
      filter = f;
      chips.forEach((c) => c.setAttribute("aria-pressed", String((c.dataset.f || null) === filter)));
      items.forEach((x, i) => {
        const off = !!filter && x.sev !== filter;
        x.el.classList.toggle("is-filtered", off);
        paths[i].classList.toggle("is-filtered", off);
        x.el.classList.toggle("is-match", !!filter && !off);          // stays lit even while a panel dims the rest
        paths[i].classList.toggle("is-match", !!filter && !off);
      });
      pkts.forEach((p) => p.c.classList.toggle("is-filtered", !!filter && items[p.i].sev !== filter));
    }

    function layout() {
      const W = graph.clientWidth, H = graph.clientHeight;
      if (!W) return;
      const cx = W * 0.5, cy = H * 0.5;
      const sx = W > H ? 1.35 : 1, sy = H > W ? 1.42 : 1;       // stretch the rings along the long side of the graph
      coreEl.style.left = cx + "px"; coreEl.style.top = cy + "px";
      svgEl.setAttribute("viewBox", `0 0 ${W} ${H}`);
      gRings.replaceChildren();
      // rings: radius grows outwards; each ring holds as many nodes as fit at the minimum spacing
      const narrow = W < 600;
      const spacing = small ? 34 : narrow ? 120 : 150, r0 = Math.min(W, H) * (small ? 0.2 : narrow ? 0.42 : 0.34), gap = small ? 34 : 120;
      let k = 0, ring = 0, maxR = r0;
      while (k < items.length) {
        const r = r0 + ring * gap, cap = Math.max(1, Math.floor((2 * Math.PI * r) / spacing)), n = Math.min(cap, items.length - k);
        const off = -Math.PI / 2 + (ring % 2 ? Math.PI / n : 0);
        gRings.append(svg("ellipse", { class: "topo-ring", cx, cy, rx: r * sx, ry: r * sy }));
        maxR = r;
        for (let i = 0; i < n; i++, k++) {
          const a = n === 1 ? -Math.PI / 2 : off + (i / n) * 2 * Math.PI;
          const x = cx + Math.cos(a) * r * sx, y = cy + Math.sin(a) * r * sy;
          const it = items[k];
          it.el.style.left = x + "px"; it.el.style.top = y + "px";
          const mx = (cx + x) / 2, my = (cy + y) / 2, bend = 0.18;                          // soft curve, not a straight wire
          paths[k].setAttribute("d", `M${cx},${cy} Q${mx - (y - cy) * bend},${my + (x - cx) * bend} ${x},${y}`);
        }
        ring++;
      }
      // the radar covers the outer ring (an ellipse like the rings; only its gradient angle turns)
      radar.style.left = cx + "px"; radar.style.top = cy + "px";
      radar.style.width = 2 * (maxR * sx + 40) + "px"; radar.style.height = 2 * (maxR * sy + 40) + "px";
    }

    function portsOf(d, probs) {
      const vuln = new Map(probs.filter((f) => f.port != null).map((f) => [f.port + "/" + f.protocol, f]));
      return d.open_ports.map((p) => {
        const f = vuln.get(p.port + "/" + p.protocol);
        return h("li", { class: f ? "sev-" + f.severity : "" },
          h("span", { class: "topo-port", text: `${p.port}/${p.protocol}` }),
          h("span", { class: "topo-svc", text: (p.service || "?").toUpperCase() + (p.tls ? " · " + t("portSecure") : "") }),
          h("span", { class: "topo-state" }, icon(f ? RISK[f.severity].icon : p.tls ? "lock" : "door"), f ? t("portVuln") : t("portOpen")));
      });
    }
    function select(d, btn) {
      if (selected && selected.btn === btn) { close(); return; }
      if (selected) selected.btn.setAttribute("aria-pressed", "false");
      selected = { d, btn };
      btn.setAttribute("aria-pressed", "true");
      const probs = problemsOf(s, d), worst = probs[0], vendor = shortVendor(d.vendor), sev = worst ? worst.severity : "safe";
      const ports = portsOf(d, probs);
      const box = (title, i, ...kids) => h("section", { class: "topo-box grunge", style: `--i:${i}` }, h("p", { class: "topo-k", text: title }), kids);
      panel.className = `topo-panel grunge sev-${sev}`;
      panel.replaceChildren(
        h("div", { class: "topo-ph", style: "--i:0" }, devIco(d.type, worst ? toneOf(worst.severity) : "green"),
          h("div", { class: "grow" }, h("h4", { text: vendor ? `${vendor} · ${deviceLabel(d.type)}` : deviceLabel(d.type) }), d.hostname ? h("p", { class: "muted", text: d.hostname }) : null),
          h("div", { class: "topo-xwrap" }, h("kbd", { class: "topo-esc", "aria-hidden": "true", text: "Esc" }),
            h("button", { type: "button", class: "btn-hud icon topo-x", "aria-label": t("closeEsc"), title: t("closeEsc"), onclick: close }, icon("x")))),
        h("div", { class: "topo-risk", style: "--i:1" }, worst ? riskPill(worst.severity) : h("span", { class: "pill p-green" }, icon("check"), t("devOk"))),
        box(t("topoNet"), 2, h("dl", { class: "topo-dl" }, h("dt", { text: t("ipLabel") }), h("dd", { text: d.ip }), h("dt", { text: t("macLabel") }), h("dd", { text: d.mac || t("unknown") }))),
        box(t("ports"), 3, ports.length ? h("ul", { class: "topo-ports" }, ports) : h("p", { class: "muted", style: "margin:0", text: t("none") })),
        box(t("topoWhy"), 4, h("p", { class: "topo-why", text: worst ? simple(worst.code).explain : t("devOkExplain") })),
        h("button", { type: "button", class: "btn-hud primary topo-cta", style: "--i:5", onclick: (e) => openDevice(d, e.currentTarget) },
          icon("shield"), h("span", { class: "grow", text: t("whatToDo") }), icon("chevron", "go")),
        h("div", { class: "topo-scan", "aria-hidden": "true" }));
      if (window.Device3D) window.Device3D.scan(panel);     // 3D model in the panel header
      // replay the reveal (scan line + boxes one by one) for every device that is opened
      if (!still) { void panel.offsetWidth; panel.classList.add("is-revealing"); }
      panel.scrollTop = 0;
      root.classList.add("open");
      graph.querySelectorAll(".topo-node").forEach((n) => n.classList.toggle("is-dim", n !== btn && !n.classList.contains("core")));
      paths.forEach((p, i) => p.classList.toggle("is-on", items[i].el === btn));
      requestAnimationFrame(layout);
    }
    function close() {
      if (!selected) return;
      const btn = selected.btn;
      btn.setAttribute("aria-pressed", "false");
      selected = null;
      root.classList.remove("open");
      graph.querySelectorAll(".topo-node").forEach((n) => n.classList.remove("is-dim"));
      paths.forEach((p) => p.classList.remove("is-on"));
      requestAnimationFrame(layout);
      btn.focus({ preventScroll: true });
    }
    root.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
    // re-layout when the graph area changes size (window resize, panel opening)
    const ro = new ResizeObserver(() => layout());
    ro.observe(graph);
    requestAnimationFrame(layout);
  }

  // Device cards: icon, name, IP and a very simple explanation (max 2 sentences) in both languages.
  function explainIn(lang, d, worst) {
    return worst ? D.simple[worst.code][lang].explain : T[lang].devOkExplain;
  }
  function deviceCards(s) {
    const other = state.lang === "ro" ? "en" : "ro";
    return h("div", { class: "grid-devices" }, s.devices.slice().sort((a, b) => b.risk_points - a.risk_points).map((d) => {
      const probs = problemsOf(s, d), worst = probs[0], vendor = shortVendor(d.vendor);
      const name = vendor || deviceLabel(d.type);
      const card = h("article", { class: "dcard", tabindex: "0", "aria-label": `${deviceLabel(d.type)} ${vendor}, ${t("ipLabel")} ${d.ip}, ${t("macLabel")} ${d.mac || t("unknown")}. ${worst ? RISK[worst.severity][state.lang] : t("devOk")}.` },
        h("div", { class: "dcard-head" }, devIco(d.type, worst ? toneOf(worst.severity) : "green"),
          h("div", null, h("h3", { text: name }), h("div", { class: "sub", text: deviceLabel(d.type) }))),
        h("dl", { class: "dcard-meta" },
          h("dt", { text: t("ipLabel") }), h("dd", { class: "mono", text: d.ip }),
          h("dt", { text: t("macLabel") }), h("dd", { class: "mono", text: d.mac || t("unknown") })),
        worst ? riskPill(worst.severity) : h("span", { class: "pill p-green" }, icon("check"), t("devOk")),
        h("p", { lang: state.lang, style: "margin-top:.8rem", text: explainIn(state.lang, d, worst) }),
        h("p", { class: "other", lang: other }, h("span", { class: "lang-tag", text: t("otherLang") + ":" }), explainIn(other, d, worst)),
        h("button", { type: "button", class: "btn btn-text", onclick: (e) => { e.stopPropagation(); openDevice(d, card); } }, t("whatToDo"), icon("chevron")));
      card.addEventListener("click", () => openDevice(d, card));
      card.addEventListener("keydown", (e) => { if (e.target === card && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); openDevice(d, card); } });
      return card;
    }));
  }

  // ---------------------------------------------------------------- FIXES: one thing at a time
  // "Done, I fixed it" is the user's own note (saved only in this browser); the score changes only after a new check.
  const fixKey = (f) => f.code + "@" + where(f);
  function fixedOf(file) {
    if (!state.fixed[file]) {
      let a = [];
      try { a = JSON.parse(store.get("fixed." + file) || "[]"); } catch (e) { a = []; }
      state.fixed[file] = new Set(Array.isArray(a) ? a : []);
    }
    return state.fixed[file];
  }
  function setFixed(file, key, on) {
    const set = fixedOf(file);
    if (on) set.add(key); else set.delete(key);
    store.set("fixed." + file, JSON.stringify([...set]));
  }
  function fixProgress(q, set) {
    const n = q.length, d = q.filter((f) => set.has(fixKey(f))).length;
    return h("div", { class: "fix-progress" },
      h("div", { class: "fp-top" }, h("strong", { text: t("fixProgress", { d, n }) }), h("span", { class: "muted", "aria-hidden": "true", text: `${Math.round((d / n) * 100)}%` })),
      h("div", { class: "fp-bar", role: "progressbar", "aria-label": t("fixProgressLabel"), "aria-valuemin": "0", "aria-valuemax": String(n),
        "aria-valuenow": String(d), "aria-valuetext": t("fixProgress", { d, n }) }, q.map((f) => h("span", { class: set.has(fixKey(f)) ? "on" : "" }))));
  }
  function fixRow(s, f, onPick, extra) {
    const dev = deviceByIp(s, f.ip) || { type: "unknown" };
    return h("li", { class: "fix-row" },
      devIco(dev.type, toneOf(f.severity)),
      h("div", { class: "grow" }, h("strong", { text: simple(f.code).title }), h("span", { class: "muted", text: `${deviceName(dev)} · ` }, h("span", { class: "mono", text: f.ip }))),
      riskPill(f.severity), onPick ? h("button", { type: "button", class: "btn btn-ghost", onclick: onPick }, t("fixNow"), icon("chevron")) : null, extra || null);
  }
  function fixFocus(root, s) {
    const q = queue(s), set = fixedOf(s.file), top = mostDangerous(s);
    const left = q.filter((f) => !set.has(fixKey(f))), done = q.filter((f) => set.has(fixKey(f)));
    root.append(fixProgress(q, set));
    if (state.lastDone[s.file]) root.append(h("p", { class: "note ok with-ico", role: "status" }, icon("check"), h("span", { text: t("doneNote", { title: state.lastDone[s.file] }) })));
    if (!left.length) {
      root.append(h("article", { class: "fix-now fix-all-done", id: "fix-now", tabindex: "-1" },
        h("h3", { class: "with-ico" }, icon("sparkles", "lg"), h("span", { text: t("allFixedT") })),
        h("p", { class: "lead", text: t("allFixedS") }),
        h("div", { class: "actions" }, h("button", { type: "button", class: "btn btn-cta", onclick: () => { setTab("home"); inspect(); } }, icon("refresh"), t("inspectAgain")))));
    } else {
      const f = left.find((x) => fixKey(x) === state.pick[s.file]) || left[0], idx = left.indexOf(f);
      const tx = simple(f.code), dev = deviceByIp(s, f.ip) || { type: "unknown", ip: f.ip };
      root.append(h("article", { class: "fix-now", id: "fix-now", tabindex: "-1", "aria-labelledby": "fix-now-title" },
        h("p", { class: "fix-step", text: done.length || idx ? t("fixNext") : t("fixNow") }),
        h("div", { class: "fix-device" }, devIco(dev.type, toneOf(f.severity), true),
          h("div", { class: "grow" },
            h("p", { class: "muted", text: top && top.ip === f.ip ? t("mostDangerous") : t("thisDevice") }),
            h("p", { class: "fix-dev-name", text: deviceName(dev) }),
            h("p", { class: "fix-ids" }, h("span", { class: "mono", text: `${t("ipLabel")} ${dev.ip}` }), dev.mac ? h("span", { class: "mono", text: `${t("macLabel")} ${dev.mac}` }) : null)),
          riskPill(f.severity)),
        h("h3", { id: "fix-now-title", class: "fix-title", text: tx.title }),
        h("p", { class: "lead", text: tx.explain }),
        h("h4", { text: t("doThis") + ":" }),
        steps(tx.steps),
        whoLine(f.code),
        h("div", { class: "actions fix-actions" },
          h("button", { type: "button", class: "btn btn-cta", onclick: () => { setFixed(s.file, fixKey(f), true); state.lastDone[s.file] = tx.title; state.pick[s.file] = null; render(); focusSel("#fix-now"); } }, icon("tick"), t("btnFixed")),
          left.length > 1 ? h("button", { type: "button", class: "btn btn-ghost", onclick: () => { state.lastDone[s.file] = null; state.pick[s.file] = fixKey(left[(idx + 1) % left.length]); render(); focusSel("#fix-now"); } }, t("btnSkip")) : null),
        h("p", { class: "note with-ico" }, icon("users"), h("span", { text: t("helpNote") })),
        techFor(f)));
      const rest = left.filter((x) => x !== f);
      if (rest.length) root.append(h("details", { class: "fix-more" },
        h("summary", null, icon("alert"), h("span", { text: rest.length === 1 ? t("moreLeft1") : t("moreLeft", { n: rest.length }) }), icon("chevron-down", "chev")),
        h("ul", { class: "fix-list" }, rest.map((x) => fixRow(s, x, () => { state.lastDone[s.file] = null; state.pick[s.file] = fixKey(x); render(); focusSel("#fix-now"); })))));
    }
    if (done.length) root.append(h("details", { class: "fix-more fix-done" },
      h("summary", null, icon("check"), h("span", { text: t("doneList", { n: done.length }) }), icon("chevron-down", "chev")),
      h("ul", { class: "fix-list" }, done.map((x) => fixRow(s, x, null,
        h("button", { type: "button", class: "btn btn-ghost", onclick: () => { setFixed(s.file, fixKey(x), false); state.lastDone[s.file] = null; render(); focusSel(".fix-done summary"); } }, icon("refresh"), t("undo")))))));
    const info = s.findings.filter((f) => f.severity === "info").length;
    if (info) root.append(h("p", { class: "note with-ico" }, icon("info"), h("span", { text: info === 1 ? t("infoNote1") : t("infoNote", { n: info }) })));
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
        devIco(d.type, tone === "green" ? "green" : worst.severity),
        h("div", null, h("div", { class: "tile-name", text: deviceLabel(d.type) }), vendor ? h("div", { class: "tile-sub", text: vendor }) : null),
        h("div", { class: "tile-meta" }, h("span", { class: "mono", text: `${t("ipLabel")} ${d.ip}` }), h("span", { class: "mono", text: `${t("macLabel")} ${d.mac || t("unknown")}` })),
        h("div", { class: "tile-status" }, icon(worst ? RISK[worst.severity].icon : "check"), h("span", { text: status })));
    }));
  }

  // The accessible list version of the map (FR-03: every device with IP, masked MAC and maker), under the map on Home.
  function fillDeviceList(box, s) {
    const withP = s.devices.filter((d) => problemsOf(s, d).length);
    const safe = s.devices.filter((d) => !problemsOf(s, d).length);
    const chip = (key, label) => h("button", { type: "button", class: "chip-btn", "aria-pressed": String(state.devFilter === key),
      onclick: () => { state.devFilter = key; fillDeviceList(box, s); box.querySelector(`.chip-btn[aria-pressed="true"]`).focus(); } }, label);
    const list = (state.devFilter === "problems" ? withP : state.devFilter === "safe" ? safe : s.devices)
      .slice().sort((a, b) => b.risk_points - a.risk_points);
    box.replaceChildren(
      h("div", { class: "chips", style: "margin-bottom:20px", role: "group", "aria-label": t("listTitle") },
        chip("all", t("fAll", { n: s.devices.length })), chip("problems", [icon("alert"), t("fProblems", { n: withP.length })]), chip("safe", [icon("check"), t("fSafe", { n: safe.length })])),
      tiles(s, list));
    if (window.Device3D) window.Device3D.scan(box);
  }
  function deviceList(s) {
    const open = state.homeList == null ? s.devices.length > 14 : state.homeList;
    const box = h("div", { class: "dev-list", id: "dev-list", hidden: !open });
    const btn = h("button", { type: "button", class: "btn btn-ghost list-toggle", "aria-expanded": String(open), "aria-controls": "dev-list" });
    const label = (o) => btn.replaceChildren(icon(o ? "x" : "phone"), h("span", { text: o ? t("hideList") : t("showList") }));
    label(open);
    btn.addEventListener("click", () => {
      const o = box.hidden; state.homeList = o; box.hidden = !o; btn.setAttribute("aria-expanded", String(o)); label(o);
      if (o) fillDeviceList(box, s);
    });
    if (open) fillDeviceList(box, s);
    return { btn, box };
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
      worst ? riskPill(worst.severity) : h("span", { class: "pill p-green" }, icon("check"), t("devOk")),
      worst ? h("h3", { style: "margin-top:1rem", text: tx.title }) : null,
      h("p", { class: "lead", style: "margin-top:.6rem", text: worst ? tx.explain : t("devOkExplain") }),
      h("h4", { text: (worst ? t("doThis") : t("keepSafe")) + ":" }),
      steps(worst ? tx.steps : t("devOkSteps")),
      worst ? whoLine(worst.code) : null,
      probs.length > 1 ? [h("h4", { text: t("otherProblems") + ":" }),
        h("div", { class: "chips" }, probs.slice(1).map((f) => h("button", { type: "button", class: "chip-btn",
          onclick: () => { closeSheet(); setTab("findings"); openFinding(s.findings.indexOf(f)); } }, icon(RISK[f.severity].icon), h("span", { text: simple(f.code).title }), icon("chevron"))))] : null,
      techBox([
        h("dl", { class: "meta" },
          h("dt", { text: t("ip") }), h("dd", { class: "mono", text: d.ip }),
          h("dt", { text: t("mac") }), h("dd", { class: "mono", text: d.mac || t("unknown") }),
          h("dt", { text: t("vendor") }), h("dd", { text: d.vendor || t("unknown") }),
          h("dt", { text: t("hostname") }), h("dd", { text: d.hostname || t("unknown") })),
        h("div", { class: "muted", style: "margin-bottom:.4rem", text: t("ports") }),
        d.open_ports.length ? h("div", { class: "tags" }, d.open_ports.map((p) => h("span", { class: "port" + (risky.has(p.port) ? " risk" : "") },
          risky.has(p.port) ? icon("alert") : null, `${p.port}/${p.protocol} ${p.service}${p.tls ? " (TLS)" : ""}`))) : h("span", { text: t("none") }),
        worst ? [h("h4", { text: t("techTitle") + ": " + detailed(worst.code).title }), h("div", { class: "evidence mono", text: worst.evidence }),
          h("span", { class: "code-tag", text: `${t("codeLabel")}: ${worst.code}` })] : null,
      ])));
    lastOpener = opener || null;
    const dlg = document.getElementById("sheet");
    if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", "");
    if (window.Device3D) window.Device3D.scan(body);
    document.getElementById("sheet-close").focus();
  }
  function closeSheet() {
    const dlg = document.getElementById("sheet");
    if (dlg.open) { if (typeof dlg.close === "function") dlg.close(); else dlg.removeAttribute("open"); }
  }

  // ---------------------------------------------------------------- FIXES (Fing-style security check)
  function renderFindings(root) {
    const s = scan();
    root.append(pageHead(t("findingsTitle"), state.fixView === "one" ? t("fixOneSub") : t("findingsSub"), `${t("ebFindings")} · ${s.error ? 0 : s.findings.filter((f) => f.severity !== "info").length}`, s.error ? "" : bandOf(s.score)));
    if (s.error) { root.append(errorBox(s)); return; }
    if (!s.findings.length) { root.append(h("div", { class: "suggest" }, h("p", { class: "lead with-ico", style: "margin:0" }, icon("check", "ok"), h("span", { text: t("noProblems") }))), reportCard(s)); return; }
    const view = (v, name, label) => h("button", { type: "button", "aria-pressed": String(state.fixView === v),
      onclick: () => { state.fixView = v; store.set("fixView", v); render(); focusSel(`.view-toggle [aria-pressed="true"]`); } }, icon(name), h("span", { text: label }));
    root.append(h("div", { class: "seg view-toggle", role: "group", "aria-label": t("fixViewLabel") }, view("one", "hand", t("fixOne")), view("all", "book", t("fixAll"))));
    if (state.fixView === "one" && queue(s).length) { fixFocus(root, s); root.append(reportCard(s)); return; }
    const sums = { high: "sumHigh", medium: "sumMedium", low: "sumLow", info: "sumInfo" };
    root.append(h("div", { class: "chips" }, Object.keys(RISK).filter((k) => s.findings.some((f) => f.severity === k))
      .map((k) => h("span", { class: "pill p-" + k }, icon(RISK[k].icon), `${t(sums[k])}: ${s.findings.filter((f) => f.severity === k).length}`))));
    Object.keys(RISK).forEach((sev) => {
      const group = s.findings.map((f, i) => ({ f, i })).filter((x) => x.f.severity === sev);
      if (!group.length) return;
      root.append(h("section", { class: "group" },
        h("div", { class: "group-head" }, h("h3", { class: "with-ico" }, icon(RISK[sev].icon, "lg tone-" + RISK[sev].tone), h("span", { text: `${RISK[sev][state.lang]} (${group.length})` }))),
        h("div", { class: "checks" }, group.map(({ f, i }) => checkCard(s, f, i)))));
    });
    root.append(reportCard(s));
  }
  function checkCard(s, f, i) {
    const tx = simple(f.code), dev = deviceByIp(s, f.ip) || { type: "unknown" }, vendor = shortVendor(dev.vendor);
    const card = h("article", { class: "check", id: "finding-" + i, tabindex: "0",
      "aria-label": `${RISK[f.severity][state.lang]}. ${tx.title}. ${deviceLabel(dev.type)}. ${t("cardHint")}` },
      h("div", { class: "check-head" }, devIco(dev.type, toneOf(f.severity)),
        h("div", { class: "grow" }, h("h3", { style: "margin:0;font-size:1.2rem", text: deviceLabel(dev.type) }), vendor ? h("div", { class: "sub", text: vendor }) : null)),
      riskPill(f.severity),
      h("h4", { class: "title", text: tx.title }),
      h("p", { text: tx.explain }),
      h("h4", { text: t("doThis") + ":" }),
      steps(tx.steps),
      h("div", { class: "foot-row" }, whoLine(f.code), h("span", { class: "code-tag", text: `${t("codeLabel")}: ${f.code}` })),
      f.severity === "info" ? null : fixToggle(s, f),
      techFor(f));
    card.addEventListener("keydown", (e) => {
      if (e.target !== card || (e.key !== "Enter" && e.key !== " ")) return;
      e.preventDefault();
      const d = card.querySelector("details.tech");
      d.open = !d.open;
    });
    return card;
  }
  function fixToggle(s, f) {
    const on = fixedOf(s.file).has(fixKey(f));
    return h("div", { class: "fix-mark" }, on ? h("span", { class: "pill p-green" }, icon("check"), t("markedFixed")) : null,
      h("button", { type: "button", class: "btn btn-ghost", "aria-pressed": String(on),
        onclick: () => { setFixed(s.file, fixKey(f), !on); render(); openFinding(s.findings.indexOf(f)); } }, icon(on ? "refresh" : "tick"), on ? t("undo") : t("markFixed")));
  }
  function openFinding(i) {
    const s = scan(), f = s.findings[i];
    if (state.tab === "findings" && state.fixView === "one" && f) {
      if (f.severity !== "info" && !fixedOf(s.file).has(fixKey(f))) { state.pick[s.file] = fixKey(f); state.lastDone[s.file] = null; render(); focusSel("#fix-now"); return; }
      state.fixView = "all"; render();          // a fixed or info item: show it in the full list (not saved as a preference)
    }
    const el = document.getElementById("finding-" + i);
    if (!el) return;
    el.focus({ preventScroll: true });
    el.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  // ---------------------------------------------------------------- HISTORY (compare + events timeline)
  function renderHistory(root) {
    root.append(pageHead(t("historyTitle"), t("historySub"), `${t("ebHistory")} · ${t("ebSaved", { n: state.historyDeleted || !D.history ? 0 : D.history.trend.length })}`));
    if (state.historyDeleted) {
      root.append(h("div", { class: "suggest" }, h("p", { class: "lead with-ico", role: "status" }, icon("trash"), h("span", { text: t("deleted") })),
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
        h("div", { class: "compare-arrow", "aria-hidden": "true" }, icon("arrow", "xl")),
        h("div", { class: "compare-col" }, h("strong", { text: t("now") }), ring(ch.score_after, true), bandPill(ch.score_after))),
      h("p", { class: "verdict with-ico" }, icon(ch.score_change > 0 ? "sparkles" : ch.score_change < 0 ? "alert" : "info", "lg"), h("span", { text: verdict })),
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
      h("button", { type: "button", class: "btn btn-danger", onclick: () => { state.confirmDelete = true; render(); focusSel(".confirm button"); } }, icon("trash"), t("deleteBtn")));
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
    const ev = (tone, name, title, sub) => h("li", null, h("span", { class: "t-ico " + tone, "aria-hidden": "true" }, icon(name)),
      h("div", { class: "t-text" }, h("strong", { text: title }), sub ? h("span", { class: "muted", text: sub }) : null));
    const after = [];
    ch.resolved_findings.forEach((f) => after.push(ev("green", "check", t("evFixed", { title: simple(f.code).title }), null)));
    ch.secured_ports.forEach((u) => after.push(ev("blue", "lock", t("evSecured"), t("evSecuredSub", { from: u.from_port, to: u.to_port }))));
    ch.new_findings.forEach((f) => after.push(ev("amber", "alert", t("evNew", { title: simple(f.code).title }), null)));
    ch.new_devices.forEach((ip) => after.push(ev("red", "plus", t("evNewDev"), ip)));
    ch.removed_devices.forEach((ip) => after.push(ev("", "leave", t("evGoneDev"), ip)));
    if (!ch.alerts) after.push(ev("green", "shield", t("evQuiet"), null));
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
      const v = svg("text", { class: "value-text", x: cx + 11, y: top - 8, "text-anchor": "middle" }); v.textContent = String(r.network_score); s.append(v);
      s.append(svg("use", { href: "#i-" + BAND_ICON[band], x: cx - 30, y: top - 26, width: 20, height: 20, class: "chart-ico tone-" + band }));
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
  // ---------------------------------------------------------------- CHAT (the "?" button next to the language)
  // The LLM answer comes from the team's assistant: window.SafeHouseAssistant.handler(question, ctx) if a page sets one,
  // else POST /api/v1/ask (service_data_contracts.md) when the page is served by `netcheck serve`. With neither (or on
  // any error / timeout) the built-in grounded answers are used, so the chat always works, also offline from file://.
  const ASK_URL = "/api/v1/ask";
  let chatOpener = null;
  function chatTurns() {
    return state.chat.slice(-12).map((m) => ({ role: m.role === "user" ? "user" : "assistant",
      content: m.role === "user" ? m.text : (m.text || (m.parts || []).map((x) => x.text).join(" ")) })).filter((x) => x.content);
  }
  async function askAssistant(q, turns) {
    const ctx = { lang: state.lang, scanFile: scan().file, history: turns };
    const custom = window.SafeHouseAssistant && window.SafeHouseAssistant.handler;
    const ctrl = typeof AbortController === "function" ? new AbortController() : null;
    const timer = setTimeout(() => ctrl && ctrl.abort(), 25000);
    try {
      if (typeof custom === "function") {
        const r = await Promise.race([custom(q, ctx), new Promise((_, no) => setTimeout(() => no(new Error("timeout")), 25000))]);
        return r && typeof r.answer === "string" ? r : null;
      }
      if (!/^https?:$/.test(location.protocol)) return null;
      const res = await fetch(`${ASK_URL}?lang=${state.lang}`, { method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q, history: turns }), signal: ctrl ? ctrl.signal : undefined });
      if (!res.ok) return null;
      const j = await res.json();
      return j && typeof j.answer === "string" && j.answer.trim() ? j : null;
    } catch (e) { return null; } finally { clearTimeout(timer); }
  }
  function builtIn(kind, s) { return answer(kind, s).map((x) => Object.assign({}, x, check(x, s))); }
  async function chatAsk(text, kind) {
    const s = scan();
    if (state.chatBusy || !text) return;
    if (text.length > 500) { state.chatNote = t("chatTooLong"); renderChat(); return; }
    state.chatNote = null;
    const turns = chatTurns();
    state.chat.push({ role: "user", text, kind: kind || classify(text) });
    state.chatBusy = true; renderChat();
    const r = s.error ? null : await askAssistant(text, turns);
    const k = kind || classify(text);
    if (r) state.chat.push({ role: "bot", text: r.answer.trim(), mode: r.mode === "ai" ? "ai" : r.mode === "rejected" ? "rejected" : "offline" });
    else state.chat.push({ role: "bot", parts: s.error ? [{ text: t("stErrS"), cites: [], ok: true }] : builtIn(k, s), mode: "builtin" });
    if (state.chat.length > 24) state.chat.splice(0, state.chat.length - 24);
    state.chatBusy = false; renderChat();
    focusSel("#chat-input");
  }
  function bubbleBot(m) {
    const wrap = h("div", { class: "msg bot" }, h("div", { class: "bot-name with-ico" }, icon("bot"), h("span", { text: t("botName") })));
    if (m.parts) {
      m.parts.forEach((x) => wrap.append(h("div", { class: "bubble bot" + (x.ok ? "" : " blocked") },
        h("span", { class: "txt", text: x.text }),
        (x.cites || []).filter((c) => c !== "scan").map((c) => h("span", { class: "proof", title: t("proof") }, icon("search"), h("span", { class: "sr", text: t("proof") + ": " }), c)),
        x.ok ? null : h("span", { class: "why" }, icon("scissors"), h("span", { text: t("blocked", { r: x.reason }) })))));
      const bad = m.parts.filter((z) => !z.ok).length;
      if (m.parts.length > 1 || bad) wrap.append(h("p", { class: "msg-meta", text: t("verified", { ok: m.parts.length - bad, bad }) }));
    } else {
      wrap.append(h("div", { class: "bubble bot" }, h("span", { class: "txt", text: m.text })));
      wrap.append(h("p", { class: "msg-meta with-ico" }, icon(m.mode === "ai" ? "sparkles" : "info"), h("span", { text: t(m.mode === "ai" ? "chatAi" : m.mode === "rejected" ? "chatRejected" : "chatOffline") })));
    }
    return wrap;
  }
  function renderChat() {
    const body = document.getElementById("chat-body");
    if (!body) return;
    const qs = [["first", "q1"], ["devices", "q2"], ["printer", "q3"]];
    const log = h("div", { class: "chat-log", role: "log", "aria-live": "polite", "aria-label": t("botName") },
      h("div", { class: "msg bot" }, h("div", { class: "bot-name with-ico" }, icon("bot"), h("span", { text: t("botName") })), h("div", { class: "bubble bot", text: t("botHello") })),
      state.chat.map((m) => m.role === "user"
        ? h("div", { class: "msg me" }, h("span", { class: "sr", text: t("chatYou") + ": " }), h("div", { class: "bubble me", text: m.text }))
        : bubbleBot(m)),
      state.chatBusy ? h("div", { class: "msg bot typing", role: "status" }, h("span", { class: "dots", "aria-hidden": "true" }, h("span"), h("span"), h("span")), h("span", { text: t("chatTyping") })) : null);
    const sugg = h("div", { class: "chat-suggest" },
      h("p", { class: "muted", text: state.chat.length ? t("chatMore") : t("chatSuggest") }),
      h("div", { class: "chat-qs" }, qs.map(([k, key]) => h("button", { type: "button", class: "chip-btn", disabled: state.chatBusy, onclick: () => chatAsk(t(key), k) }, icon("message"), h("span", { text: t(key) })))));
    const input = h("textarea", { id: "chat-input", rows: "2", maxlength: "500", placeholder: t("askPlaceholder"), "aria-describedby": "chat-privacy" });
    input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event("submit")); } });
    const form = h("form", { class: "chat-form", onsubmit: (e) => { e.preventDefault(); const q = input.value.trim(); if (q) chatAsk(q); } },
      h("label", { for: "chat-input", class: "chat-label", text: t("askLabel") }),
      h("div", { class: "composer" }, input, h("button", { type: "submit", class: "btn btn-filled", disabled: state.chatBusy, "aria-label": t("askBtn") }, h("span", { text: t("askBtn") }), icon("send"))),
      state.chatNote ? h("p", { class: "note with-ico", role: "alert" }, icon("alert"), h("span", { text: state.chatNote })) : null,
      h("p", { class: "muted with-ico chat-privacy", id: "chat-privacy" }, icon("lock"), h("span", { text: t("chatPrivacy") })));
    const extra = h("div", { class: "chat-extra" },
      state.chat.length ? h("button", { type: "button", class: "btn btn-ghost", onclick: () => { state.chat = []; state.chatNote = null; renderChat(); focusSel("#chat-input"); } }, icon("refresh"), t("chatNew")) : null,
      h("details", { class: "tech", open: state.hallucinate }, h("summary", null, icon("present"), h("span", { text: t("hallToggle") })),
        h("div", null,
          h("label", { class: "switch" }, h("input", { type: "checkbox", checked: state.hallucinate,
            onchange: (e) => { state.hallucinate = e.target.checked; renderChat(); focusSel(".chat-extra .switch input"); } }), t("hallSwitch")),
          h("p", { class: "muted", text: t("demoNote") }))));
    body.replaceChildren(log, sugg, form, extra);
    log.lastElementChild && log.lastElementChild.scrollIntoView({ block: "nearest" });
  }
  function openChat(opener) {
    chatOpener = opener || document.getElementById("help-btn");
    const dlg = document.getElementById("chat");
    renderChat();
    if (!dlg.open) { if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", ""); }
    focusSel("#chat-input");
  }
  function closeChat() {
    const dlg = document.getElementById("chat");
    if (dlg.open) { if (typeof dlg.close === "function") dlg.close(); else dlg.removeAttribute("open"); }
  }

  // ---------------------------------------------------------------- REPORT for the IT company (FR-14)
  // One self-contained HTML page (print = PDF). Built with DOM nodes, so all scan text is escaped (NFR-03).
  const REPORT_CSS = `
    @page { size: A4; margin: 10mm; }
    * { box-sizing: border-box; }
    body { font: 9.5pt/1.38 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #0f172a; margin: 0 auto; padding: 20px; max-width: 900px; background: #fff; }
    h1 { font-size: 16pt; margin: 0 0 2px; } h2 { font-size: 11.5pt; margin: 12px 0 4px; border-bottom: 1.5px solid #0f172a; padding-bottom: 2px; }
    p { margin: 4px 0; } .meta { color: #334155; margin: 0 0 8px; } .mono { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 8.8pt; }
    .score { display: flex; gap: 14px; align-items: center; padding: 6px 12px; border: 1.5px solid #0f172a; border-radius: 8px; }
    .score b { font-size: 18pt; } .band { font-weight: 700; } .band.red { color: #b91c1c; } .band.amber { color: #b45309; } .band.green { color: #047857; }
    table { width: 100%; border-collapse: collapse; } th, td { text-align: left; vertical-align: top; padding: 3px 5px; }
    th { background: #f1f5f9; font-size: 8.8pt; border-bottom: 1px solid #94a3b8; }
    table.findings th:nth-child(1) { width: 11%; } table.findings th:nth-child(2) { width: 21%; } table.findings th:nth-child(4) { width: 13%; }
    table.findings tbody { break-inside: avoid; border-bottom: 1px solid #cbd5e1; } table.devices td { border-bottom: 1px solid #e2e8f0; }
    .f-steps td { padding-top: 0; padding-bottom: 6px; } .f-steps ol { margin: 1px 0 0; padding-left: 16px; columns: 2; column-gap: 22px; }
    .f-steps li { break-inside: avoid; } .code { color: #475569; } .ev { color: #475569; font-size: 8pt; word-break: break-word; }
    .sev { font-weight: 700; white-space: nowrap; } .sev.high { color: #b91c1c; } .sev.medium { color: #b45309; } .sev.low { color: #1d4ed8; } .sev.info { color: #475569; }
    .note { margin-top: 10px; color: #475569; font-size: 8pt; }
    @media print { body { padding: 0; max-width: none; } }`;
  // Fit on one A4 page when printing (277 x 190 mm printable), but never below 80% so it stays readable.
  const REPORT_FIT = `(function(){function fit(){var b=document.body;b.style.zoom="";b.style.width="718px";b.style.maxWidth="none";b.style.padding="0";
    var z=Math.max(.8,Math.min(1,1040/b.scrollHeight));b.style.width=(718/z)+"px";b.style.zoom=z;}
    function undo(){var b=document.body;b.style.zoom="";b.style.width="";b.style.maxWidth="";b.style.padding="";}
    window.addEventListener("beforeprint",fit);window.addEventListener("afterprint",undo);
    if(window.matchMedia){window.matchMedia("print").addListener(function(m){m.matches?fit():undo();});}})();`;
  function reportDoc(s) {
    const set = fixedOf(s.file), b = bandOf(s.score), now = new Date();
    const stamp = now.toLocaleString(state.lang === "ro" ? "ro-RO" : "en-GB");
    const sevOrder = (f) => ({ high: 0, medium: 1, low: 2, info: 3 })[f.severity] ?? 4;
    const findings = s.findings.slice().sort((a, c) => sevOrder(a) - sevOrder(c));
    const groups = [];                                  // the same problem on several devices = one row with every place
    findings.forEach((f) => { const g = groups.find((x) => x.code === f.code && x.items[0].severity === f.severity); if (g) g.items.push(f); else groups.push({ code: f.code, items: [f] }); });
    const first = queue(s)[0];
    const doc = h("div", null,
      h("h1", { text: `SafeHouse · ${t("repDocTitle")}` }),
      h("p", { class: "meta" }, `${t("repGenerated")}: ${stamp} · ${t("repScan")}: `, h("span", { class: "mono", text: s.file })),
      h("div", { class: "score" }, h("b", { text: `${s.score}/100` }), h("div", null,
        h("div", { class: "band " + b, text: t("band_" + b) }),
        h("div", { text: s.findings.filter((f) => f.severity !== "info").length === 1 ? t("summaryOne", { d: s.devices.length })
          : t("summary", { d: s.devices.length, f: s.findings.filter((f) => f.severity !== "info").length }) }))),
      first ? [h("h2", { text: t("repTop") }), h("p", null, h("b", { text: t("repFirst") + ": " }), `${detailed(first.code).title} (`, h("span", { class: "mono", text: where(first) }), `, ${deviceName(deviceByIp(s, first.ip))}).`)] : null,
      h("h2", { text: t("repFindings") }),
      findings.length ? h("table", { class: "findings" },
        h("thead", null, h("tr", null, [t("repSev"), t("repWhere"), t("repProblem"), t("repStatus")].map((x) => h("th", { text: x })))),
        groups.map((g) => {
          const d = detailed(g.code), f0 = g.items[0], real = f0.severity !== "info";
          const nFixed = g.items.filter((f) => set.has(fixKey(f))).length;
          const status = !real ? t("repInfoOnly") : nFixed === g.items.length ? t("repFixedByUser") : nFixed ? `${t("repToDo")} (${g.items.length - nFixed}/${g.items.length})` : t("repToDo");
          return h("tbody", null,
            h("tr", { class: "f-head" },
              h("td", { class: "sev " + f0.severity, text: RISK[f0.severity][state.lang] }),
              h("td", null, g.items.map((f) => h("div", null, h("span", { class: "mono", text: where(f) }), ` · ${deviceName(deviceByIp(s, f.ip))}`))),
              h("td", null, h("b", { text: d.title }), " ", h("span", { class: "mono code", text: g.code }),
                g.items.map((f, i) => f.evidence ? h("div", { class: "ev" }, `${t("repEvidence")} (${where(f)}): `, f.evidence,
                  i === 0 && refs(g.code).length ? ` · ${refs(g.code).join(" · ")}` : null) : null)),
              h("td", { text: status })),
            d.steps.length ? h("tr", { class: "f-steps" }, h("td"), h("td", { colspan: "3" }, h("b", { text: t("repFix") + ":" }), h("ol", null, d.steps.map((x) => h("li", { text: x }))))) : null);
        })) : h("p", { text: t("repNone") }),
      h("h2", { text: t("repDevices") }),
      h("table", { class: "devices" },
        h("thead", null, h("tr", null, [t("repDevice"), t("repVendor"), t("ipLabel"), t("macLabel"), t("repPorts")].map((x) => h("th", { text: x })))),
        h("tbody", null, s.devices.map((d) => h("tr", null,
          h("td", { text: deviceLabel(d.type) + (d.hostname ? ` (${d.hostname})` : "") }), h("td", { text: d.vendor || "–" }),
          h("td", { class: "mono", text: d.ip }), h("td", { class: "mono", text: d.mac || "–" }),
          h("td", { class: "mono", text: d.open_ports.map((p) => `${p.port}/${p.protocol}${p.service ? " " + p.service : ""}`).join(", ") || "–" }))))),
      h("p", { class: "note", text: t("repNote") }));
    const title = `SafeHouse – ${t("repDocTitle")} – ${s.file}`;
    const esc = h("title", { text: title }).outerHTML;
    return `<!doctype html><html lang="${state.lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">${esc}<style>${REPORT_CSS}</style></head><body>${doc.innerHTML}<script>${REPORT_FIT}<\/script></body></html>`;
  }
  function downloadReport(s) {
    const blob = new Blob([reportDoc(s)], { type: "text/html;charset=utf-8" });
    const a = h("a", { href: URL.createObjectURL(blob), download: `SafeHouse-${state.lang === "ro" ? "raport" : "report"}-${s.file.replace(/\.[^.]+$/, "")}-${new Date().toISOString().slice(0, 10)}.html` });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  function printReport(s) {
    const old = document.getElementById("report-frame");
    if (old) old.remove();
    const f = h("iframe", { id: "report-frame", title: t("repTitle"), "aria-hidden": "true", tabindex: "-1",
      style: "position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden" });
    f.addEventListener("load", () => { try { f.contentWindow.focus(); f.contentWindow.print(); } catch (e) { downloadReport(s); } }, { once: true });
    f.srcdoc = reportDoc(s);
    document.body.append(f);
  }
  function reportCard(s) {
    return h("section", { class: "report-card", "aria-labelledby": "rep-title" },
      h("div", { class: "rep-text" }, h("h3", { id: "rep-title", class: "with-ico" }, icon("briefcase", "lg"), h("span", { text: t("repTitle") })),
        h("p", { class: "muted", text: t("repSub") })),
      h("div", { class: "actions" },
        h("button", { type: "button", class: "btn btn-tonal", onclick: () => printReport(s) }, icon("present"), t("repPdf")),
        h("button", { type: "button", class: "btn btn-ghost", onclick: () => downloadReport(s) }, icon("arrow"), t("repHtml"))),
      h("p", { class: "muted rep-hint", text: t("repHint") }));
  }

  // ---------------------------------------------------------------- shell
  const RENDER = { home: renderHome, findings: renderFindings, history: renderHistory };
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
    sel.replaceChildren(...D.scans.map((s, i) => h("option", { value: String(i), selected: i === state.scan }, s.error ? `${s.file} — ${t("errorWord")}` : `${s.file} — ${s.score}/100`)));
    const cur = scan(), chipEl = sel.closest(".net-chip"), sb = document.getElementById("scan-score");
    chipEl.dataset.band = cur.error ? "error" : bandOf(cur.score);
    document.getElementById("scan-file").textContent = cur.file;
    sb.textContent = cur.error ? t("errorWord") : `${cur.score}/100`;
    const panel = document.getElementById("panel-" + state.tab);
    panel.replaceChildren();
    RENDER[state.tab](panel);
    if (window.Device3D) window.Device3D.scan(panel);       // 3D models into every .dev3d slot
    const hb = document.getElementById("help-btn");
    hb.setAttribute("aria-label", t("helpAria"));
    hb.querySelector(".help-txt").textContent = t("helpBtn");
    if (document.getElementById("chat").open) renderChat();
  }

  document.getElementById("scan-select").addEventListener("change", (e) => { state.scan = Number(e.target.value); state.chat = []; render(); });
  ["ro", "en"].forEach((l) => document.getElementById("lang-" + l).addEventListener("click", () => { state.lang = l; store.set("lang", l); render(); }));
  [0, 1, 2].forEach((i) => document.getElementById("size-" + i).addEventListener("click", () => { state.size = i; store.set("size", String(i)); render(); }));
  document.querySelectorAll(".nav-item").forEach((b) => b.addEventListener("click", () => { setTab(b.dataset.tab); document.getElementById("main").focus({ preventScroll: true }); }));
  const dlg = document.getElementById("sheet");
  document.getElementById("help-btn").addEventListener("click", (e) => openChat(e.currentTarget));
  document.getElementById("chat-close").addEventListener("click", closeChat);
  const chatDlg = document.getElementById("chat");
  chatDlg.addEventListener("close", () => { if (chatOpener && document.body.contains(chatOpener)) chatOpener.focus(); });
  chatDlg.addEventListener("click", (e) => { if (e.target === chatDlg) closeChat(); });
  document.getElementById("sheet-close").addEventListener("click", closeSheet);
  dlg.addEventListener("close", () => { if (lastOpener && document.body.contains(lastOpener)) lastOpener.focus(); });
  dlg.addEventListener("click", (e) => { if (e.target === dlg) closeSheet(); });   // tap outside the sheet

  // Deep links for the pitch: #ask?q=first&hall=1 (opens the chat), #home?lang=en&scan=V3_small_office.xml, #history?theme=light&size=2,
  // #devices?open=192.168.1.40 (old link: Home with the device sheet), #findings?view=all
  (function applyHash() {
    let [tab, query] = location.hash.slice(1).split("?");
    if (tab === "devices") { tab = "home"; query = (query ? query + "&" : "") + "inspect=1"; }   // old link from the pitch
    const wantChat = tab === "ask";                                   // #ask?q=first&hall=1 opens the chat over Home
    if (wantChat) tab = "home";
    const p = new URLSearchParams(query || "");
    if (p.get("lang") === "en" || p.get("lang") === "ro") state.lang = p.get("lang");
    if (["0", "1", "2"].includes(p.get("size"))) state.size = Number(p.get("size"));
    const i = D.scans.findIndex((s) => s.file === p.get("scan"));
    if (i >= 0) state.scan = i;
    if (p.get("hall") === "1") state.hallucinate = true;
    if (p.get("inspect") === "1") state.inspected[scan().file] = true;
    if (p.get("view") === "all" || p.get("view") === "one") state.fixView = p.get("view");
    if (p.get("theme") === "light" || p.get("theme") === "dark") document.documentElement.dataset.theme = p.get("theme");
    const q = { first: "q1", devices: "q2", printer: "q3" }[p.get("q")];
    setTab(TABS.includes(tab) ? tab : "home");
    if (p.get("state")) applyHouseState(p.get("state"));
    const open = p.get("open");
    if (open && !scan().error) { const d = deviceByIp(scan(), open); if (d) openDevice(d); }
    if (wantChat) { openChat(); if (q) chatAsk(t(q), p.get("q")); }
  })();

  // SafeHouse.setState("safe" | "vulnerable" | "idle" | "scanning" | "error") and SafeHouse.inspect()
  window.SafeHouse = {
    setState(st) { if (state.tab !== "home") setTab("home"); return applyHouseState(st); },
    inspect() { if (state.tab !== "home") setTab("home"); inspect(); },
    reportHtml() { return reportDoc(scan()); },        // FR-14: the one-page report as a full HTML document
    openChat() { openChat(); },
  };

  let resizeTimer = null;
  window.addEventListener("resize", () => { if (state.tab !== "history") return; clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 150); });
})();

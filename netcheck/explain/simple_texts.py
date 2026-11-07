"""Beginner texts for children, older people and anyone new to technology (FR-07, FR-08, NFR-09).

The main texts in texts.py stay the reference (more detailed, for someone who knows a bit or for
the IT supplier). These are the first thing a beginner sees:
  * title: no technical words at all
  * explain: at most 2 short sentences, using the "your home" picture (devices, doors, locks)
  * steps: 1-3 actions, the first one always doable or "ask for help"
  * who: "self" (you can do it), "helper" (ask someone who knows computers), "it" (IT company / installer)
"""
from __future__ import annotations

# "icon" names an SVG symbol in ui/index.html (#i-user, #i-users, #i-briefcase).
WHO = {
    "self": {"ro": "Poți face singur", "en": "You can do this yourself", "icon": "user"},
    "helper": {"ro": "Cere ajutorul cuiva care se pricepe (un părinte, un nepot, un prieten)",
               "en": "Ask someone who knows computers (a parent, a grandchild, a friend)", "icon": "users"},
    "it": {"ro": "Cere ajutorul firmei IT sau al celui care a instalat aparatul",
           "en": "Ask the IT company or the person who set up the device", "icon": "briefcase"},
}

SIMPLE: dict[str, dict] = {
    "TELNET_OPEN": {
        "who": "helper",
        "ro": {
            "title": "Un aparat poate fi controlat de departe, fără protecție",
            "explain": "Aparatul are o ușă veche prin care cineva îl poate controla de departe. Parola trece prin ușa asta neascunsă, așa că altcineva o poate vedea.",
            "steps": ["Cere ajutorul cuiva care se pricepe.",
                      "Împreună, opriți opțiunea „Telnet” din setările aparatului.",
                      "Puneți aparatului o parolă nouă și lungă."],
        },
        "en": {
            "title": "A device can be controlled from far away, without protection",
            "explain": "This device has an old door that lets someone control it from far away. The password goes through that door without being hidden, so someone else can see it.",
            "steps": ["Ask someone who knows computers for help.",
                      "Together, turn off the “Telnet” option in the device settings.",
                      "Give the device a new, long password."],
        },
    },
    "RDP_EXPOSED": {
        "who": "helper",
        "ro": {
            "title": "Altcineva îți poate folosi calculatorul de departe",
            "explain": "Calculatorul lasă pe altcineva din rețea să-l folosească de departe, ca și cum ar sta în fața lui. Cei rău-intenționați încearcă multe parole la rând ca să intre.",
            "steps": ["Dacă nu folosești asta, cere ajutor ca să fie oprit „Desktop la distanță”.",
                      "Pune contului de pe calculator o parolă lungă, pe care n-o folosești în altă parte."],
        },
        "en": {
            "title": "Someone else can use your computer from far away",
            "explain": "This computer lets someone on the network use it from far away, as if they were sitting in front of it. Bad people try many passwords, one after another, to get in.",
            "steps": ["If you do not use this, ask for help to turn off “Remote Desktop”.",
                      "Give the computer account a long password that you do not use anywhere else."],
        },
    },
    "VNC_EXPOSED": {
        "who": "helper",
        "ro": {
            "title": "Altcineva îți poate vedea ecranul",
            "explain": "Pe calculator merge un program care arată ecranul altor oameni din rețea. Dacă parola e slabă, un străin ar putea vedea și apăsa ce vrea pe ecranul tău.",
            "steps": ["Întreabă în familie dacă cineva a instalat un program de „ecran la distanță”.",
                      "Dacă nu e nevoie de el, cere ajutor ca să fie închis sau șters.",
                      "Dacă e nevoie de el, pune-i o parolă lungă."],
        },
        "en": {
            "title": "Someone else can see your screen",
            "explain": "A program on this computer shows the screen to other people on the network. If its password is weak, a stranger could see your screen and click on anything.",
            "steps": ["Ask your family if someone installed a “remote screen” program.",
                      "If nobody needs it, ask for help to close or remove it.",
                      "If someone needs it, give it a long password."],
        },
    },
    "DB_EXPOSED": {
        "who": "it",
        "ro": {
            "title": "Un dulap cu date e deschis pentru toată rețeaua",
            "explain": "Pe un aparat stă un program care păstrează date, ca un dulap cu dosare. Dulapul e deschis pentru oricine din rețea, deci cineva ar putea citi sau strica datele.",
            "steps": ["Spune-i celui care a instalat programul (sau firmei IT) că acest dulap e deschis.",
                      "Rugați-l să-l închidă pentru restul rețelei și să-i pună parolă."],
        },
        "en": {
            "title": "A cupboard full of data is open to the whole network",
            "explain": "A program on this device keeps data, like a cupboard full of files. The cupboard is open to anyone on the network, so someone could read or break the data.",
            "steps": ["Tell the person who installed the program (or the IT company) that this cupboard is open.",
                      "Ask them to close it to the rest of the network and give it a password."],
        },
    },
    "CAMERA_STREAM_EXPOSED": {
        "who": "self",
        "ro": {
            "title": "Altcineva poate vedea ce filmează camera ta",
            "explain": "Camera video trimite imaginea oricui o cere din rețea. Dacă are încă parola din cutie, un străin poate vedea ce se întâmplă în casă.",
            "steps": ["Deschide aplicația camerei pe telefon.",
                      "Caută „Parolă” și pune una nouă și lungă, pe care n-o folosești în altă parte.",
                      "Dacă aplicația îți arată o „Actualizare”, apasă pe ea."],
        },
        "en": {
            "title": "Someone else can watch what your camera films",
            "explain": "Your video camera sends its picture to anyone on the network who asks. If it still has the password from the box, a stranger can see what happens in your home.",
            "steps": ["Open the camera app on your phone.",
                      "Find “Password” and set a new, long one that you do not use anywhere else.",
                      "If the app shows an “Update”, tap it."],
        },
    },
    "OUTDATED_SERVICE": {
        "who": "helper",
        "ro": {
            "title": "Un program e prea vechi și are găuri cunoscute",
            "explain": "Un program de pe aparat e foarte vechi. E ca o încuietoare pentru care hoții au deja cheia.",
            "steps": ["Caută în setările aparatului butonul „Actualizare” și apasă-l.",
                      "Dacă nu-l găsești, cere ajutorul cuiva care se pricepe.",
                      "Dacă aparatul nu mai primește actualizări, gândiți-vă să-l schimbați."],
        },
        "en": {
            "title": "A program is too old and has known holes",
            "explain": "A program on this device is very old. It is like a lock that thieves already have the key for.",
            "steps": ["Look for an “Update” button in the device settings and press it.",
                      "If you cannot find it, ask someone who knows computers.",
                      "If the device gets no more updates, think about replacing it."],
        },
    },
    "FTP_CLEARTEXT": {
        "who": "helper",
        "ro": {
            "title": "Fișierele și parola circulă fără protecție",
            "explain": "Aparatul trimite fișiere pe un drum vechi, unde parola și fișierele nu sunt ascunse. Cineva din rețea le poate vedea pe drum.",
            "steps": ["Dacă nu trimiți fișiere cu acest aparat, cere ajutor ca să fie oprit „FTP”.",
                      "Schimbă parola folosită aici, pentru că poate a fost deja văzută."],
        },
        "en": {
            "title": "Files and the password travel without protection",
            "explain": "This device sends files along an old road where the password and the files are not hidden. Someone on the network can see them on the way.",
            "steps": ["If you do not send files with this device, ask for help to turn off “FTP”.",
                      "Change the password used here, because someone may have seen it already."],
        },
    },
    "HTTP_ADMIN_CLEARTEXT": {
        "who": "helper",
        "ro": {
            "title": "Pagina cu setările aparatului nu e protejată",
            "explain": "Când scrii parola ca să schimbi setările aparatului, ea trece prin rețea neascunsă. Altcineva din rețea ar putea s-o citească.",
            "steps": ["Intră în pagina de setări doar când chiar e nevoie.",
                      "Cere ajutor ca să fie pornit „HTTPS” (adresa paginii începe atunci cu https://).",
                      "Schimbă parola aparatului cu una nouă și lungă."],
        },
        "en": {
            "title": "The device's settings page is not protected",
            "explain": "When you type the password to change this device's settings, it travels through the network without being hidden. Someone else on the network could read it.",
            "steps": ["Only open the settings page when you really need to.",
                      "Ask for help to turn on “HTTPS” (the page address then starts with https://).",
                      "Change the device password to a new, long one."],
        },
    },
    "SMB_EXPOSED": {
        "who": "helper",
        "ro": {
            "title": "Calculatorul își arată dosarele altora din rețea",
            "explain": "Calculatorul lasă alte aparate din rețea să-i vadă dosarele. Dacă un dosar nu are parolă, altcineva poate citi sau schimba fișierele tale.",
            "steps": ["Dacă nu împarți fișiere cu alții, cere ajutor ca să fie oprită „Partajarea fișierelor”.",
                      "Când folosești Wi-Fi la cafenea sau la școală, alege varianta „Publică”."],
        },
        "en": {
            "title": "Your computer shows its folders to others on the network",
            "explain": "This computer lets other devices on the network look into its folders. If a folder has no password, someone else can read or change your files.",
            "steps": ["If you do not share files with others, ask for help to turn off “File sharing”.",
                      "When you use Wi-Fi at a café or at school, choose “Public”."],
        },
    },
    "MQTT_EXPOSED": {
        "who": "helper",
        "ro": {
            "title": "Aparatele inteligente vorbesc între ele fără parolă",
            "explain": "Becurile, prizele și senzorii inteligenți își trimit mesaje printr-un loc care nu cere parolă. Cineva din rețea le-ar putea asculta sau le-ar putea da comenzi false.",
            "steps": ["Deschide aplicația aparatelor inteligente din casă.",
                      "Caută „Parolă” sau „Securitate” și pune o parolă.",
                      "Dacă nu te descurci, cere ajutorul cuiva care se pricepe."],
        },
        "en": {
            "title": "Smart devices talk to each other without a password",
            "explain": "Smart bulbs, plugs and sensors send messages through a place that asks for no password. Someone on the network could listen to them or give them fake orders.",
            "steps": ["Open the app for your smart home devices.",
                      "Find “Password” or “Security” and set a password.",
                      "If it is hard, ask someone who knows computers."],
        },
    },
    "UPNP_EXPOSED": {
        "who": "self",
        "ro": {
            "title": "Aparatele pot deschide singure uși spre internet",
            "explain": "Routerul lasă aparatele din casă să deschidă singure uși spre internet, fără să te întrebe. Dacă un aparat e păcălit, poate lăsa străini să intre.",
            "steps": ["Deschide aplicația routerului (cutia care îți dă internetul).",
                      "Caută „UPnP” și oprește-l, apoi apasă „Salvează”.",
                      "Dacă după asta un joc nu mai merge, cere ajutor."],
        },
        "en": {
            "title": "Devices can open doors to the internet by themselves",
            "explain": "Your router lets devices at home open doors to the internet without asking you. If a device is tricked, it can let strangers in.",
            "steps": ["Open the app for your router (the box that gives you internet).",
                      "Find “UPnP”, turn it off, then press “Save”.",
                      "If a game stops working after this, ask for help."],
        },
    },
    "SNMP_EXPOSED": {
        "who": "it",
        "ro": {
            "title": "Aparatul spune multe despre el oricui întreabă",
            "explain": "Aparatul răspunde la întrebări despre el de la oricine din rețea și folosește o parolă pe care o știe toată lumea. Un străin ar putea afla multe sau chiar schimba setări.",
            "steps": ["Cere ajutorul firmei IT sau al cuiva care se pricepe.",
                      "Rugați-i să oprească „SNMP” sau să-i pună o parolă adevărată."],
        },
        "en": {
            "title": "The device tells a lot about itself to anyone who asks",
            "explain": "This device answers questions about itself from anyone on the network, using a password everybody knows. A stranger could learn a lot or even change settings.",
            "steps": ["Ask the IT company or someone who knows computers.",
                      "Ask them to turn off “SNMP” or give it a real password."],
        },
    },
    "PRINTER_RAW_EXPOSED": {
        "who": "self",
        "ro": {
            "title": "Oricine din rețea poate tipări la imprimanta ta",
            "explain": "Imprimanta tipărește orice primește, fără să întrebe cine trimite. Cineva din rețea ar putea să-ți consume hârtia sau să-i schimbe setările.",
            "steps": ["Nu e o urgență dacă în rețea sunt doar oamenii din casă.",
                      "Pune o parolă la setările imprimantei (din aplicația sau instrucțiunile ei).",
                      "Dacă aplicația imprimantei îți arată o „Actualizare”, apasă pe ea."],
        },
        "en": {
            "title": "Anyone on the network can print on your printer",
            "explain": "The printer prints whatever it gets, without asking who sent it. Someone on the network could use up your paper or change its settings.",
            "steps": ["It is not urgent if only the people in your home use the network.",
                      "Set a password for the printer settings (in its app or its instructions).",
                      "If the printer app shows an “Update”, tap it."],
        },
    },
    "UNKNOWN_DEVICE": {
        "who": "self",
        "ro": {
            "title": "Un aparat necunoscut e conectat la rețeaua ta",
            "explain": "În rețeaua ta e un aparat fără nume, pe care nu-l putem recunoaște. Poate fi al tău, dar poate fi și al unui străin care îți folosește internetul.",
            "steps": ["Întreabă pe toți din casă dacă au conectat ceva nou.",
                      "Dacă nimeni nu-l recunoaște, schimbă parola Wi-Fi din aplicația routerului.",
                      "Pune apoi parola nouă doar pe aparatele voastre."],
        },
        "en": {
            "title": "An unknown device is connected to your network",
            "explain": "There is a device on your network with no name, and we cannot recognise it. It may be yours, but it may also belong to a stranger using your internet.",
            "steps": ["Ask everyone at home if they connected something new.",
                      "If nobody knows it, change the Wi-Fi password in your router app.",
                      "Then put the new password only on your own devices."],
        },
    },
    "SSH_OPEN": {
        "who": "self",
        "ro": {
            "title": "Un aparat are o ușă sigură pentru control de departe",
            "explain": "Aparatul poate fi controlat de departe, dar printr-o ușă cu lacăt bun. E în regulă dacă cineva din familie a pornit-o intenționat.",
            "steps": ["Întreabă dacă cineva din casă folosește această funcție.",
                      "Dacă nu o folosește nimeni, cere ajutor ca să fie oprită."],
        },
        "en": {
            "title": "A device has a safe door for control from far away",
            "explain": "This device can be controlled from far away, but through a door with a good lock. That is fine if someone in your family turned it on on purpose.",
            "steps": ["Ask if someone at home uses this feature.",
                      "If nobody uses it, ask for help to turn it off."],
        },
    },
}

# Words a beginner may not know, explained with the same "home" picture.
GLOSSARY = {
    "ro": [
        ("Rețea (Wi-Fi)", "Drumul nevăzut prin care aparatele din casă vorbesc între ele și cu internetul."),
        ("Router", "Cutia cu beculețe care îți dă internet în casă. E ca ușa de la intrare a casei tale digitale."),
        ("Aparat", "Orice lucru conectat la internet: telefon, calculator, televizor, cameră video, imprimantă."),
        ("Ușă deschisă", "Un loc prin care alte aparate pot intra în vorbă cu aparatul tău. Specialiștii îi spun „port”."),
        ("Parolă", "Cheia care încuie. Una bună e lungă, de exemplu trei cuvinte care nu au legătură între ele."),
        ("Actualizare", "O reparație gratuită de la cei care au făcut aparatul. Astupă găurile cunoscute."),
        ("Scor", "Un număr de la 0 la 100. Cu cât e mai mare, cu atât casa ta digitală e mai sigură."),
    ],
    "en": [
        ("Network (Wi-Fi)", "The invisible road your devices at home use to talk to each other and to the internet."),
        ("Router", "The box with little lights that gives you internet at home. It is like the front door of your digital home."),
        ("Device", "Anything connected to the internet: phone, computer, TV, video camera, printer."),
        ("Open door", "A place where other devices can start talking to your device. Experts call it a “port”."),
        ("Password", "The key that locks things. A good one is long, for example three words that have nothing in common."),
        ("Update", "A free repair from the people who made the device. It closes known holes."),
        ("Score", "A number from 0 to 100. The higher it is, the safer your digital home is."),
    ],
}


def simple_for(code: str, lang: str = "ro") -> dict:
    lang = lang if lang in ("ro", "en") else "ro"
    entry = SIMPLE[code]
    return {**entry[lang], "who": entry["who"]}

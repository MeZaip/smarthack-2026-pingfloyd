"""Built-in, human-reviewed explanations and fixes (FR-07, FR-08, NFR-09).

These texts are the ground truth shown to users and the mandatory fallback
when the LLM is unavailable. Rules for editing:
  * explanation: at most 2 sentences, no unexplained jargon, ~12-year-old level
  * steps: 1-5 concrete, ordered actions a non-expert can do
  * never mention ports, CVEs or numbers here that are not generic; the
    concrete port/device comes from the finding itself
"""
from __future__ import annotations

TEXTS: dict[str, dict] = {
    "TELNET_OPEN": {
        "refs": ["CIS Control 4.8", "OWASP IoT I2"],
        "ro": {
            "title": "Acces de la distanță fără criptare (Telnet)",
            "explain": "Dispozitivul acceptă conectări de la distanță printr-o metodă veche, în care parola circulă prin rețea ca text simplu. Oricine e conectat la aceeași rețea o poate citi și poate prelua controlul dispozitivului.",
            "steps": [
                "Intră în pagina de setări a dispozitivului (de obicei din browser, la adresa lui IP).",
                "Caută opțiunea „Telnet” sau „Remote access” și dezactiveaz-o.",
                "Dacă ai nevoie de acces de la distanță, folosește în loc „SSH”, care este criptat.",
                "Schimbă parola dispozitivului cu una lungă și unică.",
                "Dacă nu poți opri Telnet, actualizează software-ul dispozitivului sau înlocuiește-l.",
            ],
        },
        "en": {
            "title": "Remote login without encryption (Telnet)",
            "explain": "This device accepts remote logins using an old method that sends the password across the network as plain text. Anyone on the same network can read it and take control of the device.",
            "steps": [
                "Open the device's settings page (usually in a browser, at its IP address).",
                "Find the “Telnet” or “Remote access” option and turn it off.",
                "If you need remote access, use “SSH” instead, which is encrypted.",
                "Change the device password to a long, unique one.",
                "If Telnet cannot be turned off, update the device software or replace the device.",
            ],
        },
    },
    "RDP_EXPOSED": {
        "refs": ["CIS Control 4.8", "CIS Control 4.4"],
        "ro": {
            "title": "Calculatorul poate fi controlat de la distanță (Remote Desktop)",
            "explain": "Pe acest calculator este pornit „Desktop la distanță”, deci cineva din rețea poate încerca să se conecteze și să-l folosească ca și cum ar sta în fața lui. Atacatorii încearcă des parole la rând pe acest serviciu.",
            "steps": [
                "Pe calculator, deschide Setări → Sistem → Desktop la distanță.",
                "Dacă nu folosești această funcție, oprește-o.",
                "Dacă ai nevoie de ea, lasă activată opțiunea „Autentificare la nivel de rețea (NLA)”.",
                "Folosește o parolă puternică pentru contul Windows.",
            ],
        },
        "en": {
            "title": "Computer can be controlled remotely (Remote Desktop)",
            "explain": "Remote Desktop is turned on, so someone on the network can try to connect and use this computer as if they were sitting in front of it. Attackers often try many passwords against this service.",
            "steps": [
                "On the computer, open Settings → System → Remote Desktop.",
                "If you do not use this feature, turn it off.",
                "If you need it, keep “Network Level Authentication (NLA)” enabled.",
                "Use a strong password for the Windows account.",
            ],
        },
    },
    "VNC_EXPOSED": {
        "refs": ["CIS Control 4.8"],
        "ro": {
            "title": "Ecranul poate fi văzut și controlat de la distanță (VNC)",
            "explain": "Un program de partajare a ecranului ascultă conexiuni din rețea. Multe astfel de programe au parole slabe sau deloc, așa că altcineva ar putea vedea și controla ecranul.",
            "steps": [
                "Află ce program de partajare a ecranului rulează (de ex. VNC, RealVNC, TightVNC).",
                "Dacă nu îl folosești, închide-l și oprește pornirea lui automată.",
                "Dacă îl folosești, setează o parolă lungă și permite conectarea doar când ai nevoie.",
            ],
        },
        "en": {
            "title": "Screen can be viewed and controlled remotely (VNC)",
            "explain": "A screen-sharing program is listening for connections from the network. Many of these have weak or no passwords, so someone else could see and control the screen.",
            "steps": [
                "Find out which screen-sharing program is running (e.g. VNC, RealVNC, TightVNC).",
                "If you do not use it, close it and stop it from starting automatically.",
                "If you use it, set a long password and only allow connections when you need them.",
            ],
        },
    },
    "DB_EXPOSED": {
        "refs": ["CIS Control 3.3", "CIS Control 4.4"],
        "ro": {
            "title": "O bază de date poate fi accesată din rețea",
            "explain": "Un program care păstrează date (o bază de date) primește conexiuni de la orice dispozitiv din rețea. Dacă nu are parolă sau are una slabă, cineva poate citi, schimba sau șterge datele.",
            "steps": [
                "Află ce aplicație sau container a pornit baza de date.",
                "Configureaz-o să accepte conexiuni doar de pe același calculator (adresa 127.0.0.1).",
                "Setează o parolă puternică pentru acces.",
                "Dacă nu ai nevoie de ea, oprește serviciul.",
            ],
        },
        "en": {
            "title": "A database can be reached from the network",
            "explain": "A program that stores data (a database) accepts connections from any device on the network. Without a strong password, someone could read, change or delete the data.",
            "steps": [
                "Find out which app or container started the database.",
                "Configure it to accept connections only from the same computer (address 127.0.0.1).",
                "Set a strong password for access.",
                "If you do not need it, stop the service.",
            ],
        },
    },
    "CAMERA_STREAM_EXPOSED": {
        "refs": ["OWASP IoT I1", "OWASP IoT I9"],
        "ro": {
            "title": "Imaginea camerei video poate fi văzută din rețea",
            "explain": "Camera trimite imaginea video către oricine se conectează la ea din rețea. Dacă nu cere parolă sau folosește parola din fabrică, altcineva poate vedea ce filmează camera.",
            "steps": [
                "Deschide aplicația sau pagina de setări a camerei.",
                "Schimbă parola din fabrică cu una lungă și unică.",
                "Oprește opțiunea „RTSP” sau „flux video” dacă vezi imaginea doar din aplicația oficială.",
                "Instalează cea mai nouă versiune de software a camerei.",
                "Mută camera pe rețeaua de oaspeți sau pe o rețea separată, dacă routerul permite.",
            ],
        },
        "en": {
            "title": "Camera video can be watched from the network",
            "explain": "The camera sends its video to anyone who connects to it on the network. If it has no password or still uses the factory password, someone else can watch what it records.",
            "steps": [
                "Open the camera's app or settings page.",
                "Change the factory password to a long, unique one.",
                "Turn off the “RTSP” or “video stream” option if you only watch through the official app.",
                "Install the latest software update for the camera.",
                "Move the camera to a guest or separate network if your router supports it.",
            ],
        },
    },
    "OUTDATED_SERVICE": {
        "refs": ["CIS Control 7.4", "OWASP IoT I5"],
        "ro": {
            "title": "Program vechi, cu probleme de securitate cunoscute",
            "explain": "Pe dispozitiv rulează o versiune veche a unui program, pentru care se știu public metode de atac. E ca o încuietoare pentru care toată lumea are deja cheia.",
            "steps": [
                "Notează numele și versiunea programului afișate în detaliile problemei.",
                "Instalează actualizările disponibile pentru dispozitiv sau pentru acel program.",
                "Dacă nu mai există actualizări, oprește programul sau înlocuiește dispozitivul.",
                "Rulează din nou verificarea ca să confirmi că versiunea veche a dispărut.",
            ],
        },
        "en": {
            "title": "Old software with known security problems",
            "explain": "This device runs an old version of a program with publicly known ways to attack it. It is like a lock that everyone already has a key for.",
            "steps": [
                "Note the program name and version shown in the finding details.",
                "Install the available updates for the device or for that program.",
                "If no updates exist anymore, stop the program or replace the device.",
                "Run the check again to confirm the old version is gone.",
            ],
        },
    },
    "FTP_CLEARTEXT": {
        "refs": ["CIS Control 3.10", "OWASP IoT I7"],
        "ro": {
            "title": "Transfer de fișiere fără criptare (FTP)",
            "explain": "Dispozitivul permite copierea de fișiere printr-o metodă veche, în care numele de utilizator, parola și fișierele circulă necriptat. Cineva din rețea le poate intercepta.",
            "steps": [
                "Dacă nu folosești transferul de fișiere, oprește serviciul FTP din setările dispozitivului sau ale aplicației.",
                "Dacă ai nevoie de el, folosește în loc SFTP sau FTPS, care sunt criptate.",
                "Schimbă parola folosită pentru FTP, pentru că este posibil să fi fost deja văzută.",
            ],
        },
        "en": {
            "title": "File transfer without encryption (FTP)",
            "explain": "This device allows copying files using an old method where the username, password and files travel unencrypted. Someone on the network could capture them.",
            "steps": [
                "If you do not use file transfer, turn off the FTP service in the device or app settings.",
                "If you need it, use SFTP or FTPS instead, which are encrypted.",
                "Change the password used for FTP, since it may already have been seen.",
            ],
        },
    },
    "HTTP_ADMIN_CLEARTEXT": {
        "refs": ["CIS Control 3.10", "OWASP IoT I7"],
        "ro": {
            "title": "Pagină de administrare fără conexiune securizată",
            "explain": "Pagina în care te autentifici ca să schimbi setările dispozitivului nu folosește conexiune securizată (adresa începe cu http://, fără „s”). Parola pe care o scrii acolo poate fi citită de altcineva din rețea.",
            "steps": [
                "Intră în pagina de administrare și caută o opțiune precum „HTTPS”, „Secure management” sau „SSL”.",
                "Activează HTTPS și, de acum, folosește doar adresa care începe cu https://.",
                "Dezactivează accesul la administrare prin HTTP simplu, dacă există opțiunea.",
                "Schimbă parola de administrator cu una lungă și unică.",
                "Dacă dispozitivul nu are HTTPS, actualizează-i software-ul.",
            ],
        },
        "en": {
            "title": "Admin page without a secure connection",
            "explain": "The page where you log in to change the device settings does not use a secure connection (the address starts with http://, without the “s”). The password you type there can be read by someone else on the network.",
            "steps": [
                "Open the admin page and look for an option like “HTTPS”, “Secure management” or “SSL”.",
                "Turn on HTTPS and from now on use only the address starting with https://.",
                "Turn off admin access over plain HTTP if the option exists.",
                "Change the admin password to a long, unique one.",
                "If the device has no HTTPS option, update its software.",
            ],
        },
    },
    "SMB_EXPOSED": {
        "refs": ["CIS Control 4.8", "CIS Control 3.3"],
        "ro": {
            "title": "Partajare de fișiere Windows deschisă",
            "explain": "Calculatorul își împarte fișierele sau folderele cu alte dispozitive din rețea. Dacă un folder este partajat fără parolă sau cu drepturi prea largi, altcineva îl poate citi sau modifica.",
            "steps": [
                "Pe calculator, deschide Setări → Rețea și internet → Setări avansate de partajare.",
                "Dacă nu partajezi fișiere, oprește „Partajarea fișierelor și imprimantelor”.",
                "Dacă partajezi, verifică folderele partajate și lasă doar ce e necesar, cu parolă.",
                "Setează rețeaua Wi-Fi ca „Publică” când nu ești acasă.",
            ],
        },
        "en": {
            "title": "Windows file sharing is open",
            "explain": "This computer shares files or folders with other devices on the network. If a folder is shared without a password or with too many rights, someone else could read or change it.",
            "steps": [
                "On the computer, open Settings → Network & internet → Advanced sharing settings.",
                "If you do not share files, turn off “File and printer sharing”.",
                "If you do share, review the shared folders and keep only what is needed, with a password.",
                "Set the Wi-Fi network to “Public” when you are not at home.",
            ],
        },
    },
    "MQTT_EXPOSED": {
        "refs": ["OWASP IoT I2", "OWASP IoT I7"],
        "ro": {
            "title": "Centrala de mesaje pentru dispozitive inteligente este deschisă",
            "explain": "Un serviciu prin care dispozitivele inteligente (becuri, senzori, prize) își trimit comenzi acceptă conexiuni de la oricine din rețea. Cineva ar putea citi datele senzorilor sau trimite comenzi false.",
            "steps": [
                "Deschide setările hub-ului inteligent sau ale serverului MQTT (de ex. Mosquitto, Home Assistant).",
                "Activează autentificarea cu utilizator și parolă și dezactivează accesul anonim.",
                "Activează criptarea (TLS), dacă există opțiunea.",
                "Actualizează software-ul hub-ului.",
            ],
        },
        "en": {
            "title": "Smart-device message hub is open",
            "explain": "A service that smart devices (bulbs, sensors, plugs) use to send each other commands accepts connections from anyone on the network. Someone could read sensor data or send fake commands.",
            "steps": [
                "Open the settings of your smart hub or MQTT server (e.g. Mosquitto, Home Assistant).",
                "Turn on username-and-password login and turn off anonymous access.",
                "Turn on encryption (TLS) if available.",
                "Update the hub's software.",
            ],
        },
    },
    "UPNP_EXPOSED": {
        "refs": ["CIS Control 4.8", "OWASP IoT I9"],
        "ro": {
            "title": "Dispozitivul poate deschide singur „uși” în router (UPnP)",
            "explain": "Funcția UPnP permite programelor și dispozitivelor din casă să deschidă singure accesul din internet către ele, fără să te întrebe. Un dispozitiv compromis poate folosi asta ca să se expună pe internet.",
            "steps": [
                "Intră în pagina de setări a routerului.",
                "Caută „UPnP” (de obicei la Avansat sau NAT).",
                "Dezactivează UPnP și salvează setările.",
                "Dacă un joc sau o aplicație nu mai merge, deschide manual doar portul de care are nevoie.",
            ],
        },
        "en": {
            "title": "Device can open “doors” in the router by itself (UPnP)",
            "explain": "UPnP lets programs and devices at home open access from the internet to themselves without asking you. A hacked device can use it to expose itself to the internet.",
            "steps": [
                "Open your router's settings page.",
                "Look for “UPnP” (usually under Advanced or NAT).",
                "Turn UPnP off and save.",
                "If a game or app stops working, manually open only the port it needs.",
            ],
        },
    },
    "SNMP_EXPOSED": {
        "refs": ["CIS Control 4.8"],
        "ro": {
            "title": "Protocolul de administrare a dispozitivului este accesibil (SNMP)",
            "explain": "Dispozitivul răspunde la cereri prin care se pot afla multe detalii despre el, uneori chiar se pot schimba setări. De multe ori folosește o „parolă” implicită cunoscută de toată lumea, precum „public”.",
            "steps": [
                "Intră în pagina de setări a dispozitivului și caută „SNMP”.",
                "Dacă nu folosești monitorizare, dezactivează SNMP.",
                "Dacă ai nevoie de el, schimbă numele de comunitate „public” și „private” sau folosește SNMPv3 cu parolă.",
            ],
        },
        "en": {
            "title": "Device management protocol is reachable (SNMP)",
            "explain": "The device answers requests that reveal a lot about it, and sometimes allow changing settings. It often uses a default “password” everyone knows, such as “public”.",
            "steps": [
                "Open the device's settings page and look for “SNMP”.",
                "If you do not use monitoring, turn SNMP off.",
                "If you need it, change the “public” and “private” community names or use SNMPv3 with a password.",
            ],
        },
    },
    "PRINTER_RAW_EXPOSED": {
        "refs": ["CIS Control 4.8"],
        "ro": {
            "title": "Oricine din rețea poate trimite documente la imprimantă",
            "explain": "Imprimanta acceptă documente de tipărit direct, fără nicio verificare. Cineva din rețea poate tipări orice sau, la unele modele, poate schimba setări.",
            "steps": [
                "Deschide pagina de setări a imprimantei (adresa ei IP în browser).",
                "Dezactivează „Raw printing”, „Port 9100” sau „JetDirect”, dacă tipărești prin altă metodă (de ex. IPP).",
                "Setează o parolă de administrator pentru imprimantă.",
                "Actualizează software-ul imprimantei.",
            ],
        },
        "en": {
            "title": "Anyone on the network can send jobs to the printer",
            "explain": "The printer accepts print jobs directly, without any check. Someone on the network can print anything or, on some models, change settings.",
            "steps": [
                "Open the printer's settings page (its IP address in a browser).",
                "Turn off “Raw printing”, “Port 9100” or “JetDirect” if you print another way (e.g. IPP).",
                "Set an admin password on the printer.",
                "Update the printer's software.",
            ],
        },
    },
    "UNKNOWN_DEVICE": {
        "refs": ["CIS Control 1.1"],
        "ro": {
            "title": "Dispozitiv care nu poate fi identificat",
            "explain": "În rețea există un dispozitiv fără nume și fără producător cunoscut, care are servicii deschise. Trebuie să afli ce este, pentru că s-ar putea să nu fie al tău.",
            "steps": [
                "Uită-te în lista de dispozitive conectate din aplicația sau pagina routerului.",
                "Încearcă să-l recunoști după momentul conectării sau oprind pe rând dispozitivele tale.",
                "Dacă nu îl recunoști, blochează-l din router și schimbă parola Wi-Fi.",
            ],
        },
        "en": {
            "title": "Device that cannot be identified",
            "explain": "There is a device on the network with no name and no known maker, and it has open services. You should find out what it is, because it might not be yours.",
            "steps": [
                "Check the list of connected devices in your router's app or page.",
                "Try to recognise it by when it connected, or by switching your own devices off one by one.",
                "If you do not recognise it, block it in the router and change the Wi-Fi password.",
            ],
        },
    },
    "SSH_OPEN": {
        "refs": ["CIS Control 4.8"],
        "ro": {
            "title": "Acces de la distanță criptat (SSH), doar informativ",
            "explain": "Dispozitivul permite conectarea de la distanță printr-o metodă sigură, cu criptare. Nu este o problemă dacă ai pornit-o intenționat și folosești o parolă puternică.",
            "steps": [
                "Verifică dacă ai nevoie de acces de la distanță la acest dispozitiv.",
                "Dacă nu, oprește serviciul SSH.",
                "Dacă da, folosește o parolă puternică sau, mai bine, chei SSH.",
            ],
        },
        "en": {
            "title": "Encrypted remote login (SSH), for your information",
            "explain": "This device allows remote login using a secure, encrypted method. That is fine if you turned it on on purpose and use a strong password.",
            "steps": [
                "Check whether you need remote access to this device.",
                "If not, turn off the SSH service.",
                "If yes, use a strong password or, better, SSH keys.",
            ],
        },
    },
}

SEVERITY_LABELS = {
    "high": {"ro": "Risc mare", "en": "High risk", "icon": "⛔"},
    "medium": {"ro": "Risc mediu", "en": "Medium risk", "icon": "⚠️"},
    "low": {"ro": "Risc mic", "en": "Low risk", "icon": "🔎"},
    "info": {"ro": "Informativ", "en": "Information", "icon": "ℹ️"},
}

LANGS = ("ro", "en")


def text_for(code: str, lang: str = "ro") -> dict:
    lang = lang if lang in LANGS else "ro"
    entry = TEXTS[code]
    return {**entry[lang], "refs": entry.get("refs", [])}


def score_band(score: int, lang: str = "ro") -> dict:
    """Traffic light with icon + label (colour is never the only signal, NFR-08)."""
    if score >= 80:
        return {"color": "green", "icon": "✅", "label": {"ro": "Bine", "en": "Good"}[lang]}
    if score >= 50:
        return {"color": "amber", "icon": "⚠️", "label": {"ro": "Necesită atenție", "en": "Needs attention"}[lang]}
    return {"color": "red", "icon": "⛔", "label": {"ro": "Risc ridicat", "en": "High risk"}[lang]}

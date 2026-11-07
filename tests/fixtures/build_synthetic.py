"""Builds SYNTHETIC copies of the Validation Set described in the brief.

They are hand-made stand-ins so we can test before kickoff. At hour 0 drop the
OFFICIAL files into tests/fixtures/validation/ — tests prefer that folder.

Run:  python tests/fixtures/build_synthetic.py
"""
from pathlib import Path
from xml.sax.saxutils import quoteattr

OUT = Path(__file__).parent / "validation_synthetic"
NET = "192.168.1."


def port(proto, num, name, state="open", product="", version="", tunnel="", title=None):
    attrs = f'name={quoteattr(name)}'
    if product:
        attrs += f' product={quoteattr(product)}'
    if version:
        attrs += f' version={quoteattr(version)}'
    if tunnel:
        attrs += f' tunnel={quoteattr(tunnel)}'
    script = ""
    if title is not None:
        script = (f'<script id="http-title" output={quoteattr(title)}>'
                  f'<elem key="title">{title}</elem></script>')
    return (f'<port protocol="{proto}" portid="{num}"><state state="{state}" reason="syn-ack"/>'
            f'<service {attrs} method="probed" conf="10"/>{script}</port>')


def host(last, mac=None, vendor=None, hostname=None, ports=()):
    addr = f'<address addr="{NET}{last}" addrtype="ipv4"/>'
    if mac:
        v = f' vendor={quoteattr(vendor)}' if vendor else ""
        addr += f'<address addr="{mac}" addrtype="mac"{v}/>'
    hn = f'<hostname name="{hostname}" type="PTR"/>' if hostname else ""
    return (f'<host><status state="up" reason="arp-response"/>{addr}<hostnames>{hn}</hostnames>'
            f'<ports>{"".join(ports)}</ports></host>')


def doc(*hosts):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE nmaprun>\n'
            '<nmaprun scanner="nmap" args="nmap -sS -sU -sV -oX" start="1700000000" version="7.94">'
            + "".join(hosts) + '<runstats><finished time="1700000100"/></runstats></nmaprun>\n')


FILES = {
    "V1_home_basic.xml": doc(
        host(1, "14:CC:20:11:22:33", "TP-Link Technologies", "router.lan", [
            port("tcp", 53, "domain", product="dnsmasq", version="2.80"),
            port("tcp", 80, "http", product="lighttpd", title="Router Login"),
            port("tcp", 443, "http", product="lighttpd", tunnel="ssl", title="Router Login"),  # trap
        ]),
        host(10, "A4:83:E7:01:02:03", "Apple", "macbook.lan", [
            port("udp", 5353, "zeroconf", state="open|filtered"),
        ]),
        host(11, "8C:F5:A3:04:05:06", "Samsung Electronics", "galaxy.lan"),
        host(12, "02:11:22:33:44:55", None, None),  # no vendor/hostname but no open ports -> nothing
    ),
    "V2_smart_home.xml": doc(
        host(1, "C0:06:C3:10:20:30", "TP-Link Technologies", "router.lan", [
            port("tcp", 53, "domain"),
            port("tcp", 80, "http", title="Admin Panel"),
            port("udp", 1900, "upnp", product="MiniUPnP", version="2.1"),
        ]),
        host(40, "44:19:B6:00:00:40", "Hangzhou Hikvision", "ipcam.lan", [
            port("tcp", 80, "http", product="Hikvision httpd", title="Login"),
            port("tcp", 554, "rtsp", product="Hikvision rtspd"),
        ]),
        host(41, "24:0A:C4:00:00:41", "Espressif", "smarthub.lan", [
            port("tcp", 1883, "mqtt", product="Mosquitto", version="1.6.15"),
        ]),
        host(42, "F4:F5:D8:00:00:42", "Google", "chromecast.lan", [
            port("tcp", 8008, "http", title="Chromecast"),  # trap: no admin word
            port("tcp", 8009, "ajp13"),                     # trap: not in catalog
        ]),
    ),
    "V3_small_office.xml": doc(
        host(10, "3C:D9:2B:00:00:10", "Hewlett Packard", "printer.lan", [
            port("tcp", 80, "http", product="HP-ChaiSOE", title="HP LaserJet MFP"),
            port("tcp", 631, "ipp", product="HP IPP"),     # trap
            port("tcp", 9100, "jetdirect"),
        ]),
        host(20, "00:11:32:00:00:20", "Synology Incorporated", "nas.lan", [
            port("tcp", 22, "ssh", product="OpenSSH", version="8.2p1"),
            port("tcp", 139, "netbios-ssn", product="Samba smbd", version="4.6.2"),
            port("tcp", 445, "microsoft-ds", product="Samba smbd", version="4.6.2"),
            port("tcp", 5000, "http", title="Synology DiskStation"),
        ]),
        host(30, "00:15:5D:00:00:30", "Microsoft", "DESKTOP-7Q2.lan", [
            port("tcp", 135, "msrpc", product="Microsoft Windows RPC"),
            port("tcp", 3389, "ms-wbt-server", product="Microsoft Terminal Services"),
        ]),
        host(40, "F8:BC:12:00:00:40", "Dell", "srv01.lan", [
            port("tcp", 22, "ssh", product="OpenSSH", version="7.9p1 Debian 10"),
            port("tcp", 3306, "mysql", product="MySQL", version="5.7.33"),
        ]),
    ),
    "V4_legacy.xml": doc(
        host(1, "00:A0:C5:00:00:01", "ZyXEL Communications", "oldrouter.lan", [
            port("tcp", 23, "telnet", product="BusyBox telnetd"),
            port("tcp", 80, "http", title="Web Configuration"),
            port("udp", 161, "snmp", product="net-snmp"),
        ]),
        host(60, "00:0C:29:00:00:60", "VMware", "oldsrv.lan", [
            port("tcp", 21, "ftp", product="vsftpd", version="2.3.4"),
        ]),
        host(99, "02:42:AC:00:00:99", None, None, [
            port("tcp", 8888, "sun-answerbook"),
        ]),
    ),
    "V5_nonstandard_ports.xml": doc(
        host(5, "B8:27:EB:00:00:05", "Raspberry Pi Foundation", "pi5.lan", [
            port("tcp", 2323, "telnet", product="BusyBox telnetd")]),
        host(6, "B8:27:EB:00:00:06", "Raspberry Pi Foundation", "pi6.lan", [
            port("tcp", 8081, "http", title="Device Settings")]),
        host(7, "B8:27:EB:00:00:07", "Raspberry Pi Foundation", "pi7.lan", [
            port("tcp", 6380, "redis", product="Redis key-value store", version="6.0.16")]),
        host(8, "B8:27:EB:00:00:08", "Raspberry Pi Foundation", "pi8.lan", [
            port("tcp", 8443, "http", tunnel="ssl", title="Admin Console")]),   # trap: HTTPS
        host(9, "B8:27:EB:00:00:09", "Raspberry Pi Foundation", "pi9.lan", [
            port("tcp", 3306, "mysql", state="filtered")]),                      # trap: filtered
    ),
    "V6a_before.xml": doc(
        host(1, "C0:06:C3:10:20:30", "TP-Link Technologies", "router.lan", [
            port("tcp", 80, "http", title="Router Setup"),
            port("tcp", 443, "https"),
            port("udp", 1900, "upnp"),
        ]),
        host(30, "B8:27:EB:00:00:30", "Raspberry Pi Foundation", "pi.lan", [
            port("tcp", 23, "telnet")]),
    ),
    "V6b_after.xml": doc(
        host(1, "C0:06:C3:10:20:30", "TP-Link Technologies", "router.lan", [
            port("tcp", 443, "https")]),
        host(30, "B8:27:EB:00:00:30", "Raspberry Pi Foundation", "pi.lan"),
    ),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in FILES.items():
        (OUT / name).write_text(text, encoding="utf-8")
    full = FILES["V1_home_basic.xml"]
    (OUT / "V7_broken.xml").write_text(full[: len(full) // 2], encoding="utf-8")  # truncated
    print(f"wrote {len(FILES) + 1} files to {OUT}")


if __name__ == "__main__":
    main()

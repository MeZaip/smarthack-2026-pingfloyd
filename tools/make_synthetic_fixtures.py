"""Generate SYNTHETIC look-alikes of the public Validation Set (V1..V7).

They follow the network descriptions and expected answers in the brief so the
rules can be tested before kickoff. When the real Validation Set is released,
put it in tests/fixtures/validation/ - the tests will use it automatically.

    python tools/make_synthetic_fixtures.py
"""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import quoteattr

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "synthetic"

# port tuple: (proto, port, state, service, product, version, tunnel, http_title)
def P(proto, port, service, state="open", product="", version="", tunnel="", title=None):
    return (proto, port, state, service, product, version, tunnel, title)


def host(ip, mac=None, vendor=None, hostname=None, ports=()):
    return dict(ip=ip, mac=mac, vendor=vendor, hostname=hostname, ports=list(ports))


def render(hosts, udp=True) -> str:
    args = "nmap -sS -sU -sV -oX scan.xml 192.168.1.0/24" if udp else "nmap -sS -sV -oX scan.xml 192.168.1.0/24"
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<?xml-stylesheet href="file:///usr/share/nmap/nmap.xsl" type="text/xsl"?>',
           f'<nmaprun scanner="nmap" args={quoteattr(args)} start="1794040000" version="7.95" xmloutputversion="1.05">']
    for h in hosts:
        out.append('<host starttime="1794040001" endtime="1794040100"><status state="up" reason="arp-response"/>')
        out.append(f'<address addr="{h["ip"]}" addrtype="ipv4"/>')
        if h["mac"]:
            v = f' vendor={quoteattr(h["vendor"])}' if h["vendor"] else ""
            out.append(f'<address addr="{h["mac"]}" addrtype="mac"{v}/>')
        out.append("<hostnames>")
        if h["hostname"]:
            out.append(f'<hostname name={quoteattr(h["hostname"])} type="PTR"/>')
        out.append("</hostnames><ports>")
        for proto, port, state, svc, prod, ver, tun, title in h["ports"]:
            out.append(f'<port protocol="{proto}" portid="{port}"><state state="{state}" reason="syn-ack"/>')
            attrs = f'name="{svc}"'
            if prod:
                attrs += f" product={quoteattr(prod)}"
            if ver:
                attrs += f" version={quoteattr(ver)}"
            if tun:
                attrs += f' tunnel="{tun}"'
            out.append(f'<service {attrs} method="probed" conf="10"/>')
            if title is not None:
                out.append(f'<script id="http-title" output={quoteattr(title)}><elem key="title">{title}</elem></script>')
            out.append("</port>")
        out.append("</ports></host>")
    out.append('<runstats><finished time="1794040200" exit="success"/></runstats></nmaprun>')
    return "\n".join(out) + "\n"


ROUTER = dict(mac="50:C7:BF:11:22:33", vendor="TP-Link Technologies", hostname="router.lan")

FILES = {
    "V1_home_basic.xml": [
        host("192.168.1.1", **ROUTER, ports=[
            P("tcp", 53, "domain", product="dnsmasq", version="2.80"),
            P("tcp", 80, "http", product="TP-LINK router http config", title="TP-Link Router Login"),
            P("tcp", 443, "http", tunnel="ssl", title="TP-Link Router Login"),   # trap: HTTPS admin
        ]),
        host("192.168.1.20", "3C:22:FB:00:00:01", "Apple", "macbook.lan",
             ports=[P("tcp", 5000, "rtsp", state="closed")]),
        host("192.168.1.21", "A4:50:46:00:00:02", "Xiaomi Communications", None, ports=[]),
    ],
    "V2_smart_home.xml": [
        host("192.168.1.1", **ROUTER, ports=[
            P("tcp", 80, "http", title="Router Settings"),
            P("tcp", 443, "https", title="Router Settings"),
            P("udp", 1900, "upnp", product="miniupnpd", version="2.1"),
        ]),
        host("192.168.1.40", "C0:56:E3:00:00:40", "Hangzhou Hikvision", "ipcam.lan", ports=[
            P("tcp", 554, "rtsp", product="Hikvision rtspd"),
            P("tcp", 80, "http", product="Hikvision httpd", title="Camera Login"),
        ]),
        host("192.168.1.41", "B8:27:EB:00:00:41", "Raspberry Pi Foundation", "smarthub.lan", ports=[
            P("tcp", 1883, "mqtt", product="Mosquitto", version="1.6.15"),
            P("tcp", 8123, "http", title="Home Assistant"),
        ]),
        host("192.168.1.50", "8C:79:F5:00:00:50", "Samsung Electronics", "tv.lan", ports=[
            P("tcp", 8008, "http", title="Chromecast"),       # trap: TV ports not in catalog
            P("tcp", 8009, "ajp13"),
        ]),
    ],
    "V3_small_office.xml": [
        host("192.168.1.10", "3C:2A:F4:00:00:10", "Brother Industries", "printer.lan", ports=[
            P("tcp", 9100, "jetdirect"),
            P("tcp", 631, "ipp", product="CUPS", version="2.4"),   # trap: IPP is not a finding
            P("tcp", 80, "http", product="Debut embedded httpd", title="Brother HL-L2350DW"),
        ]),
        host("192.168.1.20", "00:11:32:00:00:20", "Synology Incorporated", "nas.lan", ports=[
            P("tcp", 22, "ssh", product="OpenSSH", version="8.2p1"),
            P("tcp", 139, "netbios-ssn", product="Samba smbd", version="4.6.2"),
            P("tcp", 445, "microsoft-ds", product="Samba smbd", version="4.6.2"),
            P("tcp", 5001, "http", tunnel="ssl", title="Synology DiskStation"),
        ]),
        host("192.168.1.30", "D4:BE:D9:00:00:30", "Dell", "office-pc", ports=[
            P("tcp", 135, "msrpc", product="Microsoft Windows RPC"),
            P("tcp", 3389, "ms-wbt-server", product="Microsoft Terminal Services"),
        ]),
        host("192.168.1.40", "52:54:00:00:00:40", "QEMU virtual NIC", "srv01", ports=[
            P("tcp", 22, "ssh", product="OpenSSH", version="8.9p1 Ubuntu 3ubuntu0.10"),
            P("tcp", 3306, "mysql", product="MySQL", version="8.0.36"),
        ]),
    ],
    "V4_legacy.xml": [
        host("192.168.1.1", "00:1E:58:00:00:01", "D-Link Corporation", "oldrouter", ports=[
            P("tcp", 23, "telnet", product="BusyBox telnetd"),
            P("tcp", 80, "http", product="mini_httpd", version="1.19", title="Router Setup"),
            P("udp", 161, "snmp", product="net-snmp"),
        ]),
        host("192.168.1.60", "00:0C:29:00:00:60", "VMware", "oldserver", ports=[
            P("tcp", 21, "ftp", product="vsftpd", version="2.3.4"),   # trap: 2 findings
        ]),
        host("192.168.1.99", None, None, None, ports=[
            P("tcp", 5000, "upnp"),        # upnp over TCP is NOT UPNP_EXPOSED
        ]),
    ],
    "V5_nonstandard_ports.xml": [
        host("192.168.1.5", "B8:27:EB:00:00:05", "Raspberry Pi Foundation", "pi-a", ports=[
            P("tcp", 2323, "telnet", product="BusyBox telnetd")]),
        host("192.168.1.6", "B8:27:EB:00:00:06", "Raspberry Pi Foundation", "pi-b", ports=[
            P("tcp", 8081, "http", product="nginx", version="1.25.3", title="Admin Panel")]),
        host("192.168.1.7", "02:42:AC:00:00:07", "Docker", "redis-box", ports=[
            P("tcp", 6380, "redis", product="Redis key-value store", version="7.2.4")]),
        host("192.168.1.8", "02:42:AC:00:00:08", "Docker", "web-tls", ports=[
            P("tcp", 8443, "http", tunnel="ssl", product="nginx", title="Login")]),   # trap: HTTPS
        host("192.168.1.9", "02:42:AC:00:00:09", "Docker", "db-fw", ports=[
            P("tcp", 3306, "mysql", state="filtered")]),                              # trap: filtered
    ],
    "V6a_before.xml": [
        host("192.168.1.1", **ROUTER, ports=[
            P("tcp", 80, "http", title="Router Login"),
            P("udp", 1900, "upnp", product="miniupnpd"),
        ]),
        host("192.168.1.30", "B8:27:EB:00:00:30", "Raspberry Pi Foundation", "pi-old", ports=[
            P("tcp", 23, "telnet", product="Linux telnetd")]),
    ],
    "V6b_after.xml": [
        host("192.168.1.1", **ROUTER, ports=[
            P("tcp", 443, "http", tunnel="ssl", title="Router Login"),
            P("udp", 1900, "upnp", state="closed"),
        ]),
        host("192.168.1.30", "B8:27:EB:00:00:30", "Raspberry Pi Foundation", "pi-old", ports=[]),
    ],
}

EXPECTED_FINDINGS = """file,ip,port,finding_code,severity
V1_home_basic.xml,192.168.1.1,80,HTTP_ADMIN_CLEARTEXT,medium
V2_smart_home.xml,192.168.1.1,80,HTTP_ADMIN_CLEARTEXT,medium
V2_smart_home.xml,192.168.1.1,1900,UPNP_EXPOSED,medium
V2_smart_home.xml,192.168.1.40,80,HTTP_ADMIN_CLEARTEXT,medium
V2_smart_home.xml,192.168.1.40,554,CAMERA_STREAM_EXPOSED,high
V2_smart_home.xml,192.168.1.41,1883,MQTT_EXPOSED,medium
V3_small_office.xml,192.168.1.10,9100,PRINTER_RAW_EXPOSED,low
V3_small_office.xml,192.168.1.20,22,SSH_OPEN,info
V3_small_office.xml,192.168.1.20,445,SMB_EXPOSED,medium
V3_small_office.xml,192.168.1.30,3389,RDP_EXPOSED,high
V3_small_office.xml,192.168.1.40,22,SSH_OPEN,info
V3_small_office.xml,192.168.1.40,3306,DB_EXPOSED,high
V4_legacy.xml,192.168.1.1,23,TELNET_OPEN,high
V4_legacy.xml,192.168.1.1,80,HTTP_ADMIN_CLEARTEXT,medium
V4_legacy.xml,192.168.1.1,161,SNMP_EXPOSED,medium
V4_legacy.xml,192.168.1.60,21,FTP_CLEARTEXT,medium
V4_legacy.xml,192.168.1.60,21,OUTDATED_SERVICE,high
V4_legacy.xml,192.168.1.99,,UNKNOWN_DEVICE,low
V5_nonstandard_ports.xml,192.168.1.5,2323,TELNET_OPEN,high
V5_nonstandard_ports.xml,192.168.1.6,8081,HTTP_ADMIN_CLEARTEXT,medium
V5_nonstandard_ports.xml,192.168.1.7,6380,DB_EXPOSED,high
V6a_before.xml,192.168.1.1,80,HTTP_ADMIN_CLEARTEXT,medium
V6a_before.xml,192.168.1.1,1900,UPNP_EXPOSED,medium
V6a_before.xml,192.168.1.30,23,TELNET_OPEN,high
"""

EXPECTED_SCORES = """file,network_score
V1_home_basic.xml,90
V2_smart_home.xml,40
V3_small_office.xml,45
V4_legacy.xml,25
V5_nonstandard_ports.xml,50
V6a_before.xml,60
V6b_after.xml,100
V7_broken.xml,ERROR
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, hosts in FILES.items():
        (OUT / name).write_text(render(hosts, udp=name != "V5_nonstandard_ports.xml"), encoding="utf-8")
    full = render(FILES["V1_home_basic.xml"])
    (OUT / "V7_broken.xml").write_text(full[: len(full) // 2], encoding="utf-8")  # truncated
    (OUT / "expected_findings.csv").write_text(EXPECTED_FINDINGS, encoding="utf-8")
    (OUT / "expected_scores.csv").write_text(EXPECTED_SCORES, encoding="utf-8")
    print(f"wrote {len(FILES) + 1} scan files + expected answers to {OUT}")


if __name__ == "__main__":
    main()

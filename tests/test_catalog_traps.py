"""More catalog traps for the secret Test Set (brief: "Official finding catalog"), as full nmap XML.

Each case pins the decision we took, so a later change cannot silently add or drop rows.
Rule of thumb from the brief: only state "open" counts, and the decision is made by the service name nmap reports.
"""
import pytest

from netcheck.core.parser import ScanFileError, parse_bytes
from netcheck.core.rules import evaluate, network_score

IP = "192.168.1.10"


def _port(pid, name, proto="tcp", state="open", product="", version="", tunnel="", title=None, redirect=None):
    attrs = f'name="{name}"' + (f' product="{product}"' if product else "") + (f' version="{version}"' if version else "") \
        + (f' tunnel="{tunnel}"' if tunnel else "")
    sc = ""
    if title is not None:
        sc = f'<script id="http-title" output="{title}"><elem key="title">{title}</elem></script>'
    if redirect is not None:
        sc = f'<script id="http-title" output="Did not follow redirect to {redirect}"><elem key="redirect_url">{redirect}</elem></script>'
    return f'<port protocol="{proto}" portid="{pid}"><state state="{state}"/><service {attrs}/>{sc}</port>'


def _scan(ports, vendor="Netgear", mac="AA:BB:CC:00:00:01", hostname=None, status="up"):
    addr = f'<address addr="{IP}" addrtype="ipv4"/>'
    if mac:
        addr += f'<address addr="{mac}" addrtype="mac"' + (f' vendor="{vendor}"' if vendor else "") + "/>"
    hn = f'<hostnames><hostname name="{hostname}"/></hostnames>' if hostname else ""
    xml = (f'<?xml version="1.0"?><!DOCTYPE nmaprun><nmaprun scanner="nmap"><host><status state="{status}"/>{addr}{hn}'
           f'<ports>{"".join(ports)}</ports></host></nmaprun>')
    f = evaluate(parse_bytes(xml.encode()))
    return sorted((x.port, x.code) for x in f), network_score(f)


CASES = [
    # HTTP_ADMIN_CLEARTEXT: service exactly "http", no SSL, title with one of the words
    ("admin title on 8080", [_port(8080, "http", title="Router Login")], [(8080, "HTTP_ADMIN_CLEARTEXT")]),
    ("title words are case-insensitive", [_port(80, "http", title="ADMINISTRATOR")], [(80, "HTTP_ADMIN_CLEARTEXT")]),
    ("http-proxy is not http", [_port(8080, "http-proxy", title="Router Login")], []),
    ("https admin is not cleartext", [_port(443, "http", tunnel="ssl", title="Admin")], []),
    ("service named https", [_port(443, "https", title="Admin")], []),
    ("title without a keyword", [_port(80, "http", title="Welcome")], []),
    ("redirect note is not a page title", [_port(80, "http", redirect="https://192.168.1.1/login.html")], []),
    # by service name, not by port number
    ("telnet on a non-standard port", [_port(2323, "telnet")], [(2323, "TELNET_OPEN")]),
    ("ssh answering on port 23", [_port(23, "ssh")], [(23, "SSH_OPEN")]),
    ("rtsp on 8554", [_port(8554, "rtsp")], [(8554, "CAMERA_STREAM_EXPOSED")]),
    ("vnc-1 table name is not vnc", [_port(5901, "vnc-1")], []),
    ("mongod table name is not mongodb", [_port(27017, "mongod")], []),
    ("ipp printing is not jetdirect", [_port(631, "ipp")], []),
    ("snmptrap is not snmp", [_port(162, "snmptrap", proto="udp")], []),
    # only state "open"
    ("telnet filtered", [_port(23, "telnet", state="filtered")], []),
    ("telnet closed", [_port(23, "telnet", state="closed")], []),
    ("snmp open|filtered", [_port(161, "snmp", proto="udp", state="open|filtered")], []),
    # UDP-only codes
    ("snmp on tcp", [_port(161, "snmp")], []),
    ("upnp on tcp", [_port(5000, "upnp")], []),
    ("upnp on udp", [_port(1900, "upnp", proto="udp")], [(1900, "UPNP_EXPOSED")]),
    ("same port on tcp and udp gives one row", [_port(161, "snmp", proto="udp"), _port(161, "snmp")], [(161, "SNMP_EXPOSED")]),
    # SMB: one per device, 445 if open else 139
    ("smb 139 + 445", [_port(139, "netbios-ssn"), _port(445, "microsoft-ds")], [(445, "SMB_EXPOSED")]),
    ("smb only 139", [_port(139, "netbios-ssn")], [(139, "SMB_EXPOSED")]),
    # OUTDATED_SERVICE: in addition to the service's own finding
    ("vsftpd 2.3.4", [_port(21, "ftp", product="vsftpd", version="2.3.4")], [(21, "FTP_CLEARTEXT"), (21, "OUTDATED_SERVICE")]),
    ("vsftpd 3.0.3", [_port(21, "ftp", product="vsftpd", version="3.0.3")], [(21, "FTP_CLEARTEXT")]),
    ("OpenSSH 7.2p2", [_port(22, "ssh", product="OpenSSH", version="7.2p2 Ubuntu 4ubuntu2.8")], [(22, "OUTDATED_SERVICE"), (22, "SSH_OPEN")]),
    ("OpenSSH 7.4p1 is not below 7.4", [_port(22, "ssh", product="OpenSSH", version="7.4p1")], [(22, "SSH_OPEN")]),
    ("Dropbear is not on the list", [_port(22, "ssh", product="Dropbear sshd", version="2012.55")], [(22, "SSH_OPEN")]),
    ("Apache 2.2.34", [_port(80, "http", product="Apache httpd", version="2.2.34")], [(80, "OUTDATED_SERVICE")]),
    ("Apache 1.3.42", [_port(80, "http", product="Apache httpd", version="1.3.42")], [(80, "OUTDATED_SERVICE")]),
    ("Apache 2.4.7", [_port(80, "http", product="Apache httpd", version="2.4.7")], []),
    ("IIS 7.5", [_port(80, "http", product="Microsoft IIS httpd", version="7.5")], [(80, "OUTDATED_SERVICE")]),
    ("IIS 8.0", [_port(80, "http", product="Microsoft IIS httpd", version="8.0")], []),
    ("Samba 3.0.20 on 445, 3.X - 4.X on 139",
     [_port(139, "netbios-ssn", product="Samba smbd", version="3.X - 4.X"),
      _port(445, "netbios-ssn", product="Samba smbd", version="3.0.20-Debian")], [(445, "OUTDATED_SERVICE"), (445, "SMB_EXPOSED")]),
    ("Samba 4.6.2", [_port(445, "microsoft-ds", product="Samba smbd", version="4.6.2")], [(445, "SMB_EXPOSED")]),
    ("upper-case service name", [_port(23, "Telnet")], [(23, "TELNET_OPEN")]),
]


@pytest.mark.parametrize("label,ports,expected", CASES, ids=[c[0] for c in CASES])
def test_catalog_edge_case(label, ports, expected):
    assert _scan(ports)[0] == expected


@pytest.mark.parametrize("kw,expected", [
    ({"vendor": None}, [(None, "UNKNOWN_DEVICE")]),                       # MAC without a vendor
    ({"mac": None}, [(None, "UNKNOWN_DEVICE")]),                          # no MAC at all
    ({"vendor": None, "hostname": "tv.lan"}, []),                         # a hostname identifies it
    ({"vendor": None, "ports": []}, []),                                  # needs an open port
    ({"vendor": None, "ports": [_port(8888, "http", state="filtered")]}, []),
    ({"status": "down"}, []),                                             # hosts that are down are skipped
])
def test_unknown_device_and_host_state(kw, expected):
    ports = kw.pop("ports", [_port(8888, "sun-answerbook")])
    assert _scan(ports, **kw)[0] == expected


def test_ipv4_is_used_even_when_ipv6_is_listed_first():
    xml = ('<nmaprun><host><status state="up"/><address addr="fe80::1" addrtype="ipv6"/>'
           '<address addr="192.168.1.20" addrtype="ipv4"/><ports><port protocol="tcp" portid="23"><state state="open"/>'
           '<service name="telnet"/></port></ports></host></nmaprun>')
    assert {f.ip for f in evaluate(parse_bytes(xml.encode()))} == {"192.168.1.20"}


def test_duplicate_hosts_give_one_row():
    host = ('<host><status state="up"/><address addr="192.168.1.11" addrtype="ipv4"/><ports><port protocol="tcp" portid="23">'
            '<state state="open"/><service name="telnet"/></port></ports></host>')
    codes = [f.code for f in evaluate(parse_bytes(f"<nmaprun>{host}{host}</nmaprun>".encode()))]
    assert codes.count("TELNET_OPEN") == 1 and codes.count("UNKNOWN_DEVICE") == 1


@pytest.mark.parametrize("raw", [b'<?xml version="1.0"?><html></html>', b'<nmaprun><host><status state="up"/>',
                                 b"\x00\x01PK\x03\x04", b""])
def test_unreadable_files_are_errors(raw):
    with pytest.raises(ScanFileError):
        parse_bytes(raw)


def test_empty_scan_scores_100():
    assert network_score(evaluate(parse_bytes(b"<nmaprun></nmaprun>"))) == 100

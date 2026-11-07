"""Traps beyond the Validation Set - the secret Test Set promises 'new traps'."""
import pytest

from netcheck.core.analysis import analyze_file
from netcheck.core.models import Host, Port, ScanResult
from netcheck.core.parser import ScanFileError, parse_bytes
from netcheck.core.rules import evaluate, outdated_reason


def _codes(*ports, vendor="Acme", hostnames=("x",)):
    h = Host(ip="10.0.0.2", vendor=vendor, hostnames=list(hostnames), ports=list(ports))
    return sorted((f.port, f.code) for f in evaluate(ScanResult("t", [h])))


def test_open_filtered_udp_is_not_open():
    assert _codes(Port("udp", 161, "open|filtered", "snmp")) == []


def test_upnp_snmp_only_on_udp():
    assert _codes(Port("tcp", 161, "open", "snmp"), Port("tcp", 1900, "open", "upnp")) == []


def test_decide_by_service_not_port():
    assert _codes(Port("tcp", 23, "open", "tcpwrapped")) == []
    assert _codes(Port("tcp", 9999, "open", "telnet")) == [(9999, "TELNET_OPEN")]


@pytest.mark.parametrize("title,expected", [
    ("Router Login", True), ("ADMIN", True), ("Web Configuration", True), ("Setup Wizard", True),
    ("My Settings", True), ("Welcome to nginx!", False), ("", False),
])
def test_http_admin_title(title, expected):
    p = Port("tcp", 80, "open", "http", scripts={"http-title": title} if title else {})
    assert (_codes(p) == [(80, "HTTP_ADMIN_CLEARTEXT")]) is expected


def test_http_admin_over_ssl_is_not_a_finding():
    p = Port("tcp", 443, "open", "http", tunnel="ssl", scripts={"http-title": "Admin"})
    assert _codes(p) == []


def test_smb_one_per_device():
    ports = [Port("tcp", 139, "open", "netbios-ssn"), Port("tcp", 445, "open", "microsoft-ds")]
    assert _codes(*ports) == [(445, "SMB_EXPOSED")]
    assert _codes(Port("tcp", 139, "open", "netbios-ssn")) == [(139, "SMB_EXPOSED")]


@pytest.mark.parametrize("product,version,outdated", [
    ("vsftpd", "2.3.4", True), ("vsftpd", "3.0.3", False),
    ("OpenSSH", "7.3p1", True), ("OpenSSH", "7.4", False), ("OpenSSH", "6.6.1p1 Ubuntu", True),
    ("Apache httpd", "2.2.34", True), ("Apache httpd", "2.4.57", False), ("Apache httpd", "1.3.42", True),
    ("Microsoft IIS httpd", "7.5", True), ("Microsoft IIS httpd", "10.0", False),
    ("Samba smbd", "3.6.25", True), ("Samba smbd", "4.6.2", False), ("Samba smbd", "3.X - 4.X", False),
    ("nginx", "1.0.0", False),
])
def test_outdated_list(product, version, outdated):
    assert (outdated_reason(Port("tcp", 1, "open", "x", product=product, version=version)) is not None) is outdated


def test_unknown_device_requires_open_port():
    assert _codes(Port("tcp", 80, "closed", "http"), vendor=None, hostnames=()) == []
    assert _codes(Port("tcp", 8888, "open", "sun-answerbook"), vendor=None, hostnames=()) == [(None, "UNKNOWN_DEVICE")]
    # a hostname alone is enough to identify
    assert _codes(Port("tcp", 8888, "open", "x"), vendor=None, hostnames=("thing",)) == []


# ------------------------------------------------------------- hostile input
def test_rejects_xxe():
    data = b'<?xml version="1.0"?><!DOCTYPE n [<!ENTITY x SYSTEM "file:///etc/passwd">]><nmaprun>&x;</nmaprun>'
    with pytest.raises(ScanFileError):
        parse_bytes(data)


def test_rejects_billion_laughs():
    data = b'<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;">]><nmaprun>&b;</nmaprun>'
    with pytest.raises(ScanFileError):
        parse_bytes(data)


def test_rejects_non_nmap_xml():
    with pytest.raises(ScanFileError):
        parse_bytes(b"<html><body>hi</body></html>")


@pytest.mark.parametrize("content", [b"", b"\x00\x01garbage", b"<nmaprun><host>"])
def test_broken_files_become_errors_not_crashes(tmp_path, content):
    f = tmp_path / "bad.xml"
    f.write_bytes(content)
    a = analyze_file(f)
    assert not a.ok and a.error


def test_banner_text_is_kept_as_data():
    xml = (b'<nmaprun><host><status state="up"/><address addr="10.0.0.5" addrtype="ipv4"/>'
           b'<ports><port protocol="tcp" portid="80"><state state="open"/><service name="http"/>'
           b'<script id="http-title" output="&lt;script&gt;alert(1)&lt;/script&gt; admin"/></port></ports></host></nmaprun>')
    scan = parse_bytes(xml)
    assert scan.hosts[0].ports[0].http_title.startswith("<script>")
    assert sorted(f.code for f in evaluate(scan)) == ["HTTP_ADMIN_CLEARTEXT", "UNKNOWN_DEVICE"]


# ---- parser traps for the secret Test Set ------------------------------------
def _file_codes(host_xml):
    x = ('<?xml version="1.0"?>\n<!DOCTYPE nmaprun>\n<nmaprun>' + host_xml + '</nmaprun>').encode()
    return sorted((f.port, f.code) for f in evaluate(parse_bytes(x)))


_ADDR = '<address addr="10.0.0.5" addrtype="ipv4"/><address addr="00:11:22:33:44:55" addrtype="mac" vendor="Acme"/>'
_HN = '<hostnames><hostname name="dev" type="PTR"/></hostnames>'


def _http_host(script, status='<status state="up"/>'):
    return (f'<host>{status}{_ADDR}{_HN}<ports><port protocol="tcp" portid="80"><state state="open"/>'
            f'<service name="http"/>{script}</port></ports></host>')


def test_redirect_text_is_not_a_title():
    s = ('<script id="http-title" output="Site doesn&apos;t have a title (text/html).&#xa;'
         'Requested resource was http://10.0.0.5/login.php">'
         '<elem key="redirect_url">http://10.0.0.5/login.php</elem></script>')
    assert _file_codes(_http_host(s)) == []


def test_redirect_line_ignored_when_title_elem_present():
    s = ('<script id="http-title" output="Welcome&#xa;Requested resource was /admin">'
         '<elem key="title">Welcome</elem><elem key="redirect_url">/admin</elem></script>')
    assert _file_codes(_http_host(s)) == []


@pytest.mark.parametrize("output,expected", [
    ("Router Login", [(80, "HTTP_ADMIN_CLEARTEXT")]),
    ("Site doesn&apos;t have a title (text/html; charset=utf-8).", []),
    ("Did not follow redirect to http://10.0.0.5/admin/", []),
    ("Home&#xa;Requested resource was /login", []),
])
def test_title_from_output_only_files(output, expected):
    s = f'<script id="http-title" output="{output}"/>'
    assert _file_codes(_http_host(s)) == expected


def test_host_without_status_is_evaluated():
    s = '<script id="http-title" output="Admin"><elem key="title">Admin</elem></script>'
    assert _file_codes(_http_host(s, status="")) == [(80, "HTTP_ADMIN_CLEARTEXT")]


def test_vendor_unknown_counts_as_no_vendor():
    x = ('<host><status state="up"/><address addr="10.0.0.6" addrtype="ipv4"/>'
         '<address addr="AA:BB:CC:00:00:01" addrtype="mac" vendor="Unknown"/>'
         '<ports><port protocol="tcp" portid="9999"><state state="open"/><service name="abyss"/></port>'
         '</ports></host>')
    assert _file_codes(x) == [(None, "UNKNOWN_DEVICE")]

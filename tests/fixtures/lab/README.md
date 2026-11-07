# Hotspot lab scans (our own, NFR-10)

iPhone hotspot `172.20.10.0/28`, scanned from a MacBook with:

    sudo nmap -sS -sU -sV --version-light --script http-title \
      -p T:1-1024,1433,1883,2121,2222,2323,3306,3389,5432,5900-5901,6379,8000-8081,8443,8554,9100,27017,U:53,123,161,1900,5353 \
      --max-rate 100 -oX <file> 172.20.10.0/28

| IP | Device |
|---|---|
| 172.20.10.1  | iPhone (hotspot gateway, private MAC) |
| 172.20.10.10 | MacBook - the scanner itself |
| 172.20.10.11 | Windows laptop - the target (`lab/fake_services.py` + Windows file sharing) |

| File | Target state | Score |
|---|---|---|
| `lab_01_before.xml`  | `fake_services.py` (all fake services) + file sharing on | 0 |
| `lab_02_between.xml` | `fake_services.py --fixed` (telnet, FTP, admin page off), file sharing still on | 30 |
| `lab_03_final.xml`   | fake services stopped, file sharing off | 80 |

Notes:
- `expected_*.csv` were checked by hand against what we switched on/off on the target.
- In `lab_01_before.xml` nmap named the fake admin page on 8080 `tcpwrapped` (the old fake
  server hung up before nmap's banner wait ended), so no HTTP_ADMIN_CLEARTEXT is expected there.
  Fixed in `lab/fake_services.py` afterwards.
- In `lab_02_between.xml` port 445 did not answer but 139 did, so SMB_EXPOSED is on 139.
- 902/912 (VMware Authentication Daemon) are not in the official catalog: no finding.

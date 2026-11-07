# Inter-Service Data Contracts (R Systems Hackathon 2026)

This document defines the standard JSON data formats for communication between our modules. By adhering to these contracts, team members can work in parallel. If you are working on the UI or LLM service, you can use these JSON examples as mock data right now.

---

## 1. Raw Parsed Data (Core CLI ➔ Rule Engine)
Produced by parsing the `nmap` XML file. This contains no security evaluations yet, just the raw facts of the network. Note the mandatory **masked MAC addresses** (NFR-02).

```json
{
  "scan_id": "V1_home_basic",
  "timestamp": "2026-11-07T13:15:00Z",
  "network": {
    "subnet": "192.168.1.0/24",
    "gateway": "192.168.1.1"
  },
  "devices": [
    {
      "ip": "192.168.1.1",
      "mac_masked": "XX:XX:XX:XX:1A:2B",
      "vendor": "TP-Link Technologies",
      "hostname": "home-router.local",
      "device_type_guess": "router",
      "open_ports": [
        {
          "port": 80,
          "protocol": "tcp",
          "service": "http",
          "version": "lighttpd 1.4.39",
          "evidence_banner": "title: Admin Login"
        }
      ]
    }
  ]
}
```

---

## 2. Evaluated Scan Data (Rule Engine ➔ UI / Database)
This is the deterministic output after the catalog rules and standard score formula have been applied. **No LLM is used here.** This data maps directly to the mandatory `findings.csv` and `scores.csv` exports.

```json
{
  "scan_id": "V1_home_basic",
  "network_score": 90,
  "devices": [
    {
      "ip": "192.168.1.1",
      "mac_masked": "XX:XX:XX:XX:1A:2B",
      "vendor": "TP-Link Technologies",
      "hostname": "home-router.local",
      "device_type_guess": "router"
    }
  ],
  "findings": [
    {
      "ip": "192.168.1.1",
      "port": 80,
      "finding_code": "HTTP_ADMIN_CLEARTEXT",
      "severity": "medium",
      "points": 10,
      "evidence": "Service http without SSL, and page title contains login"
    }
  ]
}
```
*Note: The `network_score` is calculated as: `max(0, 100 - sum(points of all findings))`.*

---

## 3. LLM Enrichment Payload (UI Backend ➔ LLM Service)
When the UI needs explanations and fixes for a finding, it calls the LLM service. The LLM service must return data in both English and Romanian, keeping technical jargon to a minimum.

**Request:**
```json
{
  "finding_code": "HTTP_ADMIN_CLEARTEXT",
  "port": 80,
  "device_type_guess": "router",
  "evidence": "Service http without SSL, and page title contains login"
}
```

**Response (Must include RO and EN):**
```json
{
  "finding_code": "HTTP_ADMIN_CLEARTEXT",
  "explanation_en": "Your router's login page is exposed on an unencrypted connection. This means anyone on your network could intercept your password.",
  "explanation_ro": "Pagina de autentificare a routerului este expusă pe o conexiune necriptată. Acest lucru înseamnă că oricine din rețea v-ar putea intercepta parola.",
  "fixes_en": [
    "Log in to your router's interface.",
    "Navigate to the Security or Administration settings.",
    "Disable remote HTTP access and enable HTTPS."
  ],
  "fixes_ro": [
    "Autentificați-vă în interfața routerului.",
    "Navigați la setările de Securitate sau Administrare.",
    "Dezactivați accesul HTTP și activați HTTPS."
  ]
}
```

---

## 4. History & Deltas (Database ➔ UI Dashboard)
To satisfy FR-10 and FR-13 (Alert on change), the backend must compare the current scan to the previous scan and send a "Delta" payload to the UI.

```json
{
  "current_scan_id": "V6b_after",
  "previous_scan_id": "V6a_before",
  "score_trend": {
    "previous_score": 60,
    "current_score": 100,
    "improved": true
  },
  "deltas": {
    "new_devices": [
      { "ip": "192.168.1.50", "mac_masked": "XX:XX:XX:XX:99:99" }
    ],
    "removed_devices": [],
    "new_findings": [],
    "resolved_findings": [
      {
        "ip": "192.168.1.1",
        "port": 80,
        "finding_code": "HTTP_ADMIN_CLEARTEXT"
      },
      {
        "ip": "192.168.1.30",
        "port": 23,
        "finding_code": "TELNET_OPEN"
      }
    ]
  }
}
```
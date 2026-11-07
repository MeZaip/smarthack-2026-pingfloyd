# 3D device models

One `.glb` model per **device type**, not per brand. Every device a scan finds gets exactly one of the 10 types
below from `guess_type()` in `netcheck/core/device.py` (anything it cannot recognise becomes `unknown`), so these
10 files cover every possible device. The UI loads `ui/assets/models/<type>.glb`; if a file is missing it falls back
to `unknown.glb`, and if that is missing too, to the SVG icon.

## The final list

| Type (file) | Shown as (RO / EN) | Devices from the brief that land here | What to model |
|---|---|---|---|
| `router.glb` | Router / Router | routers "with default settings", old router (V4), the team's **phone hotspot** (the gateway of the lab) | Wi-Fi router with 2-3 antennas and front LEDs |
| `camera.glb` | Cameră video / Camera | IP camera (V2), cameras in the challenge statement | security camera (bullet on a wall mount, or dome) |
| `tv.glb` | Televizor / TV | smart TV (V2); also Chromecast / Google speakers (ports 8008/8009) | thin smart TV on a stand |
| `iot.glb` | Dispozitiv inteligent / Smart device | smart hub (V2), Raspberry Pi, ESP32, smart bulbs / plugs / sensors, MQTT broker | smart bulb (the clearest for non-technical users) |
| `computer.glb` | Calculator / Computer | "forgotten laptops", laptop (V1), Windows PC (V3, RDP / SMB), the team laptop | open laptop |
| `printer.glb` | Imprimantă / Printer | printer (V3, port 9100) | office printer with a paper tray |
| `server.glb` | Server / Server | Linux server (V3), old server (V4), anything with a database or SSH only, Docker services on a laptop | small desktop server / mini-PC (not a data-centre rack) |
| `nas.glb` | Stocare în rețea (NAS) / Network storage (NAS) | NAS (V3, Synology / QNAP / WD) | box with 2-4 drive bays in front |
| `phone.glb` | Telefon / tabletă / Phone / tablet | phone (V1), old phone with an FTP app (lab setup B) | smartphone |
| `unknown.glb` | Dispozitiv necunoscut / Unknown device | unknown device (V4: no vendor, no name, open port) | simple box with a question mark |

Priority: the first six appear in the test scans and the demo; `nas` and `phone` can appear in your own lab scans;
`unknown` is required as the fallback.

## Rules for every model (so the UI can use them interactively)

- **Format**: `.glb` (binary glTF 2.0), loaded with Three.js.
- **Size**: under 1-2 MB each, low poly; textures at most 1024 px.
- **Style**: all ten in the same style (same palette, same level of detail).
- **Scale and pivot**: about 1 unit tall, origin at the bottom centre, front facing +Z, so they stand on the
  threat-path platforms without adjustment.
- **Named parts** (lowercase mesh names), so the UI can light them by risk (red / orange / green):
  - every model: `body` and `status` (an LED or glow area that changes colour with the risk);
  - type-specific, if present: `screen` (tv, computer, phone), `lens` (camera), `antenna` (router),
    `tray` (printer), `bays` (nas).
- **Licence**: CC0 preferred (Poly Pizza, Kenney, Quaternius). For CC-BY models (e.g. Sketchfab) add the author and
  link below.

## Credits

| File | Author | Source | Licence |
|---|---|---|---|
| | | | |

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
| `iot.glb` | Dispozitiv inteligent / Smart device | smart hub (V2), Raspberry Pi, ESP32, smart bulbs / plugs / sensors, MQTT broker | smart speaker (Google Nest / Amazon Echo style) with a glowing LED ring on top |
| `computer.glb` | Calculator / Computer | "forgotten laptops", laptop (V1), Windows PC (V3, RDP / SMB), the team laptop | open laptop |
| `printer.glb` | Imprimantă / Printer | printer (V3, port 9100) | office printer with a paper tray |
| `server.glb` | Server / Server | Linux server (V3), old server (V4), anything with a database or SSH only, Docker services on a laptop | small desktop server / mini-PC (not a data-centre rack) |
| `nas.glb` | Stocare în rețea (NAS) / Network storage (NAS) | NAS (V3, Synology / QNAP / WD) | box with 2-4 drive bays in front |
| `phone.glb` | Telefon / tabletă / Phone / tablet | phone (V1), old phone with an FTP app (lab setup B) | smartphone |
| `unknown.glb` | Dispozitiv necunoscut / Unknown device | unknown device (V4: no vendor, no name, open port) | just a 3D question mark (chrome), the dot is the status light |

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

## How the current models are made

All ten are generated in code by `tools/make_models.py` (needs numpy, scipy, trimesh):
`python tools/make_models.py` rewrites the files, `python tools/check_models.py` checks them (also run by
`tests/test_models.py`, which fails if a device type in `netcheck/core/device.py` has no model).
Palette: body `#1e293b`/`#334155` (metallic 0.3, roughness 0.4) with chrome `#94a3b8` accents (metallic 0.8),
screens `#090d16` glossy with a faint cyan tint, `status` emissive `#00ff66`.

`tools/make_models.py` also writes `models-bundle.js` (`window.SAFEHOUSE_MODELS_BASE64`, every `.glb` as a base64
data URI). The page uses that, not the `.glb` files, because browsers block `fetch()` of local files when the page is
opened from `file://`. `ui/device3d.js` reads the bundle with a small built-in `.glb` reader (no `GLTFLoader`, no ES
module) and one shared WebGL renderer draws every device slot (`.dev3d`) into a plain 2D canvas: cards, tiles, the
device sheet and the threat-path pedestals. The `status` part and a rim light take the risk colour (red high, amber
medium, blue low, green safe). The SVG icon inside a slot is only shown when WebGL is not available.

A mesh with two materials is a group with two children, e.g. `body` -> `body_1`, `body_2`; find parts with
`getObjectByName("status")` and recolour every mesh under it.

To replace a generated model with a hand-made one, keep the file name and the part names, then run the check.

## Variants built in code (`procedural/`)

Some devices get a more recognisable model than the one of their type, chosen in the UI from the device name and
maker (`modelOf()` in `ui/app.js`). They are Three.js code, not `.glb` files, so they also work from `file://`:

| Model key | Shown for | Built from |
|---|---|---|
| `computer-macbook` | a computer made by Apple, or named `MacBook` / `MBP` / `Mac` | photo of a MacBook Air (3/4 front) |
| `computer-imac` | a computer named `iMac` | photo of an iMac (front and back) |
| `phone-iphone` | a phone made by Apple, or named `iPhone` / `iPad` | photo of an iPhone (back) |
| `phone-android` | every other phone (the standard phone model) | no photo: a generic Android back with a full-width camera bar |
| `iot-raspberrypi` | a smart device made by Raspberry Pi | photo of a Raspberry Pi Model B+ |

- **Files**: `procedural/kit.js` (palette, materials, rounded shapes) and one `procedural/<key>.js` per model, which
  registers `window.SAFEHOUSE_MODEL_BUILDERS["<key>"] = (THREE) => Group`. `index.html` loads them after
  `models-bundle.js` and before `device3d.js`.
- **Lookup** (`device3d.js`): a slot's `data-model` (e.g. `phone-iphone`) uses the builder of that key; without one it
  falls back to the `.glb` of the base type (`phone.glb`), then to `unknown.glb`.
- **Same rules as the `.glb` models**: 1 unit tall, standing on y = 0, centred, named `body` and `status` (+ `screen`,
  `lens`, `keys`, `ports`, `pins`...), the same palette, no textures, no logos. The phones show their back (the
  cameras are what makes them recognisable); on the phones the flash is the `status` light.
- **Check**: `node tools/check_builders.mjs` (also run by `tests/test_model_builders.py`).
- **Look at them**: open `ui/assets/models/lab.html` (every model, large and in the 4 risk colours; drag to turn).
  `lab.html?only=phone-iphone&angle=0.55&size=640` shows one model at a fixed angle, for screenshots.
- The reference photos were only looked at while modelling; none of them is part of this repository.
- The device name also helps the type guess (`guess_type()` in `netcheck/core/device.py`): `MacBook` / `iMac` /
  `Mac-mini` mean a computer and `iPhone` / `iPad` / `android` / `Galaxy` / `Pixel` a phone, even when the maker alone
  would say otherwise (Apple -> phone, Samsung -> TV). Open ports still come first.

## Credits

| File | Author | Source | Licence |
|---|---|---|---|
| all ten `.glb` | SafeHouse team | generated by `tools/make_models.py` | same as this repository |
| `procedural/*.js` | SafeHouse team | written in code, shapes after reference photos (not included) | same as this repository |

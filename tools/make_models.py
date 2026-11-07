"""Build the 10 SafeHouse device models (ui/assets/models/<type>.glb) from code.

    python tools/make_models.py [out_dir]        # needs numpy, scipy, trimesh

Rules (ui/assets/models/README.md): glTF 2.0 binary, Y up, front facing +Z, height 1 unit, origin at the bottom
centre, named meshes the UI can recolour (`body`, `status` on every model + `screen`, `lens`, `antenna`, `tray`,
`bays` where they exist), PBR materials in the SafeHouse dark palette, < 500 KB each.
Geometry comes from trimesh primitives (rounded boxes are convex hulls of corner spheres, so edges are bevelled);
the .glb file is written by hand so mesh names, node names and multi-material meshes are exact.
"""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
import trimesh
from trimesh import creation, transformations as tf

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "ui" / "assets" / "models"


# ------------------------------------------------------------------ materials (sRGB hex -> linear factors)
def lin(hex_):
    c = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


MATERIALS = {
    "slate":   {"pbrMetallicRoughness": {"baseColorFactor": lin("#1e293b") + [1], "metallicFactor": 0.3, "roughnessFactor": 0.4}},
    "slate2":  {"pbrMetallicRoughness": {"baseColorFactor": lin("#334155") + [1], "metallicFactor": 0.3, "roughnessFactor": 0.4}},
    "deep":    {"pbrMetallicRoughness": {"baseColorFactor": lin("#0f172a") + [1], "metallicFactor": 0.3, "roughnessFactor": 0.45}},
    "chrome":  {"pbrMetallicRoughness": {"baseColorFactor": lin("#94a3b8") + [1], "metallicFactor": 0.8, "roughnessFactor": 0.25}},
    "screen":  {"pbrMetallicRoughness": {"baseColorFactor": lin("#090d16") + [1], "metallicFactor": 0.1, "roughnessFactor": 0.1},
                "emissiveFactor": [0.0, 0.010, 0.018]},                     # faint cyan tint
    "lens":    {"pbrMetallicRoughness": {"baseColorFactor": lin("#05070a") + [1], "metallicFactor": 0.5, "roughnessFactor": 0.05}},
    "status":  {"pbrMetallicRoughness": {"baseColorFactor": lin("#00ff66") + [1], "metallicFactor": 0.0, "roughnessFactor": 0.3},
                "emissiveFactor": lin("#00ff66")},
}


# ------------------------------------------------------------------ geometry helpers (Y up, +Z = front)
def _shade(m):
    m = m.smooth_shaded if hasattr(m, "smooth_shaded") else m
    return m


def rbox(w, h, d, r, at=(0, 0, 0), sub=1):
    """Box with bevelled (rounded) edges: convex hull of 8 corner spheres."""
    r = min(r, w / 2 - 1e-3, h / 2 - 1e-3, d / 2 - 1e-3)
    s = creation.icosphere(subdivisions=sub, radius=r)
    pts = [s.vertices + [sx * (w / 2 - r), sy * (h / 2 - r), sz * (d / 2 - r)]
           for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    m = trimesh.convex.convex_hull(np.vstack(pts))
    m.apply_translation(at)
    return m


def box(w, h, d, at=(0, 0, 0)):
    m = creation.box(extents=(w, h, d))
    m.apply_translation(at)
    return m


def cyl(r, p0, p1, sections=28):
    return creation.cylinder(radius=r, segment=np.array([p0, p1], float), sections=sections)


def sphere(r, at, sub=2):
    m = creation.icosphere(subdivisions=sub, radius=r)
    m.apply_translation(at)
    return m


def tube(points, r, sections=18):
    """A bent rod through the given points (cylinders + spheres at the joints)."""
    parts = [cyl(r, a, b, sections) for a, b in zip(points[:-1], points[1:])]
    parts += [sphere(r, p, 1) for p in points]
    return trimesh.util.concatenate(parts)


def rotate(m, deg, axis, point=(0, 0, 0)):
    m = m.copy()
    m.apply_transform(tf.rotation_matrix(math.radians(deg), axis, point))
    return m


def cat(*ms):
    return trimesh.util.concatenate([m for m in ms if m is not None])


# ------------------------------------------------------------------ the ten models
# each returns {mesh_name: [(trimesh, material), ...]}
def router():
    shell = rbox(1.6, 0.28, 1.0, 0.09, (0, 0.18, 0))
    feet = cat(*[cyl(0.06, (x, 0, z), (x, 0.04, z)) for x in (-0.65, 0.65) for z in (-0.38, 0.38)])
    trim = box(1.42, 0.022, 0.02, (0, 0.08, 0.505))
    hinges = cat(*[sphere(0.055, (x, 0.33, -0.36), 1) for x in (-0.55, 0, 0.55)])
    antennas = cat(*[rotate(rbox(0.07, 0.78, 0.07, 0.03, (x, 0.33 + 0.39, -0.36)), ang, (0, 0, 1), (x, 0.33, -0.36))
                     for x, ang in ((-0.55, 14), (0.0, 0), (0.55, -14))])
    leds = cat(*[rbox(0.075, 0.03, 0.02, 0.008, (x, 0.2, 0.505)) for x in np.linspace(-0.42, 0.42, 6)])
    return {"body": [(shell, "slate"), (cat(feet, trim, hinges), "chrome")], "antenna": [(antennas, "slate2")], "status": [(leds, "status")]}


def camera():
    base = cyl(0.3, (0, 0, 0), (0, 0.05, 0), 40)
    pole = cyl(0.05, (0, 0.05, 0), (0, 0.6, 0))
    joint = sphere(0.085, (0, 0.62, 0))
    housing = rotate(cat(cyl(0.22, (0, 0.78, -0.42), (0, 0.78, 0.34), 40), sphere(0.22, (0, 0.78, -0.42), 2)), -8, (1, 0, 0), (0, 0.78, 0))
    visor = rotate(rbox(0.56, 0.035, 0.86, 0.015, (0, 1.02, -0.02)), -8, (1, 0, 0), (0, 0.78, 0))
    arm = cyl(0.045, (0, 0.62, 0), (0, 0.76, -0.12))
    lens = rotate(cyl(0.14, (0, 0.78, 0.34), (0, 0.78, 0.39), 40), -8, (1, 0, 0), (0, 0.78, 0))
    ring = creation.annulus(r_min=0.16, r_max=0.195, height=0.02, sections=40)   # already faces +Z
    ring.apply_translation((0, 0.78, 0.36))
    ring = rotate(ring, -8, (1, 0, 0), (0, 0.78, 0))
    return {"body": [(cat(housing, visor), "slate"), (cat(base, pole, joint, arm), "chrome")],
            "lens": [(lens, "lens")], "status": [(ring, "status")]}


def tv():
    frame = rbox(1.6, 0.92, 0.05, 0.02, (0, 0.66, 0))
    back = rbox(1.4, 0.72, 0.06, 0.03, (0, 0.66, -0.045))
    neck = rbox(0.12, 0.2, 0.04, 0.015, (0, 0.2, -0.03))
    pts = [(0.52 * math.cos(t), 0.2 * math.sin(t), -0.03) for t in np.linspace(0, math.pi, 17)]
    arc = tube(pts, 0.022)                                            # curved arch stand
    screen = box(1.54, 0.86, 0.006, (0, 0.66, 0.027))
    led = rbox(0.06, 0.012, 0.012, 0.004, (0, 0.215, 0.026))
    return {"body": [(cat(frame, neck, arc), "chrome"), (back, "slate")], "screen": [(screen, "screen")], "status": [(led, "status")]}


def iot():
    ridges = cat(*[cyl(0.145 if i % 2 else 0.155, (0, 0.03 + i * 0.035, 0), (0, 0.065 + i * 0.035, 0), 32) for i in range(5)])
    tip = cyl(0.07, (0, 0, 0), (0, 0.03, 0), 24)
    # revolve() spins the profile around Z; turn it so the bulb axis is Y (up)
    collar = rotate(creation.revolve(np.array([[0.0, 0.2], [0.17, 0.2], [0.2, 0.26], [0.24, 0.36], [0.0, 0.36]]), sections=48), -90, (1, 0, 0))
    dome = sphere(0.37, (0, 0.66, 0), 3)
    dome.vertices[:, 1] = np.maximum(dome.vertices[:, 1], 0.36)      # sits on the collar
    return {"body": [(collar, "slate"), (cat(ridges, tip), "chrome")], "status": [(dome, "status")]}


def computer():
    base = rbox(1.4, 0.06, 0.95, 0.02, (0, 0.03, 0))
    deck = box(1.2, 0.006, 0.5, (0, 0.062, -0.12))
    pad = rbox(0.42, 0.006, 0.26, 0.01, (0, 0.062, 0.29))
    hinge = (0, 0.06, -0.46)
    lid = rotate(rbox(1.4, 0.9, 0.04, 0.02, (0, 0.06 + 0.45, -0.46)), -10, (1, 0, 0), hinge)
    screen = rotate(box(1.3, 0.78, 0.006, (0, 0.06 + 0.46, -0.438)), -10, (1, 0, 0), hinge)
    led = rbox(0.05, 0.014, 0.012, 0.004, (0.58, 0.035, 0.478))
    return {"body": [(cat(base, lid), "slate"), (deck, "deep"), (pad, "chrome")], "screen": [(screen, "screen")], "status": [(led, "status")]}


def printer():
    shell = rbox(1.3, 0.55, 0.95, 0.07, (0, 0.3, 0))
    feet = cat(*[cyl(0.05, (x, 0, z), (x, 0.03, z)) for x in (-0.55, 0.55) for z in (-0.38, 0.38)])
    panel = rbox(0.42, 0.04, 0.16, 0.015, (0.38, 0.59, 0.36))
    slot = box(0.9, 0.025, 0.02, (0, 0.47, 0.476))
    top_tray = rotate(rbox(0.9, 0.025, 0.5, 0.01, (0, 0.6 + 0.0, -0.32)), 22, (1, 0, 0), (0, 0.58, -0.08))
    drawer = rbox(1.1, 0.12, 0.03, 0.012, (0, 0.14, 0.476))
    led = sphere(0.022, (0.53, 0.61, 0.38), 2)
    return {"body": [(shell, "slate"), (cat(feet, panel, slot), "chrome")], "tray": [(cat(top_tray, drawer), "slate2")], "status": [(led, "status")]}


def server():
    shell = rbox(0.45, 0.98, 0.9, 0.05, (0, 0.5, 0))
    feet = cat(*[box(0.42, 0.02, 0.06, (0, 0.01, z)) for z in (-0.38, 0.38)])
    vents = cat(*[box(0.3, 0.018, 0.015, (0.03, y, 0.452)) for y in np.linspace(0.18, 0.86, 14)])
    bar = rbox(0.03, 0.62, 0.014, 0.006, (-0.17, 0.52, 0.452))
    return {"body": [(shell, "slate"), (cat(feet, vents), "chrome")], "status": [(bar, "status")]}


def nas():
    shell = rbox(0.82, 0.8, 0.8, 0.06, (0, 0.42, 0))
    feet = cat(*[cyl(0.04, (x, 0, z), (x, 0.03, z)) for x in (-0.32, 0.32) for z in (-0.3, 0.3)])
    xs = np.linspace(-0.27, 0.27, 4)
    bays = cat(*[rbox(0.15, 0.58, 0.04, 0.012, (x, 0.38, 0.41)) for x in xs])
    handles = cat(*[box(0.08, 0.012, 0.012, (x, 0.18, 0.435)) for x in xs])
    leds = cat(*[sphere(0.016, (x, 0.62, 0.433), 1) for x in xs], sphere(0.02, (0.3, 0.76, 0.402), 1))
    return {"body": [(shell, "slate"), (cat(feet, handles), "chrome")], "bays": [(bays, "deep")], "status": [(leds, "status")]}


def phone():
    tilt = (1, 0, 0)
    body = rotate(rbox(0.5, 1.0, 0.055, 0.06, (0, 0.5 + 0.02, 0)), -12, tilt, (0, 0.02, 0))
    stand = cat(rbox(0.34, 0.03, 0.34, 0.012, (0, 0.015, -0.05)),
                rotate(rbox(0.3, 0.32, 0.02, 0.01, (0, 0.03 + 0.16, -0.14)), 22, tilt, (0, 0.03, -0.14)))
    screen = rotate(box(0.46, 0.94, 0.004, (0, 0.5 + 0.02, 0.0295)), -12, tilt, (0, 0.02, 0))
    led = rotate(sphere(0.012, (0, 0.975, 0.031), 1), -12, tilt, (0, 0.02, 0))
    return {"body": [(body, "slate"), (stand, "chrome")], "screen": [(screen, "screen")], "status": [(led, "status")]}


def unknown():
    mono = rbox(0.6, 0.85, 0.6, 0.06, (0, 0.425, 0))
    plinth = rbox(0.66, 0.04, 0.66, 0.015, (0, 0.02, 0))
    z = 0.315
    cx, cy, rr = 0.0, 0.58, 0.11
    arc = [(cx + rr * math.cos(t), cy + rr * math.sin(t), z) for t in np.linspace(math.radians(165), math.radians(-60), 14)]
    end = arc[-1]
    stem = [end, (0.0, 0.46, z), (0.0, 0.4, z)]
    mark = cat(tube(arc + stem[1:], 0.03), sphere(0.038, (0.0, 0.29, z), 2))
    return {"body": [(mono, "slate"), (plinth, "chrome")], "status": [(mark, "status")]}


MODELS = {"router": router, "camera": camera, "tv": tv, "iot": iot, "computer": computer, "printer": printer,
          "server": server, "nas": nas, "phone": phone, "unknown": unknown}


# ------------------------------------------------------------------ normalise + write .glb
def normalise(meshes):
    allv = np.vstack([m.vertices for parts in meshes.values() for m, _ in parts])
    lo, hi = allv.min(0), allv.max(0)
    s = 1.0 / (hi[1] - lo[1])                                         # height = 1 unit
    shift = np.array([-(lo[0] + hi[0]) / 2, -lo[1], -(lo[2] + hi[2]) / 2])
    for parts in meshes.values():
        for m, _ in parts:
            m.vertices = (m.vertices + shift) * s
    return meshes


def write_glb(name, meshes, path):
    mats = sorted({mat for parts in meshes.values() for _, mat in parts})
    gl = {"asset": {"version": "2.0", "generator": "SafeHouse tools/make_models.py"},
          "scene": 0, "scenes": [{"name": name, "nodes": [0]}],
          "nodes": [{"name": name, "children": []}], "meshes": [], "materials": [],
          "accessors": [], "bufferViews": [], "buffers": []}
    for mname in mats:
        gl["materials"].append({"name": f"{name}_{mname}", **json.loads(json.dumps(MATERIALS[mname]))})
    blob = bytearray()

    def view(data: bytes, target):
        while len(blob) % 4:
            blob.append(0)
        off = len(blob)
        blob.extend(data)
        gl["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(data), "target": target})
        return len(gl["bufferViews"]) - 1

    for mesh_name, parts in meshes.items():
        prims = []
        for m, mat in parts:
            m = _shade(m)
            v = np.asarray(m.vertices, np.float32)
            n = np.asarray(m.vertex_normals, np.float32)
            f = np.asarray(m.faces)
            idx = f.astype(np.uint16 if v.shape[0] < 65535 else np.uint32).ravel()
            pv = view(v.tobytes(), 34962)
            nv = view(n.tobytes(), 34962)
            iv = view(idx.tobytes(), 34963)
            acc = gl["accessors"]
            acc.append({"bufferView": pv, "componentType": 5126, "count": int(v.shape[0]), "type": "VEC3",
                        "min": v.min(0).tolist(), "max": v.max(0).tolist()})
            acc.append({"bufferView": nv, "componentType": 5126, "count": int(n.shape[0]), "type": "VEC3"})
            acc.append({"bufferView": iv, "componentType": 5123 if idx.dtype == np.uint16 else 5125, "count": int(idx.size), "type": "SCALAR"})
            prims.append({"attributes": {"POSITION": len(acc) - 3, "NORMAL": len(acc) - 2}, "indices": len(acc) - 1,
                          "material": mats.index(mat)})
        gl["meshes"].append({"name": mesh_name, "primitives": prims})
        gl["nodes"].append({"name": mesh_name, "mesh": len(gl["meshes"]) - 1})
        gl["nodes"][0]["children"].append(len(gl["nodes"]) - 1)
    while len(blob) % 4:
        blob.append(0)
    gl["buffers"].append({"byteLength": len(blob)})
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob))
    out += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(blob), 0x004E4942) + bytes(blob)
    path.write_bytes(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, build in MODELS.items():
        write_glb(name, normalise(build()), OUT / f"{name}.glb")
        print(f"wrote {name}.glb")


if __name__ == "__main__":
    main()

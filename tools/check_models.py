"""Check ui/assets/models/*.glb against the rules in ui/assets/models/README.md (stdlib only)."""
import json, struct, sys
from pathlib import Path

DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "ui" / "assets" / "models"
REQUIRED = {"router": {"body", "antenna", "status"}, "camera": {"body", "lens", "status"}, "tv": {"body", "screen", "status"},
            "iot": {"body", "status"}, "computer": {"body", "screen", "status"}, "printer": {"body", "tray", "status"},
            "server": {"body", "status"}, "nas": {"body", "bays", "status"}, "phone": {"body", "screen", "status"},
            "unknown": {"body", "status"}}


def read(path):
    data = path.read_bytes()
    magic, ver, length = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67 and ver == 2 and length == len(data), "not a valid glTF 2.0 binary"
    jlen, jtype = struct.unpack_from("<II", data, 12)
    assert jtype == 0x4E4F534A
    return json.loads(data[20:20 + jlen]), len(data)


bad = 0
for name, need in REQUIRED.items():
    p = DIR / f"{name}.glb"
    try:
        gl, size = read(p)
        meshes = {m["name"] for m in gl["meshes"]}
        nodes = {n["name"] for n in gl["nodes"] if "mesh" in n}
        lo = [min(gl["accessors"][pr["attributes"]["POSITION"]]["min"][i] for m in gl["meshes"] for pr in m["primitives"]) for i in range(3)]
        hi = [max(gl["accessors"][pr["attributes"]["POSITION"]]["max"][i] for m in gl["meshes"] for pr in m["primitives"]) for i in range(3)]
        st = next(m for m in gl["meshes"] if m["name"] == "status")
        emissive = all(any(v > 0.1 for v in gl["materials"][pr["material"]].get("emissiveFactor", [0, 0, 0])) for pr in st["primitives"])
        problems = []
        if size >= 500_000: problems.append(f"size {size}")
        if not need <= meshes: problems.append(f"missing meshes {sorted(need - meshes)}")
        if not need <= nodes: problems.append(f"missing nodes {sorted(need - nodes)}")
        if abs(hi[1] - lo[1] - 1) > 1e-3: problems.append(f"height {hi[1] - lo[1]:.3f}")
        if abs(lo[1]) > 1e-3: problems.append(f"bottom at y={lo[1]:.3f}")
        if abs(lo[0] + hi[0]) > 1e-3 or abs(lo[2] + hi[2]) > 1e-3: problems.append("not centred on x/z")
        if not emissive: problems.append("status is not emissive")
        bad += bool(problems)
        print(f"{'OK ' if not problems else 'BAD'} {name:9} {size/1024:6.1f} KB  meshes={sorted(meshes)}  "
              f"size={hi[0]-lo[0]:.2f}x{hi[1]-lo[1]:.2f}x{hi[2]-lo[2]:.2f}  {'; '.join(problems)}")
    except FileNotFoundError:
        bad += 1; print(f"BAD {name:9} missing file")
sys.exit(1 if bad else 0)

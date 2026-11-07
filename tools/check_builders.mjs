// Check the procedural device models (ui/assets/models/procedural/<key>.js) against the model rules
// (ui/assets/models/README.md): every file registers exactly its own key, and every model has named `body` and
// `status` parts, is 1 unit tall, stands on y = 0, is centred on x / z, stays low-poly and uses no textures.
//   node tools/check_builders.mjs            -> one line per model, exit 1 if any rule fails
import { createRequire } from "node:module";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DIR = join(ROOT, "ui", "assets", "models", "procedural");
const require = createRequire(import.meta.url);
const _warn = console.warn; console.warn = () => {};                 // three.min.js warns that the UMD build is deprecated
const THREE = require(join(ROOT, "ui", "vendor", "three.min.js"));
console.warn = _warn;
globalThis.window = globalThis;
const run = (file) => vm.runInThisContext(readFileSync(join(DIR, file), "utf8"), { filename: file });

run("kit.js");
const MAX_TRIANGLES = 40000;
const fails = [];
const files = readdirSync(DIR).filter((f) => f.endsWith(".js") && f !== "kit.js").sort();
for (const file of files) {
  const key = file.slice(0, -3), before = new Set(Object.keys(window.SAFEHOUSE_MODEL_BUILDERS));
  run(file);
  const added = Object.keys(window.SAFEHOUSE_MODEL_BUILDERS).filter((k) => !before.has(k));
  const bad = (msg) => fails.push(`${key}: ${msg}`);
  if (added.length !== 1 || added[0] !== key) { bad(`registers ${JSON.stringify(added)}, expected ["${key}"]`); continue; }
  const g = window.SAFEHOUSE_MODEL_BUILDERS[key](THREE);
  g.updateMatrixWorld(true);
  const names = new Set(), v = new THREE.Vector3(), m = new THREE.Matrix4();
  let tris = 0, textures = 0, lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  g.traverse((o) => {
    if (!o.isMesh) return;
    for (let p = o; p; p = p.parent) if (p.name) names.add(p.name);
    const geo = o.geometry, n = o.isInstancedMesh ? o.count : 1;
    tris += ((geo.index ? geo.index.count : geo.attributes.position.count) / 3) * n;
    [].concat(o.material).forEach((mat) => { for (const k of ["map", "normalMap", "roughnessMap", "emissiveMap", "alphaMap"]) if (mat[k]) textures++; });
    for (let i = 0; i < n; i++) {
      if (o.isInstancedMesh) { o.getMatrixAt(i, m); m.premultiply(o.matrixWorld); } else m.copy(o.matrixWorld);
      const a = geo.attributes.position;
      for (let j = 0; j < a.count; j++) {
        v.fromBufferAttribute(a, j).applyMatrix4(m);
        lo = [Math.min(lo[0], v.x), Math.min(lo[1], v.y), Math.min(lo[2], v.z)];
        hi = [Math.max(hi[0], v.x), Math.max(hi[1], v.y), Math.max(hi[2], v.z)];
      }
    }
  });
  const height = hi[1] - lo[1], cx = (lo[0] + hi[0]) / 2, cz = (lo[2] + hi[2]) / 2;
  for (const part of ["body", "status"]) if (!names.has(part)) bad(`no part named "${part}"`);
  if (Math.abs(height - 1) > 0.02) bad(`height ${height.toFixed(3)}, expected 1`);
  if (Math.abs(lo[1]) > 0.01) bad(`stands at y = ${lo[1].toFixed(3)}, expected 0`);
  if (Math.abs(cx) > 0.02 || Math.abs(cz) > 0.02) bad(`not centred (x ${cx.toFixed(3)}, z ${cz.toFixed(3)})`);
  if (tris > MAX_TRIANGLES) bad(`${tris} triangles, max ${MAX_TRIANGLES}`);
  if (textures) bad(`${textures} texture(s): models use material colours only`);
  console.log(`${key.padEnd(18)} ${String(Math.round(tris)).padStart(6)} tris  size ${(hi[0] - lo[0]).toFixed(2)} x ${height.toFixed(2)} x ${(hi[2] - lo[2]).toFixed(2)}  parts ${[...names].sort().join(",")}`);
}
if (!files.length) fails.push("no procedural models found");
fails.forEach((f) => console.log("FAIL " + f));
process.exit(fails.length ? 1 : 0);

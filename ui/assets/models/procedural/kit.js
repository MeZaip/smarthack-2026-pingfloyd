/* SafeHouse procedural device models: the shared kit (palette, materials, rounded shapes).
 *
 * Every model in this folder is a plain script (no ES modules, works from file://) that registers a builder:
 *   window.SAFEHOUSE_MODEL_BUILDERS["phone-iphone"] = (THREE) => THREE.Group
 * ui/device3d.js calls the builder once and clones the result for every slot. The rules are the ones of the .glb
 * models (ui/assets/models/README.md): about 1 unit tall, origin at the bottom centre, Y up, the side to show faces
 * +Z, the SafeHouse palette, no textures and no logos, and named parts: `body` and `status` on every model (status is
 * the LED that takes the risk colour), plus `screen`, `lens`, `ports`, `keys`... where they exist.
 * The shapes follow reference photos (stylised, low-poly): see the README for which photo each model was built from.
 */
(function () {
  "use strict";
  window.SAFEHOUSE_MODEL_BUILDERS = window.SAFEHOUSE_MODEL_BUILDERS || {};
  const K = (window.SAFEHOUSE_MODEL_KIT = {});

  // the palette of tools/make_models.py, plus a few tones the new models need (all from the same slate family)
  K.PALETTE = {
    slate: "#1e293b", slate2: "#334155", slate3: "#475569", deep: "#0f172a", chrome: "#94a3b8",
    screen: "#090d16", lens: "#05070a", keys: "#0b1120", pcb: "#12302b", status: "#00ff66",
  };

  const cache = new WeakMap();
  // one set of materials per THREE instance; slots clone the model but share these (status gets its own copy)
  K.materials = function (T) {
    if (cache.has(T)) return cache.get(T);
    const P = K.PALETTE;
    const std = (color, metalness, roughness, extra) => Object.assign(new T.MeshStandardMaterial({ color, metalness, roughness }), extra || {});
    const m = {
      shell: std(P.slate2, 0.4, 0.36),           // anodised aluminium (space grey)
      shellDark: std(P.slate, 0.45, 0.38),
      frame: std(P.slate, 0.7, 0.28),            // phone frames: polished metal
      glassBack: std(P.slate3, 0.25, 0.22),      // frosted back glass
      deep: std(P.deep, 0.3, 0.45),
      chrome: std(P.chrome, 0.8, 0.25),
      keys: std(P.keys, 0.1, 0.65),
      pad: std(P.slate3, 0.35, 0.3),
      bezel: std(P.lens, 0.2, 0.2),              // black front glass (not mirror-like: the risk light would show as a dot)
      screen: std(P.screen, 0.1, 0.1),
      lens: std(P.lens, 0.5, 0.05),
      pcb: std(P.pcb, 0.15, 0.6),
      chip: std("#0b0f17", 0.2, 0.5),
      status: std(P.status, 0, 0.3),
    };
    m.screen.emissive.setRGB(0, 0.010, 0.018);   // the faint cyan tint of the .glb screens (linear factors)
    m.status.emissive.set(P.status);
    Object.entries(m).forEach(([k, v]) => { v.name = k; });
    cache.set(T, m);
    return m;
  };

  // rounded rectangle in the XY plane, centred
  K.roundRect = function (T, w, h, r) {
    r = Math.max(0.0001, Math.min(r, w / 2 - 1e-4, h / 2 - 1e-4));
    const s = new T.Shape(), x = -w / 2, y = -h / 2;
    s.moveTo(x + r, y);
    s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r);
    s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
    s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y);
    return s;
  };

  // a vertical rounded panel: w (x) by h (y), thickness t (z), centred on the origin, edges bevelled by b
  K.panel = function (T, w, h, t, r, b, holes) {
    b = Math.min(b || 0, t / 2 - 1e-4, w / 4, h / 4);
    const shape = K.roundRect(T, w - 2 * b, h - 2 * b, Math.max(0.0001, r - b));
    (holes || []).forEach((hl) => shape.holes.push(hl));
    const g = new T.ExtrudeGeometry(shape, { depth: t - 2 * b, bevelEnabled: b > 0, bevelThickness: b, bevelSize: b,
      bevelSegments: 2, curveSegments: 6 });
    g.translate(0, 0, -(t - 2 * b) / 2);
    return g;
  };

  // a horizontal rounded slab: w (x) by d (z), height h (y), sitting on y = 0, edges bevelled by b
  K.slab = function (T, w, d, h, r, b, holes) {
    const g = K.panel(T, w, d, h, r, b, holes);
    g.rotateX(-Math.PI / 2);                       // the extrusion (z) becomes up (y)
    g.translate(0, h / 2, 0);
    return g;
  };

  // a disc / short cylinder facing +Z (radius r, depth t), centred on the origin
  K.disc = function (T, r, t, seg) {
    const g = new T.CylinderGeometry(r, r, t, seg || 24);
    g.rotateX(Math.PI / 2);
    return g;
  };

  K.mesh = function (T, geo, mat, name, x, y, z) {
    const m = new T.Mesh(geo, mat);
    m.name = name || "";
    m.position.set(x || 0, y || 0, z || 0);
    return m;
  };

  // many copies of one small part (keys, pins) as one InstancedMesh; at: [[x, y, z, sx?, sz?], ...]
  K.instances = function (T, geo, mat, name, at) {
    const im = new T.InstancedMesh(geo, mat, at.length), o = new T.Object3D();
    at.forEach((p, i) => {
      o.position.set(p[0], p[1], p[2]);
      o.scale.set(p[3] || 1, 1, p[4] || 1);
      o.updateMatrix();
      im.setMatrixAt(i, o.matrix);
    });
    im.name = name || "";
    return im;
  };

  // scale the model to 1 unit tall, centre it on x / z and stand it on y = 0
  K.finish = function (T, inner) {
    inner.updateMatrixWorld(true);
    const box = new T.Box3().setFromObject(inner, true);
    const s = 1 / (box.max.y - box.min.y);
    const root = new T.Group();
    inner.scale.multiplyScalar(s);
    inner.position.set(-(box.min.x + box.max.x) / 2 * s, -box.min.y * s, -(box.min.z + box.max.z) / 2 * s);
    root.add(inner);
    root.updateMatrixWorld(true);
    return root;
  };
})();

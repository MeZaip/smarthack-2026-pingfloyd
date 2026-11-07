/* Device3D - the 3D device models in cards, tiles, the device sheet and on the threat-path pedestals.
 *
 * Works from file:// (Safari and Chrome block fetch()/GLTFLoader of local .glb files there):
 *   - the models come from ui/assets/models/models-bundle.js (window.SAFEHOUSE_MODELS_BASE64, base64 .glb);
 *   - a tiny .glb reader below turns them into THREE meshes (the files are written by tools/make_models.py:
 *     float32 POSITION/NORMAL, uint16/uint32 indices, PBR factors, no textures), so no ES module is needed;
 *   - ONE hidden WebGLRenderer draws every slot in turn and copies the picture into a plain 2D <canvas> in the
 *     slot, so there is no limit on WebGL contexts and slots also work inside the <dialog> sheet.
 *
 * Usage: any element <div class="dev3d" data-type="router" data-tone="red|amber|blue|green" [data-float]>
 * is picked up by Device3D.scan(); the model rotates gently, can be turned by dragging, and its `status`
 * part (LED) plus a rim light take the risk colour. Without WebGL, or without the bundle, the SVG icon that
 * sits inside the slot stays visible.
 */
(function () {
  "use strict";
  const T3 = window.THREE;
  const BUNDLE = window.SAFEHOUSE_MODELS_BASE64;
  const api = { supported: false, scan() {}, refresh() {} };
  window.Device3D = api;
  if (!T3 || !BUNDLE) return;

  let renderer;
  try {
    renderer = new T3.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  } catch (e) { return; }
  if (!renderer.getContext()) return;
  api.supported = true;

  const SIZE = 320;                                   // offscreen render size, copied (scaled) into each square slot
  renderer.setPixelRatio(1);
  renderer.setSize(SIZE, SIZE, false);
  renderer.setClearColor(0x000000, 0);
  renderer.toneMapping = T3.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;

  const TONES = { red: "#ef4444", amber: "#f59e0b", blue: "#38bdf8", green: "#10b981" };
  const reduce = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ------------------------------------------------------------------ tiny .glb reader (our own files only)
  function decode(dataUri) {
    const bin = atob(dataUri.slice(dataUri.indexOf(",") + 1));
    const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    return buf.buffer;
  }
  function parseGlb(ab) {
    const dv = new DataView(ab);
    if (dv.getUint32(0, true) !== 0x46546C67) throw new Error("not a glb");
    const jsonLen = dv.getUint32(12, true);
    const gl = JSON.parse(new TextDecoder().decode(new Uint8Array(ab, 20, jsonLen)));
    const binStart = 20 + jsonLen + 8;
    const view = (acc) => {
      const bv = gl.bufferViews[acc.bufferView], off = binStart + (bv.byteOffset || 0) + (acc.byteOffset || 0);
      const n = acc.count * (acc.type === "VEC3" ? 3 : 1);
      if (acc.componentType === 5126) return new Float32Array(ab.slice(off, off + n * 4));
      if (acc.componentType === 5123) return new Uint16Array(ab.slice(off, off + n * 2));
      return new Uint32Array(ab.slice(off, off + n * 4));
    };
    const mats = (gl.materials || []).map((m) => {
      const p = m.pbrMetallicRoughness || {}, c = p.baseColorFactor || [1, 1, 1, 1], e = m.emissiveFactor || [0, 0, 0];
      const mat = new T3.MeshStandardMaterial({ metalness: p.metallicFactor ?? 1, roughness: p.roughnessFactor ?? 1 });
      mat.color.setRGB(c[0], c[1], c[2]);             // glTF factors are linear, like three's working space
      mat.emissive.setRGB(e[0], e[1], e[2]);
      mat.name = m.name || "";
      return mat;
    });
    const root = new T3.Group();
    const scene = gl.scenes[gl.scene || 0];
    const addNode = (i, parent) => {
      const nd = gl.nodes[i], g = new T3.Group();
      g.name = nd.name || "";
      if (nd.mesh != null) {
        const prims = gl.meshes[nd.mesh].primitives;
        prims.forEach((pr, k) => {
          const geo = new T3.BufferGeometry();
          geo.setAttribute("position", new T3.BufferAttribute(view(gl.accessors[pr.attributes.POSITION]), 3));
          if (pr.attributes.NORMAL != null) geo.setAttribute("normal", new T3.BufferAttribute(view(gl.accessors[pr.attributes.NORMAL]), 3));
          else geo.computeVertexNormals();
          if (pr.indices != null) geo.setIndex(new T3.BufferAttribute(view(gl.accessors[pr.indices]), 1));
          const mesh = new T3.Mesh(geo, mats[pr.material] || new T3.MeshStandardMaterial());
          mesh.name = prims.length > 1 ? `${g.name}_${k + 1}` : g.name;
          g.add(mesh);
        });
      }
      (nd.children || []).forEach((c) => addNode(c, g));
      parent.add(g);
    };
    scene.nodes.forEach((i) => addNode(i, root));
    return root;
  }

  const templates = {};
  function template(type) {
    const key = BUNDLE[type] ? type : "unknown";
    if (!templates[key]) {
      const g = parseGlb(decode(BUNDLE[key]));
      const box = new T3.Box3().setFromObject(g), sph = box.getBoundingSphere(new T3.Sphere());
      templates[key] = { group: g, center: sph.center, radius: sph.radius };
    }
    return templates[key];
  }

  // ------------------------------------------------------------------ one shared scene + camera
  const scene = new T3.Scene();
  scene.add(new T3.HemisphereLight(0xdbeafe, 0x0f172a, 1.35));
  const key = new T3.DirectionalLight(0xffffff, 2.4); key.position.set(2.5, 3.5, 4); scene.add(key);
  const rim = new T3.PointLight(0x10b981, 0, 8, 2); rim.position.set(-1.4, 1.4, -1.2); scene.add(rim);
  const glow = new T3.PointLight(0x10b981, 0, 4, 2); glow.position.set(0, 0.15, 1.4); scene.add(glow);
  const camera = new T3.PerspectiveCamera(30, 1, 0.01, 50);
  const holder = new T3.Group(); scene.add(holder);

  // ------------------------------------------------------------------ slots
  const slots = new Set();
  // on screen = its box overlaps the viewport (checked every frame: cheap, and no observer timing to wait for)
  function onScreen(el) {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.bottom > -80 && r.top < innerHeight + 80 && r.right > 0 && r.left < innerWidth;
  }

  function makeSlot(el) {
    const type = el.dataset.type || "unknown";
    const tone = TONES[el.dataset.tone] || TONES.green;
    const t = template(type);
    const model = t.group.clone(true);
    // own material copies for the status part, so each slot can glow in its own risk colour
    model.traverse((o) => {
      if (!o.isMesh) return;
      let p = o, isStatus = false;
      while (p) { if (p.name === "status") { isStatus = true; break; } p = p.parent; }
      if (isStatus) { o.material = o.material.clone(); o.material.color.set(tone); o.material.emissive.set(tone); o.material.emissiveIntensity = 1.6; }
    });
    const cv = document.createElement("canvas");
    cv.className = "dev3d-canvas";
    cv.setAttribute("aria-hidden", "true");
    el.prepend(cv);
    el.classList.add("ready");
    const s = { el, cv, ctx: cv.getContext("2d"), model, t, tone, spin: Math.random() * Math.PI * 2, drag: 0, hover: false, float: el.hasAttribute("data-float"), drawn: false };
    // turn the model by dragging; a drag does not count as a click on the card
    let down = null, moved = false;
    cv.addEventListener("pointerdown", (e) => { down = e.clientX; moved = false; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener("pointermove", (e) => { if (down == null) return; const dx = e.clientX - down; if (Math.abs(dx) > 3) moved = true; s.drag += dx * 0.012; down = e.clientX; s.drawn = false; });
    const end = () => { down = null; };
    cv.addEventListener("pointerup", end); cv.addEventListener("pointercancel", end);
    cv.addEventListener("click", (e) => { if (moved) { e.stopPropagation(); e.preventDefault(); } }, true);
    el.addEventListener("pointerenter", () => { s.hover = true; });
    el.addEventListener("pointerleave", () => { s.hover = false; });
    slots.add(s);
  }

  api.scan = function (root) {
    (root || document).querySelectorAll(".dev3d:not(.ready)").forEach((el) => {
      try { makeSlot(el); } catch (e) { /* keep the SVG fallback for this slot */ }
    });
    kick();
  };
  api.refresh = () => { slots.forEach((s) => { s.drawn = false; }); kick(); };

  // ------------------------------------------------------------------ draw loop (only visible slots)
  function draw(s, time) {
    const w = s.el.clientWidth, h = s.el.clientHeight;
    if (!w || !h) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cw = Math.round(w * dpr), ch = Math.round(h * dpr);
    if (s.cv.width !== cw || s.cv.height !== ch) { s.cv.width = cw; s.cv.height = ch; }
    const still = reduce();
    const angle = (still ? 0.55 : 0.55 + Math.sin(s.spin + time * 0.0006) * 0.45 + (s.hover ? time * 0.0012 : 0)) + s.drag;
    holder.clear();
    s.model.rotation.set(0, angle, 0);
    s.model.position.set(-s.t.center.x, -s.t.center.y + (s.float && !still ? Math.sin(time * 0.0018 + s.spin) * 0.04 : 0), -s.t.center.z);
    holder.add(s.model);
    rim.color.set(s.tone); rim.intensity = 5;
    glow.color.set(s.tone); glow.intensity = 1.6;
    camera.aspect = 1;                                  // slots are square, like the offscreen renderer
    const dist = (s.t.radius * 0.74) / Math.sin((camera.fov * Math.PI) / 360);   // the bounding sphere is larger than the visible shape
    camera.position.set(0, dist * 0.34, dist);
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
    s.ctx.clearRect(0, 0, cw, ch);
    s.ctx.drawImage(renderer.domElement, 0, 0, cw, ch);
    s.drawn = true;
  }

  let raf = 0;
  function loop(time) {
    raf = 0;
    const still = reduce();
    for (const s of slots) {
      if (!s.el.isConnected) { slots.delete(s); continue; }
      if (!onScreen(s.el)) continue;
      if (still && s.drawn) continue;
      draw(s, time);
    }
    // keep going while any slot exists: the first frames can come before layout, and slots scroll in and out.
    // Off-screen slots cost one getBoundingClientRect per frame; nothing is drawn for them.
    if (slots.size) raf = requestAnimationFrame(loop);
  }
  function kick() { if (!raf) raf = requestAnimationFrame(loop); }
  window.addEventListener("scroll", kick, { passive: true });   // scrolling may bring slots into view
  window.addEventListener("resize", api.refresh);
})();

/* Safehouse3D - the 3D house on the Home page (Three.js r159, bundled in ui/vendor).
 *
 *   Safehouse3D.supported            true when Three.js + WebGL are available (else the CSS house is used)
 *   Safehouse3D.mount(element)       puts the canvas inside element (can be called again after a re-render)
 *   Safehouse3D.setState(state)      "idle" | "scanning" | "safe" | "vulnerable" | "error"
 *
 * Scene: a modern two-volume house (white plaster + wood cladding, big glass windows, flat roofs, hinged
 * door) in a minimalist garden (lawn, stone path, hedge, stylised trees, bushes, grass tufts). All textures
 * are drawn on canvases at start, so nothing is downloaded. buildHouse() is the one place to swap in a
 * .gltf model later (GLTFLoader) - the windows / door / doorway names below are what the states animate.
 *
 * States: "scanning" sweeps a translucent laser grid from the roof to the ground in a smooth loop;
 * "safe" stops the laser and the windows glow emerald (emissive + point lights inside);
 * "vulnerable" swings the door open on a glowing orange doorway. Colour is never the only signal:
 * the page always shows an icon + words next to the house (glass panel + status).
 * With prefers-reduced-motion the camera does not sway and the laser is not shown.
 */
(function () {
  "use strict";
  const T3 = window.THREE;
  const hasWebGL = (() => {
    try {
      const c = document.createElement("canvas");
      return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
    } catch (e) { return false; }
  })();
  const api = { supported: !!T3 && hasWebGL, mount() {}, setState() {}, state: "idle" };
  window.Safehouse3D = api;
  if (!api.supported) return;

  const reduce = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const EMERALD = new T3.Color("#10b981"), AMBER = new T3.Color("#f29900"), BLACK = new T3.Color("#000000");
  const SWEEP = 1.3;          // seconds for one roof-to-ground pass of the laser
  const TOP = 5.9, BOTTOM = 0.05;

  // ------------------------------------------------------------------ procedural textures
  function canvasTex(w, h, draw, rx, ry) {
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    draw(c.getContext("2d"), w, h);
    const tex = new T3.CanvasTexture(c);
    tex.colorSpace = T3.SRGBColorSpace;
    tex.wrapS = tex.wrapT = T3.RepeatWrapping;
    tex.repeat.set(rx || 1, ry || 1);
    tex.anisotropy = 4;
    return tex;
  }
  let seed = 7;
  const rand = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
  function noise(ctx, w, h, n, alpha, light) {
    for (let i = 0; i < n; i++) {
      ctx.fillStyle = (rand() < .5 ? (light || "rgba(255,255,255,") : "rgba(0,0,0,") + (rand() * alpha) + ")";
      ctx.fillRect(rand() * w, rand() * h, 1 + rand() * 2, 1 + rand() * 2);
    }
  }
  const TEX = {
    plaster: () => canvasTex(256, 256, (c, w, h) => { c.fillStyle = "#f1efea"; c.fillRect(0, 0, w, h); noise(c, w, h, 5000, .05); }, 2, 1),
    wood: () => canvasTex(256, 256, (c, w, h) => {
      for (let x = 0; x < w; x += 16) {
        const l = 38 + rand() * 10;
        c.fillStyle = `hsl(28, 45%, ${l}%)`; c.fillRect(x, 0, 16, h);
        c.fillStyle = "rgba(0,0,0,.25)"; c.fillRect(x + 15, 0, 1, h);
        for (let k = 0; k < 6; k++) { c.fillStyle = `rgba(60,30,10,${rand() * .18})`; c.fillRect(x + rand() * 14, 0, 1, h); }
      }
    }, 3, 1),
    grass: () => canvasTex(512, 512, (c, w, h) => { c.fillStyle = "#6aa84f"; c.fillRect(0, 0, w, h); noise(c, w, h, 26000, .12, "rgba(210,255,170,"); }, 6, 6),
    stone: () => canvasTex(128, 128, (c, w, h) => { c.fillStyle = "#c9c6bf"; c.fillRect(0, 0, w, h); noise(c, w, h, 2500, .12); }),
    grid: () => canvasTex(512, 512, (c, w, h) => {
      c.clearRect(0, 0, w, h);
      const g = c.createRadialGradient(w / 2, h / 2, 10, w / 2, h / 2, w * .7);
      g.addColorStop(0, "rgba(125,211,252,.55)"); g.addColorStop(1, "rgba(56,189,248,.08)");
      c.fillStyle = g; c.fillRect(0, 0, w, h);
      c.strokeStyle = "rgba(186,230,253,.95)"; c.lineWidth = 2;
      for (let i = 0; i <= w; i += 32) { c.beginPath(); c.moveTo(i, 0); c.lineTo(i, h); c.stroke(); c.beginPath(); c.moveTo(0, i); c.lineTo(w, i); c.stroke(); }
    }),
  };

  // ------------------------------------------------------------------ renderer, scene, camera
  const renderer = new T3.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = T3.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T3.PCFSoftShadowMap;
  const canvas = renderer.domElement;
  canvas.className = "house3d-canvas";
  canvas.setAttribute("aria-hidden", "true");

  const scene = new T3.Scene();
  const camera = new T3.PerspectiveCamera(30, 1, 0.1, 100);
  const target = new T3.Vector3(0.4, 2.6, 0.6);

  // Night / cyberpunk mood. The hemisphere light is the scene's ambient light: it is cut drastically
  // (1.1 -> 0.14) so the rooms are dark and only the neon lights and the screens light them.
  // The sun becomes a cool, dim moonlight so the garden is still readable. Tweak the mood here.
  const MOOD = { ambient: 0.14, sky: "#4a5a9a", ground: "#0b1410", moon: 0.95, moonColor: "#a9bcff", exposure: 1.15 };
  renderer.toneMappingExposure = MOOD.exposure;
  scene.add(new T3.HemisphereLight(MOOD.sky, MOOD.ground, MOOD.ambient));
  const sun = new T3.DirectionalLight(MOOD.moonColor, MOOD.moon);
  sun.position.set(7, 12, 8);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  Object.assign(sun.shadow.camera, { left: -10, right: 10, top: 10, bottom: -10, near: 1, far: 40 });
  sun.shadow.bias = -0.0008;
  scene.add(sun);

  const mat = (o) => new T3.MeshStandardMaterial(Object.assign({ roughness: .85, metalness: 0 }, o));
  function mesh(geo, material, pos, opts) {
    const m = new T3.Mesh(geo, material);
    if (pos) m.position.set(pos[0], pos[1], pos[2]);
    m.castShadow = !(opts && opts.noCast);
    m.receiveShadow = true;
    return m;
  }

  // ------------------------------------------------------------------ garden
  function buildGarden(group) {
    const lawn = mesh(new T3.CylinderGeometry(9, 9.2, 0.4, 72), [mat({ color: "#6f5338" }), mat({ map: TEX.grass() }), mat({ color: "#6f5338" })], [0, -0.2, 0], { noCast: true });
    group.add(lawn);
    const stoneMat = mat({ map: TEX.stone(), roughness: .95 });
    for (let i = 0; i < 6; i++) {
      const s = mesh(new T3.BoxGeometry(1.0, 0.06, 0.55), stoneMat, [1.6 + (i % 2 ? .12 : -.12), 0.03, 3.25 + i * 0.85], { noCast: true });
      s.rotation.y = (rand() - .5) * .25;
      group.add(s);
    }
    const hedgeMat = mat({ color: "#2f6b3a", roughness: 1 });
    group.add(mesh(new T3.BoxGeometry(7.5, 0.8, 0.7), hedgeMat, [-0.3, 0.4, -3.9]));
    const leaf = [mat({ color: "#3f8f4a", flatShading: true }), mat({ color: "#2e7d43", flatShading: true }), mat({ color: "#5aa15a", flatShading: true })];
    const trunk = mat({ color: "#7a5236" });
    function tree(x, z, s, k) {
      const t = new T3.Group();
      t.add(mesh(new T3.CylinderGeometry(0.09 * s, 0.13 * s, 1.4 * s, 8), trunk, [0, 0.7 * s, 0]));
      t.add(mesh(new T3.IcosahedronGeometry(0.95 * s, 1), leaf[k % 3], [0, 1.95 * s, 0]));
      t.add(mesh(new T3.IcosahedronGeometry(0.6 * s, 1), leaf[(k + 1) % 3], [0.35 * s, 2.55 * s, 0.1 * s]));
      t.position.set(x, 0, z);
      group.add(t);
    }
    tree(-5.6, -1.6, 1.15, 0); tree(-4.9, 3.6, 0.9, 1); tree(5.7, -2.4, 1.05, 2); tree(5.6, 3.9, 0.8, 0);
    [[-2.6, 2.75, .5], [-0.9, 2.8, .42], [3.6, 1.6, .45], [-3.4, -0.6, .4], [0.2, 6.2, .35], [3.1, 5.4, .4]].forEach(([x, z, r], i) =>
      group.add(mesh(new T3.IcosahedronGeometry(r, 1), leaf[i % 3], [x, r * .8, z])));
    // grass tufts
    const tuftGeo = new T3.ConeGeometry(0.05, 0.28, 4);
    const tufts = new T3.InstancedMesh(tuftGeo, mat({ color: "#4e9a3f" }), 160);
    const m4 = new T3.Matrix4();
    let n = 0;
    while (n < 160) {
      const a = rand() * Math.PI * 2, r = 3.2 + rand() * 5.4, x = Math.cos(a) * r, z = Math.sin(a) * r;
      if (Math.abs(x - 1.6) < .8 && z > 2.4) continue;                 // keep the path clear
      m4.makeTranslation(x, 0.12, z);
      tufts.setMatrixAt(n++, m4);
    }
    tufts.receiveShadow = true;
    group.add(tufts);
  }

  // ------------------------------------------------------------------ house (swap for a .gltf here later)
  const windows = [];
  let doorPivot, doorway, roofTop = 5.4;
  // Window glass: physically based, see-through (low opacity, no depth write so the rooms behind stay visible).
  // emissive is kept, so the "safe" state can still make the glass glow emerald.
  const GLASS = () => new T3.MeshPhysicalMaterial({
    color: "#bfe3ff", metalness: 0, roughness: 0.04,
    transparent: true, opacity: 0.18, depthWrite: false, side: T3.DoubleSide,
    clearcoat: 1, clearcoatRoughness: 0.05, ior: 1.5, specularIntensity: 1, reflectivity: 0.5,
    emissive: BLACK.clone(), emissiveIntensity: 1,
  });
  const frameMat = mat({ color: "#2a2e34", roughness: .6 });
  function glass(w, h, pos, rotY, group) {
    const g = new T3.Group();
    g.position.set(pos[0], pos[1], pos[2]);
    g.rotation.y = rotY || 0;
    const pane = mesh(new T3.PlaneGeometry(w, h), GLASS(), [0, 0, 0.012], { noCast: true });
    pane.renderOrder = 2;                                   // draw after the rooms and the network glow
    g.add(pane);
    const f = 0.08;                                          // thin frame around the hole (no solid backing any more)
    [[0, h / 2 + f / 2, w + 2 * f, f], [0, -h / 2 - f / 2, w + 2 * f, f], [-w / 2 - f / 2, 0, f, h], [w / 2 + f / 2, 0, f, h]]
      .forEach(([x, y, ww, hh]) => g.add(mesh(new T3.BoxGeometry(ww, hh, 0.06), frameMat, [x, y, 0])));
    group.add(g);
    windows.push(pane);
  }

  // A wall with rectangular holes (the windows), extruded inwards from its outer face.
  //   axis "z": wall facing +z/-z at z = at, running along x from `from` to `to`
  //   axis "x": wall facing +x/-x at x = at, running along z from `from` to `to`
  //   holes: [centre along the wall, centre height, width, height] in world units
  const WALL = 0.12;
  function wall(group, material, axis, at, from, to, y0, h, holes, outward, depth = WALL) {
    const shape = new T3.Shape();
    shape.moveTo(0, 0); shape.lineTo(to - from, 0); shape.lineTo(to - from, h); shape.lineTo(0, h); shape.lineTo(0, 0);
    (holes || []).forEach(([c, yc, w, hh]) => {
      const u = c - from, v = yc - y0, p = new T3.Path();
      p.moveTo(u - w / 2, v - hh / 2); p.lineTo(u - w / 2, v + hh / 2); p.lineTo(u + w / 2, v + hh / 2); p.lineTo(u + w / 2, v - hh / 2); p.lineTo(u - w / 2, v - hh / 2);
      shape.holes.push(p);
    });
    const m = mesh(new T3.ExtrudeGeometry(shape, { depth, bevelEnabled: false }), material);
    if (axis === "z") m.position.set(from, y0, outward > 0 ? at - depth : at);
    else { m.rotation.y = -Math.PI / 2; m.position.set(outward > 0 ? at : at + depth, y0, from); }
    group.add(m);
  }
  // A hollow box: 4 walls (+ an inside floor), holes per side. ExtrudeGeometry UVs are in world units,
  // so the textures get a per-metre repeat here.
  function shell(group, material, x0, x1, z0, z1, y0, h, holes) {
    wall(group, material, "z", z1, x0, x1, y0, h, holes.front, 1);
    wall(group, material, "z", z0, x0, x1, y0, h, holes.back, -1);
    wall(group, material, "x", x1, z0, z1, y0, h, holes.right, 1);
    wall(group, material, "x", x0, z0, z1, y0, h, holes.left, -1);
  }

  // The two volumes and their window openings (world units): used for the outer walls and the dark inner lining.
  const ROOMS = [
    { x0: -3, x1: 3, z0: -2.1, z1: 2.1, y0: 0, h: 2.8,
      holes: { front: [[-1.5, 1.35, 2.6, 1.9]], right: [[-0.4, 1.5, 1.8, 1.4]], left: [[0.6, 1.6, 1.2, 1.0]] } },
    { x0: -1.4, x1: 3.2, z0: -2.2, z1: 1.6, y0: 2.98, h: 2.32,
      holes: { front: [[0.9, 4.05, 3.6, 1.1]], right: [[-0.3, 4.0, 1.6, 1.0]] } },
  ];
  function buildHouse(group) {
    const plaster = mat({ map: TEX.plaster(), roughness: .9 });
    const wood = mat({ map: TEX.wood(), roughness: .75 });
    const slab = mat({ color: "#30343a", roughness: .7 });
    plaster.map.repeat.set(0.35, 0.35);
    wood.map.repeat.set(0.65, 0.42);
    // hollow volumes with real window openings, so the rooms (and the network inside) are visible
    [plaster, wood].forEach((m, i) => { const r = ROOMS[i]; shell(group, m, r.x0, r.x1, r.z0, r.z1, r.y0, r.h, r.holes); });
    // dark, slightly glossy floors: they pick up the neon as coloured highlights
    const floorMat = mat({ color: "#0b0d12", roughness: .32, metalness: .45 });
    group.add(mesh(new T3.BoxGeometry(5.76, 0.02, 3.96), floorMat, [0, 0.01, 0], { noCast: true }));
    group.add(mesh(new T3.BoxGeometry(4.36, 0.02, 3.56), floorMat, [0.9, 2.99, -0.3], { noCast: true }));
    group.add(mesh(new T3.BoxGeometry(6.3, 0.18, 4.5), slab, [0, 2.89, 0]));
    group.add(mesh(new T3.BoxGeometry(4.9, 0.2, 4.1), slab, [0.9, 5.3, -0.3]));
    roofTop = 5.4;
    // windows: big ground-floor glass, upper band, side windows
    glass(2.6, 1.9, [-1.5, 1.35, 2.1], 0, group);
    glass(3.6, 1.1, [0.9, 4.05, 1.6], 0, group);
    glass(1.8, 1.4, [3.0, 1.5, -0.4], Math.PI / 2, group);
    glass(1.6, 1.0, [3.2, 4.0, -0.3], Math.PI / 2, group);
    glass(1.2, 1.0, [-3.0, 1.6, 0.6], -Math.PI / 2, group);
    // entrance: doorway (glows orange when a door is open), hinged wooden door, canopy and step
    doorway = mesh(new T3.PlaneGeometry(1.0, 2.1), new T3.MeshStandardMaterial({ color: "#16181c", roughness: 1, emissive: BLACK.clone(), emissiveIntensity: 1 }), [1.6, 1.05, 2.104], { noCast: true });
    group.add(doorway);
    doorPivot = new T3.Group();
    doorPivot.position.set(1.1, 0, 2.13);
    const door = mesh(new T3.BoxGeometry(1.0, 2.1, 0.06), mat({ map: TEX.wood(), color: "#b98a63", roughness: .6 }), [0.5, 1.05, 0]);
    const knob = mesh(new T3.SphereGeometry(0.045, 12, 12), mat({ color: "#d8c08a", metalness: .8, roughness: .3 }), [0.88, 1.05, 0.05]);
    doorPivot.add(door, knob);
    group.add(doorPivot);
    group.add(mesh(new T3.BoxGeometry(1.7, 0.1, 1.0), slab, [1.6, 2.35, 2.55]));
    group.add(mesh(new T3.BoxGeometry(1.5, 0.14, 0.7), mat({ color: "#bdb9b1" }), [1.6, 0.07, 2.5]));
  }

  const world = new T3.Group();
  buildGarden(world);
  buildHouse(world);
  scene.add(world);

  // ------------------------------------------------------------------ cyberpunk interior: neon, devices, hacker, data pulses
  // The rooms are dark (see MOOD). Light inside comes only from neon point lights and glowing screens.
  // Screens are MeshStandardMaterial with a strong emissive drawn on a canvas. Emissive makes a surface
  // bright but does not light anything else, so every glowing device also has a PointLight of the same
  // colour next to it: that is what makes the walls, the desk and the hood pick up the glow.
  // Packets are short neon laser pulses fired in bursts along curved paths router <-> device.
  const NEON = { cyan: "#00f0ff", magenta: "#ff2bd6", green: "#39ff14", violet: "#a855f7", red: "#ff2d55" };
  const network = (function buildCyber(group) {
    const neon = (c, o) => new T3.MeshBasicMaterial(Object.assign({ color: c, toneMapped: false }, o));
    const screenMat = (tex, intensity) => new T3.MeshStandardMaterial({
      color: "#000000", roughness: 0.2, metalness: 0,
      emissive: "#ffffff", emissiveMap: tex, emissiveIntensity: intensity,
      toneMapped: false,                                  // keep the neon saturated (ACES would wash it to white)
    });
    const glowTex = canvasTex(64, 64, (c, w, h) => {
      const g = c.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
      g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(0.25, "rgba(255,255,255,.8)");
      g.addColorStop(0.6, "rgba(255,255,255,.15)"); g.addColorStop(1, "rgba(255,255,255,0)");
      c.fillStyle = g; c.fillRect(0, 0, w, h);
    });
    glowTex.wrapS = glowTex.wrapT = T3.ClampToEdgeWrapping;
    // additive halo sprite: fakes a bloom around bright things (no post-processing needed)
    const halo = (color, size, opacity) => {
      const sp = new T3.Sprite(new T3.SpriteMaterial({ map: glowTex, color, transparent: true, opacity, depthWrite: false, blending: T3.AdditiveBlending, toneMapped: false }));
      sp.scale.setScalar(size); sp.userData.base = opacity; group.add(sp); return sp;
    };
    const lights = [];
    const addLight = (color, intensity, dist, pos) => {
      const l = new T3.PointLight(color, intensity, dist, 2);
      l.position.set(pos[0], pos[1], pos[2]); l.userData.base = intensity;
      scene.add(l); lights.push(l); return l;
    };
    const strip = (color, size, pos) => group.add(mesh(new T3.BoxGeometry(size[0], size[1], size[2]), neon(color), pos, { noCast: true }));
    const UP = new T3.Vector3(0, 1, 0);
    function limb(parent, a, b, r, material) {                // capsule between two points (arms, legs)
      const A = new T3.Vector3(a[0], a[1], a[2]), B = new T3.Vector3(b[0], b[1], b[2]), d = B.clone().sub(A), len = d.length();
      const m = mesh(new T3.CapsuleGeometry(r, Math.max(0.01, len - 2 * r), 4, 10), material);
      m.position.copy(A).add(B).multiplyScalar(0.5);
      m.quaternion.setFromUnitVectors(UP, d.normalize());
      parent.add(m);
    }

    // ---- screen contents, drawn once and scrolled in the loop
    const wave = (x, w, f, a, ph) => Math.sin((x / w) * Math.PI * 2 * f + ph) * a;    // integer f -> tiles when scrolled
    const tvTex = canvasTex(256, 144, (c, w, h) => {
      c.fillStyle = "#020814"; c.fillRect(0, 0, w, h);
      c.strokeStyle = "rgba(0,240,255,.14)"; c.lineWidth = 1;
      for (let x = 0; x < w; x += 16) { c.beginPath(); c.moveTo(x + .5, 0); c.lineTo(x + .5, h); c.stroke(); }
      for (let y = 0; y < h; y += 16) { c.beginPath(); c.moveTo(0, y + .5); c.lineTo(w, y + .5); c.stroke(); }
      [[NEON.cyan, 2, 5, 0.4], [NEON.magenta, 3, 7, 1.7]].forEach(([col, f1, f2, ph], i) => {
        c.strokeStyle = col; c.lineWidth = 3; c.beginPath();
        for (let x = 0; x <= w; x += 2) {
          const y = h * (0.36 + i * 0.16) + wave(x, w, f1, 20, ph) + wave(x, w, f2, 6, ph * 2);
          if (x) c.lineTo(x, y); else c.moveTo(x, y);
        }
        c.stroke();
      });
      for (let x = 0; x < w; x += 16) { const bh = 8 + Math.abs(wave(x, w, 4, 16, .5)); c.fillStyle = NEON.green; c.fillRect(x + 3, h - 6 - bh, 9, bh); }
    });
    const codeTex = canvasTex(128, 128, (c, w, h) => {
      c.fillStyle = "#010a03"; c.fillRect(0, 0, w, h);
      for (let y = 4; y < h; y += 8) {                        // 16 rows of "code": tiles when scrolled up
        let x = 6 + Math.floor(rand() * 3) * 8;
        while (x < w - 12 && rand() > 0.12) {
          const len = 6 + rand() * 24;
          c.fillStyle = rand() < .12 ? NEON.magenta : rand() < .25 ? "#c6ffbf" : NEON.green;
          c.fillRect(x, y, Math.min(len, w - 6 - x), 3);
          x += len + 5;
        }
      }
    });
    const panelTex = canvasTex(256, 256, (c, w, h) => {       // dark tech panels for the inside walls
      c.fillStyle = "#1a1d26"; c.fillRect(0, 0, w, h);
      c.strokeStyle = "rgba(0,0,0,.55)"; c.lineWidth = 3;
      for (let x = 0; x <= w; x += 64) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, h); c.stroke(); }
      c.beginPath(); c.moveTo(0, h * .7); c.lineTo(w, h * .7); c.stroke();
      noise(c, w, h, 1800, .05);
    }, 0.5, 0.5);

    // ---- dark lining on the inside of every wall (same window holes), so the rooms read as dark
    const panelMat = new T3.MeshStandardMaterial({ map: panelTex, roughness: 0.45, metalness: 0.25 });
    const LINE = 0.012;
    ROOMS.forEach((r) => {
      const i = WALL;
      wall(group, panelMat, "z", r.z1 - i, r.x0 + i, r.x1 - i, r.y0, r.h, r.holes.front, 1, LINE);
      wall(group, panelMat, "z", r.z0 + i, r.x0 + i, r.x1 - i, r.y0, r.h, r.holes.back, -1, LINE);
      wall(group, panelMat, "x", r.x1 - i, r.z0 + i, r.z1 - i, r.y0, r.h, r.holes.right, 1, LINE);
      wall(group, panelMat, "x", r.x0 + i, r.z0 + i, r.z1 - i, r.y0, r.h, r.holes.left, -1, LINE);
    });
    // neon floor strips along the walls (visible through the windows from the camera's height)
    strip(NEON.cyan, [0.02, 0.02, 3.9], [-2.855, 0.04, 0]);
    strip(NEON.magenta, [5.7, 0.02, 0.02], [0, 0.04, -1.955]);
    strip(NEON.magenta, [4.3, 0.02, 0.02], [0.9, 3.02, -2.055]);
    strip(NEON.cyan, [0.02, 0.02, 3.5], [-1.255, 3.02, -0.3]);

    const dark = mat({ color: "#0d0f14", roughness: .4, metalness: .55 });
    const fabric = mat({ color: "#08090c", roughness: .95, side: T3.DoubleSide });

    // ---- router: cabinet with a neon edge, body, antennas, green status LEDs
    const RX = -1.45, RZ = 0.85;
    group.add(mesh(new T3.BoxGeometry(1.0, 0.6, 0.5), dark, [RX, 0.3, RZ]));
    strip(NEON.cyan, [1.0, 0.012, 0.012], [RX, 0.6, RZ + 0.25]);
    group.add(mesh(new T3.BoxGeometry(0.46, 0.1, 0.3), dark, [RX, 0.65, RZ]));
    [-0.13, 0.13].forEach((x) => {
      group.add(mesh(new T3.CylinderGeometry(0.018, 0.018, 0.32, 8), dark, [RX + x, 0.86, RZ - 0.12]));
      group.add(mesh(new T3.SphereGeometry(0.03, 10, 8), neon(NEON.green), [RX + x, 1.03, RZ - 0.12], { noCast: true }));
    });
    const routerLed = mesh(new T3.BoxGeometry(0.34, 0.025, 0.012), neon(NEON.green), [RX, 0.66, RZ + 0.155], { noCast: true });
    group.add(routerLed);
    const routerHalo = halo(NEON.green, 0.9, 0.5);
    routerHalo.position.set(RX, 0.72, RZ + 0.22);
    const routerLight = addLight(NEON.green, 2.2, 1.4, [RX, 0.95, RZ + 0.05]);
    const ROUTER = new T3.Vector3(RX, 0.95, RZ - 0.05);

    // ---- Smart TV on the left wall (faces +x, seen through the big front window)
    const TVX = -2.84, TVY = 1.05, TVZ = -0.35;
    group.add(mesh(new T3.BoxGeometry(0.05, 0.8, 1.36), dark, [TVX, TVY, TVZ]));
    const tvScreen = new T3.Mesh(new T3.PlaneGeometry(1.26, 0.7), screenMat(tvTex, 2.2));
    tvScreen.rotation.y = Math.PI / 2;
    tvScreen.position.set(TVX + 0.03, TVY, TVZ);
    group.add(tvScreen);
    strip(NEON.magenta, [0.012, 0.012, 1.4], [TVX + 0.03, TVY - 0.47, TVZ]);
    const tvHalo = halo(NEON.cyan, 2.2, 0.3);
    tvHalo.position.set(TVX + 0.2, TVY, TVZ);
    const tvLight = addLight(NEON.cyan, 8, 3.2, [TVX + 0.75, TVY, TVZ]);

    // ---- hacker's desk against the back wall (seen through the right-hand window), neon edge
    const HX = 2.25;
    group.add(mesh(new T3.BoxGeometry(1.2, 0.05, 0.6), dark, [HX - 0.1, 0.715, -1.62]));
    [[-0.55, -0.27], [0.55, -0.27], [-0.55, 0.27], [0.55, 0.27]].forEach(([x, z]) =>
      group.add(mesh(new T3.BoxGeometry(0.04, 0.69, 0.04), dark, [HX - 0.1 + x, 0.345, -1.62 + z])));
    strip(NEON.magenta, [1.2, 0.014, 0.014], [HX - 0.1, 0.69, -1.315]);
    // laptop: base + lid hinged at the back, screen facing the hacker
    group.add(mesh(new T3.BoxGeometry(0.38, 0.02, 0.26), dark, [HX, 0.75, -1.6]));
    group.add(mesh(new T3.BoxGeometry(0.3, 0.003, 0.13), neon(NEON.green, { transparent: true, opacity: .35 }), [HX, 0.762, -1.58], { noCast: true }));
    const lid = new T3.Group();
    lid.position.set(HX, 0.76, -1.73);
    lid.rotation.x = -0.28;                                    // leans back
    lid.add(mesh(new T3.BoxGeometry(0.38, 0.26, 0.012), dark, [0, 0.13, -0.008]));
    const lapScreen = new T3.Mesh(new T3.PlaneGeometry(0.35, 0.23), screenMat(codeTex, 2.4));
    lapScreen.position.set(0, 0.13, 0);
    lid.add(lapScreen);
    group.add(lid);
    const lapHalo = halo(NEON.green, 0.9, 0.35);
    lapHalo.position.set(HX, 0.9, -1.6);
    const lapLight = addLight(NEON.green, 3.2, 1.35, [HX - 0.1, 0.95, -1.42]);   // lights the hacker's front and the desk

    // ---- the hooded hacker (placeholder from basic shapes), sitting on an office chair, facing the laptop (-z)
    const hacker = new T3.Group();
    hacker.position.set(HX, 0, -0.82);
    hacker.add(mesh(new T3.CylinderGeometry(0.26, 0.26, 0.04, 20), dark, [0, 0.03, 0]));
    hacker.add(mesh(new T3.CylinderGeometry(0.03, 0.03, 0.42, 8), dark, [0, 0.25, 0]));
    hacker.add(mesh(new T3.BoxGeometry(0.46, 0.07, 0.46), dark, [0, 0.47, 0]));
    const chairBack = mesh(new T3.BoxGeometry(0.44, 0.6, 0.06), dark, [0, 0.84, 0.25]);
    chairBack.rotation.x = 0.12;
    hacker.add(chairBack);
    const torso = mesh(new T3.CylinderGeometry(0.16, 0.21, 0.52, 16), fabric, [0, 0.77, -0.04]);
    torso.rotation.x = -0.22;                                  // hunched over the keyboard
    hacker.add(torso);
    const shoulders = mesh(new T3.SphereGeometry(0.17, 16, 12), fabric, [0, 0.99, -0.1]);
    shoulders.scale.set(1.25, 0.6, 0.95);
    hacker.add(shoulders);
    hacker.add(mesh(new T3.SphereGeometry(0.105, 16, 12), mat({ color: "#16120f", roughness: .9 }), [0, 1.16, -0.16]));  // head
    // hood: an open shell around the head (opening faces the laptop) + a pointed tip at the back
    const hood = mesh(new T3.SphereGeometry(0.15, 24, 16, 3 * Math.PI / 2 + 0.9, 2 * Math.PI - 1.8, 0, 2.3), fabric, [0, 1.17, -0.15]);
    hood.rotation.x = -0.25;
    hacker.add(hood);
    const tip = mesh(new T3.ConeGeometry(0.07, 0.2, 12), fabric, [0, 1.26, -0.03]);
    tip.rotation.x = 0.9;
    hacker.add(tip);
    [-1, 1].forEach((sd) => {
      limb(hacker, [sd * 0.18, 0.97, -0.12], [sd * 0.1, 0.79, -0.72], 0.05, fabric);   // arms to the keyboard
      hacker.add(mesh(new T3.SphereGeometry(0.04, 10, 8), fabric, [sd * 0.1, 0.785, -0.74]));
      limb(hacker, [sd * 0.1, 0.52, -0.02], [sd * 0.11, 0.52, -0.38], 0.065, fabric);  // thighs
      limb(hacker, [sd * 0.11, 0.52, -0.38], [sd * 0.11, 0.07, -0.45], 0.055, fabric); // shins
    });
    group.add(hacker);

    // ---- upstairs IoT: thermostat on the back wall, smart speaker with a neon top ring
    group.add(mesh(new T3.CylinderGeometry(0.2, 0.2, 0.05, 32), dark, [0.4, 3.45, -2.04]).rotateX(Math.PI / 2));
    const thermoRing = new T3.Mesh(new T3.RingGeometry(0.12, 0.16, 32), neon(NEON.green));
    thermoRing.position.set(0.4, 3.45, -2.012);
    group.add(thermoRing);
    const thermoHalo = halo(NEON.green, 0.8, 0.4);
    thermoHalo.position.set(0.4, 3.45, -1.95);
    group.add(mesh(new T3.CylinderGeometry(0.16, 0.18, 0.5, 24), dark, [2.4, 3.23, -1.2]));
    const spRing = new T3.Mesh(new T3.RingGeometry(0.09, 0.14, 32), neon(NEON.cyan));
    spRing.rotation.x = -Math.PI / 2;
    spRing.position.set(2.4, 3.485, -1.2);
    group.add(spRing);
    const spHalo = halo(NEON.cyan, 0.8, 0.45);
    spHalo.position.set(2.4, 3.55, -1.2);

    // ---- neon accent lights that splash colour on the dark walls. Point lights have no shadows here
    // (6 extra renders each), so they are kept away from the outer walls and their range ends before them:
    // otherwise the glow would leak through the walls onto the garden.
    addLight(NEON.magenta, 4, 2.4, [1.6, 1.6, -0.2]);          // rim light on the hacker's back
    addLight(NEON.magenta, 5, 2.6, [1.6, 4.3, -0.9]);          // upstairs
    addLight(NEON.cyan, 4, 2.4, [-0.2, 3.7, -1.3]);

    // ---- links + packets
    const devices = [
      { id: "tv", at: new T3.Vector3(TVX + 0.1, TVY, TVZ), color: NEON.cyan, halo: tvHalo, light: tvLight, screen: tvScreen.material },
      { id: "laptop", at: new T3.Vector3(HX, 0.95, -1.66), color: NEON.magenta, halo: lapHalo, light: lapLight, screen: lapScreen.material },
      { id: "thermostat", at: new T3.Vector3(0.4, 3.45, -1.96), color: NEON.green, halo: thermoHalo },
      { id: "speaker", at: new T3.Vector3(2.4, 3.55, -1.2), color: NEON.green, halo: spHalo },
    ];
    const router = { halo: routerHalo, light: routerLight, hit: 0 };
    devices.forEach((d) => { d.hit = 0; d.alert = false; d.screenBase = d.screen ? d.screen.emissiveIntensity : 0; });

    const links = devices.map((d) => {
      const mid = ROUTER.clone().lerp(d.at, 0.5);
      mid.y += 0.6 + ROUTER.distanceTo(d.at) * 0.12;          // arc through the room
      const curve = new T3.QuadraticBezierCurve3(ROUTER.clone(), mid, d.at.clone());
      const tubeMat = neon(d.color, { transparent: true, opacity: 0.18, depthWrite: false, blending: T3.AdditiveBlending });
      group.add(new T3.Mesh(new T3.TubeGeometry(curve, 64, 0.008, 6, false), tubeMat));
      return { device: d, curve, tubeMat, length: curve.getLength(), base: new T3.Color(d.color), col: new T3.Color(d.color), mult: 1, blocked: false };
    });

    // each link fires bursts of 3 short pulses: 2 bursts router -> device and 1 burst back per lap
    const pulseGeo = new T3.CylinderGeometry(0.016, 0.016, 1, 6, 1, true);
    const pulses = [];
    links.forEach((link) => {
      [[0, false], [0.5, false], [0.25, true]].forEach(([start, up]) => {
        for (let k = 0; k < 3; k++) {
          const streak = new T3.Mesh(pulseGeo, neon(link.base, { transparent: true, depthWrite: false, blending: T3.AdditiveBlending }));
          group.add(streak);
          pulses.push({ link, up, streak, head: halo(link.base, 0.24, 1), phase: start - k * 0.05, prev: 0 });
        }
      });
    });

    const SPEED = 2.4;               // metres per second at rate 1
    const PULSE = 0.3;               // length of one laser pulse (metres)
    const RATE = { idle: 1, scanning: 2.2, safe: 0.8, vulnerable: 1.4, error: 0 };
    const RED = new T3.Color(NEON.red), A = new T3.Vector3(), B = new T3.Vector3(), D = new T3.Vector3();
    let clock = 0, screenClock = 0;

    return {
      setAlert(id, on) { devices.forEach((d) => { if (d.id === id) d.alert = !!on; }); },
      update(dt, st, still) {
        const run = still ? 0 : RATE[st];
        clock += dt * run;
        screenClock += dt * (still ? 0 : 1);
        tvTex.offset.x = (screenClock * 0.05) % 1;            // TV graph scrolls sideways
        codeTex.offset.y = (screenClock * 0.22) % 1;          // code scrolls up on the laptop

        // state -> link look: the hacker's link turns red and fast when the house is vulnerable,
        // and is cut (no packets, dim path) when the house is safe
        links.forEach((L) => {
          const isHacker = L.device.id === "laptop";
          L.blocked = st === "error" || (isHacker && st === "safe");
          L.mult = isHacker && st === "vulnerable" ? 1.7 : 1;
          L.col.copy(L.device.alert || (isHacker && st === "vulnerable") ? RED : L.base);
          L.tubeMat.color.copy(L.col);
          L.tubeMat.opacity = L.blocked ? 0.04 : 0.14 + 0.08 * (0.5 + 0.5 * Math.sin(clock * 5 + L.length));
        });

        pulses.forEach((p) => {
          const L = p.link, show = run > 0 && !L.blocked;
          p.streak.visible = p.head.visible = show;
          if (!show) return;
          const t = (((clock * SPEED * L.mult) / L.length + p.phase) % 1 + 1) % 1;
          if (t < p.prev) (p.up ? router : L.device).hit = 1;  // finished a trip: flash the receiver
          p.prev = t;
          const u = p.up ? 1 - t : t;                          // head position on the curve
          const du = PULSE / L.length;
          const tail = p.up ? Math.min(1, u + du) : Math.max(0, u - du);
          L.curve.getPointAt(u, A);
          L.curve.getPointAt(tail, B);
          D.subVectors(A, B);
          const len = D.length();
          p.head.position.copy(A);
          if (len > 1e-4) {                                    // stretch a thin cylinder from tail to head
            p.streak.position.addVectors(A, B).multiplyScalar(0.5);
            p.streak.quaternion.setFromUnitVectors(UP, D.multiplyScalar(1 / len));
            p.streak.scale.set(1, len, 1);
          } else p.streak.visible = false;
          const fade = Math.min(1, t * 10, (1 - t) * 10);
          p.streak.material.color.copy(L.col);
          p.head.material.color.copy(L.col);
          p.streak.material.opacity = 0.95 * fade;
          p.head.material.opacity = fade;
        });

        // receivers flash when a pulse lands, then settle (exponential decay)
        const decay = Math.exp(-dt * 7);
        [router, ...devices].forEach((d) => {
          if (d.light) d.light.intensity = d.light.userData.base * (1 + 1.3 * d.hit);
          if (d.screen) d.screen.emissiveIntensity = d.screenBase * (1 + 0.35 * d.hit);
          d.halo.material.opacity = d.halo.userData.base * (1 + 1.6 * d.hit);
          d.hit *= decay;
        });
        routerLed.material.color.set(NEON.green).multiplyScalar(0.55 + 0.45 * (0.5 + 0.5 * Math.sin(screenClock * 14)));
      },
    };
  })(world);
  api.setDeviceAlert = (id, on) => network.setAlert(id, on);   // e.g. Safehouse3D.setDeviceAlert("tv", true)

  // lights inside the house (emerald when safe) and at the doorway (orange when a door is open)
  const inside = [new T3.PointLight(EMERALD, 0, 9, 2), new T3.PointLight(EMERALD, 0, 9, 2)];
  inside[0].position.set(-1.2, 1.4, 0.6); inside[1].position.set(0.9, 4.0, -0.2);
  const doorLight = new T3.PointLight(AMBER, 0, 7, 2);
  doorLight.position.set(1.6, 1.3, 2.9);
  scene.add(inside[0], inside[1], doorLight);

  // laser: translucent glowing grid plane + bright edge, swept from roof to ground
  const laser = new T3.Group();
  const laserMat = new T3.MeshBasicMaterial({ map: TEX.grid(), color: "#7dd3fc", transparent: true, opacity: 0, side: T3.DoubleSide, depthWrite: false, blending: T3.AdditiveBlending });
  const plane = new T3.Mesh(new T3.PlaneGeometry(7.4, 5.6), laserMat);
  plane.rotation.x = -Math.PI / 2;
  const edgeMat = new T3.LineBasicMaterial({ color: "#e0f2fe", transparent: true, opacity: 0 });
  const edge = new T3.LineLoop(new T3.BufferGeometry().setFromPoints([[-3.7, -2.8], [3.7, -2.8], [3.7, 2.8], [-3.7, 2.8]].map(([x, z]) => new T3.Vector3(x, 0, z))), edgeMat);
  // thick glowing rim so the laser plane reads clearly from any angle
  const rimMat = new T3.MeshBasicMaterial({ color: "#7dd3fc", transparent: true, opacity: 0, depthWrite: false, blending: T3.AdditiveBlending });
  [[0, -2.8, 7.4, 0.07], [0, 2.8, 7.4, 0.07], [-3.7, 0, 0.07, 5.6], [3.7, 0, 0.07, 5.6]].forEach(([x, z, w, d]) => {
    const b = new T3.Mesh(new T3.BoxGeometry(w, 0.07, d), rimMat);
    b.position.set(x, 0, z);
    laser.add(b);
  });
  laser.add(plane, edge);
  laser.position.set(0.3, TOP, 0);
  scene.add(laser);

  // ------------------------------------------------------------------ state + animation
  let state = "idle", scanStart = 0;
  const cur = { door: -0.3, glow: 0, warm: 0, doorGlow: 0, laser: 0 };
  function goals() {
    return {
      idle: { door: -0.3, glow: 0, warm: 0, doorGlow: 0, laser: 0 },
      scanning: { door: -0.3, glow: 0, warm: 0.25, doorGlow: 0, laser: 0 },   // the page's CSS .scanline is the scanner now
      safe: { door: 0, glow: 1, warm: 0, doorGlow: 0, laser: 0 },
      vulnerable: { door: -1.35, glow: 0, warm: 0.35, doorGlow: 1, laser: 0 },
      error: { door: 0, glow: 0, warm: 0, doorGlow: 0, laser: 0 },
    }[state];
  }
  api.setState = function (st) {
    state = ["idle", "scanning", "safe", "vulnerable", "error"].includes(st) ? st : "idle";
    api.state = state;
    if (state === "scanning") scanStart = performance.now();
    if (reduce()) Object.assign(cur, goals());                 // jump straight to the result
  };

  let az = 0, userAz = 0, dragging = false, lastX = 0;
  canvas.addEventListener("pointerdown", (e) => { dragging = true; lastX = e.clientX; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener("pointermove", (e) => { if (!dragging) return; userAz = Math.max(-1.1, Math.min(1.1, userAz + (e.clientX - lastX) * 0.006)); lastX = e.clientX; });
  canvas.addEventListener("pointerup", () => { dragging = false; });
  canvas.addEventListener("pointercancel", () => { dragging = false; });

  const ease = (x) => x < .5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
  let last = performance.now();
  function frame(now) {
    requestAnimationFrame(frame);
    const dt = Math.min(0.05, (now - last) / 1000);              // clamp: no jumps after a hidden tab
    last = now;
    if (!canvas.isConnected || document.hidden) return;
    network.update(dt, state, reduce());
    const g = goals(), k = reduce() ? 1 : 0.08;
    for (const key of Object.keys(cur)) cur[key] += (g[key] - cur[key]) * k;

    doorPivot.rotation.y = cur.door;
    windows.forEach((w) => {
      w.material.emissive.copy(BLACK).lerp(EMERALD, cur.glow).add(AMBER.clone().multiplyScalar(cur.warm * 0.35));
      w.material.emissiveIntensity = 0.4 + cur.glow * 1.6;
    });
    inside.forEach((l) => { l.intensity = cur.glow * 26; });
    doorway.material.emissive.copy(BLACK).lerp(AMBER, cur.doorGlow);
    doorway.material.emissiveIntensity = 1.6 * cur.doorGlow;
    doorLight.intensity = cur.doorGlow * 18;

    if (state === "scanning" && !reduce()) {
      const p = (((now - scanStart) / 1000) / SWEEP) % 1;
      laser.position.y = TOP - (TOP - BOTTOM) * ease(p);
    }
    laserMat.opacity = 0.8 * cur.laser;
    rimMat.opacity = 0.95 * cur.laser;
    edgeMat.opacity = 0.95 * cur.laser;
    laser.visible = cur.laser > 0.01;

    az = reduce() ? 0.62 : 0.62 + Math.sin(now / 4200) * 0.14;
    const a = az + userAz, r = 27;
    camera.position.set(Math.sin(a) * r, 10.5, Math.cos(a) * r);
    camera.lookAt(target);
    renderer.render(scene, camera);
  }

  // ------------------------------------------------------------------ mount (survives page re-renders)
  let observed = null;
  const ro = new ResizeObserver(() => {
    if (!observed) return;
    const w = Math.max(1, observed.clientWidth), h = Math.max(1, observed.clientHeight);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.fov = w / h < 0.9 ? 40 : 30;                         // narrow phones: widen the view
    camera.updateProjectionMatrix();
  });
  api.mount = function (el) {
    if (!el) return;
    el.appendChild(canvas);
    if (observed) ro.unobserve(observed);
    observed = el;
    ro.observe(el);
  };
  requestAnimationFrame(frame);
})();

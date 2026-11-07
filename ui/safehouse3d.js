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
  const target = new T3.Vector3(0.4, 3.3, 0.6);

  scene.add(new T3.HemisphereLight("#dbeafe", "#4d7c3a", 1.1));
  const sun = new T3.DirectionalLight("#fff3dd", 2.6);
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
  function glass(w, h, pos, rotY, group) {
    const frame = mesh(new T3.PlaneGeometry(w + 0.16, h + 0.16), mat({ color: "#2a2e34", roughness: .6 }), pos, { noCast: true });
    const pane = mesh(new T3.PlaneGeometry(w, h), new T3.MeshStandardMaterial({ color: "#3b5876", roughness: .08, metalness: .35, emissive: BLACK.clone(), emissiveIntensity: 1 }), pos, { noCast: true });
    frame.rotation.y = pane.rotation.y = rotY || 0;
    const n = new T3.Vector3(Math.sin(rotY || 0), 0, Math.cos(rotY || 0));
    frame.position.addScaledVector(n, 0.005); pane.position.addScaledVector(n, 0.012);
    group.add(frame, pane);
    windows.push(pane);
  }
  function buildHouse(group) {
    const plaster = mat({ map: TEX.plaster(), roughness: .9 });
    const wood = mat({ map: TEX.wood(), roughness: .75 });
    const slab = mat({ color: "#30343a", roughness: .7 });
    group.add(mesh(new T3.BoxGeometry(6, 2.8, 4.2), plaster, [0, 1.4, 0]));
    group.add(mesh(new T3.BoxGeometry(4.6, 2.4, 3.8), wood, [0.9, 4.0, -0.3]));
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
      scanning: { door: -0.3, glow: 0, warm: 0.25, doorGlow: 0, laser: reduce() ? 0 : 1 },
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
  function frame(now) {
    requestAnimationFrame(frame);
    if (!canvas.isConnected || document.hidden) return;
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
    const a = az + userAz, r = 23.5;
    camera.position.set(Math.sin(a) * r, 8.6, Math.cos(a) * r);
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

/* iot-raspberrypi: a single-board computer (reference: a Raspberry Pi Model B+ photo; no logo, app colours).
 * Parts: the board with four mounting holes (body), the 40-pin GPIO header along the back edge (pins), two stacked
 * USB blocks and the Ethernet jack on the right edge, HDMI, micro USB and the audio jack on the front edge (ports),
 * the processor and network chips plus the ribbon connectors (chips), and the PWR / ACT LEDs (status).
 * Built in centimetres (8.5 x 5.6 cm board). Lying flat it would be a thin sliver from the UI camera, so the board is
 * propped up at an angle (like the reference photo, seen from above), then scaled to 1 unit tall.
 */
(function () {
  "use strict";
  const K = window.SAFEHOUSE_MODEL_KIT;
  window.SAFEHOUSE_MODEL_BUILDERS["iot-raspberrypi"] = function (T) {
    const M = K.materials(T), g = new T.Group(), b = new T.Group();
    const L = 8.5, Wd = 5.6, PCB = 0.16, top = PCB;               // board: length (x), width (z), thickness (y)
    // board: rounded rectangle with four mounting holes (on the B+: 5.8 x 4.9 cm apart, 0.35 cm from the left edge)
    const holes = [];
    const hx = [-L / 2 + 0.35, -L / 2 + 0.35 + 5.8], hz = [-2.45, 2.45];
    hx.forEach((x) => hz.forEach((z) => { const c = new T.Path(); c.absarc(x, -z, 0.14, 0, Math.PI * 2, true); holes.push(c); }));
    b.add(K.mesh(T, K.slab(T, L, Wd, PCB, 0.35, 0.03, holes), M.pcb, "body"));
    hx.forEach((x) => hz.forEach((z) => {                      // metal pads around the holes
      const ring = new T.RingGeometry(0.16, 0.32, 20);
      ring.rotateX(-Math.PI / 2);
      b.add(K.mesh(T, ring, M.chrome, "body", x, top + 0.004, z));
    }));
    // GPIO header: a black base strip with 2 x 20 pins along the back edge
    const gx0 = -L / 2 + 0.75, pitch = 0.254, gz = -Wd / 2 + 0.35;
    b.add(K.mesh(T, new T.BoxGeometry(20 * pitch + 0.05, 0.25, 0.52), M.chip, "pins", gx0 + 9.5 * pitch, top + 0.125, gz));
    const pins = [];
    for (let i = 0; i < 20; i++) for (let r = 0; r < 2; r++) pins.push([gx0 + i * pitch, top + 0.25 + 0.3, gz - 0.127 + r * pitch]);
    b.add(K.instances(T, new T.BoxGeometry(0.065, 0.6, 0.065), M.chrome, "pins", pins));
    // right edge: two stacked USB blocks and the Ethernet jack (metal, overhanging the board a little)
    const port = (w, h, d, x, z, name) => b.add(K.mesh(T, new T.BoxGeometry(w, h, d), M.chrome, name || "ports", x, top + h / 2, z));
    port(1.75, 1.55, 1.35, L / 2 - 0.7, -1.95);
    port(1.75, 1.55, 1.35, L / 2 - 0.7, -0.35);
    port(2.1, 1.35, 1.6, L / 2 - 0.85, 1.75);
    // the openings of those ports (dark insets on the outer faces)
    const slot = (h, d, y, z) => b.add(K.mesh(T, new T.BoxGeometry(0.06, h, d), M.lens, "ports", L / 2 + 0.18, top + y, z));
    [[-1.95], [-0.35]].forEach(([z]) => { slot(0.32, 1.0, 0.45, z); slot(0.32, 1.0, 1.1, z); });
    slot(0.9, 1.15, 0.62, 1.75);
    // front edge: HDMI, micro USB, audio jack
    port(1.5, 0.62, 1.15, -1.0, Wd / 2 - 0.45);
    port(0.8, 0.32, 0.55, -L / 2 + 1.05, Wd / 2 - 0.2);
    b.add(K.mesh(T, new T.BoxGeometry(0.7, 0.55, 1.2), M.chip, "ports", 1.25, top + 0.275, Wd / 2 - 0.55));
    const jack = new T.CylinderGeometry(0.3, 0.3, 0.3, 20);
    jack.rotateX(Math.PI / 2);
    b.add(K.mesh(T, jack, M.chip, "ports", 1.25, top + 0.3, Wd / 2 + 0.15));
    // chips and ribbon connectors
    b.add(K.mesh(T, new T.BoxGeometry(1.4, 0.12, 1.4), M.chip, "chips", -1.0, top + 0.06, 0.0));       // processor
    b.add(K.mesh(T, new T.BoxGeometry(0.9, 0.1, 0.9), M.chip, "chips", 1.55, top + 0.05, 0.55));       // network chip
    b.add(K.mesh(T, new T.BoxGeometry(0.4, 0.45, 2.2), M.chip, "chips", -L / 2 + 0.55, top + 0.225, -0.3));   // display connector
    b.add(K.mesh(T, new T.BoxGeometry(2.2, 0.45, 0.4), M.chip, "chips", 0.2, top + 0.225, 1.25));          // camera connector
    // PWR / ACT LEDs at the front-left corner: the light that takes the risk colour
    b.add(K.mesh(T, new T.BoxGeometry(0.16, 0.09, 0.26), M.status, "status", -L / 2 + 0.3, top + 0.045, 1.25));
    b.add(K.mesh(T, new T.BoxGeometry(0.16, 0.09, 0.26), M.status, "status", -L / 2 + 0.3, top + 0.045, 1.65));
    // prop it up: the front edge rests on the ground, the board tilted towards the viewer
    const tilt = new T.Group();
    tilt.rotation.x = 0.62;
    b.position.set(0, 0, 0);
    tilt.add(b);
    g.add(tilt);
    return K.finish(T, g);
  };
})();

/* computer-macbook: a thin open laptop (reference: a MacBook Air photo, 3/4 front view; no logo).
 * Parts: deck (body), keyboard well + keycaps (keys), trackpad (pad), hinge, lid (body), black front glass (bezel)
 * with the display (screen) and the camera notch, and a small LED on the front lip (status).
 * Built in centimetres (deck 30.4 x 21.5 cm), then scaled to 1 unit tall by K.finish.
 */
(function () {
  "use strict";
  const K = window.SAFEHOUSE_MODEL_KIT;
  window.SAFEHOUSE_MODEL_BUILDERS["computer-macbook"] = function (T) {
    const M = K.materials(T), g = new T.Group();
    const W = 30.4, D = 21.5, H = 1.13, R = 1.3;               // deck: width, depth, thickness, corner radius
    // deck (one uniform slab, slightly rounded edges)
    g.add(K.mesh(T, K.slab(T, W, D, H, R, 0.28), M.shell, "body"));
    // keyboard well: a dark recessed plate across the back two thirds, with the key grid on it
    const wellW = 27.2, wellD = 11.4, wellZ = -D / 2 + 1.6 + wellD / 2;
    g.add(K.mesh(T, K.slab(T, wellW, wellD, 0.04, 0.5, 0), M.deep, "keyboard", 0, H - 0.02, wellZ));
    const pitch = 1.9, cap = 1.62, keys = [];
    const top = -D / 2 + 1.6 + 0.55;                             // z of the first (function) row
    for (let c = 0; c < 14; c++) keys.push([-(13 * pitch) / 2 + c * pitch, H + 0.07, top + 0.2, 1, 0.55]);   // function row: half height
    for (let r = 0; r < 4; r++) for (let c = 0; c < 14; c++) keys.push([-(13 * pitch) / 2 + c * pitch, H + 0.07, top + 1.55 + r * pitch, 1, 1]);
    const lastZ = top + 1.55 + 4 * pitch;                        // bottom row: 4 small keys each side of the space bar
    [-6.5, -5.5, -4.5, -3.5, 3.5, 4.5, 5.5, 6.5].forEach((c) => keys.push([c * pitch, H + 0.07, lastZ, 1, 1]));
    g.add(K.instances(T, new T.BoxGeometry(cap, 0.14, cap), M.keys, "keys", keys));
    g.add(K.mesh(T, new T.BoxGeometry(5.3 * pitch, 0.14, cap), M.keys, "keys", 0, H + 0.07, lastZ));          // space bar
    // trackpad: a large flush rounded rectangle centred in front of the keyboard
    g.add(K.mesh(T, K.slab(T, 12.4, 7.2, 0.05, 0.6, 0), M.pad, "pad", 0, H - 0.01, D / 2 - 1.3 - 3.6));
    // status LED: a short light strip on the front lip, right of centre
    g.add(K.mesh(T, new T.BoxGeometry(2.4, 0.26, 0.1), M.status, "status", 7.5, H * 0.5, D / 2 + 0.02));
    // hinge barrel along the rear edge
    const hinge = new T.CylinderGeometry(0.52, 0.52, W - 6, 20);
    hinge.rotateZ(Math.PI / 2);
    g.add(K.mesh(T, hinge, M.shellDark, "hinge", 0, H + 0.05, -D / 2 + 0.55));
    // lid: pivots on the hinge, open about 105 degrees from the deck (15 degrees past vertical)
    const lidH = 20.9, lidT = 0.55, lid = new T.Group();
    lid.name = "lid";
    lid.position.set(0, H + 0.05, -D / 2 + 0.55);
    lid.rotation.x = -15 * Math.PI / 180;
    const shell = K.mesh(T, K.panel(T, W, lidH, lidT, R, 0.18), M.shell, "body", 0, lidH / 2, -lidT / 2);
    const glass = K.mesh(T, K.panel(T, W - 0.5, lidH - 0.5, 0.06, R - 0.2, 0), M.bezel, "bezel", 0, lidH / 2, 0.02);
    const scrH = lidH - 2.3, scrY = lidH / 2 - 0.35;              // the chin under the display is a little taller
    const screen = K.mesh(T, new T.PlaneGeometry(W - 1.6, scrH), M.screen, "screen", 0, scrY, 0.06);
    const notch = K.mesh(T, K.panel(T, 3.2, 0.9, 0.02, 0.3, 0), M.bezel, "notch", 0, scrY + scrH / 2 - 0.4, 0.075);
    lid.add(shell, glass, screen, notch);
    g.add(lid);
    return K.finish(T, g);
  };
})();

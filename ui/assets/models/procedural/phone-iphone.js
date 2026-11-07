/* phone-iphone: a smartphone seen from the back (reference: an iPhone photo, back view; no logo, app colours).
 * Parts: metal frame (body), frosted back glass (glass), the raised camera plateau across the top (body) with three
 * lenses in a triangle (lens), the LiDAR dot (lens) and the flash, which is the light that takes the risk colour
 * (status). The display (screen) is on the other side. The back faces +Z, so the cameras are what you see.
 * Built in centimetres (7.15 x 14.65 cm), standing on its bottom edge, then scaled to 1 unit tall.
 */
(function () {
  "use strict";
  const K = window.SAFEHOUSE_MODEL_KIT;
  window.SAFEHOUSE_MODEL_BUILDERS["phone-iphone"] = function (T) {
    const M = K.materials(T), g = new T.Group(), p = new T.Group();
    const W = 7.15, H = 14.65, TH = 0.83, R = 1.15;
    p.add(K.mesh(T, K.panel(T, W, H, TH, R, 0.22), M.frame, "body"));
    p.add(K.mesh(T, K.panel(T, W - 0.32, H - 0.32, 0.04, R - 0.15, 0), M.shell, "glass", 0, 0, TH / 2));
    // the lower back: a lighter frosted glass panel inset under the camera plateau, with an even border around it
    const lowTop = H / 2 - 0.32 - 4.5 - 0.35, lowBot = -H / 2 + 0.45;
    p.add(K.mesh(T, K.panel(T, W - 0.95, lowTop - lowBot, 0.03, 0.85, 0), M.glassBack, "glass", 0, (lowTop + lowBot) / 2, TH / 2 + 0.03));
    // the other side: the display behind a thin black border
    const front = K.mesh(T, K.panel(T, W - 0.3, H - 0.3, 0.03, R - 0.15, 0), M.bezel, "bezel", 0, 0, -TH / 2 - 0.005);
    const screen = K.mesh(T, new T.PlaneGeometry(W - 0.75, H - 0.75), M.screen, "screen", 0, 0, -TH / 2 - 0.025);
    screen.rotation.y = Math.PI;
    p.add(front, screen);
    // camera plateau: a raised rounded block across the top of the back
    const PW = 6.5, PH = 4.5, PY = H / 2 - 0.32 - PH / 2, PZ = TH / 2 + 0.04;
    p.add(K.mesh(T, K.panel(T, PW, PH, 0.16, 1.0, 0.05), M.shell, "body", 0, PY, PZ + 0.08));
    const top = PZ + 0.16;
    const lens = (x, y) => {
      p.add(K.mesh(T, K.disc(T, 0.82, 0.3, 32), M.frame, "lens", x, PY + y, top + 0.15));
      p.add(K.mesh(T, K.disc(T, 0.56, 0.32, 32), M.lens, "lens", x, PY + y, top + 0.17));
    };
    lens(-1.55, 1.05); lens(-1.55, -1.05); lens(0.5, 0);           // three lenses in a triangle
    p.add(K.mesh(T, K.disc(T, 0.34, 0.08, 24), M.status, "status", 2.15, PY + 1.25, top + 0.04));   // flash
    p.add(K.mesh(T, K.disc(T, 0.3, 0.08, 24), M.lens, "lens", 2.15, PY - 1.2, top + 0.04));         // LiDAR
    // stand on the bottom edge, leaning back a little
    p.position.set(0, H / 2, 0);
    const lean = new T.Group();
    lean.rotation.x = -0.12;
    lean.add(p);
    g.add(lean);
    return K.finish(T, g);
  };
})();

/* phone-android: the standard model for every phone that is not an iPhone (no reference photo: a generic modern
 * Android back, built so it can never be mistaken for the iPhone model). The look that says "Android": a black camera
 * bar across the full width of the back with two lenses side by side, instead of the iPhone's square plateau.
 * Parts: frame (body), back glass (glass), camera bar (body), lenses (lens), flash = status light (status), and the
 * display with a punch-hole camera on the other side (screen). Built in centimetres (7.3 x 15.2 cm), scaled to 1 unit.
 */
(function () {
  "use strict";
  const K = window.SAFEHOUSE_MODEL_KIT;
  window.SAFEHOUSE_MODEL_BUILDERS["phone-android"] = function (T) {
    const M = K.materials(T), g = new T.Group(), p = new T.Group();
    const W = 7.3, H = 15.2, TH = 0.86, R = 1.3;
    p.add(K.mesh(T, K.panel(T, W, H, TH, R, 0.26), M.frame, "body"));
    p.add(K.mesh(T, K.panel(T, W - 0.3, H - 0.3, 0.04, R - 0.15, 0), M.glassBack, "glass", 0, 0, TH / 2));
    const front = K.mesh(T, K.panel(T, W - 0.28, H - 0.28, 0.03, R - 0.15, 0), M.bezel, "bezel", 0, 0, -TH / 2 - 0.005);
    const screen = K.mesh(T, new T.PlaneGeometry(W - 0.6, H - 0.6), M.screen, "screen", 0, 0, -TH / 2 - 0.025);
    screen.rotation.y = Math.PI;
    const hole = K.mesh(T, K.disc(T, 0.16, 0.02, 16), M.lens, "lens", 0, H / 2 - 0.8, -TH / 2 - 0.035);
    p.add(front, screen, hole);
    // camera bar: full width, rounded ends, standing proud of the back
    const BY = H / 2 - 3.3, BZ = TH / 2 + 0.2;
    p.add(K.mesh(T, K.panel(T, W + 0.02, 2.3, 0.4, 1.15, 0.12), M.deep, "body", 0, BY, BZ));
    const lens = (x, r) => {
      p.add(K.mesh(T, K.disc(T, r + 0.14, 0.06, 32), M.frame, "lens", x, BY, BZ + 0.21));
      p.add(K.mesh(T, K.disc(T, r, 0.08, 32), M.lens, "lens", x, BY, BZ + 0.23));
    };
    lens(-2.15, 0.62); lens(-0.55, 0.5);
    p.add(K.mesh(T, K.disc(T, 0.26, 0.06, 24), M.status, "status", 1.55, BY, BZ + 0.22));   // flash
    p.add(K.mesh(T, K.disc(T, 0.18, 0.06, 16), M.lens, "lens", 2.35, BY, BZ + 0.22));       // sensor
    p.position.set(0, H / 2, 0);
    const lean = new T.Group();
    lean.rotation.x = -0.12;
    lean.add(p);
    g.add(lean);
    return K.finish(T, g);
  };
})();

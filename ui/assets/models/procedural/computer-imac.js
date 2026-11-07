/* computer-imac: an all-in-one desktop (reference: an iMac photo, front and back; no logo).
 * Parts: display shell with the aluminium chin (body), edge-to-edge black front glass (bezel) with the display
 * (screen), the rounded back (body), the bent L-shaped stand: foot, curve and neck (stand), and a small light slot in
 * the middle of the chin (status). Built in centimetres (display 65 x 45 cm), then scaled to 1 unit tall.
 */
(function () {
  "use strict";
  const K = window.SAFEHOUSE_MODEL_KIT;
  window.SAFEHOUSE_MODEL_BUILDERS["computer-imac"] = function (T) {
    const M = K.materials(T), g = new T.Group();
    const W = 65, H = 45, TH = 0.7, CHIN = 8.4, LIFT = 10.5;    // display width, height, edge thickness, chin, height above the desk
    // stand: a foot plate, a rounded bend at the back and the neck leaning forward to the back of the display
    g.add(K.mesh(T, K.slab(T, 20, 19, 0.6, 2.2, 0.15), M.chrome, "stand", 0, 0, -3.6));
    const bend = new T.CylinderGeometry(1.6, 1.6, 20, 24, 1, false, Math.PI, Math.PI / 2);
    bend.rotateZ(Math.PI / 2);
    g.add(K.mesh(T, bend, M.chrome, "stand", 0, 1.6, -11.5));
    const neck = K.mesh(T, K.panel(T, 20, 25.6, 0.7, 0.3, 0.12), M.chrome, "stand", 0, 13.6, -9.6);
    neck.rotation.x = 0.27;
    g.add(neck);
    // display: tilted back a little, pivoting on its bottom edge
    const disp = new T.Group();
    disp.name = "display";
    disp.position.set(0, LIFT, 0);
    disp.rotation.x = -0.07;
    disp.add(K.mesh(T, K.panel(T, W, H, TH, 1.6, 0.2), M.shell, "body", 0, H / 2, -TH / 2));
    // the rounded back: a softer, smaller panel behind the middle of the display
    disp.add(K.mesh(T, K.panel(T, 44, 30, 4.2, 6, 1.6), M.shell, "body", 0, H / 2 + 1.5, -TH - 1.4));
    // front: black glass over everything above the chin, the display inside it
    const glassH = H - CHIN;
    disp.add(K.mesh(T, K.panel(T, W - 0.3, glassH - 0.15, 0.06, 1.5, 0), M.bezel, "bezel", 0, CHIN + glassH / 2, 0.02));
    disp.add(K.mesh(T, new T.PlaneGeometry(W - 4.2, glassH - 4.0), M.screen, "screen", 0, CHIN + glassH / 2 + 0.2, 0.06));
    // status: a short light slot in the middle of the chin, where the logo would be
    disp.add(K.mesh(T, new T.BoxGeometry(3.2, 0.5, 0.1), M.status, "status", 0, CHIN / 2, 0.03));
    g.add(disp);
    return K.finish(T, g);
  };
})();

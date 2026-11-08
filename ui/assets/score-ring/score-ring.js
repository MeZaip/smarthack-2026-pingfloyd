/* ScoreRing - the home score as a futuristic dial (inline SVG + CSS, no chart library, works offline and from file://).
 *
 *   ScoreRing.create(40, { of: "din 100", aria: "40 din 100, Risc înalt", key: "scan.xml" })  -> element
 *   ScoreRing.pending("din 100")                                                            -> the same dial, empty, "–"
 *
 * Parts: a 270-degree track made of short segments (like a digital rev counter; the gap is at the bottom), the segments
 * up to the score lit in the colour of the state, a thicker glowing progress line over them, a bright end cap at the
 * tip of the line, a soft light behind the dial in the same colour, and the number in Orbitron (a technical font kept
 * in this folder) with "din 100" under it. Three states, from the score: safe (80+, neon green / cyan), warning
 * (50-79, neon orange), danger (under 50, neon red); or pass { state }.
 * When the dial is put on the page it counts from 0 to the score while the line draws itself, once per `key` (a page
 * that re-renders does not replay it); with prefers-reduced-motion it shows the score at once.
 */
(function () {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";
  const C = 110, R = 84, START = 135, SWEEP = 270, SEGMENTS = 46, DURATION = 1500;
  const played = new Set();
  let uid = 0;

  const svg = (tag, attrs) => { const el = document.createElementNS(NS, tag); for (const k in attrs) el.setAttribute(k, attrs[k]); return el; };
  const point = (deg, r) => { const a = (deg * Math.PI) / 180; return [C + Math.cos(a) * r, C + Math.sin(a) * r]; };
  const stateOf = (score) => (score >= 80 ? "safe" : score >= 50 ? "warning" : "danger");
  const reduced = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  // the arc of the dial (pathLength 100: dash lengths are percentages of the sweep)
  const ARC = (() => { const [x1, y1] = point(START, R), [x2, y2] = point(START + SWEEP, R);
    return `M${x1.toFixed(2)},${y1.toFixed(2)} A${R},${R} 0 1 1 ${x2.toFixed(2)},${y2.toFixed(2)}`; })();
  const SEG = 100 / SEGMENTS, DASH = SEG * 0.42, GAP = SEG - DASH;
  // the segments up to `pct` only: n dashes, then a gap longer than the arc
  const litDashes = (pct) => { const n = Math.round((pct / 100) * SEGMENTS); return n ? `${Array(n).fill(`${DASH.toFixed(3)} ${GAP.toFixed(3)}`).join(" ")} 0 200` : "0 200"; };

  function build(score, opts) {
    const id = "sr" + ++uid, empty = score == null;
    const state = opts.state || (empty ? "none" : stateOf(score));
    const el = document.createElement("div");
    el.className = "score-ring is-" + state;
    if (opts.size) el.style.setProperty("--sr-size", opts.size + "px");
    el.setAttribute("role", "img");
    el.setAttribute("aria-label", opts.aria || (empty ? "–" : `${score} ${opts.of || "/ 100"}`));
    const s = svg("svg", { class: "sr-svg", viewBox: "0 0 220 220", "aria-hidden": "true" });
    const defs = svg("defs", {});
    // the line goes from light at its start to full neon at its tip, whatever the score (the end follows the tip)
    const [sx, sy] = point(START, R);
    const grad = svg("linearGradient", { id: id + "-g", gradientUnits: "userSpaceOnUse", x1: sx.toFixed(1), y1: sy.toFixed(1), x2: "200", y2: "120" });
    grad.append(svg("stop", { offset: "0", class: "sr-stop-a" }), svg("stop", { offset: "1", class: "sr-stop-b" }));
    const face = svg("radialGradient", { id: id + "-f", cx: "50%", cy: "42%", r: "60%" });
    face.append(svg("stop", { offset: "0", class: "sr-face-a" }), svg("stop", { offset: "1", class: "sr-face-b" }));
    const glow = svg("filter", { id: id + "-glow", x: "-50%", y: "-50%", width: "200%", height: "200%" });
    const merge = svg("feMerge", {});
    merge.append(svg("feMergeNode", { in: "b" }), svg("feMergeNode", { in: "SourceGraphic" }));
    glow.append(svg("feGaussianBlur", { stdDeviation: "4.5", result: "b" }), merge);
    defs.append(grad, face, glow);
    s.append(defs);
    s.append(svg("circle", { class: "sr-face", cx: C, cy: C, r: 70, fill: `url(#${id}-f)` }));
    s.append(svg("path", { class: "sr-track", d: ARC, pathLength: "100", "stroke-dasharray": `${DASH.toFixed(3)} ${GAP.toFixed(3)}` }));
    const lit = svg("path", { class: "sr-lit", d: ARC, pathLength: "100", "stroke-dasharray": "0 200" });
    const line = svg("path", { class: "sr-line", d: ARC, pathLength: "100", stroke: `url(#${id}-g)`, filter: `url(#${id}-glow)`, "stroke-dasharray": "0 200" });
    const cap = svg("g", { class: "sr-cap" });
    cap.append(svg("circle", { class: "sr-cap-glow", r: 13, filter: `url(#${id}-glow)` }), svg("circle", { class: "sr-cap-dot", r: 7.5 }));
    s.append(lit, line, cap);
    const num = document.createElement("div");
    num.className = "sr-num";
    num.textContent = empty ? "–" : "0";
    const of = document.createElement("div");
    of.className = "sr-of";
    of.textContent = opts.of || "/ 100";
    const center = document.createElement("div");
    center.className = "sr-center";
    center.setAttribute("aria-hidden", "true");
    center.append(num, of);
    el.append(s, center);

    // draw the dial at `v` (0-100): progress line, lit segments, end cap and the number
    const draw = (v) => {
      const pct = Math.max(0, Math.min(100, v));
      line.setAttribute("stroke-dasharray", pct > 0.2 ? `${pct.toFixed(2)} 200` : "0 200");
      lit.setAttribute("stroke-dasharray", litDashes(pct));
      const [x, y] = point(START + (SWEEP * pct) / 100, R);
      cap.setAttribute("transform", `translate(${x.toFixed(2)} ${y.toFixed(2)})`);
      if (Math.hypot(x - sx, y - sy) > 1) { grad.setAttribute("x2", x.toFixed(1)); grad.setAttribute("y2", y.toFixed(1)); }
      cap.style.opacity = pct > 0.2 ? "1" : "0";
      num.textContent = String(Math.round(v));
    };
    if (empty) { cap.style.opacity = "0"; return el; }
    const key = opts.key != null ? `${opts.key}|${score}` : null;
    if (opts.animate === false || reduced() || (key && played.has(key))) { draw(score); return el; }
    if (key) played.add(key);
    draw(0);
    // start counting once the dial is on the page (the caller appends it right after create())
    let tries = 0;
    const start = () => {
      if (!el.isConnected) { if (++tries < 120) requestAnimationFrame(start); else draw(score); return; }
      const t0 = performance.now(), ease = (p) => 1 - Math.pow(1 - p, 3);
      const step = (now) => { const p = Math.min(1, (now - t0) / DURATION); draw(score * ease(p)); if (p < 1) requestAnimationFrame(step); };
      requestAnimationFrame(step);
    };
    requestAnimationFrame(start);
    return el;
  }

  window.ScoreRing = {
    create: (score, opts) => build(Math.max(0, Math.min(100, Math.round(Number(score) || 0))), opts || {}),
    pending: (of) => build(null, { of }),
    stateOf,
  };
})();

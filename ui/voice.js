/*
 * SafeHouse voice for the assistant chat (voice mode, like a live voice conversation).
 * No library. Three parts:
 *  1. Speech to text: the browser's SpeechRecognition (ro-RO / en-US). On the device when the browser offers it
 *     (Chrome 139+ "processLocally"); otherwise the browser's own service turns speech into text (Chrome: Google,
 *     Safari: Apple), so the page asks once before the first use. No recognition (e.g. Firefox) = no voice mode.
 *  2. Text to speech: first the natural voice made by the team gateway (POST /api/v1/tts, which holds the key),
 *     played through an <audio> element; only when that is not available (file://, no key, offline, error) the
 *     browser's own voice, choosing the most natural one installed for the language.
 *  3. Levels for the orb: the microphone level while the user speaks (Web Audio, nothing is recorded or sent)
 *     and the answer's audio level while the assistant speaks.
 *
 * window.SafeVoice = { canSpeak, canListen, speak(text, {lang, id, natural, onstart, onend}), stop(), speakingId,
 *                      hasVoice(lang), localListening(lang), listen({...}), stopListening(keep), listening,
 *                      startMeter(), stopMeter(), level(), Orb }
 */
(function () {
  "use strict";
  const synth = window.speechSynthesis || null;
  const Rec = window.SpeechRecognition || window.webkitSpeechRecognition || null;
  const TAGS = { ro: "ro-RO", en: "en-US" };
  const tagOf = (lang) => TAGS[lang] || lang || "en-US";
  const norm = (l) => String(l || "").replace("_", "-").toLowerCase();

  // ------------------------------------------------------------------ browser voice (last resort): the most natural one
  let voices = [];
  const loadVoices = () => { if (synth) { try { voices = synth.getVoices() || []; } catch (e) { voices = []; } } };
  if (synth) {
    loadVoices();
    if (typeof synth.addEventListener === "function") synth.addEventListener("voiceschanged", loadVoices);
    else synth.onvoiceschanged = loadVoices;
  }
  const NATURAL = /(natural|neural|premium|enhanced|siri|wavenet|online)/i;
  function voiceFor(lang) {
    if (!voices.length) loadVoices();
    const tag = norm(tagOf(lang)), base = tag.slice(0, 2);
    const same = voices.filter((v) => norm(v.lang).startsWith(base));
    const score = (v) => (NATURAL.test(v.name) ? 8 : 0) + (/google/i.test(v.name) ? 4 : 0)
      + (norm(v.lang) === tag ? 2 : 0) + (v.localService ? 1 : 0) - (/compact|espeak/i.test(v.name) ? 6 : 0);
    return same.sort((a, b) => score(b) - score(a))[0] || null;
  }

  function speakable(text) {
    return String(text || "").replace(/https?:\/\/\S+/g, "").replace(/[·•→←]/g, ", ")
      .replace(/\s*[—–]\s*/g, ", ").replace(/[*_#`>]/g, "").replace(/\s+/g, " ").trim();
  }
  function chunks(text) {
    const parts = speakable(text).split(/(?<=[.!?…])\s+/);
    const out = [];
    parts.forEach((p) => {
      p = p.trim();
      if (!p) return;
      if (out.length && (out[out.length - 1] + " " + p).length <= 220) out[out.length - 1] += " " + p;
      else out.push(p);
    });
    return out;
  }

  // ------------------------------------------------------------------ audio levels (orb)
  let ctx = null, micStream = null, micAnalyser = null, outAnalyser = null, synthPulse = 0;
  const buf = new Uint8Array(256);
  function audioCtx() {
    if (!ctx) { const AC = window.AudioContext || window.webkitAudioContext; if (AC) ctx = new AC(); }
    if (ctx && ctx.state === "suspended") ctx.resume().catch(() => {});
    return ctx;
  }
  function rms(an) {
    if (!an) return 0;
    an.getByteTimeDomainData(buf);
    let sum = 0;
    for (let i = 0; i < buf.length; i++) { const x = (buf[i] - 128) / 128; sum += x * x; }
    return Math.min(1, Math.sqrt(sum / buf.length) * 4);
  }

  let speakToken = 0, audioEl = null, current = null;
  function stopAudio() {
    if (audioEl) { try { audioEl.pause(); } catch (e) { /* ignore */ } if (audioEl._url) URL.revokeObjectURL(audioEl._url); audioEl = null; }
    outAnalyser = null;
  }

  const api = {
    canSpeak: !!(synth && window.SpeechSynthesisUtterance) || typeof Audio === "function",
    canListen: !!Rec,
    speakingId: null,
    listening: false,
    usedNatural: false,                 // last answer was read by the gateway's natural voice

    hasVoice(lang) { return !!voiceFor(lang); },

    // opts.natural: async (text) => Blob|null  (the page fetches /api/v1/tts); null/failure -> browser voice.
    speak(text, opts) {
      const o = opts || {};
      const list = chunks(text);
      if (!list.length) return false;
      api.stopListening(false);
      api.stop();
      const token = ++speakToken;
      api.speakingId = o.id == null ? "speech" : o.id;
      const finish = (ok) => {
        if (token !== speakToken) return;
        api.speakingId = null; synthPulse = 0; stopAudio();
        if (o.onend) o.onend(ok);
      };
      const browserVoice = () => {
        if (token !== speakToken) return;
        api.usedNatural = false;
        if (!synth || !window.SpeechSynthesisUtterance) { finish(false); return; }
        const voice = voiceFor(o.lang);
        let i = 0;
        const next = () => {
          if (token !== speakToken) return;
          if (i >= list.length) { finish(true); return; }
          const u = new window.SpeechSynthesisUtterance(list[i++]);
          u.lang = voice ? voice.lang : tagOf(o.lang);
          if (voice) u.voice = voice;
          u.rate = 0.95; u.pitch = 1;
          u.onboundary = () => { synthPulse = 1; };          // the orb moves with the words
          u.onend = next;
          u.onerror = (e) => { if (e && (e.error === "interrupted" || e.error === "canceled")) return; finish(false); };
          synth.speak(u);
        };
        next();
      };
      if (o.onstart) o.onstart();
      if (typeof o.natural === "function") {
        Promise.resolve().then(() => o.natural(list.join(" "))).then((blob) => {
          if (token !== speakToken) return;
          if (!blob) { browserVoice(); return; }
          const url = URL.createObjectURL(blob);
          const el = new Audio(url);
          el._url = url; audioEl = el;
          try {
            const c = audioCtx();
            if (c) { const src = c.createMediaElementSource(el); outAnalyser = c.createAnalyser(); outAnalyser.fftSize = 512; src.connect(outAnalyser); outAnalyser.connect(c.destination); }
          } catch (e) { outAnalyser = null; }
          el.onended = () => finish(true);
          el.onerror = () => { if (token === speakToken) { stopAudio(); browserVoice(); } };
          api.usedNatural = true;
          el.play().catch(() => { if (token === speakToken) { stopAudio(); browserVoice(); } });
        }).catch(() => browserVoice());
      } else browserVoice();
      return true;
    },

    stop() {
      speakToken++;
      const was = api.speakingId;
      api.speakingId = null; synthPulse = 0;
      stopAudio();
      if (synth) { try { synth.cancel(); } catch (e) { /* ignore */ } }
      return was;
    },

    async localListening(lang) {
      if (!Rec || typeof Rec.available !== "function") return false;
      try {                                   // never wait more than 1.5 s (some builds never reply)
        const res = await Promise.race([Rec.available({ langs: [tagOf(lang)], processLocally: true }),
          new Promise((ok) => setTimeout(() => ok("timeout"), 1500))]);
        return res === "available";
      } catch (e) { return false; }
    },

    // One utterance. onInterim(text), onFinal(text), onError(code): "unsupported" | "not-allowed" |
    // "no-speech" | "network" | "audio-capture" | "aborted" | other.
    listen(o) {
      if (!Rec) { if (o.onError) o.onError("unsupported"); return false; }
      api.stop();
      api.stopListening(false);
      const r = new Rec();
      r.lang = tagOf(o.lang);
      r.interimResults = true;
      r.continuous = false;
      r.maxAlternatives = 1;
      if (o.local) { try { r.processLocally = true; } catch (e) { /* older browser */ } }
      let finalText = "", error = null;
      r.onresult = (e) => {
        if (r.cancelled) return;
        let interim = "";
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const res = e.results[i];
          if (res.isFinal) finalText += res[0].transcript; else interim += res[0].transcript;
        }
        synthPulse = 1;
        if (o.onInterim) o.onInterim((finalText + " " + interim).replace(/\s+/g, " ").trim());
      };
      r.onerror = (e) => { error = e.error || "error"; };
      r.onend = () => {
        if (current === r) current = null;
        api.listening = false;
        if (r.done) return;
        r.done = true;
        const text = r.cancelled ? "" : finalText.replace(/\s+/g, " ").trim();
        if (r.cancelled) { if (o.onError) o.onError("aborted"); }
        else if (text) { if (o.onFinal) o.onFinal(text); }
        else if (o.onError) o.onError(error === "aborted" ? "aborted" : error || "no-speech");
      };
      current = r;
      api.listening = true;
      try { r.start(); } catch (e) { current = null; api.listening = false; if (o.onError) o.onError("error"); return false; }
      return true;
    },

    stopListening(keep) {
      const r = current;
      if (!r) return;
      if (!keep) r.cancelled = true;
      try { if (keep) r.stop(); else r.abort(); } catch (e) { /* already stopped */ }
    },

    // Microphone level for the orb only (analysed in the page, never recorded or sent). Best effort.
    async startMeter() {
      if (micStream || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return !!micStream;
      try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
        const c = audioCtx();
        if (!c) return true;
        micAnalyser = c.createAnalyser(); micAnalyser.fftSize = 512;
        c.createMediaStreamSource(micStream).connect(micAnalyser);
        return true;
      } catch (e) { micStream = null; micAnalyser = null; return false; }
    },
    stopMeter() {
      if (micStream) micStream.getTracks().forEach((t) => t.stop());
      micStream = null; micAnalyser = null;
    },
    // 0..1: the assistant's voice while it speaks, else the microphone, else a soft pulse from the words.
    level() {
      synthPulse *= 0.9;
      if (api.speakingId != null && outAnalyser) return rms(outAnalyser);
      if (api.speakingId == null && micAnalyser && api.listening) return Math.max(rms(micAnalyser), synthPulse * 0.6);
      return synthPulse * 0.8;
    },
  };

  // ------------------------------------------------------------------ the orb: a glowing sphere with fluid waves
  // Colours by state: listening = blue/cyan, thinking = violet, speaking = emerald/teal, idle = dim blue.
  const PALETTE = {
    idle: ["#1e3a8a", "#3b82f6", "#93c5fd"],
    listening: ["#0ea5e9", "#3b82f6", "#a5f3fc"],
    thinking: ["#6d28d9", "#8b5cf6", "#ddd6fe"],
    speaking: ["#059669", "#14b8a6", "#a7f3d0"],
  };
  const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const mix = (a, b, t) => a.map((x, i) => Math.round(x + (b[i] - x) * t));
  class Orb {
    constructor(canvas) {
      this.c = canvas; this.g = canvas.getContext("2d"); this.state = "idle"; this.t = 0; this.lv = 0;
      this.col = PALETTE.idle.map(hex); this.running = false;
      this.still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }
    setState(s) { this.state = PALETTE[s] ? s : "idle"; if (this.still) { this.col = PALETTE[this.state].map(hex); this.draw(); } }
    start() { if (this.running) return; this.running = true; const loop = () => { if (!this.running || !this.c.isConnected) { this.running = false; return; } this.draw(); requestAnimationFrame(loop); }; requestAnimationFrame(loop); }
    stop() { this.running = false; }
    draw() {
      const c = this.c, g = this.g, dpr = Math.min(2, window.devicePixelRatio || 1);
      const w = c.clientWidth || 240, hgt = c.clientHeight || 240;
      if (c.width !== Math.round(w * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(hgt * dpr); }
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.clearRect(0, 0, w, hgt);
      const target = PALETTE[this.state].map(hex);
      this.col = this.col.map((cc, i) => mix(cc, target[i], 0.18));
      const raw = this.still ? 0.15 : this.state === "thinking" ? 0.25 + 0.15 * Math.sin(this.t * 3) : api.level();
      this.lv += (raw - this.lv) * 0.25;
      this.t += this.still ? 0 : 0.016 * (this.state === "thinking" ? 1.8 : 1);
      const cx = w / 2, cy = hgt / 2, R = Math.min(w, hgt) * 0.3 * (1 + this.lv * 0.18);
      const [c0, c1, c2] = this.col.map((x) => `rgb(${x[0]},${x[1]},${x[2]})`);
      const glow = g.createRadialGradient(cx, cy, R * 0.6, cx, cy, R * 1.9);       // outer glow
      glow.addColorStop(0, `rgba(${this.col[1].join(",")},${0.35 + this.lv * 0.3})`);
      glow.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = glow; g.beginPath(); g.arc(cx, cy, R * 1.9, 0, Math.PI * 2); g.fill();
      for (let layer = 0; layer < 3; layer++) {                                       // three fluid layers
        const amp = (4 + this.lv * 22) * (1 - layer * 0.25), rr = R * (1.06 - layer * 0.1), n = 64;
        g.beginPath();
        for (let i = 0; i <= n; i++) {
          const a = (i / n) * Math.PI * 2;
          const d = Math.sin(a * 3 + this.t * (1.3 + layer * 0.4)) * 0.5 + Math.sin(a * 5 - this.t * (1.1 + layer * 0.3)) * 0.35 + Math.sin(a * 2 + this.t * 0.7 + layer) * 0.4;
          const r = rr + d * amp;
          const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
          if (i) g.lineTo(x, y); else g.moveTo(x, y);
        }
        g.closePath();
        const fill = g.createRadialGradient(cx - R * 0.35, cy - R * 0.4, R * 0.1, cx, cy, rr * 1.15);
        fill.addColorStop(0, layer === 2 ? c2 : c1);
        fill.addColorStop(1, c0);
        g.globalAlpha = layer === 0 ? 0.35 : layer === 1 ? 0.55 : 0.95;
        g.fillStyle = fill; g.fill();
      }
      g.globalAlpha = 0.5;                                                            // highlight
      const hl = g.createRadialGradient(cx - R * 0.4, cy - R * 0.45, 0, cx - R * 0.4, cy - R * 0.45, R * 0.7);
      hl.addColorStop(0, "rgba(255,255,255,.55)"); hl.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = hl; g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.fill();
      g.globalAlpha = 1;
    }
  }
  api.Orb = Orb;
  window.SafeVoice = api;
})();

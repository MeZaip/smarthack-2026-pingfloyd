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
  // The most human-sounding voice installed: Premium / Enhanced / Neural / Natural first, then the calm everyday
  // system voices; never the novelty voices (macOS "Zarvox", "Bells"...) and the robotic network voices last.
  const NATURAL = /(premium|enhanced|neural|natural|îmbunătățit|imbunatatit)/i;
  const GOOD = /^(ioana|samantha|ava|allison|susan|karen|moira|tessa|serena|daniel|kate|zoe|evan|nathan|joelle|nicky|alex|microsoft (?:emma|jenny|aria|guy|alina|emil))/i;
  const NOVELTY = /(albert|bad news|bahh|bells|boing|bubbles|cellos|wobble|eddy|flo|fred|good news|grandma|grandpa|jester|junior|kathy|organ|superstar|ralph|reed|rocko|sandy|shelley|trinoids|whisper|zarvox|espeak|compact)/i;
  function voiceFor(lang) {
    if (!voices.length) loadVoices();
    const tag = norm(tagOf(lang)), base = tag.slice(0, 2);
    const same = voices.filter((v) => norm(v.lang).startsWith(base));
    const score = (v) => (NATURAL.test(v.name) ? 20 : 0) + (GOOD.test(v.name) ? 8 : 0) + (v.localService ? 3 : 0)
      + (norm(v.lang) === tag ? 2 : 0) - (/google/i.test(v.name) ? 2 : 0) - (NOVELTY.test(v.name) ? 50 : 0);
    const best = same.sort((a, b) => score(b) - score(a))[0];
    return best && score(best) > -20 ? best : null;
  }

  const RATE = 0.82;
  function speakable(text) {
    return String(text || "").replace(/https?:\/\/[^\s)]*\.[^\s)]+/g, "").replace(/\bhttps:\/\/?/gi, "HTTPS").replace(/\bhttp:\/\/?/gi, "HTTP").replace(/[·•→←]/g, ", ")
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

  // ONE audio player for the natural voice, unlocked during a tap (unlock()): Safari and phones refuse to start
  // sound later, after the answer arrived, on an element that was never played during a user gesture.
  const SILENT = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=";
  let speakToken = 0, player = null, playerUrl = null, playerAnalyser = null, current = null;
  function getPlayer() {
    if (player) return player;
    player = new Audio();
    player.preload = "auto";
    try {                                     // route through Web Audio only when it runs (else it would be silent)
      const c = audioCtx();
      if (c && c.state === "running") {
        const src = c.createMediaElementSource(player);
        playerAnalyser = c.createAnalyser(); playerAnalyser.fftSize = 512;
        src.connect(playerAnalyser); playerAnalyser.connect(c.destination);
      }
    } catch (e) { playerAnalyser = null; }
    return player;
  }
  function stopAudio() {
    if (player) { try { player.pause(); } catch (e) { /* ignore */ } }
    if (playerUrl) { URL.revokeObjectURL(playerUrl); playerUrl = null; }
    outAnalyser = null;
  }

  const api = {
    canSpeak: !!(synth && window.SpeechSynthesisUtterance) || typeof Audio === "function",
    canListen: !!Rec,
    speakingId: null,
    listening: false,
    usedNatural: false,                 // last answer was read by the gateway's natural voice
    isSafari: !window.SpeechRecognition && !!window.webkitSpeechRecognition && /^((?!chrome|chromium|android|crios|edg).)*safari/i.test(navigator.userAgent),

    hasVoice(lang) { return !!voiceFor(lang); },
    voiceName(lang) { const v = voiceFor(lang); return v ? v.name : null; },     // which browser voice reads (for help texts)

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
          u.rate = RATE; u.pitch = 1;                     // slower and calm: easier for older listeners
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
          const el = getPlayer();
          if (playerUrl) URL.revokeObjectURL(playerUrl);
          playerUrl = URL.createObjectURL(blob);
          el.src = playerUrl;
          outAnalyser = playerAnalyser;
          el.onended = () => finish(true);
          el.onerror = () => { if (token === speakToken) { stopAudio(); browserVoice(); } };
          api.usedNatural = true;
          el.play().catch(() => { if (token === speakToken) { stopAudio(); browserVoice(); } });
        }).catch(() => browserVoice());
      } else browserVoice();
      return true;
    },

    // Call from a tap/click handler: wakes up the sound so a later answer can be played (Safari, iPhone, Android).
    unlock() {
      const c = audioCtx();
      const el = getPlayer();
      if (!el._unlocked) {
        el._unlocked = true;
        try { el.src = SILENT; const p = el.play(); if (p && p.catch) p.catch(() => {}); } catch (e) { /* ignore */ }
      }
      if (synth && synth.paused) { try { synth.resume(); } catch (e) { /* ignore */ } }
      return !!c;
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
      let finalText = "", heard = "", error = null, silence = null;
      // Safari keeps listening after you stop talking and often never marks a result as final:
      // after ~1.5 s of silence we stop ourselves and use what was heard; nothing at all after 8 s = "no speech";
      // never longer than 25 s.
      const stopSoon = (ms) => { clearTimeout(silence); silence = setTimeout(() => { try { r.stop(); } catch (e) { /* ended */ } }, ms); };
      const hardStop = setTimeout(() => { try { r.stop(); } catch (e) { /* ended */ } }, 25000);
      r.onresult = (e) => {
        if (r.cancelled) return;
        let interim = "";
        finalText = "";
        for (let i = 0; i < e.results.length; i++) {
          const res = e.results[i];
          if (res.isFinal) finalText += res[0].transcript + " "; else interim += res[0].transcript + " ";
        }
        heard = (finalText + interim).replace(/\s+/g, " ").trim();
        synthPulse = 1;
        stopSoon(1500);
        if (o.onInterim) o.onInterim(heard);
      };
      r.onspeechstart = () => { synthPulse = 1; stopSoon(6000); };
      r.onerror = (e) => { error = e.error || "error"; };
      r.onend = () => {
        clearTimeout(silence); clearTimeout(hardStop);
        if (current === r) current = null;
        api.listening = false;
        if (r.done) return;
        r.done = true;
        const text = r.cancelled ? "" : (finalText.trim() ? finalText : heard).replace(/\s+/g, " ").trim();
        if (r.cancelled) { if (o.onError) o.onError("aborted"); }
        else if (text) { if (o.onFinal) o.onFinal(text); }
        else if (o.onError) o.onError(error === "aborted" ? "aborted" : error || "no-speech");
      };
      current = r;
      api.listening = true;
      try { r.start(); } catch (e) { clearTimeout(hardStop); current = null; api.listening = false; if (o.onError) o.onError("error"); return false; }
      stopSoon(8000);                                   // nobody spoke: end with "no speech" instead of waiting forever
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
      if (api.isSafari) return false;                    // Safari: the recognition needs the microphone to itself
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

  // ------------------------------------------------------------------ the shield's energy (voice mode)
  // Drawn on a canvas behind the SafeHouse shield: a soft glow plus rings of energy that ripple outwards, stronger
  // the louder the voice. Green while YOU speak, cyan-blue while SafeHouse speaks, a slow violet pulse while it
  // thinks, a faint green breath when idle. The level is also written to --lv on the button (the shield glows/grows).
  const PALETTE = {
    idle: [34, 197, 94], listening: [34, 255, 120], thinking: [139, 92, 246], speaking: [34, 211, 238],
  };
  const mix = (a, b, t) => a.map((x, i) => x + (b[i] - x) * t);
  class Orb {
    constructor(canvas, host) {
      this.c = canvas; this.host = host || canvas.parentElement; this.g = canvas.getContext("2d");
      this.state = "idle"; this.t = 0; this.lv = 0; this.col = PALETTE.idle.slice(); this.rings = []; this.spawn = 0;
      this.running = false;
      this.still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }
    setState(s) { this.state = PALETTE[s] ? s : "idle"; if (this.still) { this.col = PALETTE[this.state].slice(); this.draw(); } }
    start() { if (this.running) return; this.running = true; const loop = () => { if (!this.running || !this.c.isConnected) { this.running = false; return; } this.draw(); requestAnimationFrame(loop); }; requestAnimationFrame(loop); }
    stop() { this.running = false; }
    draw() {
      const c = this.c, g = this.g, dpr = Math.min(2, window.devicePixelRatio || 1);
      const w = c.clientWidth || 260, hgt = c.clientHeight || 260;
      if (c.width !== Math.round(w * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(hgt * dpr); }
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.clearRect(0, 0, w, hgt);
      this.col = mix(this.col, PALETTE[this.state], 0.15);
      const idle = this.state === "idle";
      const raw = this.still ? 0.2 : this.state === "thinking" ? 0.3 + 0.2 * Math.sin(this.t * 3) : idle ? 0.12 + 0.08 * Math.sin(this.t * 1.5) : api.level();
      this.lv += (raw - this.lv) * 0.3;
      this.t += this.still ? 0 : 0.016;
      if (this.host && this.host.style) this.host.style.setProperty("--lv", this.lv.toFixed(3));
      const rgb = this.col.map((x) => Math.round(x)).join(","), cx = w / 2, cy = hgt / 2, R = Math.min(w, hgt) * 0.27;
      // the glow behind the shield
      const glow = g.createRadialGradient(cx, cy, R * 0.2, cx, cy, R * (1.5 + this.lv * 0.9));
      glow.addColorStop(0, `rgba(${rgb},${0.45 + this.lv * 0.4})`);
      glow.addColorStop(0.55, `rgba(${rgb},${0.12 + this.lv * 0.2})`);
      glow.addColorStop(1, `rgba(${rgb},0)`);
      g.fillStyle = glow; g.beginPath(); g.arc(cx, cy, R * 2.2, 0, Math.PI * 2); g.fill();
      // rings of energy rippling outwards (more and brighter while someone speaks)
      if (!this.still) {
        this.spawn += 0.012 + this.lv * 0.09;
        if (this.spawn >= 1) { this.spawn = 0; this.rings.push({ r: R * 0.95, a: 0.35 + this.lv * 0.6, seed: Math.random() * 6 }); }
        this.rings = this.rings.filter((ring) => ring.a > 0.02 && ring.r < Math.min(w, hgt) * 0.5);
        this.rings.forEach((ring) => {
          ring.r += 0.6 + this.lv * 2.2; ring.a *= 0.975;
          g.beginPath();
          for (let i = 0; i <= 72; i++) {
            const a = (i / 72) * Math.PI * 2;
            const wob = Math.sin(a * 6 + this.t * 4 + ring.seed) * (1.5 + this.lv * 5);
            const x = cx + Math.cos(a) * (ring.r + wob), y = cy + Math.sin(a) * (ring.r + wob);
            if (i) g.lineTo(x, y); else g.moveTo(x, y);
          }
          g.closePath();
          g.strokeStyle = `rgba(${rgb},${ring.a})`; g.lineWidth = 1.5 + this.lv * 2.5;
          g.shadowColor = `rgba(${rgb},${ring.a})`; g.shadowBlur = 12;
          g.stroke(); g.shadowBlur = 0;
        });
      } else {
        g.strokeStyle = `rgba(${rgb},.5)`; g.lineWidth = 2; g.beginPath(); g.arc(cx, cy, R * 1.25, 0, Math.PI * 2); g.stroke();
      }
    }
  }
  api.Orb = Orb;
  window.SafeVoice = api;
})();

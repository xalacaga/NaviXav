"use strict";

/**
 * Sons de cabine en turbulence, synthétisés à la volée.
 *
 * Aucun fichier son : tout naît ici, de bruit et d'oscillateurs Web Audio.
 * Un grondement de structure suit l'intensité ressentie ; chaque secousse
 * marquée signalée par le service ajoute un coup sourd dans le plancher et,
 * selon sa force, le cliquetis des coffres à bagages et le craquement des
 * panneaux de cabine. Rien ne joue en pause, au sol ou hors turbulence.
 *
 * Comme la voix et l'ambiance radio, c'est une préférence de l'appareil.
 */
const CABIN_SOUND = (() => {
  const ENABLED_KEY = "navixav-cabin-sound-enabled";
  const VOLUME_KEY = "navixav-cabin-sound-volume";
  const DEFAULT_VOLUME = 0.6;
  // EDR auquel le grondement atteint son plein niveau (turbulence forte).
  const FULL_EDR = 0.5;
  // Sous cet EDR, la cabine est silencieuse.
  const QUIET_EDR = 0.06;
  // Une secousse de cette force (g efficace) sonne à plein.
  const FULL_JOLT_G = 0.25;
  const MAX_JOLTS_PER_UPDATE = 3;

  const read = (key) => {
    try {
      return localStorage.getItem(key);
    } catch (_error) {
      return null;
    }
  };
  const write = (key, value) => {
    try {
      localStorage.setItem(key, value);
    } catch (_error) {
      // Préférence non retenue : la session garde le réglage.
    }
  };

  let enabled = read(ENABLED_KEY) !== "0";
  const storedVolume = Number(read(VOLUME_KEY));
  let volume = read(VOLUME_KEY) !== null && Number.isFinite(storedVolume)
    ? Math.min(1, Math.max(0, storedVolume)) : DEFAULT_VOLUME;

  let context = null;
  let master = null;
  let rumble = null;
  let noise = null;
  let lastJolts = null;

  const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
  const between = (low, high) => low + Math.random() * (high - low);

  function noiseBuffer(ctx) {
    const length = ctx.sampleRate * 2;
    const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < length; i += 1) data[i] = Math.random() * 2 - 1;
    return buffer;
  }

  /** Contexte audio créé au premier besoin ; WebView2 le suspend sans geste. */
  function ensure() {
    if (context) return context;
    const Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) return null;
    context = new Audio();
    noise = noiseBuffer(context);
    master = context.createGain();
    master.gain.value = volume;
    master.connect(context.destination);

    // Grondement : bruit filtré très bas, avec la résonance du plancher vers
    // 60 Hz et un souffle de structure vers 400 Hz, bien plus discret.
    const source = context.createBufferSource();
    source.buffer = noise;
    source.loop = true;
    const low = context.createBiquadFilter();
    low.type = "lowpass";
    low.frequency.value = 150;
    const floor = context.createBiquadFilter();
    floor.type = "peaking";
    floor.frequency.value = 60;
    floor.Q.value = 1.2;
    floor.gain.value = 9;
    const hiss = context.createBiquadFilter();
    hiss.type = "bandpass";
    hiss.frequency.value = 420;
    hiss.Q.value = 0.8;
    const hissGain = context.createGain();
    hissGain.gain.value = 0.06;
    rumble = context.createGain();
    rumble.gain.value = 0;
    source.connect(low).connect(floor).connect(rumble);
    source.connect(hiss).connect(hissGain).connect(rumble);
    rumble.connect(master);
    source.start();
    return context;
  }

  function resume() {
    if (context && context.state === "suspended") context.resume().catch(() => {});
  }
  // La lecture n'est permise qu'après une interaction avec la fenêtre.
  ["pointerdown", "keydown"].forEach((name) => {
    document.addEventListener(name, resume, { passive: true });
  });

  function burst(at, duration, filterType, frequency, q, gain) {
    const source = context.createBufferSource();
    source.buffer = noise;
    const filter = context.createBiquadFilter();
    filter.type = filterType;
    filter.frequency.value = frequency;
    filter.Q.value = q;
    const envelope = context.createGain();
    envelope.gain.setValueAtTime(0.0001, at);
    envelope.gain.exponentialRampToValueAtTime(gain, at + 0.004);
    envelope.gain.exponentialRampToValueAtTime(0.0001, at + duration);
    source.connect(filter).connect(envelope).connect(master);
    source.start(at, Math.random() * 1.5, duration + 0.05);
  }

  /** Coup sourd dans le plancher : sinus grave qui retombe, et son souffle. */
  function thump(at, strength) {
    const oscillator = context.createOscillator();
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(between(52, 66), at);
    oscillator.frequency.exponentialRampToValueAtTime(32, at + 0.28);
    const envelope = context.createGain();
    envelope.gain.setValueAtTime(0.0001, at);
    envelope.gain.exponentialRampToValueAtTime(0.7 * strength, at + 0.008);
    envelope.gain.exponentialRampToValueAtTime(0.0001, at + 0.38);
    oscillator.connect(envelope).connect(master);
    oscillator.start(at);
    oscillator.stop(at + 0.42);
    burst(at, 0.22, "lowpass", 280, 0.7, 0.35 * strength);
  }

  /** Cliquetis : loquets des coffres et chariots, une grappe de petits chocs. */
  function rattle(at, strength) {
    const count = Math.round(between(4, 6 + 6 * strength));
    let time = at + between(0.02, 0.08);
    for (let i = 0; i < count; i += 1) {
      const fade = 1 - i / (count + 1);
      burst(time, between(0.012, 0.03), "bandpass", between(2200, 4600), 5,
        0.12 * strength * fade);
      time += between(0.025, 0.065);
    }
  }

  /** Craquement : panneau de cabine qui travaille, grave et nasillard. */
  function creak(at, strength) {
    const duration = between(0.25, 0.55);
    const oscillator = context.createOscillator();
    oscillator.type = "sawtooth";
    oscillator.frequency.setValueAtTime(between(90, 150), at);
    oscillator.frequency.linearRampToValueAtTime(between(70, 190), at + duration);
    const filter = context.createBiquadFilter();
    filter.type = "bandpass";
    filter.Q.value = 6;
    filter.frequency.setValueAtTime(between(650, 900), at);
    filter.frequency.linearRampToValueAtTime(between(900, 1300), at + duration);
    const envelope = context.createGain();
    envelope.gain.setValueAtTime(0.0001, at);
    envelope.gain.exponentialRampToValueAtTime(0.06 * strength, at + 0.05);
    envelope.gain.exponentialRampToValueAtTime(0.0001, at + duration);
    oscillator.connect(filter).connect(envelope).connect(master);
    oscillator.start(at);
    oscillator.stop(at + duration + 0.05);
  }

  function jolt(at, strength) {
    thump(at, strength);
    if (Math.random() < 0.35 + 0.55 * strength) rattle(at, strength);
    if (Math.random() < 0.1 + 0.4 * strength) creak(at + between(0.05, 0.2), strength);
  }

  function silence() {
    if (rumble && context) rumble.gain.setTargetAtTime(0, context.currentTime, 0.4);
  }

  /** Accorde la cabine au dernier état relevé du service de turbulence. */
  function update(status) {
    const active = enabled && status?.enabled && status.state === "active";
    const edr = Number(status?.felt_edr) || 0;
    const jolts = Number(status?.jolts);
    if (!active || edr < QUIET_EDR) {
      silence();
      lastJolts = Number.isFinite(jolts) ? jolts : null;
      return;
    }
    const ctx = ensure();
    if (!ctx) return;
    resume();
    const level = clamp((edr - QUIET_EDR) / (FULL_EDR - QUIET_EDR), 0, 1);
    rumble.gain.setTargetAtTime(0.55 * level ** 1.2, ctx.currentTime, 0.8);
    if (Number.isFinite(jolts) && lastJolts !== null && jolts > lastJolts) {
      const strength = clamp((Number(status.jolt_g) || 0) / FULL_JOLT_G, 0.2, 1);
      const count = Math.min(MAX_JOLTS_PER_UPDATE, jolts - lastJolts);
      for (let i = 0; i < count; i += 1) {
        jolt(ctx.currentTime + 0.02 + i * between(0.06, 0.14), strength);
      }
    }
    lastJolts = Number.isFinite(jolts) ? jolts : lastJolts;
  }

  return {
    enabled: () => enabled,
    volume: () => volume,
    setEnabled(value) {
      enabled = Boolean(value);
      write(ENABLED_KEY, enabled ? "1" : "0");
      if (!enabled) silence();
    },
    setVolume(value) {
      volume = clamp(Number(value) || 0, 0, 1);
      write(VOLUME_KEY, String(volume));
      if (master && context) master.gain.setTargetAtTime(volume, context.currentTime, 0.05);
    },
    update,
    stop: silence,
  };
})();

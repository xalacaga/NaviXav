"use strict";

/**
 * Ambiance radio ATC.
 *
 * Des échanges complets — un message et sa collation — générés une fois pour
 * toutes (scripts/generate_chatter_bank.py) et joués en fond selon la phase
 * du vol : le sol au roulage, la tour au décollage et en courte finale,
 * l'approche sous le FL100, le centre en route. C'est un décor sonore, pas un
 * contrôleur : rien de ce qui est dit ne concerne l'avion du pilote.
 *
 * L'ambiance se tait pendant une annonce NaviXav et reprend après. Elle ne
 * joue qu'avec un avion en vol ou au roulage, jamais en pause ni pendant une
 * relecture. Comme la voix, c'est une préférence de l'appareil.
 */
const CHATTER = (() => {
  const ENABLED_KEY = "navixav-chatter-enabled";
  const VOLUME_KEY = "navixav-chatter-volume";
  const ROOT = "/static/chatter";
  const DEFAULT_VOLUME = 0.35;
  // Silence entre deux échanges, en secondes : la tour et le sol parlent plus
  // que le centre, où les messages sont rares.
  const GAPS_S = {
    ground: [6, 22],
    tower: [5, 18],
    approach: [6, 20],
    center: [14, 45],
  };
  // Un échange ne revient pas avant que ceux-ci aient été joués.
  const RECENT_LIMIT = 15;
  const VOICE_RETRY_MS = 2500;
  // Sous ces hauteurs, l'avion parle à la tour ; sous le FL100, à l'approche.
  const TOWER_AGL_FT = 2000;
  const APPROACH_ALTITUDE_FT = 10000;

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

  let enabled = read(ENABLED_KEY) === "1";
  const storedVolume = Number(read(VOLUME_KEY));
  let volume = Number.isFinite(storedVolume) && read(VOLUME_KEY) !== null
    ? Math.min(1, Math.max(0, storedVolume)) : DEFAULT_VOLUME;
  let manifest = null;
  let position = null;
  let timer = null;
  let current = null;
  let recent = [];

  /** Position radio écoutée pour cette phase, ou null : l'ambiance se tait. */
  function positionFor(phaseKey, aircraft) {
    if (!aircraft || aircraft.paused) return null;
    const agl = Number(aircraft.height_above_ground_ft);
    const altitude = Number(aircraft.altitude_ft);
    const low = Number.isFinite(altitude) && altitude < APPROACH_ALTITUDE_FT;
    switch (phaseKey) {
      case "phase_taxi_out":
      case "phase_taxi_in":
        return "ground";
      case "phase_takeoff":
      case "phase_landing":
        return "tower";
      case "phase_approach":
        return Number.isFinite(agl) && agl < TOWER_AGL_FT ? "tower" : "approach";
      case "phase_climb":
        if (Number.isFinite(agl) && agl < TOWER_AGL_FT) return "tower";
        return low ? "approach" : "center";
      case "phase_descent":
        return low ? "approach" : "center";
      case "phase_cruise":
      case "phase_enroute":
        return "center";
      default:
        return null;
    }
  }

  function loadManifest() {
    if (manifest === null) {
      manifest = fetch(`${ROOT}/manifest.json`, { cache: "no-cache" })
        .then((response) => (response.ok ? response.json() : null))
        .catch(() => null)
        .then((value) => {
          manifest = value || { positions: {} };
          return manifest;
        });
    }
    return manifest instanceof Promise ? null : manifest;
  }

  /** Prochain échange de la position, en évitant ceux entendus récemment. */
  function pick(entries, history = recent, random = Math.random) {
    if (!entries?.length) return null;
    const fresh = entries.filter((entry) => !history.includes(entry.file));
    const pool = fresh.length ? fresh : entries;
    return pool[Math.floor(random() * pool.length)] || null;
  }

  function stopCurrent() {
    if (!current) return;
    try {
      current.pause();
    } catch (_error) {
      // Déjà arrêté.
    }
    current = null;
  }

  function clearTimer() {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  }

  function schedule(delayMs = null) {
    clearTimer();
    if (!enabled || !position) return;
    const [low, high] = GAPS_S[position] || GAPS_S.center;
    const wait = delayMs ?? (low + Math.random() * (high - low)) * 1000;
    timer = setTimeout(playNext, wait);
  }

  function playNext() {
    timer = null;
    if (!enabled || !position || current) return;
    // Une annonce NaviXav passe avant : on réessaie juste après elle.
    if (typeof VOICE !== "undefined" && VOICE.speaking?.()) {
      schedule(VOICE_RETRY_MS);
      return;
    }
    const bank = loadManifest();
    if (!bank) {
      schedule(VOICE_RETRY_MS);
      return;
    }
    const entry = pick(bank.positions?.[position]);
    if (!entry) return;
    recent = [...recent, entry.file].slice(-RECENT_LIMIT);
    const audio = new Audio(`${ROOT}/${entry.file}`);
    audio.volume = volume;
    current = audio;
    const done = () => {
      if (current !== audio) return;
      current = null;
      schedule();
    };
    audio.addEventListener("ended", done);
    audio.addEventListener("error", done);
    audio.play().catch(done);
  }

  function setPosition(next) {
    if (next === position) return;
    const wasSilent = position === null;
    position = next;
    if (!position) {
      stopCurrent();
      clearTimer();
      return;
    }
    // Changer de fréquence coupe l'échange entendu sur l'ancienne.
    stopCurrent();
    schedule(wasSilent ? 2000 + Math.random() * 4000 : null);
  }

  // Une annonce NaviXav coupe l'échange en cours ; l'ambiance reprend ensuite.
  if (typeof window !== "undefined") {
    window.addEventListener?.("navixav:voice-start", () => {
      if (!current) return;
      stopCurrent();
      schedule();
    });
  }

  return {
    enabled: () => enabled,
    setEnabled(value) {
      enabled = Boolean(value);
      write(ENABLED_KEY, enabled ? "1" : "0");
      if (enabled) {
        loadManifest();
        if (position) schedule(1500);
      } else {
        stopCurrent();
        clearTimer();
      }
    },
    volume: () => volume,
    setVolume(value) {
      volume = Math.min(1, Math.max(0, Number(value) || 0));
      write(VOLUME_KEY, String(volume));
      if (current) current.volume = volume;
    },
    /** Appelé à chaque relevé : choisit la position d'après la phase du vol. */
    update(phaseKey, aircraft, { replay = false } = {}) {
      setPosition(enabled && !replay ? positionFor(phaseKey, aircraft) : null);
    },
    // Exposés pour les tests.
    _positionFor: positionFor,
    _pick: pick,
  };
})();

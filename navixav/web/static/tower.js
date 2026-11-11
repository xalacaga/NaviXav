"use strict";

/**
 * Radio et interphone hors ligne : ce que le vol chargé entendrait.
 *
 * Chaque message est dit une fois par vol, au moment où il le serait :
 *  - la délivrance donne la clairance au poste ;
 *  - le chef de cabine annonce la fin de l'embarquement (GSX) ;
 *  - la piste signale le devis de masse et centrage ;
 *  - le sol approuve le repoussage, puis donne le roulage ;
 *  - le mécanicien au casque accompagne un repoussage natif MSFS (GSX a déjà
 *    sa propre voix d'équipage : la doubler serait faux) ;
 *  - la tour aligne, autorise le décollage avec le vent, transfère au départ ;
 *  - à l'arrivée, le sol donne le poste et le mécanicien annonce les cales.
 *
 * Tout vient du vol chargé : indicatif de l'OFP (dit avec l'indicatif radio de
 * la compagnie quand il est connu, épelé sinon), SID, piste, destination,
 * voies de roulage, cap de repoussage et poste calculés par NaviXav, vent
 * mesuré, fréquence de départ. Les contrôleurs et l'équipage parlent français
 * sur un aérodrome français quand l'interface est en français, anglais
 * ailleurs.
 *
 * Avec le moteur vocal facultatif, chaque phrase est synthétisée entière,
 * préparée à l'avance pour être prête au bon moment. Sans lui, seuls les
 * messages de la tour existent, composés de groupes pré-enregistrés : une
 * clairance avec sa SID et sa destination ne s'assemble pas en morceaux.
 *
 * L'effet est appliqué en direct : radio VHF pour les contrôleurs, interphone
 * pour la cabine et le casque. Ce n'est pas un service de contrôle : tout se
 * tait quand le trafic VATSIM ou IVAO est choisi.
 */
const TOWER = (() => {
  const ENABLED_KEY = "navixav-tower-enabled";
  const ROOT = "/static/tower";
  const HOLD_DISTANCE_M = 45;
  const PREPARE_TAKEOFF_M = 400;
  const HANDOFF_AGL_FT = 1500;
  const ALIGN_TOLERANCE_DEG = 20;
  const ENGINE_WAIT_MS = 8000;
  // La clairance se demande avion immobilisé au poste depuis un moment.
  const CLEARANCE_SETTLE_MS = 20000;
  const STAND_DISTANCE_M = 80;
  // Le sol donne le roulage un instant après la fin du repoussage.
  const TAXI_DELAY_MS = 6000;
  const RECORDED_KINDS = new Set(["lineup", "takeoff", "handoff"]);
  const INTERPHONE = new Set(["cabin_boarding", "loadsheet", "pushback_start", "pushback_complete", "chocks"]);

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
      // Préférence non retenue : la session garde le choix.
    }
  };

  let enabled = read(ENABLED_KEY) !== "0";
  let planKey = null;
  let said = {};
  let queue = [];
  let pending = null;
  let pendingSince = 0;
  let parkedSince = 0;
  let audio = null;
  let busy = false;
  let prepared = {};
  const listeners = new Set();
  const manifests = new Map();
  const buffers = new Map();

  const finite = (value) => {
    const parsed = Number(value);
    return value === null || value === undefined || value === "" || !Number.isFinite(parsed) ? null : parsed;
  };

  /* ------------------------------------------- composition enregistrée */

  const digitsOf = (text) => String(text).split("").filter((c) => /\d/.test(c)).map((c) => `digit_${c}`);

  function callsignParts(callsign, airlines) {
    const text = String(callsign || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
    if (!text) return null;
    const match = text.match(/^([A-Z]{3})([0-9][0-9A-Z]*)$/);
    const parts = [];
    let rest = text;
    if (match && airlines.includes(match[1])) {
      parts.push(`airline_${match[1]}`);
      rest = match[2];
    }
    for (const character of rest) {
      parts.push(/\d/.test(character) ? `digit_${character}` : `letter_${character}`);
    }
    return parts;
  }

  function runwayName(runway) {
    const match = String(runway || "").toUpperCase().match(/(\d{1,2})([LRC]?)/);
    if (!match || Number(match[1]) < 1 || Number(match[1]) > 36) return null;
    return `${match[1].padStart(2, "0")}${match[2]}`;
  }

  function magneticWind(directionTrue, magVar) {
    return ((Math.round((directionTrue - (finite(magVar) || 0)) / 10) * 10) % 360 + 360) % 360 || 360;
  }

  function windParts(directionTrue, speedKt, magVar, maxKnots = 60) {
    const speed = finite(speedKt);
    const direction = finite(directionTrue);
    if (speed === null || direction === null) return null;
    if (speed < 3) return ["wind_calm"];
    const knots = Math.round(speed);
    const speedParts = knots <= maxKnots ? [`knots_${knots}`] : [...digitsOf(knots), "knots"];
    return [`wind_${String(magneticWind(direction, magVar)).padStart(3, "0")}`, ...speedParts];
  }

  function frequencyParts(mhz) {
    const value = finite(mhz);
    if (value === null) return null;
    const [whole, fraction = "0"] = value.toFixed(3).split(".");
    const trimmed = fraction.replace(/0+$/, "") || "0";
    return [...digitsOf(whole), "decimal", ...digitsOf(trimmed)];
  }

  /** Message de la tour en morceaux enregistrés ; null pour les autres. */
  function compose(kind, data, bank) {
    const callsign = callsignParts(data.callsign, bank?.airlines || []);
    const runway = runwayName(data.runway);
    if (!callsign) return null;
    if (kind === "lineup") return runway ? [...callsign, ",", `rwy_${runway}_lineup`] : null;
    if (kind === "takeoff") {
      if (!runway) return null;
      const wind = windParts(data.windDirection, data.windSpeed, data.magVar, bank?.max_knots || 60);
      return [...callsign, ",", ...(wind ? [...wind, ","] : []), `rwy_${runway}_takeoff`];
    }
    if (kind === "handoff") {
      const frequency = frequencyParts(data.departureMhz);
      return frequency ? [...callsign, ",", "contact_departure", ...frequency, ",", "good_day"] : null;
    }
    return null;
  }

  /* ------------------------------------------------------- décision */

  function headingGap(a, b) {
    return Math.abs((((a - b) % 360) + 540) % 360 - 180);
  }

  /** Message de la tour à dire maintenant, ou null. */
  function due(context) {
    const { aircraft, guidance } = context;
    if (!aircraft || aircraft.paused || context.role !== "departure") return null;
    const runway = String(context.runway || "").toUpperCase();
    if (!runway) return null;
    if (aircraft.on_ground) {
      const speed = finite(aircraft.ground_speed_kt) || 0;
      const holdRunways = String(guidance?.hold_short || "").toUpperCase().split(/[^0-9A-Z]+/);
      if (!said.lineup && !said.takeoff && speed < 2 && holdRunways.includes(runway)
        && (finite(guidance?.distance_to_hold_m) ?? Infinity) <= HOLD_DISTANCE_M) {
        return "lineup";
      }
      const number = finite(runway.match(/\d{1,2}/)?.[0]);
      const heading = finite(aircraft.heading_magnetic_deg);
      if (!said.takeoff && context.onRunway && speed < 5 && number !== null && heading !== null
        && headingGap(heading, number * 10) <= ALIGN_TOLERANCE_DEG) {
        return "takeoff";
      }
      return null;
    }
    if (said.takeoff && !said.handoff && (finite(aircraft.height_above_ground_ft) || 0) >= HANDOFF_AGL_FT
      && (finite(aircraft.vertical_speed_fpm) || 0) > 0) {
      return "handoff";
    }
    return null;
  }

  /** Messages du sol et du poste, déclenchés par l'état de l'avion. */
  function dueOnGround(context, now = Date.now()) {
    const { aircraft } = context;
    if (!aircraft?.on_ground || aircraft.paused) {
      parkedSince = 0;
      return null;
    }
    const speed = finite(aircraft.ground_speed_kt) || 0;
    if (context.role === "departure") {
      const atStand = speed < 1 && (finite(context.standDistance) ?? Infinity) <= STAND_DISTANCE_M
        && !context.pushbackActive;
      parkedSince = atStand ? parkedSince || now : 0;
      if (!said.clearance && atStand && now - parkedSince >= CLEARANCE_SETTLE_MS
        && context.destination && context.runway) {
        return "clearance";
      }
      if (!said.pushback_approved && (context.gsxDeparture === "requested" || context.pushbackActive)) {
        return "pushback_approved";
      }
    }
    if (context.role === "arrival") {
      if (!said.arrival_taxi && !context.onRunway && speed >= 3 && speed <= 30) return "arrival_taxi";
      if (!said.chocks && context.docked && speed < 0.3) return "chocks";
    }
    return null;
  }

  /* ------------------------------------------------------- son */

  function audioContext() {
    if (!audio) {
      const Context = window.AudioContext || window.webkitAudioContext;
      if (!Context) return null;
      audio = new Context();
    }
    if (audio.state === "suspended") audio.resume().catch(() => {});
    return audio;
  }

  async function manifest(language) {
    if (!manifests.has(language)) {
      manifests.set(language, fetch(`${ROOT}/${language}/manifest.json`, { cache: "no-cache" })
        .then((response) => (response.ok ? response.json() : null))
        .catch(() => null));
    }
    return manifests.get(language);
  }

  function decoded(url, ctx) {
    if (!buffers.has(url)) {
      buffers.set(url, fetch(url)
        .then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          return response.arrayBuffer();
        })
        .then((data) => ctx.decodeAudioData(data))
        .catch((error) => {
          buffers.delete(url);
          throw error;
        }));
    }
    return buffers.get(url);
  }

  function noiseBuffer(ctx, seconds) {
    const buffer = ctx.createBuffer(1, Math.ceil(seconds * ctx.sampleRate), ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let index = 0; index < data.length; index += 1) data[index] = Math.random() * 2 - 1;
    return buffer;
  }

  /*
   * Deux timbres : la radio VHF des contrôleurs (bande étroite, saturation,
   * souffle, queue de squelch) et l'interphone de bord ou du casque au sol
   * (bande un peu plus large, presque sans souffle, coupure nette).
   */
  const EFFECTS = {
    radio: { low: 330, high: 3000, drive: 2.2, hiss: 0.025, click: 0.35, tail: 0.16 },
    interphone: { low: 280, high: 3600, drive: 1.4, hiss: 0.006, click: 0.08, tail: 0 },
  };

  function broadcast(ctx, schedule, profile = EFFECTS.radio) {
    const voice = ctx.createGain();
    const highpass = ctx.createBiquadFilter();
    highpass.type = "highpass";
    highpass.frequency.value = profile.low;
    const lowpass = ctx.createBiquadFilter();
    lowpass.type = "lowpass";
    lowpass.frequency.value = profile.high;
    const drive = ctx.createWaveShaper();
    const curve = new Float32Array(1024);
    for (let index = 0; index < curve.length; index += 1) {
      const x = (index / (curve.length - 1)) * 2 - 1;
      curve[index] = Math.tanh(profile.drive * x) / Math.tanh(profile.drive);
    }
    drive.curve = curve;
    const master = ctx.createGain();
    master.gain.value = 0.85 * (typeof VOICE !== "undefined" ? VOICE.volume() : 1);
    voice.connect(highpass).connect(lowpass).connect(drive).connect(master).connect(ctx.destination);

    const start = ctx.currentTime + 0.12;
    const end = schedule(voice, start);

    const hiss = ctx.createBufferSource();
    hiss.buffer = noiseBuffer(ctx, end - start + 0.5);
    const hissGain = ctx.createGain();
    hiss.connect(hissGain).connect(highpass);
    hissGain.gain.setValueAtTime(0, start - 0.06);
    hissGain.gain.linearRampToValueAtTime(profile.click, start - 0.05);
    hissGain.gain.linearRampToValueAtTime(profile.hiss, start - 0.03);
    hissGain.gain.setValueAtTime(profile.hiss, end);
    if (profile.tail) {
      hissGain.gain.linearRampToValueAtTime(profile.tail, end + 0.01);
      hissGain.gain.exponentialRampToValueAtTime(0.0001, end + 0.14);
    } else {
      hissGain.gain.linearRampToValueAtTime(0, end + 0.02);
    }
    hiss.start(start - 0.06);
    hiss.stop(end + 0.16);
    try {
      window.dispatchEvent(new CustomEvent("navixav:voice-start"));
    } catch (_error) {
      // Navigateur sans CustomEvent : le message passe quand même.
    }
  }

  async function prepareRecorded(kind, data, language) {
    const ctx = audioContext();
    const bank = await manifest(language);
    if (!ctx || !bank) return null;
    const parts = compose(kind, data, bank);
    if (!parts) return null;
    const names = parts.filter((part) => part !== ",").map((part) => bank.clips[part]);
    if (names.some((name) => !name)) return null;
    const clips = await Promise.all(names.map((name) => decoded(`${ROOT}/${language}/${name}`, ctx)));
    return { ctx, parts, clips };
  }

  async function transmitRecorded(kind, data, language) {
    const ready = await prepareRecorded(kind, data, language);
    if (!ready) return false;
    const { ctx, parts, clips } = ready;
    broadcast(ctx, (input, start) => {
      let at = start;
      let index = 0;
      for (const part of parts) {
        if (part === ",") {
          at += 0.1;
          continue;
        }
        const source = ctx.createBufferSource();
        source.buffer = clips[index];
        source.connect(input);
        source.start(at);
        at += clips[index].duration + 0.01;
        index += 1;
      }
      return at;
    });
    return true;
  }

  function transmitBuffer(buffer, kind) {
    const ctx = audioContext();
    if (!ctx || !buffer) return false;
    broadcast(ctx, (input, start) => {
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(input);
      source.start(start);
      return start + buffer.duration;
    }, INTERPHONE.has(kind) ? EFFECTS.interphone : EFFECTS.radio);
    return true;
  }

  /* ------------------------------------------------------- moteur */

  function engineRequest(kind, data, language) {
    return {
      kind,
      language,
      callsign: String(data.callsign || "").slice(0, 12),
      runway: runwayName(data.runway) || "",
      wind_direction: finite(data.windDirection),
      wind_speed: finite(data.windSpeed),
      mag_var: finite(data.magVar) || 0,
      departure_mhz: finite(data.departureMhz),
      destination: String(data.destination || "").slice(0, 40),
      sid: String(data.sid || "").slice(0, 10),
      passengers: finite(data.passengers),
      pushback_heading: finite(data.pushbackHeading),
      taxiways: (Array.isArray(data.taxiways) ? data.taxiways : []).slice(0, 12).map((name) => String(name).slice(0, 6)),
      stand: String(data.stand || "").slice(0, 24),
    };
  }

  /** Ce qui, s'il change, impose de refaire la phrase. */
  function phraseKey(request) {
    const wind = request.kind === "takeoff" && request.wind_direction !== null && request.wind_speed !== null
      ? `${magneticWind(request.wind_direction, request.mag_var)}/${request.wind_speed < 3 ? 0 : Math.round(request.wind_speed)}`
      : "";
    return JSON.stringify({ ...request, wind_direction: undefined, wind_speed: undefined, mag_var: undefined, wind });
  }

  function prepare(kind, data, language) {
    const request = engineRequest(kind, data, language);
    const key = phraseKey(request);
    if (prepared[kind]?.key === key) return prepared[kind];
    const ctx = audioContext();
    const entry = { key, ready: false, failed: false, buffer: null };
    entry.promise = fetch("/api/tower/speech", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.arrayBuffer();
      })
      .then((bytes) => ctx.decodeAudioData(bytes))
      .then((buffer) => {
        entry.buffer = buffer;
        entry.ready = true;
        return buffer;
      })
      .catch(() => {
        entry.failed = true;
        return null;
      });
    prepared[kind] = entry;
    return entry;
  }

  /** Prépare ce qui sera bientôt dit, pour que la voix soit prête à temps. */
  function prepareAhead(context, language) {
    const { aircraft, guidance } = context;
    if (!aircraft?.on_ground) return;
    if (context.role === "departure") {
      if (!said.clearance && context.destination && context.runway) prepare("clearance", context, language);
      if (!said.pushback_approved) prepare("pushback_approved", context, language);
      if (!said.taxi && context.taxiways?.length) prepare("taxi", context, language);
      if (context.runway) {
        if (!said.lineup) prepare("lineup", context, language);
        if (!said.handoff) prepare("handoff", context, language);
        const toHold = finite(guidance?.distance_to_hold_m);
        if (!said.takeoff && (context.onRunway || (toHold !== null && toHold <= PREPARE_TAKEOFF_M))) {
          prepare("takeoff", context, language);
        }
      }
    } else if (context.role === "arrival") {
      if (!said.arrival_taxi) prepare("arrival_taxi", context, language);
      if (!said.chocks) prepare("chocks", context, language);
    }
  }

  /* ------------------------------------------------------- public */

  function language(departureIcao) {
    const french = window.I18N?.getLanguage?.() === "fr";
    return french && /^LF/i.test(String(departureIcao || "")) ? "fr" : "en";
  }

  /** Dit un message : moteur si sa phrase est prête, sinon voix enregistrée. */
  async function speak(kind, context, lang, { waitForEngine }) {
    if (context.engine) {
      const entry = prepare(kind, context, lang);
      if (!entry.ready && !entry.failed && waitForEngine) return "wait";
      const buffer = entry.ready ? entry.buffer : await entry.promise;
      if (buffer && transmitBuffer(buffer, kind)) return "spoken";
    }
    if (!RECORDED_KINDS.has(kind)) return "failed";
    return (await transmitRecorded(kind, context, lang).catch(() => false)) ? "spoken" : "failed";
  }

  return {
    enabled: () => enabled,
    setEnabled(value) {
      enabled = Boolean(value);
      write(ENABLED_KEY, enabled ? "1" : "0");
      if (!enabled) {
        queue = [];
        pending = null;
        prepared = {};
        if (audio) {
          const active = audio;
          audio = null;
          active.close().catch(() => {});
        }
      }
      for (const listener of listeners) listener(enabled);
    },
    onChange(listener) { listeners.add(listener); },
    language,
    /** Lance la synthèse de l'essai avant le clic, sans bloquer l'interface. */
    prepareTest(context) {
      const lang = language(context.departureIcao);
      // Les deux chemins sont amorcés : la voix naturelle quand elle est
      // installée, et le repli enregistré qui doit rester instantané.
      prepareRecorded("takeoff", context, lang).catch(() => {});
      if (context.engine) prepare("takeoff", context, lang);
    },
    /**
     * Un événement d'escale à faire entendre : fin d'embarquement, devis de
     * masse, repoussage. Il attend son tour dans la file.
     */
    notify(type, { gsxPushback = false } = {}) {
      const kinds = {
        boarding_completed: ["cabin_boarding"],
        loadsheet_issued: ["loadsheet"],
        // GSX parle déjà pour son équipage : le casque ne double que MSFS.
        pushback_started: gsxPushback ? [] : ["pushback_start"],
        pushback_completed: gsxPushback ? ["taxi"] : ["pushback_complete", "taxi"],
      }[type] || [];
      const now = Date.now();
      for (const kind of kinds) {
        if (said[kind] || queue.some((entry) => entry.kind === kind)) continue;
        queue.push({ kind, after: kind === "taxi" ? now + TAXI_DELAY_MS : now });
      }
    },
    /** Appelé à chaque relevé : prépare la suite et dit le message dû, une fois. */
    async update(context) {
      if (context.planKey !== planKey) {
        planKey = context.planKey;
        said = {};
        queue = [];
        pending = null;
        prepared = {};
        parkedSince = 0;
      }
      if (!enabled || context.online || busy) return;
      const lang = language(context.departureIcao);
      if (context.engine) prepareAhead(context, lang);
      const now = Date.now();
      let kind = pending || due(context) || dueOnGround(context, now);
      if (!kind) {
        const next = queue.find((entry) => entry.after <= now);
        if (next) kind = next.kind;
      }
      if (!kind) return;
      if (typeof VOICE !== "undefined" && VOICE.speaking()) {
        pending = kind;
        return;
      }
      if (pending !== kind) {
        pending = kind;
        pendingSince = now;
      }
      busy = true;
      try {
        const result = await speak(kind, context, lang, { waitForEngine: now - pendingSince < ENGINE_WAIT_MS });
        if (result === "wait") return;
        pending = null;
        said[kind] = true;
        queue = queue.filter((entry) => entry.kind !== kind);
      } finally {
        busy = false;
      }
    },
    /** Fait entendre immédiatement une autorisation de décollage d'essai.
     *
     * Si la voix naturelle finit encore sa synthèse, la version enregistrée
     * part sans attendre. La requête continue en arrière-plan : le prochain
     * essai et les messages du vol profiteront du résultat mis en cache.
     */
    async test(context) {
      const lang = language(context.departureIcao);
      if (context.engine) {
        const entry = prepare("takeoff", context, lang);
        if (entry.ready && transmitBuffer(entry.buffer, "takeoff")) return true;
      }
      return transmitRecorded("takeoff", context, lang).catch(() => false);
    },
    // Exposés pour les tests : la décision ne dépend d'aucun son.
    _compose: compose,
    _callsignParts: callsignParts,
    _windParts: windParts,
    _frequencyParts: frequencyParts,
    _due: due,
    _dueOnGround: dueOnGround,
  };
})();

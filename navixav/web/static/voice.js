"use strict";

/**
 * Annonces vocales.
 *
 * NaviXav joue sa propre banque de phrases : des fichiers audio générés une
 * fois pour toutes avec des voix neuronales (scripts/generate_voice_bank.py)
 * et livrés avec l'application. Rien ne part sur le réseau et aucun moteur de
 * synthèse ne tourne pendant le vol.
 *
 * Une annonce est une suite de clés de traduction, éventuellement avec des
 * valeurs : {key: "taxi_hold_short", values: {runway: "32R"}}. Les parties
 * fixes sont des fichiers ; distance, piste et taxiway se composent de
 * nombres, de chiffres, de lettres OACI et du côté de piste. Ce que la banque
 * ne sait pas dire n'est pas annoncé : mieux vaut se taire qu'improviser avec
 * une autre voix.
 *
 * Le choix est une préférence de l'appareil, comme la langue : il reste dans le
 * stockage local, si bien qu'une tablette connectée peut parler, ou se taire,
 * indépendamment du poste.
 */
const VOICE = (() => {
  const ENABLED_KEY = "navixav-voice-enabled";
  const NAME_KEY = "navixav-voice-name";
  const BANK_ROOT = "/static/voice";
  const BANK_PREFIX = "bank:";
  // Une même phrase ne revient pas avant ce délai : une valeur qui oscille
  // autour d'un seuil ne doit pas faire bégayer la voix.
  const REPEAT_MS = 30000;
  // Au-delà de ce retard, une annonce ordinaire est abandonnée plutôt que
  // dite alors qu'elle ne correspond plus à la situation.
  const MAX_BACKLOG_S = 6;
  const SEGMENT_GAP_S = 0.05;
  const ANNOUNCEMENT_GAP_S = 0.3;

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
      // Préférence non retenue : la session en cours garde le choix.
    }
  };

  let enabled = read(ENABLED_KEY) === "1";
  // Vide : la voix par défaut de la langue. « bank:<dossier> » : une autre voix
  // NaviXav de la même langue. Un ancien nom de voix Windows vaut le défaut.
  let preferredName = read(NAME_KEY) || "";
  const recent = new Map();
  const listeners = new Set();

  const banks = new Map();
  const buffers = new Map();
  let index = null;
  let audioContext = null;
  let playing = [];
  let queueEnd = 0;

  const language = () => window.I18N?.getLanguage?.() || "fr";
  const notify = () => {
    for (const listener of listeners) {
      try {
        listener();
      } catch (_error) {
        // Un abonné défaillant ne prive pas les autres de la mise à jour.
      }
    }
  };

  /* ---------------------------------------------------------- banque */

  /** Voix NaviXav livrées, par langue, la voix par défaut en tête. */
  function loadIndex() {
    if (index === null) {
      index = fetch(`${BANK_ROOT}/index.json`, { cache: "no-cache" })
        .then((response) => (response.ok ? response.json() : {}))
        .catch(() => ({}))
        .then((value) => {
          index = value || {};
          notify();
          return index;
        });
    }
    return index instanceof Promise ? null : index;
  }

  /** Dossier de la voix retenue pour la langue affichée. */
  function selectedBankId(code = language()) {
    const available = loadIndex()?.[code] || [];
    const wanted = preferredName.startsWith(BANK_PREFIX)
      ? preferredName.slice(BANK_PREFIX.length)
      : "";
    if (wanted && available.some((entry) => entry.bank === wanted)) return wanted;
    // Sans index encore lu, la voix par défaut porte le nom de la langue.
    return available[0]?.bank || code;
  }

  function loadBank(bankId = selectedBankId()) {
    if (!banks.has(bankId)) {
      const request = fetch(`${BANK_ROOT}/${bankId}/manifest.json`, { cache: "no-cache" })
        .then((response) => (response.ok ? response.json() : null))
        .catch(() => null)
        .then((manifest) => {
          banks.set(bankId, manifest);
          notify();
          return manifest;
        });
      banks.set(bankId, request);
    }
    const bank = banks.get(bankId);
    return bank instanceof Promise ? null : bank;
  }

  /** Fichiers d'une valeur variable, ou null si la banque ne sait pas la dire. */
  function slotClips(slot, value, clips) {
    const text = String(value ?? "").toUpperCase().replace(/\s+/g, "");
    if (!text) return null;
    const ids = [];
    if (slot === "distance") {
      ids.push(`number_${Math.round(Number(value))}`);
    } else if (slot === "runway") {
      const match = text.match(/^(?:RWY)?(\d{1,2})([LRC]?)$/);
      if (!match) return null;
      for (const digit of match[1].padStart(2, "0")) ids.push(`digit_${digit}`);
      if (match[2]) ids.push(`runway_${match[2]}`);
    } else {
      for (const character of text) {
        if (/\d/.test(character)) ids.push(`digit_${character}`);
        else if (/[A-Z]/.test(character)) ids.push(`letter_${character}`);
        else if (character !== "-") return null;
      }
    }
    return ids.length && ids.every((id) => clips[id]) ? ids : null;
  }

  /** Suite de fichiers d'une annonce, ou null : elle ne sera pas dite. */
  function plan(bank, parts) {
    if (!bank) return null;
    const ids = [];
    for (const part of parts) {
      const template = bank.templates?.[part.key];
      if (!template) {
        if (!bank.clips?.[part.key]) return null;
        ids.push(part.key);
        continue;
      }
      for (const segment of template) {
        if (segment.clip) {
          if (!bank.clips[segment.clip]) return null;
          ids.push(segment.clip);
          continue;
        }
        const slot = slotClips(segment.slot, part.values?.[segment.slot], bank.clips);
        if (!slot) return null;
        ids.push(...slot);
      }
    }
    const folder = bank.bank || bank.language;
    return ids.map((id) => `${BANK_ROOT}/${folder}/${bank.clips[id]}`);
  }

  /* ----------------------------------------------------------- lecture */

  function context() {
    if (!audioContext) {
      const Context = window.AudioContext || window.webkitAudioContext;
      if (!Context) return null;
      audioContext = new Context();
    }
    // Un contexte créé avant tout geste démarre suspendu dans un navigateur.
    if (audioContext.state === "suspended") audioContext.resume().catch(() => {});
    return audioContext;
  }

  function buffer(url, audio) {
    if (!buffers.has(url)) {
      buffers.set(url, fetch(url)
        .then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          return response.arrayBuffer();
        })
        .then((data) => audio.decodeAudioData(data))
        .catch((error) => {
          buffers.delete(url);
          throw error;
        }));
    }
    return buffers.get(url);
  }

  function stop() {
    for (const source of playing) {
      try {
        source.stop();
      } catch (_error) {
        // Déjà terminé.
      }
    }
    playing = [];
    queueEnd = 0;
  }

  async function play(urls, priority) {
    const audio = context();
    if (!audio) return false;
    const decoded = await Promise.all(urls.map((url) => buffer(url, audio)));
    if (priority) stop();
    let start = Math.max(audio.currentTime + 0.05, queueEnd);
    if (!priority && start - audio.currentTime > MAX_BACKLOG_S) return false;
    for (const clip of decoded) {
      const source = audio.createBufferSource();
      source.buffer = clip;
      source.connect(audio.destination);
      source.start(start);
      source.addEventListener("ended", () => {
        playing = playing.filter((item) => item !== source);
      });
      playing.push(source);
      start += clip.duration + SEGMENT_GAP_S;
    }
    queueEnd = start + ANNOUNCEMENT_GAP_S;
    return true;
  }

  function say(parts, priority) {
    const urls = plan(loadBank(), parts);
    if (!urls) return false;
    play(urls, priority).catch(() => {});
    return true;
  }

  /**
   * Annonce `parts` si les annonces sont actives.
   * `priority` interrompt ce qui se dit : réservé aux alarmes critiques.
   */
  function announce(parts, { priority = false } = {}) {
    if (!enabled || !parts?.length) return false;
    const fingerprint = JSON.stringify(parts);
    const now = Date.now();
    if (!priority && now - (recent.get(fingerprint) || 0) < REPEAT_MS) return false;
    recent.set(fingerprint, now);
    return say(parts, priority);
  }

  // Les navigateurs n'autorisent le son qu'après un premier geste : le
  // premier clic réveille le contexte audio pour toute la session.
  if (typeof document !== "undefined") {
    document.addEventListener?.("pointerdown", () => context(), { once: true, capture: true });
  }
  if (typeof window !== "undefined") {
    window.addEventListener?.("navixav:languagechange", () => {
      loadIndex();
      loadBank();
    });
  }

  return {
    available: () => Boolean(window.AudioContext || window.webkitAudioContext),
    enabled: () => enabled,
    setEnabled(value) {
      enabled = Boolean(value);
      write(ENABLED_KEY, enabled ? "1" : "0");
      if (enabled) {
        context();
        loadBank();
      } else {
        stop();
      }
      notify();
    },
    preferredName: () => (preferredName.startsWith(BANK_PREFIX) ? preferredName : ""),
    setPreferredName(name) {
      preferredName = String(name || "");
      write(NAME_KEY, preferredName);
      loadBank();
      notify();
    },
    /** La voix retenue pour la langue affichée, ou null tant qu'elle manque. */
    bank: () => loadBank(),
    /** Voix NaviXav de la langue affichée : [{value, label}], défaut en tête. */
    banks: () => (loadIndex()?.[language()] || []).map((entry, position) => ({
      value: position === 0 ? "" : `${BANK_PREFIX}${entry.bank}`,
      label: entry.label,
    })),
    announce,
    /** Fait entendre la voix retenue, même annonces coupées. */
    test() {
      return say([{ key: "voice_test_phrase" }], true);
    },
    onChange(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    // Exposés pour les tests : la composition ne dépend d'aucun son.
    _plan: plan,
    _slotClips: slotClips,
  };
})();

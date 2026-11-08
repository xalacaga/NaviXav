"use strict";

/**
 * Annonces vocales.
 *
 * La synthèse passe par l'API Web Speech du navigateur : dans la fenêtre
 * NaviXav, ce sont les voix installées dans Windows, sans réseau ni compte.
 * Une voix « naturelle » exposée par le système (voix hors ligne du Narrateur
 * de Windows 11 rendues visibles, ou voix en ligne si le moteur WebView2 les
 * publie un jour) est préférée d'office ; le pilote peut en imposer une autre.
 *
 * Le choix est une préférence de l'appareil, comme la langue : il reste dans le
 * stockage local, si bien qu'une tablette connectée peut parler, ou se taire,
 * indépendamment du poste.
 */
const VOICE = (() => {
  const ENABLED_KEY = "navixav-voice-enabled";
  const NAME_KEY = "navixav-voice-name";
  // Une même phrase ne revient pas avant ce délai : une valeur qui oscille
  // autour d'un seuil ne doit pas faire bégayer la voix.
  const REPEAT_MS = 30000;
  // Au-delà, une annonce ordinaire est abandonnée plutôt que dite en retard.
  const MAX_QUEUED = 2;
  const LOCALES = {
    fr: "fr-FR", en: "en-GB", de: "de-DE", es: "es-ES",
    it: "it-IT", pt: "pt-PT", nl: "nl-NL", pl: "pl-PL",
  };

  const synth = typeof window !== "undefined" ? window.speechSynthesis || null : null;
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
  let preferredName = read(NAME_KEY) || "";
  let queued = 0;
  const recent = new Map();
  const listeners = new Set();

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

  if (synth) synth.addEventListener?.("voiceschanged", notify);

  /** Plus la note est haute, plus la voix est agréable à écouter. */
  function quality(voice) {
    const name = String(voice.name || "").toLowerCase();
    let score = 0;
    if (name.includes("natural")) score += 4;
    if (name.includes("neural")) score += 3;
    if (name.includes("online")) score += 1;
    if (voice.localService) score += 0.5;
    return score;
  }

  function voicesFor(code = language()) {
    if (!synth) return [];
    const prefix = String(code).toLowerCase();
    return synth.getVoices()
      .filter((voice) => String(voice.lang || "").toLowerCase().startsWith(prefix))
      .sort((first, second) => quality(second) - quality(first)
        || String(first.name).localeCompare(String(second.name)));
  }

  /** Voix retenue : celle du pilote si elle parle la langue, sinon la meilleure. */
  function selectVoice(code = language()) {
    const candidates = voicesFor(code);
    return candidates.find((voice) => voice.name === preferredName) || candidates[0] || null;
  }

  function utter(text, priority) {
    const utterance = new SpeechSynthesisUtterance(text);
    const code = language();
    utterance.lang = LOCALES[code] || code;
    const voice = selectVoice(code);
    if (voice) utterance.voice = voice;
    utterance.rate = 1.05;
    queued += 1;
    const done = () => {
      queued = Math.max(0, queued - 1);
    };
    utterance.addEventListener("end", done);
    utterance.addEventListener("error", done);
    if (priority) {
      synth.cancel();
      queued = 1;
    }
    synth.speak(utterance);
  }

  /**
   * Dit `text` si les annonces sont actives.
   * `priority` interrompt ce qui se dit : réservé aux alarmes critiques.
   */
  function speak(text, { priority = false } = {}) {
    if (!enabled || !synth || !text) return false;
    const now = Date.now();
    if (!priority && now - (recent.get(text) || 0) < REPEAT_MS) return false;
    if (!priority && queued >= MAX_QUEUED) return false;
    recent.set(text, now);
    utter(text, priority);
    return true;
  }

  return {
    available: () => Boolean(synth),
    enabled: () => enabled,
    setEnabled(value) {
      enabled = Boolean(value);
      write(ENABLED_KEY, enabled ? "1" : "0");
      if (!enabled && synth) {
        synth.cancel();
        queued = 0;
      }
      notify();
    },
    preferredName: () => preferredName,
    setPreferredName(name) {
      preferredName = String(name || "");
      write(NAME_KEY, preferredName);
      notify();
    },
    /** Voix de la langue affichée, la meilleure en tête. */
    voices: () => voicesFor().map((voice) => ({
      name: voice.name,
      natural: quality(voice) >= 3,
    })),
    activeName: () => selectVoice()?.name || "",
    speak,
    /** Fait entendre la voix retenue, même annonces coupées. */
    test(text) {
      if (!synth || !text) return false;
      utter(text, true);
      return true;
    },
    onChange(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
})();

#!/usr/bin/env node
"use strict";

/*
 * Liste des phrases de la banque vocale NaviXav, pour chaque langue.
 *
 * Les annonces sont des phrases fixes (alarmes, étapes du TOD, consignes de
 * roulage) dont seules quelques parties varient : distance, piste, taxiway.
 * Chaque phrase est découpée sur ses {paramètres} : les morceaux fixes
 * deviennent des fichiers audio, les paramètres sont composés à partir de
 * nombres, de chiffres, de lettres de l'alphabet OACI et des côtés de piste.
 *
 * Les textes viennent de i18n.js : la banque dit exactement ce que l'interface
 * affiche. Sortie JSON sur la sortie standard, lue par generate_voice_bank.py.
 *
 *   node scripts/voice_bank_phrases.cjs > phrases.json
 */

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const LANGUAGES = ["fr", "en", "de", "es", "it", "pt", "nl", "pl"];

// Clés annoncées à la voix par app.js. Les alarmes s'y ajoutent d'elles-mêmes.
const ANNOUNCED_KEYS = [
  "master_caution", "master_warning",
  "voice_tod_prepare", "voice_tod_imminent", "voice_tod_now", "voice_test_phrase",
  "voice_stabilized",
  "taxi_arrived", "taxi_off_route", "taxi_hold_short",
  "taxi_turn_left", "taxi_turn_right", "taxi_continue",
];

// Distances annoncées : le TOD n'est annoncé qu'à partir de 50 NM.
const MAX_NUMBER = 60;

// Chiffres prononcés un à un, à la manière de la radiotéléphonie.
const DIGITS = {
  fr: ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"],
  en: ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "niner"],
  de: ["null", "eins", "zwo", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun"],
  es: ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"],
  it: ["zero", "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove"],
  pt: ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"],
  nl: ["nul", "één", "twee", "drie", "vier", "vijf", "zes", "zeven", "acht", "negen"],
  pl: ["zero", "jeden", "dwa", "trzy", "cztery", "pięć", "sześć", "siedem", "osiem", "dziewięć"],
};

// Côté de piste, après les deux chiffres de l'identifiant.
const RUNWAY_SIDES = {
  fr: { L: "gauche", R: "droite", C: "centre" },
  en: { L: "left", R: "right", C: "center" },
  de: { L: "links", R: "rechts", C: "Mitte" },
  es: { L: "izquierda", R: "derecha", C: "centro" },
  it: { L: "sinistra", R: "destra", C: "centro" },
  pt: { L: "esquerda", R: "direita", C: "centro" },
  nl: { L: "links", R: "rechts", C: "midden" },
  pl: { L: "lewy", R: "prawy", C: "centralny" },
};

// Alphabet OACI : les mêmes mots dans toutes les langues.
const ALPHABET = {
  A: "Alfa", B: "Bravo", C: "Charlie", D: "Delta", E: "Echo", F: "Foxtrot",
  G: "Golf", H: "Hotel", I: "India", J: "Juliett", K: "Kilo", L: "Lima",
  M: "Mike", N: "November", O: "Oscar", P: "Papa", Q: "Quebec", R: "Romeo",
  S: "Sierra", T: "Tango", U: "Uniform", V: "Victor", W: "Whiskey",
  X: "X-ray", Y: "Yankee", Z: "Zulu",
};

function loadTranslations() {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "navixav", "web", "static", "i18n.js"),
    "utf8"
  );
  // La langue choisie vit dans le stockage local : il doit la retenir, sinon
  // chaque langue retomberait sur le français.
  const storage = new Map();
  const window = {
    localStorage: {
      getItem: (key) => (storage.has(key) ? storage.get(key) : null),
      setItem: (key, value) => storage.set(key, String(value)),
    },
    dispatchEvent() {},
    CustomEvent: function CustomEvent() {},
    document: {
      documentElement: {},
      title: "",
      querySelector: () => null,
      querySelectorAll: () => [],
    },
    navigator: { languages: [] },
  };
  window.window = window;
  vm.runInContext(source, vm.createContext(window));
  return window.I18N;
}

/** Morceaux d'une phrase : textes fixes et {paramètres}, ponctuation seule ignorée. */
function split(text) {
  const segments = [];
  for (const piece of text.split(/(\{[a-z_]+\})/)) {
    const slot = piece.match(/^\{([a-z_]+)\}$/);
    if (slot) segments.push({ slot: slot[1] });
    else if (/[\p{L}\p{N}]/u.test(piece)) segments.push({ text: piece.trim() });
  }
  return segments;
}

/** Alarmes réellement levées : les identifiants de ALERT_RULES dans app.js. */
function alertKeys() {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "navixav", "web", "static", "app.js"),
    "utf8"
  ).replaceAll("\r\n", "\n");
  const start = source.indexOf("const ALERT_RULES = [");
  const block = source.slice(start, source.indexOf("\n];\n", start));
  return [...block.matchAll(/^\s+id: "([a-z_]+)",$/gm)].map((match) => `alert_${match[1]}`);
}

function phrases(i18n, language) {
  i18n.setLanguage(language);
  const keys = [...ANNOUNCED_KEYS, ...alertKeys()];
  const clips = {};
  const templates = {};
  for (const key of keys) {
    if (!i18n.has(key)) throw new Error(`${language}: clé absente ${key}`);
    const segments = split(i18n.t(key));
    if (segments.length === 1 && segments[0].text) {
      clips[key] = segments[0].text;
      continue;
    }
    templates[key] = segments.map((segment, index) => {
      if (segment.slot) return { slot: segment.slot };
      const id = `${key}.${index}`;
      clips[id] = segment.text;
      return { clip: id };
    });
  }
  for (let number = 0; number <= MAX_NUMBER; number += 1) clips[`number_${number}`] = String(number);
  DIGITS[language].forEach((word, digit) => { clips[`digit_${digit}`] = word; });
  for (const [letter, word] of Object.entries(ALPHABET)) clips[`letter_${letter}`] = word;
  for (const [side, word] of Object.entries(RUNWAY_SIDES[language])) clips[`runway_${side}`] = word;
  return { clips, templates };
}

const i18n = loadTranslations();
const bank = {};
for (const language of LANGUAGES) bank[language] = phrases(i18n, language);
process.stdout.write(JSON.stringify(bank, null, 2));

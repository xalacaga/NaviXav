"""Génère la banque vocale NaviXav : un fichier Opus par phrase et par langue.

Les modèles de synthèse ne servent qu'ici, au moment du développement :
l'application n'embarque que les fichiers audio produits, quelques Mo, et
aucun moteur. Kokoro (Apache 2.0) parle français, anglais, espagnol et
italien ; Piper (voix CC0 et Apache 2.0) parle portugais européen, allemand,
néerlandais et polonais.

Prérequis, dans un environnement séparé de celui de NaviXav :

    python -m venv ttsenv
    ttsenv\\Scripts\\pip install kokoro-onnx piper-tts soundfile scipy

et, dans un dossier de modèles :
    kokoro-v1.0.onnx, voices-v1.0.bin  (github.com/thewh1teagle/kokoro-onnx)
    <voix>.onnx et <voix>.onnx.json    (huggingface.co/rhasspy/piper-voices)

Utilisation :

    node scripts/voice_bank_phrases.cjs > phrases.json
    ttsenv\\Scripts\\python scripts/generate_voice_bank.py phrases.json <modèles>

Seuls les fichiers dont le texte ou la voix ont changé sont régénérés.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import json
import sys
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

OUTPUT = Path(__file__).resolve().parent.parent / "navixav" / "web" / "static" / "voice"
SAMPLE_RATE = 24000

# Voix livrées. Clé : dossier de la banque. La première voix d'une langue est
# celle par défaut et garde le dossier nommé d'après la langue ; les autres
# s'appellent <langue>-<voix>. Valeur : (langue, moteur, voix, code espeak,
# crédit, nom affiché dans les Paramètres).
VOICES: dict[str, tuple[str, str, str, str, str, str]] = {
    "fr": ("fr", "kokoro", "ff_siwis", "fr-fr", "Kokoro-82M (Apache 2.0), voix ff_siwis", "Siwis"),
    "en": ("en", "kokoro", "af_heart", "en-us", "Kokoro-82M (Apache 2.0), voice af_heart", "Heart (US)"),
    "en-af_bella": ("en", "kokoro", "af_bella", "en-us", "Kokoro-82M (Apache 2.0), voice af_bella", "Bella (US)"),
    "en-bf_emma": ("en", "kokoro", "bf_emma", "en-gb", "Kokoro-82M (Apache 2.0), voice bf_emma", "Emma (UK)"),
    "es": ("es", "kokoro", "ef_dora", "es", "Kokoro-82M (Apache 2.0), voz ef_dora", "Dora"),
    "it": ("it", "kokoro", "if_sara", "it", "Kokoro-82M (Apache 2.0), voce if_sara", "Sara"),
    "pt": ("pt", "piper", "pt_PT-tugao-medium", "", "Piper, voz pt_PT-tugão-medium (CC0)", "Tugão"),
    "de": ("de", "piper", "de_DE-thorsten-high", "", "Piper, Stimme de_DE-thorsten-high (CC0)", "Thorsten"),
    "nl": ("nl", "piper", "nl_NL-pim-medium", "", "Piper, stem nl_NL-pim-medium (CC0)", "Pim"),
    "pl": ("pl", "piper", "pl_PL-bass-high", "", "Piper, głos pl_PL-bass-high (Apache 2.0)", "Bass"),
}
KOKORO_SPEED = 1.05

# Les termes aéronautiques restent en anglais dans toutes les langues, comme
# dans un cockpit : la voix de la langue les prononce à l'anglaise, au milieu
# de sa phrase, sans changer de locuteur. Chaque motif est remplacé par sa
# forme parlée anglaise ; les sigles sont épelés, STD se dit « standard ».
ENGLISH_TERMS: tuple[tuple[str, str], ...] = (
    (r"MASTER CAUTION", "master caution"),
    (r"MASTER WARNING", "master warning"),
    (r"Top of [Dd]escent", "top of descent"),
    (r"Navigation lights", "navigation lights"),
    (r"Landing lights", "landing lights"),
    (r"Taxi light", "taxi light"),
    (r"Strobes", "strobes"),
    (r"Beacon", "beacon"),
    (r"still on", "still on"),
    (r"not reset", "not reset"),
    (r"not tuned", "not tuned"),
    (r"\boff\b", "off"),
    (r"\bTOD\b", "T O D"),
    (r"\bFMGC\b", "F M G C"),
    (r"\bQNH\b", "Q N H"),
    (r"\bILS\b", "I L S"),
    (r"\bSTD\b", "standard"),
    (r"\bSIGMET\b", "sig met"),
)
_ENGLISH_PATTERN = re.compile("|".join(f"({pattern})" for pattern, _spoken in ENGLISH_TERMS))
ENGLISH_ESPEAK = "en-us"
# Version de la prononciation : la changer régénère les phrases concernées.
PRONUNCIATION_VERSION = 1

# Sons anglais absents d'une voix Piper, rapprochés du plus proche : c'est
# l'accent d'un pilote de cette langue, pas un mot amputé.
PIPER_FALLBACKS = {
    "ɹ": ("ɾ", "r", "ʁ"), "θ": ("s",), "ð": ("d", "z"), "w": ("u", "v"),
    "æ": ("ɛ", "a"), "ʌ": ("a", "ɐ"), "ɜ": ("ø", "ə", "e"), "ɚ": ("ɐ", "ə"),
    "ᵻ": ("ɪ", "i"), "ɐ": ("a",), "ɑ": ("a",), "ɔ": ("o",), "ɪ": ("i",),
    "ʊ": ("u",), "ɾ": ("t", "d"), "ʒ": ("ʃ", "z"), "ŋ": ("n",), "ɡ": ("g",),
}


def runs(clip_id: str, text: str) -> list[tuple[str, bool]]:
    """Morceaux de la phrase, chacun marqué anglais ou non.

    L'alphabet OACI est anglais dans toutes les langues. Deux termes anglais
    séparés par une simple espace forment un seul morceau, pour garder le
    phrasé de « Strobes off » ou « Landing lights still on ».
    """
    if clip_id.startswith("letter_"):
        return [(text, True)]
    pieces: list[tuple[str, bool]] = []
    position = 0
    for match in _ENGLISH_PATTERN.finditer(text):
        if match.start() > position:
            pieces.append((text[position:match.start()], False))
        spoken = ENGLISH_TERMS[match.lastindex - 1][1]
        pieces.append((spoken, True))
        position = match.end()
    if position < len(text):
        pieces.append((text[position:], False))
    merged: list[tuple[str, bool]] = []
    for piece, english in pieces:
        if merged and english and merged[-1][1]:
            merged[-1] = (f"{merged[-1][0].rstrip()} {piece}", True)
        elif merged and not english and merged[-1][1] and not piece.strip(" -.,") and piece:
            # Ponctuation ou trait d'union collé au terme anglais.
            merged[-1] = (merged[-1][0] + piece, True)
        else:
            merged.append((piece, english))
    return [(piece, english) for piece, english in merged if piece.strip()]


class Synthesizer:
    def __init__(self, models: Path) -> None:
        self.models = models
        self._kokoro = None
        self._piper: dict[str, object] = {}

    def __call__(self, bank: str, clip_id: str, text: str) -> np.ndarray:
        language, engine, voice, code, _credit, _label = VOICES[bank]
        pieces = runs(clip_id, text)
        mixed = any(english for _piece, english in pieces)
        if engine == "kokoro":
            kokoro = self._load_kokoro()
            if not mixed:
                samples, rate = kokoro.create(text, voice=voice, speed=KOKORO_SPEED, lang=code)
            else:
                # Les voix Kokoro lisent des phonèmes IPA communs à toutes les
                # langues : la partie anglaise est transcrite en anglais, avec
                # l'accent de la voix quand elle est elle-même anglophone.
                english_code = code if language == "en" else ENGLISH_ESPEAK
                phonemes = " ".join(
                    kokoro.tokenizer.phonemize(piece.strip(), english_code if english else code)
                    for piece, english in pieces
                )
                samples, rate = kokoro.create(
                    phonemes, voice=voice, speed=KOKORO_SPEED, is_phonemes=True
                )
            return _resample(np.asarray(samples, dtype=np.float32), rate)

        piper = self._load_piper(voice)
        if mixed:
            text = " ".join(
                f"[[ {self._english_phonemes(piper, piece)} ]]" if english else piece.strip()
                for piece, english in pieces
            )
        chunks, rate = [], SAMPLE_RATE
        for chunk in piper.synthesize(text):
            chunks.append(np.asarray(chunk.audio_float_array, dtype=np.float32))
            rate = chunk.sample_rate
        return _resample(np.concatenate(chunks), rate)

    def _load_kokoro(self):
        if self._kokoro is None:
            from kokoro_onnx import Kokoro

            self._kokoro = Kokoro(
                str(self.models / "kokoro-v1.0.onnx"), str(self.models / "voices-v1.0.bin")
            )
        return self._kokoro

    def _load_piper(self, voice: str):
        if voice not in self._piper:
            from piper import PiperVoice

            self._piper[voice] = PiperVoice.load(str(self.models / f"{voice}.onnx"))
        return self._piper[voice]

    def _english_phonemes(self, piper, text: str) -> str:
        """Phonèmes anglais ramenés à ceux que la voix sait prononcer."""
        from piper.phonemize_espeak import ESPEAK_DATA_DIR, EspeakPhonemizer

        if not hasattr(self, "_espeak"):
            self._espeak = EspeakPhonemizer(ESPEAK_DATA_DIR)
        known = piper.config.phoneme_id_map
        spoken: list[str] = []
        for sentence in self._espeak.phonemize(ENGLISH_ESPEAK, text):
            for phoneme in sentence:
                if phoneme in known:
                    spoken.append(phoneme)
                    continue
                replacement = next(
                    (option for option in PIPER_FALLBACKS.get(phoneme, ()) if option in known), None
                )
                if replacement:
                    spoken.append(replacement)
        return "".join(spoken).strip()


def _resample(samples: np.ndarray, rate: int) -> np.ndarray:
    if rate == SAMPLE_RATE:
        return samples
    factor = gcd(SAMPLE_RATE, rate)
    return resample_poly(samples, SAMPLE_RATE // factor, rate // factor).astype(np.float32)


def _finish(samples: np.ndarray) -> np.ndarray:
    """Silences de tête et de queue retirés, crête à -1 dBFS, fondus de 10 ms."""
    level = np.abs(samples)
    loud = np.flatnonzero(level > max(0.01, level.max() * 0.02))
    if loud.size:
        pad = int(0.03 * SAMPLE_RATE)
        samples = samples[max(0, loud[0] - pad): loud[-1] + pad]
    peak = float(np.abs(samples).max()) or 1.0
    samples = samples * (0.89 / peak)
    fade = min(len(samples) // 2, int(0.01 * SAMPLE_RATE))
    if fade:
        ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        samples[:fade] *= ramp
        samples[-fade:] *= ramp[::-1]
    return samples.astype(np.float32)


def _signature(bank: str, clip_id: str, text: str) -> str:
    _language, engine, voice, code, _credit, _label = VOICES[bank]
    speed = KOKORO_SPEED if engine == "kokoro" else 1.0
    pieces = runs(clip_id, text)
    if any(english for _piece, english in pieces):
        # Seules les phrases à prononciation anglaise dépendent de sa version.
        text = f"pron{PRONUNCIATION_VERSION}|{pieces!r}"
    return hashlib.sha256(f"{engine}|{voice}|{code}|{speed}|{text}".encode()).hexdigest()[:16]


def generate(phrases: dict, models: Path, banks: list[str]) -> None:
    synthesize = Synthesizer(models)
    for bank_id in banks:
        language, engine, voice, _code, credit, label = VOICES[bank_id]
        bank = phrases[language]
        folder = OUTPUT / bank_id
        folder.mkdir(parents=True, exist_ok=True)
        manifest_path = folder / "manifest.json"
        previous = {}
        if manifest_path.is_file():
            previous = json.loads(manifest_path.read_text(encoding="utf-8")).get("signatures", {})

        clips, signatures, made = {}, {}, 0
        for clip_id, text in bank["clips"].items():
            name = f"{clip_id}.ogg"
            signature = _signature(bank_id, clip_id, text)
            target = folder / name
            if previous.get(clip_id) != signature or not target.is_file():
                audio = _finish(synthesize(bank_id, clip_id, text))
                sf.write(target, audio, SAMPLE_RATE, format="OGG", subtype="OPUS")
                made += 1
            clips[clip_id] = name
            signatures[clip_id] = signature

        for stale in folder.glob("*.ogg"):
            if stale.name not in set(clips.values()):
                stale.unlink()

        manifest = {
            "bank": bank_id,
            "language": language,
            "engine": engine,
            "voice": voice,
            "label": label,
            "credit": credit,
            "clips": clips,
            "templates": bank["templates"],
            "signatures": signatures,
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        size = sum(path.stat().st_size for path in folder.glob("*.ogg"))
        print(f"{bank_id}: {made} généré(s), {len(clips)} au total, {size / 1024:.0f} Ko")
    write_index()


def write_index() -> None:
    """Voix livrées par langue, la voix par défaut en tête."""
    index: dict[str, list[dict[str, str]]] = {}
    for bank_id, (language, _engine, voice, _code, _credit, label) in VOICES.items():
        if (OUTPUT / bank_id / "manifest.json").is_file():
            index.setdefault(language, []).append({"bank": bank_id, "voice": voice, "label": label})
    (OUTPUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("phrases", type=Path)
    parser.add_argument("models", type=Path)
    parser.add_argument("--banks", nargs="*", default=list(VOICES))
    args = parser.parse_args(argv)
    phrases = json.loads(args.phrases.read_text(encoding="utf-8"))
    generate(phrases, args.models, args.banks)
    return 0


if __name__ == "__main__":
    sys.exit(main())

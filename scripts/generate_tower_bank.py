"""Banque pré-enregistrée de la tour, pour qui n'a pas installé le moteur vocal.

Avec le moteur facultatif, la tour dit ses phrases entières en direct. Sans
lui, elle les compose à partir de cette banque. Pour garder le phrasé d'un
contrôleur, les morceaux sont des groupes entiers dits d'un souffle — « runway
three two right, cleared for takeoff », « wind three two zero degrees » — et
seuls l'indicatif et la fréquence, propres à chaque vol, restent assemblés
chiffre par chiffre. Les mots viennent de navixav/tower_phraseology.py, la
même source que le moteur.

Les morceaux sont enregistrés à sec : l'effet de radio VHF est appliqué en
direct sur le message entier.

    python generate_tower_bank.py chemin/vers/modeles

Seuls les morceaux nouveaux ou modifiés sont synthétisés.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from navixav.tower_phraseology import AIRLINES, LETTERS, VOICES, WORDS  # noqa: E402

OUT = ROOT / "navixav" / "web" / "static" / "tower"
RATE = 24000
MAX_KNOTS = 60
SIDES = ("", "L", "R", "C")


def spoken_digits(language: str, text: str) -> str:
    return " ".join(WORDS[language]["digits"][int(c)] for c in text)


def clips(language: str) -> dict[str, str]:
    """Identifiant de morceau -> texte dit d'un souffle."""
    words = WORDS[language]
    result = {f"digit_{index}": text for index, text in enumerate(words["digits"])}
    result.update({f"letter_{chr(65 + index)}": text for index, text in enumerate(LETTERS)})
    result.update({f"airline_{code}": name for code, name in AIRLINES.items()})
    for key in ("decimal", "contact_departure", "good_day", "wind_calm", "knots"):
        result[key] = words[key]
    for number in range(1, 37):
        for side in SIDES:
            runway = spoken_digits(language, f"{number:02d}")
            if side:
                runway += " " + words[f"side_{side}"]
            name = f"{number:02d}{side}"
            result[f"rwy_{name}_lineup"] = f"{words['runway']} {runway}, {words['line_up_and_wait']}."
            result[f"rwy_{name}_takeoff"] = f"{words['runway']} {runway}, {words['cleared_for_takeoff']}."
    for direction in range(10, 361, 10):
        result[f"wind_{direction:03d}"] = (
            f"{words['wind']} {spoken_digits(language, f'{direction:03d}')} {words['degrees']},"
        )
    for speed in range(3, MAX_KNOTS + 1):
        result[f"knots_{speed}"] = f"{spoken_digits(language, str(speed))} {words['knots']},"
    return result


def signature(language: str, text: str) -> str:
    voice, code, speed = VOICES[language]
    return hashlib.sha256(f"{voice}|{code}|{speed}|{text}".encode()).hexdigest()[:16]


def finish(samples):
    """Silences retirés, crête à -1 dBFS : les morceaux s'enchaînent sans trou."""
    import numpy as np

    level = np.abs(samples)
    loud = np.flatnonzero(level > max(0.01, level.max() * 0.02))
    if loud.size:
        pad = int(0.015 * RATE)
        samples = samples[max(0, loud[0] - pad): loud[-1] + pad]
    return (samples * (0.89 / (float(np.abs(samples).max()) or 1.0))).astype(np.float32)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("models", type=Path)
    args = parser.parse_args(argv)

    import numpy as np
    import soundfile as sf
    from kokoro_onnx import Kokoro

    kokoro = Kokoro(str(args.models / "kokoro-v1.0.onnx"), str(args.models / "voices-v1.0.bin"))
    for language, (voice, code, speed) in VOICES.items():
        folder = OUT / language
        folder.mkdir(parents=True, exist_ok=True)
        manifest_path = folder / "manifest.json"
        previous = {}
        if manifest_path.is_file():
            previous = json.loads(manifest_path.read_text(encoding="utf-8")).get("signatures", {})
        entries, signatures, made = {}, {}, 0
        for clip_id, text in clips(language).items():
            name = f"{clip_id}.ogg"
            sig = signature(language, text)
            target = folder / name
            if previous.get(clip_id) != sig or not target.is_file():
                samples, rate = kokoro.create(text, voice=voice, speed=speed, lang=code)
                if rate != RATE:
                    raise RuntimeError(f"Fréquence inattendue : {rate}")
                sf.write(target, finish(np.asarray(samples, dtype=np.float32)), RATE,
                         format="OGG", subtype="OPUS")
                made += 1
                if made % 50 == 0:
                    print(f"{language}: {made}…", flush=True)
            entries[clip_id] = name
            signatures[clip_id] = sig
        for stale in folder.glob("*.ogg"):
            if stale.name not in set(entries.values()):
                stale.unlink()
        manifest_path.write_text(json.dumps({
            "language": language,
            "voice": voice,
            "credit": f"Kokoro-82M (Apache 2.0), voice {voice}",
            "max_knots": MAX_KNOTS,
            "clips": entries,
            "airlines": sorted(AIRLINES),
            "signatures": signatures,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        size = sum(path.stat().st_size for path in folder.glob("*.ogg"))
        print(f"{language}: {made} généré(s), {len(entries)} au total, {size / 1024:.0f} Ko", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

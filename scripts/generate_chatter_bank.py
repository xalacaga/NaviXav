"""Banque d'ambiance radio ATC : échanges synthétisés une fois, joués en vol.

Chaque fichier est un échange complet — un message et sa collation — passé
dans un effet de radio VHF. Les phrases sont synthétisées d'un bloc avec
Kokoro : composer mot à mot pour glisser des indicatifs réels hacherait la
voix, et c'est le phrasé naturel qui fait l'ambiance.

Les échanges sont tirés au sort (indicatifs, niveaux, caps, fréquences) avec
une graine fixe : relancer le script régénère la même banque. Seuls les
fichiers absents sont synthétisés.

    python generate_chatter_bank.py chemin/vers/modeles [--per-position 40]

Les modèles (kokoro-v1.0.onnx, voices-v1.0.bin) ne sont pas livrés avec
NaviXav : seuls les fichiers audio produits le sont.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path

# numpy, scipy, soundfile et kokoro ne servent qu'à la synthèse : les tests
# relisent les échanges sans eux.

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "navixav" / "web" / "static" / "chatter"
RATE = 24000
SEED = 2026
POSITIONS = ("ground", "tower", "approach", "center")

# Contrôleurs : deux voix par position, pour ne pas entendre toujours la même.
CONTROLLERS = {
    "ground": [("bm_lewis", "en-gb", 1.1), ("af_kore", "en-us", 1.1)],
    "tower": [("af_sarah", "en-us", 1.1), ("bm_daniel", "en-gb", 1.1)],
    "approach": [("bm_george", "en-gb", 1.12), ("am_liam", "en-us", 1.12)],
    "center": [("am_onyx", "en-us", 1.08), ("bf_isabella", "en-gb", 1.1)],
}
# Équipages. af_nicole est exclue : timbre chuchoté, déplacé à la radio.
PILOTS = [
    ("am_michael", "en-us", 1.05), ("bf_emma", "en-gb", 1.08), ("am_eric", "en-us", 1.12),
    ("am_adam", "en-us", 1.15), ("af_jessica", "en-us", 1.08), ("bm_daniel", "en-gb", 1.08),
    ("am_onyx", "en-us", 1.02), ("bf_isabella", "en-gb", 1.08),
]

AIRLINES = [
    "Air France", "Speedbird", "Lufthansa", "KLM", "Easy", "Ryanair", "Delta", "United",
    "American", "Iberia", "Swiss", "Vueling", "Transavia", "Brussels", "Austrian",
    "Scandinavian", "Finnair", "Emirates", "Qatari", "Air Canada", "Aer Lingus", "Tap",
    "Lot", "Shamrock", "Hop", "Air Europa", "Condor", "Eurowings",
]
WAYPOINTS = ["Lumas", "Rotno", "Gotar", "Kelux", "Banko", "Merek", "Turlu", "Velin", "Sorax", "Dikon"]
DIGITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "niner"]
LETTERS = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "kilo",
           "lima", "mike", "november", "papa", "quebec", "romeo", "sierra", "tango", "victor",
           "whiskey", "x-ray", "yankee", "zulu"]
TAXIWAYS = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "November", "Romeo", "Whiskey", "Kilo", "Papa"]
SIDES = {"L": "left", "R": "right", "C": "center"}


def digits(value: int | str) -> str:
    return " ".join(DIGITS[int(c)] for c in str(value))


class Scenario:
    """Valeurs tirées au sort pour un échange, cohérentes entre message et collation."""

    def __init__(self, rng: random.Random):
        self.rng = rng
        airline = rng.choice(AIRLINES)
        number = str(rng.randint(1, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(rng.randint(0, 3)))
        suffix = f" {rng.choice(LETTERS)}" if rng.random() < 0.3 else ""
        self.callsign = f"{airline} {digits(number)}{suffix}"
        heading = rng.choice([21, 24, 25, 26, 27, 9, 14, 32, 6, 18])
        side = rng.choice(["", "L", "R"]) if rng.random() < 0.6 else ""
        self.runway = f"{digits(f'{heading:02d}')}{' ' + SIDES[side] if side else ''}"

    def level(self, low: int = 70, high: int = 390) -> str:
        return f"flight level {digits(self.rng.randrange(low, high + 1, 10))}"

    def altitude(self) -> str:
        value = self.rng.choice([2000, 2500, 3000, 3500, 4000, 5000, 6000])
        thousands, hundreds = divmod(value, 1000)
        text = f"{DIGITS[thousands] if thousands < 10 else digits(thousands)} thousand"
        return text + (" five hundred feet" if hundreds else " feet")

    def heading(self) -> str:
        return f"heading {digits(f'{self.rng.randrange(10, 361, 10):03d}')}"

    def speed(self) -> str:
        return f"{digits(self.rng.choice([160, 170, 180, 190, 200, 210, 220, 230, 250]))} knots"

    def frequency(self, low: int = 118, high: int = 135) -> str:
        whole = self.rng.randint(low, high)
        decimal = self.rng.choice(["05", "1", "15", "2", "25", "3", "35", "4", "45", "5", "6", "65", "7", "75", "8", "85", "9", "95"])
        return f"{digits(whole)} decimal {digits(decimal)}"

    def qnh(self) -> str:
        return digits(self.rng.randint(995, 1032))

    def squawk(self) -> str:
        return digits("".join(str(self.rng.randint(0, 7)) for _ in range(4)))

    def wind(self) -> str:
        direction = self.rng.randrange(10, 361, 10)
        return f"wind {digits(f'{direction:03d}')} degrees, {digits(self.rng.randint(3, 18))} knots"

    def taxiways(self, count: int = 2) -> str:
        picks = self.rng.sample(TAXIWAYS, count)
        return " and ".join(picks)


# Un modèle rend une liste de transmissions : ("ATC" ou "PILOT", texte).
def ground_templates(s: Scenario) -> list[list[tuple[str, str]]]:
    stand = f"{s.rng.choice(TAXIWAYS)} {digits(s.rng.randint(1, 60))}"
    return [
        [("PILOT", f"Ground, {s.callsign}, stand {stand}, request taxi."),
         ("ATC", f"{s.callsign}, taxi to holding point runway {s.runway} via {s.taxiways()}, QNH {s.qnh()}."),
         ("PILOT", f"Taxi holding point runway {s.runway} via {s.taxiways()}, QNH {s.qnh()}, {s.callsign}.")],
        [("ATC", f"{s.callsign}, pushback and start up approved, facing {s.rng.choice(['north', 'south', 'east', 'west'])}."),
         ("PILOT", f"Pushback and start up approved, {s.callsign}.")],
        [("ATC", f"{s.callsign}, hold short of taxiway {s.rng.choice(TAXIWAYS)}, give way to the Airbus from your left."),
         ("PILOT", f"Holding short, giving way to the Airbus, {s.callsign}.")],
        [("ATC", f"{s.callsign}, vacate {s.rng.choice(['left', 'right'])} via {s.rng.choice(TAXIWAYS)} {digits(s.rng.randint(1, 9))}, taxi to stand {stand}."),
         ("PILOT", f"Taxi to stand {stand}, {s.callsign}.")],
        [("ATC", f"{s.callsign}, contact Tower {s.frequency()}, good day."),
         ("PILOT", f"Tower, {s.callsign}, good day.")],
    ]


def tower_templates(s: Scenario) -> list[list[tuple[str, str]]]:
    return [
        [("ATC", f"{s.callsign}, {s.wind()}, runway {s.runway}, cleared to land."),
         ("PILOT", f"Cleared to land runway {s.runway}, {s.callsign}.")],
        [("ATC", f"{s.callsign}, runway {s.runway}, line up and wait."),
         ("PILOT", f"Line up and wait runway {s.runway}, {s.callsign}.")],
        [("ATC", f"{s.callsign}, {s.wind()}, runway {s.runway}, cleared for take off."),
         ("PILOT", f"Cleared for take off runway {s.runway}, {s.callsign}.")],
        [("PILOT", f"Tower, {s.callsign}, established ILS runway {s.runway}."),
         ("ATC", f"{s.callsign}, continue approach, number {s.rng.choice(['two', 'three'])}."),
         ("PILOT", f"Continue approach, {s.callsign}.")],
        [("ATC", f"{s.callsign}, contact Departure {s.frequency()}, good bye."),
         ("PILOT", f"Departure {s.frequency()}, {s.callsign}, bye bye.")],
    ]


def approach_templates(s: Scenario) -> list[list[tuple[str, str]]]:
    altitude = s.altitude()
    heading = s.heading()
    speed = s.speed()
    return [
        [("PILOT", f"Approach, {s.callsign}, descending {s.level(80, 150)}, information {s.rng.choice(LETTERS)}."),
         ("ATC", f"{s.callsign}, radar contact, descend {altitude}, QNH {s.qnh()}."),
         ("PILOT", f"Descend {altitude}, QNH {s.qnh()}, {s.callsign}.")],
        [("ATC", f"{s.callsign}, turn {s.rng.choice(['left', 'right'])} {heading}."),
         ("PILOT", f"{heading.capitalize()}, {s.callsign}.")],
        [("ATC", f"{s.callsign}, reduce speed {speed}."),
         ("PILOT", f"Speed {speed}, {s.callsign}.")],
        [("ATC", f"{s.callsign}, {heading}, cleared ILS approach runway {s.runway}."),
         ("PILOT", f"{heading.capitalize()}, cleared ILS runway {s.runway}, {s.callsign}.")],
        [("ATC", f"{s.callsign}, contact Tower {s.frequency()}."),
         ("PILOT", f"Tower {s.frequency()}, {s.callsign}.")],
    ]


def center_templates(s: Scenario) -> list[list[tuple[str, str]]]:
    level = s.level(240, 410)
    fix = s.rng.choice(WAYPOINTS)
    return [
        [("PILOT", f"Good day, {s.callsign}, {s.level(240, 410)}."),
         ("ATC", f"{s.callsign}, identified, maintain level, expect direct {fix} shortly."),
         ("PILOT", f"Maintain, expect direct {fix}, {s.callsign}.")],
        [("ATC", f"{s.callsign}, climb {level}."),
         ("PILOT", f"Climb {level}, {s.callsign}.")],
        [("ATC", f"{s.callsign}, descend {s.level(100, 240)}, rate one thousand or greater."),
         ("PILOT", f"Descend {s.level(100, 240)}, rate one thousand or greater, {s.callsign}.")],
        [("ATC", f"{s.callsign}, proceed direct {fix}."),
         ("PILOT", f"Direct {fix}, {s.callsign}.")],
        [("ATC", f"{s.callsign}, squawk {s.squawk()}."),
         ("PILOT", f"Squawk {s.squawk()}, {s.callsign}.")],
        [("PILOT", f"{s.callsign}, request {level} due to turbulence."),
         ("ATC", f"{s.callsign}, climb {level}, report reaching."),
         ("PILOT", f"Climb {level}, wilco, {s.callsign}.")],
        [("ATC", f"{s.callsign}, contact Control {s.frequency()}, good day."),
         ("PILOT", f"{s.frequency().capitalize()}, {s.callsign}, good day.")],
    ]


TEMPLATES = {
    "ground": ground_templates,
    "tower": tower_templates,
    "approach": approach_templates,
    "center": center_templates,
}



@dataclass(frozen=True)
class Exchange:
    position: str
    index: int
    controller: tuple[str, str, float]
    pilot: tuple[str, str, float]
    lines: tuple[tuple[str, str], ...]
    callsign: str = ""

    @property
    def name(self) -> str:
        return f"{self.position}_{self.index:03d}.ogg"


def scripted_exchanges(per_position: int) -> list[Exchange]:
    """Les échanges de la banque, toujours les mêmes pour une graine donnée."""
    rng = random.Random(SEED)
    exchanges = []
    for position in POSITIONS:
        for index in range(per_position):
            # Chaque valeur est tirée une seule fois par échange : la collation
            # répète exactement ce que le contrôleur a dit.
            scenario = Scenario(rng)
            frozen = _Frozen(scenario)
            options = TEMPLATES[position](frozen)
            lines = rng.choice(options)
            controller = rng.choice(CONTROLLERS[position])
            pilot = rng.choice([p for p in PILOTS if p[0] != controller[0]])
            exchanges.append(Exchange(position, index, controller, pilot, tuple(lines),
                                      scenario.callsign))
    return exchanges


class _Frozen:
    """Scenario dont chaque méthode rend toujours la même valeur une fois tirée."""

    def __init__(self, scenario: Scenario):
        self._scenario = scenario
        self._cache: dict[tuple, str] = {}
        self.rng = scenario.rng
        self.callsign = scenario.callsign
        self.runway = scenario.runway

    def __getattr__(self, name):
        method = getattr(self._scenario, name)

        def frozen(*args):
            key = (name, args)
            if key not in self._cache:
                self._cache[key] = method(*args)
            return self._cache[key]

        return frozen


class Radio:
    """Effet de radio VHF : bande étroite, saturation, souffle, déclic et queue de squelch."""

    def __init__(self, low: float, high: float, hiss_db: float, drive: float, seed: int):
        import numpy as np
        from scipy.signal import butter

        self.sos = butter(4, [low, high], btype="bandpass", fs=RATE, output="sos")
        self.hiss = 10 ** (hiss_db / 20)
        self.drive = drive
        self.rng = np.random.default_rng(seed)

    def __call__(self, voice):
        import numpy as np
        from scipy.signal import sosfilt

        rng = self.rng
        voice = voice / (np.max(np.abs(voice)) + 1e-9)
        body = np.concatenate([np.zeros(int(0.06 * RATE), np.float32), voice,
                               np.zeros(int(0.05 * RATE), np.float32)])
        body = np.tanh(self.drive * body) / np.tanh(self.drive)
        noise = rng.normal(0, 1, body.size).astype(np.float32) * self.hiss
        flutter = 1 + 0.25 * np.sin(np.linspace(0, rng.uniform(6, 14), body.size))
        signal = sosfilt(self.sos, body + noise * flutter).astype(np.float32)
        click = np.zeros(int(0.012 * RATE), np.float32)
        click[:40] = rng.normal(0, 0.6, 40)
        tail = rng.normal(0, 1, int(0.09 * RATE)).astype(np.float32) * 0.35
        tail *= np.linspace(1, 0, tail.size) ** 2
        out = np.concatenate([sosfilt(self.sos, click), signal, sosfilt(self.sos, tail)])
        return (0.7 * out / (np.max(np.abs(out)) + 1e-9)).astype(np.float32)


def render(kokoro, exchange: Exchange, controller_radio: Radio, pilot_radio: Radio,
           rng: random.Random):
    import numpy as np

    parts = []
    for speaker, text in exchange.lines:
        voice, lang, speed = exchange.controller if speaker == "ATC" else exchange.pilot
        samples, rate = kokoro.create(text, voice=voice, speed=speed, lang=lang)
        if rate != RATE:
            raise RuntimeError(f"Fréquence inattendue : {rate}")
        radio = controller_radio if speaker == "ATC" else pilot_radio
        parts.append(radio(np.asarray(samples, dtype=np.float32)))
        # Une collation suit vite son message.
        parts.append(np.zeros(int(rng.uniform(0.3, 0.6) * RATE), np.float32))
    return np.concatenate(parts[:-1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("models", type=Path)
    parser.add_argument("--per-position", type=int, default=40)
    args = parser.parse_args(argv)

    import soundfile as sf
    from kokoro_onnx import Kokoro

    kokoro = Kokoro(str(args.models / "kokoro-v1.0.onnx"), str(args.models / "voices-v1.0.bin"))
    OUT.mkdir(parents=True, exist_ok=True)
    exchanges = scripted_exchanges(args.per_position)
    manifest: dict[str, list[dict]] = {position: [] for position in POSITIONS}
    generated = 0
    for exchange in exchanges:
        target = OUT / exchange.name
        if not target.exists():
            # Graine propre à l'échange : un fichier régénéré seul sonne pareil.
            seed = SEED + POSITIONS.index(exchange.position) * 1000 + exchange.index
            audio = render(kokoro, exchange, Radio(330, 3000, -34, 2.2, seed),
                           Radio(420, 2600, -27, 3.0, seed + 500), random.Random(seed))
            sf.write(target, audio, RATE, format="OGG", subtype="OPUS")
            generated += 1
            print(f"{exchange.name} ({generated})", flush=True)
        info = sf.info(target)
        manifest[exchange.position].append({
            "file": exchange.name,
            "duration": round(info.frames / info.samplerate, 2),
            "lines": [text for _speaker, text in exchange.lines],
        })
    (OUT / "manifest.json").write_text(
        json.dumps({"version": 1, "positions": manifest}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    size = sum(p.stat().st_size for p in OUT.glob("*.ogg"))
    print(f"{generated} généré(s), {len(exchanges)} au total, {size // 1024} Ko")
    return 0


if __name__ == "__main__":
    sys.exit(main())

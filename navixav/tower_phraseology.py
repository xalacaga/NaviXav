"""Phraséologie de la radio et de l'interphone hors ligne, en anglais et en français.

Une seule source pour les deux voix : le moteur vocal facultatif dit ces
phrases d'un seul souffle, et la banque pré-enregistrée (sans moteur) est
générée à partir des mêmes mots pour les messages de la tour. Les nombres
sont écrits en toutes lettres, chiffre par chiffre, comme à la radio.

Chaque message a un locuteur : la délivrance, le sol et la tour parlent à la
radio ; le chef de cabine et le mécanicien au casque parlent à l'interphone.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

# Indicatifs radio (téléphonie) des compagnies, d'après l'OACI (Doc 8585).
# Une compagnie absente est épelée en alphabet OACI : c'est ce qu'un
# contrôleur fait d'un indicatif qu'il ne connaît pas.
AIRLINES = {
    "AAL": "American", "ACA": "Air Canada", "AEA": "Europa", "AEE": "Aegean",
    "AFL": "Aeroflot", "AFR": "Air France", "ANA": "All Nippon", "ASA": "Alaska",
    "AUA": "Austrian", "BAW": "Speedbird", "BEL": "Bee-Line", "BTI": "Air Baltic",
    "CCA": "Air China", "CCM": "Corsica", "CES": "China Eastern", "CFG": "Condor",
    "CLG": "Chalair", "CPA": "Cathay", "CRL": "Corsair", "CSN": "China Southern",
    "CTN": "Croatia", "DAL": "Delta", "DHK": "World Express", "DLA": "Dolomiti",
    "DLH": "Lufthansa", "EIN": "Shamrock", "EJU": "Alpine", "ELY": "El Al",
    "ETD": "Etihad", "ETH": "Ethiopian", "EWG": "Eurowings", "EXS": "Channex",
    "EZS": "Top Swiss", "EZY": "Easy", "FBU": "French Bee", "FDX": "Fedex",
    "FFT": "Frontier Flight", "FIN": "Finnair", "HAL": "Hawaiian", "HOP": "Air Hop",
    "IBE": "Iberia", "ICE": "Ice Air", "ITY": "Itarrow", "JAL": "Japan Air",
    "JBU": "Jet Blue", "KAL": "Korean Air", "KLM": "K L M", "KQA": "Kenya",
    "LOG": "Logan", "LOT": "Pollot", "MSR": "Egyptair", "NAX": "Nor Shuttle",
    "NKS": "Spirit Wings", "PGT": "Sunturk", "QFA": "Qantas", "QTR": "Qatari",
    "RAM": "Royal Air Maroc", "REU": "Reunion", "RYR": "Ryanair", "SAA": "Springbok",
    "SAS": "Scandinavian", "SIA": "Singapore", "SVA": "Saudia", "SWA": "Southwest",
    "SWR": "Swiss", "SXS": "Sunexpress", "TAP": "Air Portugal", "THY": "Turkish",
    "TJT": "Twinjet", "TOM": "Tomson", "TRA": "Transavia", "TSC": "Air Transat",
    "TVF": "France Soleil", "UAE": "Emirates", "UAL": "United", "UPS": "U P S",
    "VLG": "Vueling", "VOE": "Volotea", "WJA": "Westjet", "WZZ": "Wizz Air",
}

LETTERS = ["Alfa", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India",
           "Juliett", "Kilo", "Lima", "Mike", "November", "Oscar", "Papa", "Quebec", "Romeo",
           "Sierra", "Tango", "Uniform", "Victor", "Whiskey", "X-ray", "Yankee", "Zulu"]

WORDS = {
    "en": {
        "digits": ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "niner"],
        "runway": "runway", "line_up_and_wait": "line up and wait",
        "wind": "wind", "degrees": "degrees", "knots": "knots", "wind_calm": "wind calm",
        "cleared_for_takeoff": "cleared for takeoff", "contact_departure": "contact Departure",
        "decimal": "decimal", "good_day": "good day",
        "side_L": "left", "side_R": "right", "side_C": "center",
        "north": "north", "east": "east", "south": "south", "west": "west",
    },
    "fr": {
        "digits": ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"],
        "runway": "piste", "line_up_and_wait": "alignez-vous et attendez",
        "wind": "vent", "degrees": "degrés", "knots": "nœuds", "wind_calm": "vent calme",
        "cleared_for_takeoff": "autorisé décollage", "contact_departure": "contactez Départ",
        "decimal": "décimal", "good_day": "au revoir",
        "side_L": "gauche", "side_R": "droite", "side_C": "centre",
        "north": "au nord", "east": "à l’est", "south": "au sud", "west": "à l’ouest",
    },
}

# Locuteurs : (voix Kokoro, langue eSpeak, débit) par langue. Kokoro n'a
# qu'une voix française : en français, les rôles se distinguent par le débit
# et par l'effet (radio ou interphone) appliqué à la lecture.
SPEAKERS = {
    "en": {
        "delivery": ("bm_george", "en-gb", 1.08),
        "ground": ("bm_lewis", "en-gb", 1.08),
        "tower": ("bm_daniel", "en-gb", 1.1),
        "cabin": ("bf_emma", "en-gb", 1.02),
        "crew": ("bm_fable", "en-gb", 1.0),
    },
    "fr": {
        "delivery": ("ff_siwis", "fr-fr", 1.1),
        "ground": ("ff_siwis", "fr-fr", 1.05),
        "tower": ("ff_siwis", "fr-fr", 1.08),
        "cabin": ("ff_siwis", "fr-fr", 0.98),
        "crew": ("ff_siwis", "fr-fr", 0.95),
    },
}
# Voix de la tour, reprises par la banque pré-enregistrée.
VOICES = {language: speakers["tower"] for language, speakers in SPEAKERS.items()}
ENGINE_VOICES = sorted({voice for speakers in SPEAKERS.values() for voice, _code, _speed in speakers.values()})

# Qui dit quoi.
KINDS = {
    "clearance": "delivery",
    "cabin_boarding": "cabin",
    "loadsheet": "crew",
    "pushback_approved": "ground",
    "pushback_start": "crew",
    "pushback_complete": "crew",
    "taxi": "ground",
    "lineup": "tower",
    "takeoff": "tower",
    "handoff": "tower",
    "arrival_taxi": "ground",
    "chocks": "crew",
}


@dataclass(frozen=True)
class TowerData:
    callsign: str
    runway: str = ""
    wind_direction_true: float | None = None
    wind_speed_kt: float | None = None
    magnetic_variation: float = 0.0
    departure_mhz: float | None = None
    destination: str = ""
    sid: str = ""
    squawk: str = ""
    passengers: int | None = None
    pushback_heading: float | None = None
    taxiways: tuple[str, ...] = field(default_factory=tuple)
    stand: str = ""


def _digits(language: str, text: str) -> list[str]:
    return [WORDS[language]["digits"][int(c)] for c in str(text) if c.isdigit()]


def _spell(language: str, text: str) -> list[str]:
    """Lettres en alphabet OACI, chiffres un à un."""
    return [WORDS[language]["digits"][int(c)] if c.isdigit() else LETTERS[ord(c) - 65]
            for c in re.sub(r"[^A-Z0-9]", "", str(text).upper())]


def callsign_words(callsign: str, language: str) -> list[str]:
    """Indicatif radio : compagnie connue dite par son nom, sinon épelée."""
    text = re.sub(r"[^A-Z0-9]", "", str(callsign or "").upper())
    if not text:
        return []
    match = re.fullmatch(r"([A-Z]{3})([0-9][0-9A-Z]*)", text)
    if match and match.group(1) in AIRLINES:
        return [AIRLINES[match.group(1)], *_spell(language, match.group(2))]
    return _spell(language, text)


def runway_words(runway: str, language: str) -> list[str]:
    match = re.search(r"(\d{1,2})([LRC]?)", str(runway or "").upper())
    if not match:
        return []
    words = _digits(language, match.group(1).zfill(2))
    if match.group(2):
        words.append(WORDS[language][f"side_{match.group(2)}"])
    return words


def wind_words(data: TowerData, language: str) -> list[str]:
    """Vent ramené au nord magnétique, à la dizaine de degrés ; calme sous 3 kt."""
    if data.wind_direction_true is None or data.wind_speed_kt is None:
        return []
    words = WORDS[language]
    if data.wind_speed_kt < 3:
        return [words["wind_calm"]]
    magnetic = round((data.wind_direction_true - data.magnetic_variation) / 10) * 10 % 360 or 360
    return [words["wind"], *_digits(language, f"{magnetic:03d}"), words["degrees"] + ",",
            *_digits(language, round(data.wind_speed_kt)), words["knots"]]


def frequency_words(mhz: float | None, language: str) -> list[str]:
    if mhz is None:
        return []
    whole, fraction = f"{mhz:.3f}".split(".")
    fraction = fraction.rstrip("0") or "0"
    return [*_digits(language, whole), WORDS[language]["decimal"], *_digits(language, fraction)]


def sid_words(sid: str, language: str) -> list[str]:
    """« LACOU5A » se dit « Lacou five Alfa » : le nom, le chiffre, la lettre."""
    match = re.fullmatch(r"([A-Z]{2,6})(\d)([A-Z]?)", re.sub(r"\s", "", str(sid or "").upper()))
    if not match:
        return []
    words = [match.group(1).capitalize(), *_digits(language, match.group(2))]
    if match.group(3):
        words.append(LETTERS[ord(match.group(3)) - 65])
    return words


def squawk_for(seed: str) -> str:
    """Code transpondeur vraisemblable et stable pour un vol, hors codes réservés.

    L'OFP n'en donne pas : celui-ci est tiré de l'identité du vol, en octal,
    loin des codes d'urgence et de conspicuité (7500, 7600, 7700, 2000, 7000, 1200).
    """
    reserved = {"7500", "7600", "7700", "2000", "7000", "1200", "0000"}
    counter = 0
    while True:
        digest = hashlib.sha256(f"{seed}:{counter}".encode()).digest()
        code = "".join(str(byte % 8) for byte in digest[:4])
        if code not in reserved and not code.startswith("77"):
            return code
        counter += 1


def facing_words(heading: float | None, language: str) -> list[str]:
    """Cap du nez après repoussage, ramené au point cardinal le plus proche."""
    if heading is None:
        return []
    index = round((heading % 360) / 90) % 4
    return [WORDS[language][("north", "east", "south", "west")[index]]]


def stand_words(stand: str, language: str) -> list[str]:
    """Poste « porte U 21 » : la désignation, épelée chiffre par chiffre."""
    text = re.sub(r"(?i)\b(porte|gate|parking|stand|poste|ramp|gate_?\w*)\b", " ", str(stand or ""))
    return _spell(language, text)


def taxiway_words(names: tuple[str, ...], language: str) -> list[str]:
    spoken = [" ".join(_spell(language, name)) for name in names if name]
    return [", ".join(spoken)] if spoken else []


def compose(kind: str, data: TowerData, language: str) -> str | None:
    """La phrase entière, ponctuée comme elle se dit ; None s'il manque une donnée."""
    words = WORDS[language]
    french = language == "fr"
    callsign = callsign_words(data.callsign, language)
    runway = runway_words(data.runway, language)
    lead = (" ".join(callsign) + ", ") if callsign else ""
    rw = " ".join(runway)

    if kind in ("lineup", "takeoff", "handoff", "clearance", "pushback_approved", "taxi", "arrival_taxi") and not lead:
        return None
    if kind == "lineup" and runway:
        return lead + f"{words['runway']} {rw}, {words['line_up_and_wait']}."
    if kind == "takeoff" and runway:
        wind = wind_words(data, language)
        middle = (" ".join(wind) + ", ") if wind else ""
        return lead + middle + f"{words['runway']} {rw}, {words['cleared_for_takeoff']}."
    if kind == "handoff":
        frequency = frequency_words(data.departure_mhz, language)
        if frequency:
            return lead + f"{words['contact_departure']} {' '.join(frequency)}, {words['good_day']}."
        return None
    if kind == "clearance":
        sid = " ".join(sid_words(data.sid, language))
        code = data.squawk or squawk_for(f"{data.callsign}|{data.destination}|{data.runway}")
        squawk = " ".join(_digits(language, code))
        if not (data.destination and runway and squawk):
            return None
        if french:
            route = f"départ {sid}, " if sid else ""
            return lead + f"autorisé {data.destination}, {route}piste {rw}, transpondeur {squawk}."
        route = f" via {sid} departure" if sid else ""
        return lead + f"cleared to {data.destination}{route}, runway {rw}, squawk {squawk}."
    if kind == "cabin_boarding":
        count = " ".join(_digits(language, str(data.passengers))) if data.passengers else ""
        if french:
            return ("Commandant, ici la cabine : embarquement terminé"
                    + (f", {count} passagers à bord." if count else "."))
        return "Captain, cabin: boarding completed" + (f", {count} passengers on board." if count else ".")
    if kind == "loadsheet":
        return ("Commandant, ici la piste : le devis de masse et centrage définitif est prêt."
                if french else "Captain, ramp: the final loadsheet is ready.")
    if kind == "pushback_approved":
        facing = " ".join(facing_words(data.pushback_heading, language))
        if french:
            return lead + ("repoussage approuvé" + (f", face {facing}." if facing else "."))
        return lead + ("pushback approved" + (f", facing {facing}." if facing else "."))
    if kind == "pushback_start":
        return ("Freins desserrés, on repousse." if french
                else "Brakes released, pushing back now.")
    if kind == "pushback_complete":
        return ("Repoussage terminé, serrez le frein de parc. Je déconnecte, bon vol."
                if french else "Pushback complete, set parking brake. Disconnecting, have a nice flight.")
    if kind == "taxi" and runway:
        via = taxiway_words(data.taxiways, language)
        route = f" via {via[0]}" if via else ""
        if french:
            return lead + f"roulez point d’arrêt piste {rw}{route}."
        return lead + f"taxi to holding point runway {rw}{route}."
    if kind == "arrival_taxi":
        stand = " ".join(stand_words(data.stand, language))
        if french:
            return lead + (f"roulez au poste {stand}." if stand else "roulez au parking.")
        return lead + (f"taxi to stand {stand}." if stand else "taxi to the stand.")
    if kind == "chocks":
        return ("Cales en place, vous pouvez couper les moteurs." if french
                else "Chocks in, you may shut down the engines.")
    return None


def speaker_for(kind: str) -> str:
    return KINDS[kind]

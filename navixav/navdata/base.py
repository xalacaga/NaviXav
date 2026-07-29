"""Types et interface communs aux fournisseurs de données de navigation.

L'implémentation de référence est `MsfsProvider` : la base NaviXav, alimentée
depuis MSFS par l'API Facilities de SimConnect. Un autre fournisseur (CIFP
X-Plane, cycle ARINC…) n'a qu'à respecter le protocole `NavdataProvider`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, Sequence


class ProcedureKind(str, Enum):
    SID = "SID"
    STAR = "STAR"
    APPROACH = "APPROACH"


@dataclass(frozen=True)
class Airport:
    ident: str
    name: str
    city: str | None
    country: str | None
    lat: float
    lon: float
    altitude_ft: float | None
    mag_var: float | None
    transition_altitude_ft: int | None
    transition_level_ft: int | None


@dataclass(frozen=True)
class Runway:
    """Une extrémité de piste utilisable (ex. « 32R »)."""

    name: str
    heading_true_deg: float
    length_ft: float
    width_ft: float | None
    surface: str | None
    ils_ident: str | None
    is_landing: bool
    is_takeoff: bool
    lat: float
    lon: float

    @property
    def has_ils(self) -> bool:
        return bool(self.ils_ident)


@dataclass(frozen=True)
class ProcedureLeg:
    leg_type: str
    fix_ident: str | None
    fix_type: str | None
    is_missed: bool
    alt_descriptor: str | None
    altitude1_ft: float | None
    altitude2_ft: float | None
    speed_limit_kt: int | None
    speed_limit_type: str | None
    course_deg: float | None
    distance_nm: float | None
    lat: float | None
    lon: float | None
    vertical_angle_deg: float | None = None
    is_faf: bool = False


@dataclass(frozen=True)
class Transition:
    """Transition d'une procédure (entrée de STAR/approche, sortie de SID)."""

    ident: str
    transition_type: str | None
    legs: tuple[ProcedureLeg, ...] = ()

    @property
    def entry_fix(self) -> str | None:
        return _first_fix(self.legs)

    @property
    def exit_fix(self) -> str | None:
        return _last_fix(self.legs)


@dataclass(frozen=True)
class Procedure:
    provider_id: int
    kind: ProcedureKind
    ident: str
    arinc_name: str | None
    proc_type: str | None
    suffix: str | None
    runway_name: str | None
    runways: tuple[str, ...]
    legs: tuple[ProcedureLeg, ...] = ()
    transitions: tuple[Transition, ...] = ()
    has_gps_overlay: bool = False
    ils_ident: str | None = None
    requires_rnp: bool = False
    missed_altitude_ft: int | None = None

    @property
    def missed_approach_altitude_ft(self) -> int | None:
        """Altitude de remise de gaz, publiée ou reconstituée.

        Le champ dédié n'est renseigné que par certaines sources. À défaut,
        on retient
        l'altitude la plus haute imposée aux segments d'approche interrompue,
        qui redonne la valeur publiée sur les cas vérifiables.
        """
        if self.missed_altitude_ft:
            return self.missed_altitude_ft
        altitudes = [
            int(leg.altitude1_ft)
            for leg in self.legs
            if leg.is_missed and leg.altitude1_ft
        ]
        return max(altitudes) if altitudes else None

    @property
    def has_published_transitions(self) -> bool:
        """L'approche publie-t-elle des segments initiaux depuis un IAF ?"""
        return bool(self.transitions)

    @property
    def has_artificial_entry(self) -> bool:
        """L'entrée est-elle un point fictif d'interception (« CF32R ») ?

        En ARINC 424, une variante prévue pour le guidage radar débute sur un
        repère synthétique nommé CF + piste, et non sur un IAF publié.
        """
        entry = self.entry_fix
        return bool(entry and _ARTIFICIAL_ENTRY_RE.match(entry))

    @property
    def is_vectors_entry(self) -> bool:
        """Variante destinée au guidage radar plutôt qu'à une arrivée publiée.

        C'est la structure qui distingue « ILS Y » de « ILS Z », pas la lettre :
        celle-ci n'est qu'un identifiant attribué à rebours depuis Z et ne porte
        aucune notion de priorité.
        """
        return not self.has_published_transitions and self.has_artificial_entry

    @property
    def entry_fix(self) -> str | None:
        """Premier point publié (pertinent pour une STAR ou une approche)."""
        return _first_fix(self.legs)

    @property
    def exit_fix(self) -> str | None:
        """Dernier point publié hors approche interrompue (sortie de SID/STAR)."""
        return _last_fix(self.legs)

    @property
    def display_name(self) -> str:
        if self.kind is not ProcedureKind.APPROACH:
            return self.ident
        parts = [self.proc_type or "APP"]
        if self.suffix:
            parts.append(self.suffix)
        if self.runway_name:
            parts.append(f"RWY {self.runway_name}")
        return " ".join(parts)

    def serves_runway(self, runway_name: str) -> bool:
        return _normalise_runway(runway_name) in self.runways

    def transition_idents(self) -> tuple[str, ...]:
        return tuple(t.ident for t in self.transitions)

    def find_transition(self, ident: str) -> Transition | None:
        for transition in self.transitions:
            if transition.ident == ident:
                return transition
        return None


class NavdataProvider(Protocol):
    """Interface minimale attendue par le moteur de complétion."""

    @property
    def airac_cycle(self) -> str: ...

    @property
    def source_name(self) -> str: ...

    @property
    def supports_rnp_flag(self) -> bool: ...

    def airport(self, icao: str) -> Airport | None: ...

    def runways(self, icao: str) -> list[Runway]: ...

    def procedures(self, icao: str, kind: ProcedureKind) -> list[Procedure]: ...

    def ils_frequency(self, icao: str, runway_name: str) -> float | None: ...

    def is_airway(self, name: str) -> bool: ...

    def fix_position(
        self, ident: str, icao: str | None = None
    ) -> tuple[float, float] | None:
        """Position d'un repère.

        `icao` rattache la recherche à un aérodrome ; il est indispensable pour
        les repères de seuil de piste, homonymes d'un terrain à l'autre.
        """
        ...

    def close(self) -> None: ...


# --------------------------------------------------------------------------- #
# Helpers partagés
# --------------------------------------------------------------------------- #

_RUNWAY_RE = re.compile(r"^(?:RW)?(\d{1,2})([LRCB]?)$")

# Repère d'interception synthétique : « CF32R », « CF05 ».
_ARTIFICIAL_ENTRY_RE = re.compile(r"^CF\d{1,2}[LRC]?$")


def _first_fix(legs: Sequence[ProcedureLeg]) -> str | None:
    for leg in legs:
        if not leg.is_missed and leg.fix_ident:
            return leg.fix_ident
    return None


def _last_fix(legs: Sequence[ProcedureLeg]) -> str | None:
    for leg in reversed(legs):
        if not leg.is_missed and leg.fix_ident:
            return leg.fix_ident
    return None


def _normalise_runway(name: str) -> str:
    """« RW05 », « 5 », « 05L » -> « 05 », « 05L »."""
    match = _RUNWAY_RE.match(name.strip().upper())
    if not match:
        return name.strip().upper()
    number, designator = match.groups()
    return f"{int(number):02d}{designator}"


def expand_arinc_runways(
    arinc_name: str | None,
    runway_name: str | None,
    available: Sequence[str],
) -> tuple[str, ...]:
    """Développe la désignation ARINC d'une procédure en pistes concrètes.

    « RW05 » -> ('05',) ; « RW32B » -> ('32L', '32R') ; « ALL »/None -> toutes.
    """
    normalised_available = tuple(_normalise_runway(r) for r in available)

    if runway_name:
        target = _normalise_runway(runway_name)
        if target in normalised_available:
            return (target,)

    token = (arinc_name or "").strip().upper()
    if not token or token in {"ALL", "RWALL"}:
        return normalised_available

    match = _RUNWAY_RE.match(token)
    if not match:
        return normalised_available

    number, designator = match.groups()
    base = f"{int(number):02d}"

    if designator == "B":
        # « B » = toutes les pistes parallèles portant ce numéro.
        matched = tuple(r for r in normalised_available if r.startswith(base))
        return matched or normalised_available
    if designator:
        candidate = f"{base}{designator}"
        return (candidate,) if candidate in normalised_available else (candidate,)

    if base in normalised_available:
        return (base,)
    # Piste unique publiée sans suffixe alors que l'aéroport en a plusieurs.
    matched = tuple(r for r in normalised_available if r.startswith(base))
    return matched or (base,)


def normalise_runway(name: str) -> str:
    return _normalise_runway(name)


@dataclass
class NavdataError(Exception):
    message: str
    details: str = field(default="")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message if not self.details else f"{self.message} ({self.details})"

"""Normalisation du JSON SimBrief en une structure exploitable.

Le JSON SimBrief est volumineux et peu régulier : certains champs sont des
listes, d'autres un objet unique quand il n'y a qu'un élément. Ce module en
extrait le strict nécessaire pour le moteur de complétion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

# Points calculés par SimBrief, absents de la navdata réelle.
_PSEUDO_FIXES = {"TOC", "TOD", "T/C", "T/D", "ETP", "EEP", "EXP"}


@dataclass
class NavlogFix:
    ident: str
    name: str = ""
    fix_type: str = ""
    via_airway: str = ""
    is_sid_star: bool = False
    stage: str = ""

    @property
    def is_real_fix(self) -> bool:
        return bool(self.ident) and self.ident.upper() not in _PSEUDO_FIXES


@dataclass
class DispatchSummary:
    """Données de dispatch de l'OFP : masses, carburant, temps, distances.

    Tous les champs sont optionnels : SimBrief ne renvoie pas les mêmes clés
    selon le profil d'avion et les options du compte. Un champ absent reste à
    None et n'est simplement pas affiché.
    """

    units: str = ""  # « kgs » ou « lbs »

    # Masses
    oew: int | None = None
    payload: int | None = None
    zfw: int | None = None
    max_zfw: int | None = None
    takeoff_weight: int | None = None
    max_takeoff_weight: int | None = None
    landing_weight: int | None = None
    max_landing_weight: int | None = None
    passengers: int | None = None
    bags: int | None = None
    cargo: int | None = None

    # Carburant
    block_fuel: int | None = None
    taxi_fuel: int | None = None
    trip_fuel: int | None = None
    contingency_fuel: int | None = None
    alternate_fuel: int | None = None
    reserve_fuel: int | None = None
    extra_fuel: int | None = None
    min_takeoff_fuel: int | None = None
    landing_fuel: int | None = None
    average_fuel_flow: int | None = None
    max_tanks: int | None = None

    # Profil et performances
    cost_index: str = ""
    cruise_profile: str = ""
    climb_profile: str = ""
    descent_profile: str = ""
    average_wind_component: str = ""
    average_wind_direction: str = ""
    average_wind_speed: str = ""
    average_temperature_dev: str = ""
    tropopause_ft: int | None = None

    # Distances et temps
    route_distance_nm: int | None = None
    air_distance_nm: int | None = None
    great_circle_distance_nm: int | None = None
    time_enroute_s: int | None = None
    block_time_s: int | None = None
    off_block: datetime | None = None
    takeoff: datetime | None = None
    landing: datetime | None = None
    on_block: datetime | None = None

    # Dégagement
    alternate_route: str = ""
    alternate_distance_nm: int | None = None
    alternate_time_s: int | None = None
    alternate_burn: int | None = None
    alternate_altitude_ft: int | None = None
    alternate_metar: str | None = None
    alternate_taf: str | None = None

    # Divers
    registration: str = ""
    equipment: str = ""
    selcal: str = ""
    atc_flightplan_text: str = ""
    ofp_pdf_link: str = ""

    @property
    def unit_label(self) -> str:
        return {"kgs": "kg", "lbs": "lb"}.get(self.units.lower(), self.units or "")


@dataclass
class OfpSummary:
    """Vue normalisée d'un OFP SimBrief."""

    origin_icao: str = ""
    destination_icao: str = ""
    alternate_icao: str | None = None
    aircraft_icao: str = ""
    aircraft_name: str = ""
    callsign: str = ""
    route: str = ""
    cruise_altitude_ft: int | None = None
    generated_at: datetime | None = None
    airac: str = ""

    origin_planned_runway: str | None = None
    destination_planned_runway: str | None = None

    origin_metar: str | None = None
    destination_metar: str | None = None

    origin_taf: str | None = None
    destination_taf: str | None = None

    navlog: list[NavlogFix] = field(default_factory=list)

    # Noms de procédures tels que SimBrief les a filés, s'ils existent.
    simbrief_sid: str | None = None
    simbrief_star: str | None = None

    # Points de raccord : dernier point du bloc SID et premier point du bloc
    # STAR dans le navlog. Ce sont les identifiants que la SID doit atteindre
    # et que la STAR doit reprendre.
    sid_exit_hint: str | None = None
    star_entry_hint: str | None = None

    dispatch: DispatchSummary = field(default_factory=DispatchSummary)

    @property
    def enroute_fixes(self) -> list[str]:
        """Points en route, hors SID/STAR, hors points pseudo et aéroports."""
        fixes: list[str] = []
        for fix in self.navlog:
            if fix.is_sid_star or not fix.is_real_fix:
                continue
            if fix.fix_type.lower() in {"apt", "airport"}:
                continue
            if fixes and fixes[-1] == fix.ident:
                continue
            fixes.append(fix.ident)
        return fixes

    @property
    def enroute_route(self) -> list[dict[str, str]]:
        """Séquence VIA/TO du navlog, hors procédures et points calculés."""
        route: list[dict[str, str]] = []
        for fix in self.navlog:
            if fix.is_sid_star or not fix.is_real_fix:
                continue
            if fix.fix_type.lower() in {"apt", "airport"}:
                continue
            if route and route[-1]["to"] == fix.ident:
                continue
            route.append({
                "via": fix.via_airway or "DCT",
                "to": fix.ident,
                "stage": fix.stage.upper(),
            })
        return route

    @property
    def first_enroute_fix(self) -> str | None:
        fixes = self.enroute_fixes
        return fixes[0] if fixes else None

    @property
    def last_enroute_fix(self) -> str | None:
        fixes = self.enroute_fixes
        return fixes[-1] if fixes else None

    def route_tokens(self) -> list[str]:
        return [t for t in self.route.replace("\n", " ").split(" ") if t]


def parse_ofp(data: dict[str, Any]) -> OfpSummary:
    origin = _as_dict(data.get("origin"))
    destination = _as_dict(data.get("destination"))
    alternate = _first_dict(data.get("alternate"))
    aircraft = _as_dict(data.get("aircraft"))
    general = _as_dict(data.get("general"))
    atc = _as_dict(data.get("atc"))
    params = _as_dict(data.get("params"))
    weather = _as_dict(data.get("weather"))

    navlog = _parse_navlog(data.get("navlog"))
    sid_block = _leading_procedure_block(navlog)
    star_block = _trailing_procedure_block(navlog)
    sid = _block_procedure_name(sid_block)
    star = _block_procedure_name(star_block)

    summary = OfpSummary(
        origin_icao=_text(origin, "icao_code").upper(),
        destination_icao=_text(destination, "icao_code").upper(),
        alternate_icao=_text(alternate, "icao_code").upper() or None,
        aircraft_icao=(_text(aircraft, "icaocode") or _text(aircraft, "icao_code")).upper(),
        aircraft_name=_text(aircraft, "name"),
        callsign=_text(atc, "callsign") or _text(general, "icao_airline")
        + _text(general, "flight_number"),
        route=_text(general, "route") or _text(atc, "route"),
        cruise_altitude_ft=_int(general, "initial_altitude"),
        generated_at=_timestamp(params.get("time_generated")),
        airac=_text(params, "airac"),
        origin_planned_runway=_runway(origin, "plan_rwy"),
        destination_planned_runway=_runway(destination, "plan_rwy"),
        origin_metar=_text(weather, "orig_metar") or _text(origin, "metar") or None,
        destination_metar=_text(weather, "dest_metar")
        or _text(destination, "metar")
        or None,
        origin_taf=_text(weather, "orig_taf") or _text(origin, "taf") or None,
        destination_taf=_text(weather, "dest_taf") or _text(destination, "taf") or None,
        navlog=navlog,
        simbrief_sid=sid,
        simbrief_star=star,
        sid_exit_hint=sid_block[-1].ident if sid_block else None,
        star_entry_hint=star_block[0].ident if star_block else None,
        dispatch=_parse_dispatch(data),
    )
    return summary


def _parse_dispatch(data: dict[str, Any]) -> DispatchSummary:
    """Extraction tolérante : toute clé absente reste à None."""
    general = _as_dict(data.get("general"))
    params = _as_dict(data.get("params"))
    fuel = _as_dict(data.get("fuel"))
    weights = _as_dict(data.get("weights"))
    times = _as_dict(data.get("times"))
    aircraft = _as_dict(data.get("aircraft"))
    atc = _as_dict(data.get("atc"))
    alternate = _first_dict(data.get("alternate"))
    files = _as_dict(data.get("files"))
    weather = _as_dict(data.get("weather"))

    return DispatchSummary(
        units=_text(params, "units") or _text(general, "units"),
        oew=_int(weights, "oew"),
        payload=_int(weights, "payload"),
        zfw=_int(weights, "est_zfw"),
        max_zfw=_int(weights, "max_zfw"),
        takeoff_weight=_int(weights, "est_tow"),
        max_takeoff_weight=_int(weights, "max_tow"),
        landing_weight=_int(weights, "est_ldw"),
        max_landing_weight=_int(weights, "max_ldw"),
        passengers=_int(weights, "pax_count_actual") or _int(weights, "pax_count"),
        bags=_int(weights, "bag_count_actual") or _int(weights, "bag_count"),
        cargo=_int(weights, "cargo"),
        block_fuel=_int(fuel, "plan_ramp"),
        taxi_fuel=_int(fuel, "taxi"),
        trip_fuel=_int(fuel, "enroute_burn"),
        contingency_fuel=_int(fuel, "contingency"),
        alternate_fuel=_int(fuel, "alternate_burn"),
        reserve_fuel=_int(fuel, "reserve"),
        extra_fuel=_int(fuel, "extra"),
        min_takeoff_fuel=_int(fuel, "min_takeoff"),
        landing_fuel=_int(fuel, "plan_landing"),
        average_fuel_flow=_int(fuel, "avg_fuel_flow"),
        max_tanks=_int(fuel, "max_tanks"),
        cost_index=_text(general, "costindex") or _text(general, "cost_index"),
        cruise_profile=_text(general, "cruise_profile"),
        climb_profile=_text(general, "climb_profile"),
        descent_profile=_text(general, "descent_profile"),
        average_wind_component=_text(general, "avg_wind_comp"),
        average_wind_direction=_text(general, "avg_wind_dir"),
        average_wind_speed=_text(general, "avg_wind_spd"),
        average_temperature_dev=_text(general, "avg_temp_dev"),
        tropopause_ft=_int(general, "avg_tropopause"),
        route_distance_nm=_int(general, "route_distance"),
        air_distance_nm=_int(general, "air_distance"),
        great_circle_distance_nm=_int(general, "gc_distance"),
        time_enroute_s=_int(times, "est_time_enroute"),
        block_time_s=_int(times, "est_block"),
        off_block=_timestamp(times.get("est_out")),
        takeoff=_timestamp(times.get("est_off")),
        landing=_timestamp(times.get("est_on")),
        on_block=_timestamp(times.get("est_in")),
        alternate_route=_text(alternate, "route"),
        alternate_distance_nm=_int(alternate, "distance"),
        alternate_time_s=_int(alternate, "ete"),
        alternate_burn=_int(alternate, "burn"),
        alternate_altitude_ft=_int(alternate, "cruise_altitude"),
        alternate_metar=_text(weather, "altn_metar") or None,
        alternate_taf=_text(weather, "altn_taf") or None,
        registration=_text(aircraft, "reg"),
        equipment=_text(aircraft, "equip"),
        selcal=_text(aircraft, "selcal"),
        atc_flightplan_text=_text(atc, "flightplan_text"),
        ofp_pdf_link=_text(_as_dict(files.get("pdf")), "link"),
    )


# --------------------------------------------------------------------------- #
# Helpers de normalisation
# --------------------------------------------------------------------------- #


def _parse_navlog(raw: Any) -> list[NavlogFix]:
    # SimBrief renvoie soit {"navlog": {"fix": [...]}}, soit directement la liste.
    if isinstance(raw, dict):
        entries = _as_list(raw.get("fix"))
    else:
        entries = _as_list(raw)
    fixes: list[NavlogFix] = []
    for entry in entries:
        item = _as_dict(entry)
        if not item:
            continue
        ident = _text(item, "ident").upper()
        if not ident:
            continue
        fixes.append(
            NavlogFix(
                ident=ident,
                name=_text(item, "name"),
                fix_type=_text(item, "type"),
                via_airway=_text(item, "via_airway").upper(),
                is_sid_star=_text(item, "is_sid_star") in {"1", "true", "True"},
                stage=_text(item, "stage"),
            )
        )
    return fixes


def _block_procedure_name(block: list[NavlogFix]) -> str | None:
    """Nom de procédure porté par un bloc du navlog.

    SimBrief place le nom de la SID/STAR dans `via_airway` de chaque segment
    concerné ; on retient le nom le plus représenté du bloc.
    """
    names = [f.via_airway for f in block if f.via_airway and f.via_airway != "DCT"]
    if not names:
        return None
    return max(set(names), key=names.count)


def _is_airport(fix: NavlogFix) -> bool:
    return fix.fix_type.lower() in {"apt", "airport"}


def _leading_procedure_block(navlog: list[NavlogFix]) -> list[NavlogFix]:
    """Points de tête marqués SID, en ignorant l'aéroport de départ."""
    block: list[NavlogFix] = []
    for fix in navlog:
        if _is_airport(fix) and not block:
            continue
        if not fix.is_real_fix and not block:
            continue
        if fix.is_sid_star:
            block.append(fix)
            continue
        break
    return block


def _trailing_procedure_block(navlog: list[NavlogFix]) -> list[NavlogFix]:
    """Points de queue marqués STAR, en ignorant l'aéroport d'arrivée."""
    block: list[NavlogFix] = []
    for fix in reversed(navlog):
        if _is_airport(fix) and not block:
            continue
        if not fix.is_real_fix and not block:
            continue
        if fix.is_sid_star:
            block.insert(0, fix)
            continue
        break
    return block


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def _first_dict(value: Any) -> dict[str, Any]:
    return _as_dict(value)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _text(source: dict[str, Any] | None, key: str) -> str:
    if not source:
        return ""
    value = source.get(key)
    if value is None or isinstance(value, (dict, list)):
        return ""
    return str(value).strip()


def _int(source: dict[str, Any] | None, key: str) -> int | None:
    raw = _text(source, key)
    if not raw:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def _runway(source: dict[str, Any] | None, key: str) -> str | None:
    raw = _text(source, key).upper()
    if not raw or raw in {"NONE", "N/A", "0"}:
        return None
    return raw.removeprefix("RW")


def _timestamp(value: Any) -> datetime | None:
    if value in (None, "", "0"):
        return None
    try:
        return datetime.fromtimestamp(int(str(value)), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def iter_idents(fixes: Iterable[NavlogFix]) -> list[str]:
    return [f.ident for f in fixes]

"""Rendu terminal du plan complété, dans l'esprit du panneau Navigraph."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from navixav import format as fmt
from navixav.models import ArrivalBlock, Choice, Confidence, DepartureBlock, FlightPlan

_CONFIDENCE_STYLE = {
    Confidence.HIGH: "green",
    Confidence.MEDIUM: "yellow",
    Confidence.LOW: "red",
    Confidence.NONE: "dim",
}

_SOURCE_LABEL = {
    "simbrief": "SimBrief",
    "moteur": "calculé",
    "utilisateur": "imposé",
}


def render_plan(plan: FlightPlan, console: Console | None = None) -> None:
    console = console or Console()

    origin = plan.departure.icao if plan.departure else "????"
    destination = plan.arrival.icao if plan.arrival else "????"

    header = Text()
    header.append(f"{origin} → {destination}", style="bold")
    details = [plan.aircraft or "type inconnu"]
    if plan.callsign:
        details.append(plan.callsign)
    if plan.alternate_icao:
        details.append(f"dégagement {plan.alternate_icao}")
    header.append("   " + " · ".join(details), style="dim")

    source = plan.source
    subtitle = (
        f"navdata {source.get('navdata_source', '?')} · AIRAC "
        f"{source.get('navdata_airac', '?')}"
    )
    if source.get("simbrief_airac"):
        subtitle += f" · OFP AIRAC {source['simbrief_airac']}"

    console.print(Panel(header, subtitle=subtitle, border_style="cyan"))

    if plan.departure:
        console.print(_departure_table(plan.departure))
    console.print(_enroute_panel(plan))
    if plan.arrival:
        console.print(_arrival_table(plan.arrival))

    dispatch = _dispatch_tables(plan)
    if dispatch is not None:
        console.print(dispatch)

    if plan.warnings:
        console.print(
            Panel(
                Group(*[Text(f"• {w}") for w in plan.warnings]),
                title="Avertissements",
                border_style="yellow",
            )
        )


def _section_table(title: str, subtitle: str) -> Table:
    table = Table(
        title=f"[bold]{title}[/bold]  [dim]{subtitle}[/dim]",
        title_justify="left",
        show_header=False,
        box=None,
        pad_edge=False,
        padding=(0, 1),
    )
    table.add_column("champ", style="dim", width=12)
    table.add_column("valeur", style="bold", width=18)
    table.add_column("confiance", width=10)
    table.add_column("justification", overflow="fold")
    return table


def _add_choice_row(table: Table, label: str, choice: Choice, extra: str = "") -> None:
    value = choice.value or "—"
    style = _CONFIDENCE_STYLE[choice.confidence]
    detail = choice.reason
    if extra:
        detail = f"{extra} · {detail}" if detail else extra
    origin = _SOURCE_LABEL.get(choice.source, choice.source)
    table.add_row(
        label,
        Text(value, style="bold" if choice.value else "dim"),
        Text(choice.confidence.value, style=style),
        Text(f"[{origin}] {detail}".strip(), style="dim"),
    )


def _departure_table(block: DepartureBlock) -> Table:
    table = _section_table("DÉPART", f"{block.icao} · {block.name}")
    table.add_row("METAR", "", "", Text(block.wind.raw_metar or "indisponible", style="dim"))
    table.add_row("Vent", Text(block.wind.label(), style="bold"), "", "")

    if block.runway:
        extra = _runway_extra(block)
        _add_choice_row(table, "Piste", block.runway.choice, extra)
    _add_choice_row(table, "SID", block.sid)
    _add_choice_row(table, "Transition", block.sid_transition)
    if block.transition_altitude_ft:
        table.add_row("Alt. trans.", f"{block.transition_altitude_ft} ft", "", "")
    return table


def _arrival_table(block: ArrivalBlock) -> Table:
    table = _section_table("ARRIVÉE", f"{block.icao} · {block.name}")
    table.add_row("METAR", "", "", Text(block.wind.raw_metar or "indisponible", style="dim"))
    table.add_row("Vent", Text(block.wind.label(), style="bold"), "", "")

    if block.runway:
        extra = _runway_extra(block)
        _add_choice_row(table, "Piste", block.runway.choice, extra)
    _add_choice_row(table, "STAR", block.star)
    _add_choice_row(table, "Transition", block.star_transition)
    _add_choice_row(table, "Approche", block.approach)
    _add_choice_row(table, "Trans. app.", block.approach_transition)
    if block.ils_frequency_mhz:
        table.add_row("ILS", f"{block.ils_frequency_mhz:.2f} MHz", "", "")
    if block.transition_level_ft:
        table.add_row("Niv. trans.", f"{block.transition_level_ft} ft", "", "")
    return table


def _runway_extra(block: DepartureBlock | ArrivalBlock) -> str:
    runway = block.runway
    if runway is None:
        return ""
    parts: list[str] = []
    if runway.headwind_kt is not None:
        parts.append(f"face {runway.headwind_kt:+.0f} kt")
    if runway.crosswind_kt is not None:
        parts.append(f"trav. {runway.crosswind_kt:.0f} kt")
    if runway.length_ft:
        parts.append(f"{runway.length_ft:.0f} ft")
    if runway.ils_ident:
        parts.append(f"ILS {runway.ils_ident}")
    return " · ".join(parts)


def _dispatch_tables(plan: FlightPlan) -> Panel | None:
    """Synthèse du dispatch SimBrief : masses, carburant, temps, dégagement."""
    d = plan.dispatch
    unit = d.unit_label

    masses = _pairs(
        ("Passagers", str(d.passengers) if d.passengers is not None else None),
        ("Fret", fmt.mass(d.cargo, unit)),
        ("Charge marchande", fmt.mass(d.payload, unit)),
        ("Masse à vide", fmt.mass(d.oew, unit)),
        ("ZFW", fmt.ratio(d.zfw, d.max_zfw, unit)),
        ("Décollage", fmt.ratio(d.takeoff_weight, d.max_takeoff_weight, unit)),
        ("Atterrissage", fmt.ratio(d.landing_weight, d.max_landing_weight, unit)),
    )
    fuel = _pairs(
        ("Bloc", fmt.mass(d.block_fuel, unit)),
        ("Roulage", fmt.mass(d.taxi_fuel, unit)),
        ("Étape", fmt.mass(d.trip_fuel, unit)),
        ("Imprévus", fmt.mass(d.contingency_fuel, unit)),
        ("Dégagement", fmt.mass(d.alternate_fuel, unit)),
        ("Réserve finale", fmt.mass(d.reserve_fuel, unit)),
        ("Supplément", fmt.mass(d.extra_fuel, unit)),
        ("Mini décollage", fmt.mass(d.min_takeoff_fuel, unit)),
        ("Restant à l'arrivée", fmt.mass(d.landing_fuel, unit)),
        ("Conso horaire", fmt.mass(d.average_fuel_flow, f"{unit}/h" if unit else "")),
        ("Capacité", fmt.mass(d.max_tanks, unit)),
    )
    profile = _pairs(
        ("Cost index", d.cost_index or None),
        ("Croisière", d.cruise_profile or None),
        ("Montée", d.climb_profile or None),
        ("Descente", d.descent_profile or None),
        ("Vent moyen", _wind_summary(d)),
        ("Écart ISA", f"{d.average_temperature_dev} °C" if d.average_temperature_dev else None),
        ("Tropopause", fmt.flight_level(d.tropopause_ft)),
    )
    legs = _pairs(
        ("Distance route", fmt.distance(d.route_distance_nm)),
        ("Distance air", fmt.distance(d.air_distance_nm)),
        ("Orthodromie", fmt.distance(d.great_circle_distance_nm)),
        ("Temps de vol", fmt.duration(d.time_enroute_s)),
        ("Temps bloc", fmt.duration(d.block_time_s)),
        ("Départ bloc", fmt.clock(d.off_block)),
        ("Décollage", fmt.clock(d.takeoff)),
        ("Atterrissage", fmt.clock(d.landing)),
        ("Arrivée bloc", fmt.clock(d.on_block)),
    )
    alternate = _pairs(
        ("Terrain", plan.alternate_icao),
        ("Route", d.alternate_route or None),
        ("Distance", fmt.distance(d.alternate_distance_nm)),
        ("Temps", fmt.duration(d.alternate_time_s)),
        ("Carburant", fmt.mass(d.alternate_burn, unit)),
        ("Niveau", fmt.flight_level(d.alternate_altitude_ft)),
        ("METAR", d.alternate_metar),
    )
    aircraft = _pairs(
        ("Immatriculation", d.registration or None),
        ("Équipement", d.equipment or None),
        ("SELCAL", d.selcal or None),
    )

    groups = [
        ("Masses", masses),
        ("Carburant", fuel),
        ("Profil", profile),
        ("Distances et temps", legs),
        ("Dégagement", alternate),
        ("Avion", aircraft),
    ]
    populated = [(title, rows) for title, rows in groups if rows]
    if not populated:
        return None

    blocks: list[object] = []
    for index, (title, rows) in enumerate(populated):
        if index:
            blocks.append(Text(""))
        blocks.append(_key_value_table(title, rows))

    if d.atc_flightplan_text:
        blocks.append(Text(""))
        blocks.append(Text("Plan de vol OACI", style="bold"))
        blocks.append(Text(d.atc_flightplan_text, style="dim"))

    return Panel(
        Group(*blocks),
        title="DISPATCH SIMBRIEF",
        title_align="left",
        border_style="magenta",
    )


def _pairs(*items: tuple[str, str | None]) -> list[tuple[str, str]]:
    return [(label, value) for label, value in items if value]


def _key_value_table(title: str, rows: list[tuple[str, str]]) -> Table:
    table = Table(
        title=f"[bold]{title}[/bold]",
        title_justify="left",
        show_header=False,
        box=None,
        pad_edge=False,
        padding=(0, 1),
    )
    table.add_column("champ", style="dim", width=20, no_wrap=True)
    table.add_column("valeur", overflow="fold")
    for label, value in rows:
        table.add_row(label, value)
    return table


def _wind_summary(dispatch) -> str | None:
    component = dispatch.average_wind_component
    direction = dispatch.average_wind_direction
    speed = dispatch.average_wind_speed
    if direction and speed:
        base = f"{direction}°/{speed} kt"
        return f"{base} (composante {component} kt)" if component else base
    return f"composante {component} kt" if component else None


def _enroute_panel(plan: FlightPlan) -> Panel:
    enroute = plan.enroute
    lines = [Text(plan.atc_route() or "route indisponible", style="bold")]
    meta: list[str] = []
    if enroute.cruise_altitude_ft:
        meta.append(f"croisière {enroute.cruise_altitude_ft} ft")
    if enroute.first_fix:
        meta.append(f"premier point {enroute.first_fix}")
    if enroute.last_fix:
        meta.append(f"dernier point {enroute.last_fix}")
    if meta:
        lines.append(Text(" · ".join(meta), style="dim"))
    return Panel(Group(*lines), title="ROUTE", title_align="left", border_style="blue")

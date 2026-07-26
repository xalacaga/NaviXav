"""Fiche de saisie MCDU (Airbus).

Traduit le plan complété dans le vocabulaire du FMS Airbus. Le point qui prête
le plus à confusion est la page ARRIVAL :

    APPR   procédure d'approche          ILS Z RWY 32R
    VIA    transition d'APPROCHE         ADIMO
    STAR   arrivée normalisée            AFRI8N
    TRANS  transition d'entrée de STAR   AFRIC

« VIA » et « TRANS » désignent donc deux transitions différentes, aux deux
extrémités de la STAR — l'inverse de la lecture intuitive.
"""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from navixav import format as fmt
from navixav.models import Choice, Confidence, FlightPlan

# Marqueur des éléments à confirmer à l'ATIS avant saisie.
_TO_CONFIRM = {Confidence.MEDIUM, Confidence.LOW, Confidence.NONE}

_CONFIDENCE_STYLE = {
    Confidence.HIGH: "green",
    Confidence.MEDIUM: "yellow",
    Confidence.LOW: "red",
    Confidence.NONE: "dim",
}


def render_mcdu_card(plan: FlightPlan, console: Console | None = None) -> None:
    console = console or Console()

    sections: list[Table] = [_init_page(plan)]
    init_b = _init_b_page(plan)
    if init_b is not None:
        sections.append(init_b)
    performance = _performance_page(plan)
    if performance is not None:
        sections.append(performance)
    if plan.departure:
        sections.append(_departure_page(plan))
        constraints = _constraints_page(
            f"CONTRAINTES › {plan.departure.sid.value or 'SID'}",
            plan.departure.sid_constraints,
        )
        if constraints is not None:
            sections.append(constraints)
    if plan.arrival:
        sections.append(_arrival_page(plan))
        for title, rows in (
            (
                f"CONTRAINTES › {plan.arrival.star.value or 'STAR'}",
                plan.arrival.star_constraints,
            ),
            (
                f"CONTRAINTES › {plan.arrival.approach.value or 'APPROCHE'}",
                plan.arrival.approach_constraints,
            ),
        ):
            constraints = _constraints_page(title, rows)
            if constraints is not None:
                sections.append(constraints)
        radnav = _radnav_page(plan)
        if radnav is not None:
            sections.append(radnav)

    body: list[object] = []
    for index, table in enumerate(sections):
        if index:
            body.append(Text(""))
        body.append(table)

    to_confirm = _items_to_confirm(plan)
    if to_confirm:
        body.append(Text(""))
        body.append(
            Text(
                "À confirmer à l'ATIS avant saisie : " + ", ".join(to_confirm),
                style="yellow",
            )
        )

    origin = plan.departure.icao if plan.departure else "????"
    destination = plan.arrival.icao if plan.arrival else "????"
    console.print(
        Panel(
            Group(*body),
            title=f"SAISIE MCDU · {origin} → {destination}",
            title_align="left",
            border_style="cyan",
            padding=(1, 2),
        )
    )


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #


def _page(title: str) -> Table:
    table = Table(
        title=f"[bold]{title}[/bold]",
        title_justify="left",
        show_header=False,
        box=None,
        pad_edge=False,
        padding=(0, 1),
    )
    table.add_column("champ", style="dim", width=10, no_wrap=True)
    table.add_column("valeur", width=16)
    table.add_column("note", style="dim", overflow="fold")
    return table


def _row(table: Table, field: str, choice: Choice, note: str = "") -> None:
    value = choice.value or "—"
    style = _CONFIDENCE_STYLE[choice.confidence]
    marker = " ⚠" if choice.confidence in _TO_CONFIRM and choice.value else ""
    table.add_row(field, Text(f"{value}{marker}", style=style), note)


def _init_page(plan: FlightPlan) -> Table:
    table = _page("INIT A")
    origin = plan.departure.icao if plan.departure else "????"
    destination = plan.arrival.icao if plan.arrival else "????"
    table.add_row("FROM/TO", Text(f"{origin}/{destination}", style="bold"), "")
    if plan.alternate_icao:
        table.add_row("ALTN", Text(plan.alternate_icao, style="bold"), "")
    if plan.callsign:
        table.add_row("FLT NBR", Text(plan.callsign, style="bold"), "")
    if plan.dispatch.cost_index:
        table.add_row("COST INDEX", Text(plan.dispatch.cost_index, style="bold"), "")
    level = fmt.flight_level(plan.enroute.cruise_altitude_ft)
    if level:
        table.add_row("CRZ FL", Text(level, style="bold"), "")
    return table


def _init_b_page(plan: FlightPlan) -> Table | None:
    """Masses et carburant, tels qu'on les saisit sur INIT B."""
    dispatch = plan.dispatch
    unit = dispatch.unit_label
    rows = [
        ("ZFW", fmt.mass(dispatch.zfw, unit)),
        ("BLOCK", fmt.mass(dispatch.block_fuel, unit)),
        ("TAXI", fmt.mass(dispatch.taxi_fuel, unit)),
        ("TRIP", fmt.mass(dispatch.trip_fuel, unit)),
        ("RSV", fmt.mass(dispatch.reserve_fuel, unit)),
        ("ALTN", fmt.mass(dispatch.alternate_fuel, unit)),
        ("FINAL", fmt.mass(dispatch.landing_fuel, unit)),
    ]
    present = [(name, value) for name, value in rows if value]
    if not present:
        return None

    table = _page("INIT B")
    for name, value in present:
        table.add_row(name, Text(value, style="bold"), "")
    return table


def _performance_page(plan: FlightPlan) -> Table | None:
    dispatch = plan.dispatch
    rows = [
        ("COST INDEX", dispatch.cost_index or None, ""),
        ("CRZ FL", fmt.flight_level(plan.enroute.cruise_altitude_ft), ""),
        ("TROPO", fmt.flight_level(dispatch.tropopause_ft), ""),
        (
            "WIND",
            _average_wind(dispatch),
            "vent moyen en croisière",
        ),
        ("ETE", fmt.duration(dispatch.time_enroute_s), ""),
    ]
    present = [(name, value, note) for name, value, note in rows if value]
    if not present:
        return None

    table = _page("PERF / CRUISE")
    for name, value, note in present:
        table.add_row(name, Text(value, style="bold"), note)
    return table


def _constraints_page(title: str, rows: list) -> Table | None:
    """Contraintes publiées à vérifier après insertion de la procédure."""
    if not rows:
        return None
    table = _page(title)
    for row in rows:
        style = "bold" if row.is_fix else "bold dim"
        table.add_row(
            "", Text(row.label, style=style), Text(row.summary(), style="cyan")
        )
    return table


def _average_wind(dispatch) -> str | None:
    direction = dispatch.average_wind_direction
    speed = dispatch.average_wind_speed
    if direction and speed:
        return f"{direction}°/{speed}"
    return None


def _departure_page(plan: FlightPlan) -> Table:
    departure = plan.departure
    assert departure is not None
    table = _page("F-PLN › DEPARTURE")

    if departure.runway:
        _row(table, "RWY", departure.runway.choice, departure.wind.label())
    _row(table, "SID", departure.sid)
    _row(table, "TRANS", departure.sid_transition, "point de sortie de la SID")
    if departure.transition_altitude_ft:
        table.add_row(
            "TRANS ALT", Text(f"{departure.transition_altitude_ft}", style="bold"), ""
        )
    return table


def _arrival_page(plan: FlightPlan) -> Table:
    arrival = plan.arrival
    assert arrival is not None
    table = _page("F-PLN › ARRIVAL")

    if arrival.runway:
        _row(table, "RWY", arrival.runway.choice, arrival.wind.label())
    _row(table, "APPR", arrival.approach)
    _row(table, "VIA", arrival.approach_transition, "transition d'APPROCHE")
    _row(table, "STAR", arrival.star)
    _row(table, "TRANS", arrival.star_transition, "transition d'entrée de STAR")
    if arrival.transition_level_ft:
        table.add_row(
            "TRANS LVL", Text(f"{arrival.transition_level_ft}", style="bold"), ""
        )
    if arrival.missed_approach_altitude_ft:
        table.add_row(
            "GA ALT",
            Text(f"{arrival.missed_approach_altitude_ft} ft", style="bold"),
            "altitude de remise de gaz",
        )
    return table


def _radnav_page(plan: FlightPlan) -> Table | None:
    arrival = plan.arrival
    assert arrival is not None
    frequency = arrival.ils_frequency_mhz
    identifier = arrival.runway.ils_ident if arrival.runway else None
    if not frequency and not identifier:
        return None

    table = _page("RAD NAV")
    label = " / ".join(
        part for part in (f"{frequency:.2f}" if frequency else None, identifier) if part
    )
    table.add_row("ILS", Text(label, style="bold"), "réglage automatique en général")
    return table


# --------------------------------------------------------------------------- #


def _items_to_confirm(plan: FlightPlan) -> list[str]:
    """Éléments dont la confiance ne suffit pas pour saisir sans vérifier."""
    labels: list[tuple[str, Choice | None]] = []
    if plan.departure:
        labels += [
            ("piste départ", plan.departure.runway.choice if plan.departure.runway else None),
            ("SID", plan.departure.sid),
            ("TRANS départ", plan.departure.sid_transition),
        ]
    if plan.arrival:
        labels += [
            ("piste arrivée", plan.arrival.runway.choice if plan.arrival.runway else None),
            ("APPR", plan.arrival.approach),
            ("VIA", plan.arrival.approach_transition),
            ("STAR", plan.arrival.star),
            ("TRANS arrivée", plan.arrival.star_transition),
        ]
    return [
        name
        for name, choice in labels
        if choice is not None and choice.value and choice.confidence in _TO_CONFIRM
    ]

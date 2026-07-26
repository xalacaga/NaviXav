"""Interface en ligne de commande de NaviXav."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from navixav import __version__
from navixav.config import Settings
from navixav.navdata.base import NavdataError, ProcedureKind
from navixav.mcdu import render_mcdu_card
from navixav.planner.engine import CompletionEngine, PlannerOverrides
from navixav.render import render_plan
from navixav.simbrief.client import SimBriefClient, SimBriefError
from navixav.simbrief.parser import parse_ofp

console = Console()
error_console = Console(stderr=True)


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--env", metavar="FICHIER", help="chemin d'un fichier .env alternatif"
    )

    parser = argparse.ArgumentParser(
        prog="navixav",
        parents=[common],
        description=(
            "Complète le dernier plan de vol SimBrief avec piste, SID, STAR, "
            "approche et transitions, à partir d'une base de navigation locale."
        ),
    )
    parser.add_argument("--version", action="version", version=f"NaviXav {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    plan = subparsers.add_parser(
        "plan", parents=[common], help="compléter le dernier OFP SimBrief"
    )
    plan.add_argument("--pilot-id", help="Pilot ID SimBrief (sinon .env)")
    plan.add_argument("--username", help="alias SimBrief (sinon .env)")
    plan.add_argument(
        "--ofp", metavar="FICHIER", help="lire un OFP JSON local au lieu d'appeler SimBrief"
    )
    plan.add_argument(
        "--store", metavar="FICHIER", help="base NaviXav à utiliser"
    )
    plan.add_argument("--dep-rwy", help="forcer la piste de départ")
    plan.add_argument("--arr-rwy", help="forcer la piste d'arrivée")
    plan.add_argument("--sid", help="forcer la SID")
    plan.add_argument("--sid-trans", help="forcer la transition de SID")
    plan.add_argument("--star", help="forcer la STAR")
    plan.add_argument("--star-trans", help="forcer la transition de STAR")
    plan.add_argument("--approach", help="forcer l'approche, ex. \"ILS Z RWY 32R\"")
    plan.add_argument("--approach-trans", help="forcer la transition d'approche")
    plan.add_argument("--metar-dep", help="METAR de départ imposé")
    plan.add_argument("--metar-arr", help="METAR d'arrivée imposé")
    plan.add_argument("--no-ils", action="store_true", help="ne pas privilégier l'ILS")
    plan.add_argument(
        "--no-rnp",
        action="store_true",
        help="avion non qualifié RNP : écarte les approches qui l'exigent",
    )
    plan.add_argument(
        "--mcdu",
        action="store_true",
        help="fiche de saisie MCDU (vocabulaire Airbus) au lieu du panneau",
    )
    plan.add_argument("--json", action="store_true", help="sortie JSON au lieu du panneau")
    plan.add_argument("--out", metavar="FICHIER", help="écrire le JSON dans un fichier")
    plan.add_argument(
        "--save-ofp", metavar="FICHIER", help="enregistrer l'OFP brut récupéré"
    )

    navdata = subparsers.add_parser(
        "navdata", parents=[common], help="contenu de la base NaviXav"
    )
    navdata.add_argument("--store", metavar="FICHIER", help="base NaviXav à consulter")

    web = subparsers.add_parser(
        "web", parents=[common], help="lancer l'application web locale"
    )
    web.add_argument("--host", default="127.0.0.1", help="défaut : 127.0.0.1")
    web.add_argument("--port", type=int, default=8765, help="défaut : 8765")
    web.add_argument(
        "--no-open", action="store_true", help="ne pas ouvrir le navigateur"
    )

    importer = subparsers.add_parser(
        "import",
        parents=[common],
        help="importer des aéroports depuis MSFS dans la base NaviXav",
    )
    importer.add_argument("icao", nargs="+", help="codes OACI, ex. LFST LFBO")
    importer.add_argument(
        "--refresh", action="store_true", help="réimporter même si déjà en base"
    )
    importer.add_argument("--store", metavar="FICHIER", help="base NaviXav à alimenter")

    airport = subparsers.add_parser(
        "airport", parents=[common], help="inspecter un aéroport"
    )
    airport.add_argument("icao")
    airport.add_argument("--store", metavar="FICHIER", help="base NaviXav à consulter")
    airport.add_argument("--runway", help="ne montrer que les procédures d'une piste")

    return parser


# --------------------------------------------------------------------------- #
# Commandes
# --------------------------------------------------------------------------- #


def cmd_plan(args: argparse.Namespace, settings: Settings) -> int:
    try:
        raw = (
            SimBriefClient.from_file(args.ofp)
            if args.ofp
            else SimBriefClient(
                pilot_id=args.pilot_id or settings.simbrief_pilot_id,
                username=args.username or settings.simbrief_username,
            ).fetch_latest()
        )
    except SimBriefError as exc:
        error_console.print(f"[red]SimBrief :[/red] {exc}")
        return 2

    if args.save_ofp:
        Path(args.save_ofp).write_text(
            json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        console.print(f"[dim]OFP brut enregistré dans {args.save_ofp}[/dim]")

    ofp = parse_ofp(raw)
    if not ofp.origin_icao or not ofp.destination_icao:
        error_console.print("[red]OFP inexploitable : origine ou destination absente.[/red]")
        return 2

    try:
        provider = _open_provider(args.store)
    except NavdataError as exc:
        error_console.print(f"[red]Navdata :[/red] {exc}")
        return 3

    overrides = PlannerOverrides(
        departure_runway=args.dep_rwy,
        sid=args.sid,
        sid_transition=args.sid_trans,
        arrival_runway=args.arr_rwy,
        star=args.star,
        star_transition=args.star_trans,
        approach=args.approach,
        approach_transition=args.approach_trans,
        departure_metar=args.metar_dep,
        arrival_metar=args.metar_arr,
        prefer_ils=not args.no_ils,
        rnp_capable=False if args.no_rnp else None,
    )

    try:
        plan = CompletionEngine(provider, settings).complete(ofp, overrides)
    finally:
        provider.close()

    payload = json.dumps(plan.to_dict(), indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        console.print(f"[dim]Plan écrit dans {args.out}[/dim]")

    if args.json:
        print(payload)
    elif args.mcdu:
        render_mcdu_card(plan, console)
    else:
        render_plan(plan, console)
    return 0


def cmd_navdata(args: argparse.Namespace, settings: Settings) -> int:
    """Contenu de la base NaviXav, alimentée depuis MSFS."""
    try:
        provider = _open_provider(args.store, allow_fetch=False)
    except NavdataError as exc:
        error_console.print(f"[red]{exc}[/red]")
        return 3

    try:
        stats = provider.stats()
        if not stats["airports"]:
            console.print(
                "[yellow]Base vide.[/yellow] Lance « navixav import LFST LFBO » "
                "avec Microsoft Flight Simulator ouvert."
            )
            return 0

        console.print(f"[bold]{provider.source_name}[/bold]")
        table = Table(title="Terrains en base", title_justify="left")
        for column in ("OACI", "Terrain", "Pistes", "SID", "STAR", "Approches", "Ajouté"):
            table.add_column(column, justify="right" if column not in ("Terrain", "Ajouté") else "left")

        for row in provider.airports_in_store():
            code = row["icao"]
            counts = {kind: len(provider.procedures(code, kind)) for kind in ProcedureKind}
            table.add_row(
                code,
                row["name"],
                str(len(provider.runways(code))),
                str(counts[ProcedureKind.SID]),
                str(counts[ProcedureKind.STAR]),
                str(counts[ProcedureKind.APPROACH]),
                row["fetched_at"][:10],
            )
        console.print(table)

        extras = provider.reference_counts()
        console.print(
            f"[dim]{extras['waypoints']} repères · {extras['navaids']} installations "
            f"· {extras['airways']} segments de route.\n"
            "« navixav import » ajoute un terrain, « --refresh » le met à jour.[/dim]"
        )
        return 0
    finally:
        provider.close()


def cmd_airport(args: argparse.Namespace, settings: Settings) -> int:
    try:
        provider = _open_provider(args.store)
    except NavdataError as exc:
        error_console.print(f"[red]Navdata :[/red] {exc}")
        return 3

    try:
        icao = args.icao.strip().upper()
        airport = provider.airport(icao)
        if airport is None:
            error_console.print(f"[red]{icao} absent de la base.[/red]")
            return 4

        console.print(
            f"[bold]{airport.ident}[/bold] · {airport.name} "
            f"[dim]{airport.city or ''} {airport.country or ''}[/dim]"
        )

        runways = Table(title="Pistes", title_justify="left")
        for column in ("Piste", "Cap vrai", "Longueur", "ILS", "Surface"):
            runways.add_column(column)
        for runway in provider.runways(icao):
            runways.add_row(
                runway.name,
                f"{runway.heading_true_deg:.0f}°",
                f"{runway.length_ft:.0f} ft",
                runway.ils_ident or "—",
                runway.surface or "—",
            )
        console.print(runways)

        wanted = args.runway.strip().upper() if args.runway else None
        for kind, title in (
            (ProcedureKind.SID, "SID"),
            (ProcedureKind.STAR, "STAR"),
            (ProcedureKind.APPROACH, "Approches"),
        ):
            procedures = provider.procedures(icao, kind)
            if wanted:
                procedures = [p for p in procedures if p.serves_runway(wanted)]
            if not procedures:
                continue
            table = Table(title=title, title_justify="left")
            for column in ("Nom", "Pistes", "Entrée", "Sortie", "Transitions"):
                table.add_column(column)
            for procedure in procedures:
                table.add_row(
                    procedure.display_name,
                    ", ".join(procedure.runways) or "—",
                    procedure.entry_fix or "—",
                    procedure.exit_fix or "—",
                    ", ".join(procedure.transition_idents()) or "—",
                )
            console.print(table)
        return 0
    finally:
        provider.close()


# --------------------------------------------------------------------------- #


def cmd_import(args: argparse.Namespace, settings: Settings) -> int:
    """Alimente la base NaviXav depuis le simulateur, terrain par terrain."""
    from navixav.navdata.msfs import MsfsProvider

    try:
        provider = MsfsProvider(args.store)
    except NavdataError as exc:
        error_console.print(f"[red]{exc}[/red]")
        return 3

    table = Table(title="Import depuis MSFS", title_justify="left")
    for column in ("OACI", "Terrain", "Pistes", "SID", "STAR", "Approches", "Sol"):
        table.add_column(column, justify="right" if column != "Terrain" else "left")

    failures = 0
    try:
        for icao in args.icao:
            code = icao.strip().upper()
            try:
                fetched = provider.ensure(code, refresh=args.refresh)
            except (NavdataError, Exception) as exc:  # noqa: BLE001 - message affiché
                error_console.print(f"[red]{code} :[/red] {exc}")
                failures += 1
                continue

            airport = provider.airport(code)
            if airport is None:
                error_console.print(f"[red]{code} : introuvable dans le simulateur.[/red]")
                failures += 1
                continue

            counts = {
                kind: len(provider.procedures(code, kind)) for kind in ProcedureKind
            }
            ground = provider._conn.execute(  # noqa: SLF001 - diagnostic
                "SELECT COUNT(*) FROM taxi_path WHERE icao = ?", (code,)
            ).fetchone()[0]
            table.add_row(
                f"[green]{code}[/green]" if fetched else code,
                airport.name,
                str(len(provider.runways(code))),
                str(counts[ProcedureKind.SID]),
                str(counts[ProcedureKind.STAR]),
                str(counts[ProcedureKind.APPROACH]),
                f"{ground:,}".replace(",", " "),
            )
    finally:
        provider.close()

    console.print(table)
    console.print(
        "[dim]En vert : récupéré du simulateur. Les autres étaient déjà en base "
        "et restent consultables simulateur fermé.[/dim]"
    )
    return 1 if failures else 0


def cmd_web(args: argparse.Namespace, settings: Settings) -> int:
    from navixav.web.app import serve

    url = f"http://{args.host}:{args.port}"
    console.print(f"[bold]NaviXav[/bold] — application locale sur [cyan]{url}[/cyan]")
    console.print("[dim]Ctrl+C pour arrêter.[/dim]")

    if not args.no_open:
        import threading
        import webbrowser

        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        serve(host=args.host, port=args.port, settings=settings)
    except KeyboardInterrupt:  # pragma: no cover - interruption manuelle
        console.print("[dim]Arrêté.[/dim]")
    return 0


def _open_provider(store: str | None, allow_fetch: bool = True) -> "MsfsProvider":
    """Ouvre la base NaviXav.

    `allow_fetch` autorise la récupération d'un terrain manquant auprès du
    simulateur ; on le désactive pour les commandes de simple consultation.
    """
    from navixav.navdata.msfs import MsfsProvider

    return MsfsProvider(store, allow_fetch=allow_fetch)


COMMANDS = ("plan", "navdata", "airport", "web", "import")


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    # « navixav --json » équivaut à « navixav plan --json ».
    if not any(token in COMMANDS for token in raw) and not (
        {"--version", "-h", "--help"} & set(raw)
    ):
        raw.insert(0, "plan")

    parser = build_parser()
    args = parser.parse_args(raw)
    settings = Settings.load(args.env)

    handlers = {
        "plan": cmd_plan,
        "navdata": cmd_navdata,
        "airport": cmd_airport,
        "web": cmd_web,
        "import": cmd_import,
    }
    handler = handlers.get(args.command or "plan")
    if handler is None:  # pragma: no cover - argparse couvre déjà ce cas
        parser.print_help()
        return 1
    return handler(args, settings)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""API locale et service des fichiers statiques.

L'application n'écoute que sur la boucle locale : elle expose le Pilot ID et le
contenu du dispatch, qui n'ont pas à sortir de la machine.
"""

from __future__ import annotations

import asyncio
import copy
import ipaddress
import logging
import math
import socket
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from navixav import __version__
from navixav.aircraft import AircraftMatcher
from navixav.aircraft.community import community_folders, survey
from navixav.aircraft.scaffold import write_entry
from navixav.aircraft.procedures import procedure_payload
from navixav.changelog import load_changelog
from navixav.chart import EARTH_RADIUS_M, build_chart
from navixav.ground import (
    DEPARTURE,
    GroundError,
    build_graph,
    guide,
    plan_taxi,
    replan,
    replan_needed,
)
from navixav.config import (
    Settings,
    load_user_settings,
    save_user_settings,
)
from navixav.faa import FaaClient, FaaError
from navixav.live import LiveTracker, PositionUnavailable
from navixav.live.demo import DemoSource
from navixav.live.demo_flight import DemoFlightSource
from navixav.national_aip import (
    NATIONAL_AIP_SOURCES,
    NationalAipClient,
    NationalAipError,
    national_source_for_icao,
)
from navixav.navdata.base import NavdataError, ProcedureKind
from navixav.navdata.msfs import MsfsProvider
from navixav.paths import resource_path
from navixav.planner.engine import CompletionEngine, PlannerOverrides
from navixav.preferences import AirportPreferences
from navixav.simbrief.client import SimBriefClient, SimBriefError
from navixav.simbrief.parser import parse_ofp
from navixav.sia import SiaClient, SiaError
from navixav.updater import GitHubUpdater, UpdateError
from navixav.weather.briefing import build_briefing

STATIC_DIR = resource_path("navixav", "web", "static")
DEMO_OFP = resource_path("tests", "data", "ofp_lcph_eham.json")
FAA_ICAO_PREFIXES = {
    "PA", "PF", "PG", "PH", "PJ", "PM", "PO", "PW",
    "NS", "TI", "TJ",
}
LOGGER = logging.getLogger(__name__)
WEATHER_REFRESH_SECONDS = 300


class PlanRequest(BaseModel):
    demo: bool = False
    departure_runway: str | None = None
    sid: str | None = None
    sid_transition: str | None = None
    arrival_runway: str | None = None
    star: str | None = None
    star_transition: str | None = None
    approach: str | None = None
    approach_transition: str | None = None
    departure_metar: str | None = None
    arrival_metar: str | None = None
    prefer_ils: bool = True
    rnp_capable: bool | None = None

    def to_overrides(self) -> PlannerOverrides:
        return PlannerOverrides(
            departure_runway=self.departure_runway,
            sid=self.sid,
            sid_transition=self.sid_transition,
            arrival_runway=self.arrival_runway,
            star=self.star,
            star_transition=self.star_transition,
            approach=self.approach,
            approach_transition=self.approach_transition,
            departure_metar=self.departure_metar,
            arrival_metar=self.arrival_metar,
            prefer_ils=self.prefer_ils,
            rnp_capable=self.rnp_capable,
        )


class SettingsRequest(BaseModel):
    simbrief_pilot_id: str = Field(default="", max_length=32)
    simbrief_username: str = Field(default="", max_length=80)
    navdata_store: str = Field(default="", max_length=500)
    metar_source: str = Field(default="simbrief", pattern="^(simbrief|live)$")
    approach_preference: list[str] = Field(default_factory=list, max_length=20)
    max_tailwind_kt: int = Field(default=10, ge=0, le=50)
    max_crosswind_kt: int = Field(default=35, ge=0, le=100)
    min_runway_length_ft: int = Field(default=0, ge=0, le=30000)
    aircraft_rnp_capable: bool = True
    map_basemap: str = Field(
        default="osm", pattern="^(osm|opentopo|carto_light|carto_dark)$"
    )
    map_trail_color: str = Field(default="#22d3ee", pattern="^#[0-9A-Fa-f]{6}$")
    aircraft_community_path: str = Field(default="", max_length=1000)
    lan_enabled: bool = False


class AircraftScaffoldRequest(BaseModel):
    label: str = Field(min_length=1, max_length=300)
    package: str = Field(min_length=1, max_length=300)
    community_path: str = Field(default="", max_length=1000)


def _is_loopback(host: str | None) -> bool:
    if not host:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host in {"localhost", "testclient"}


def _local_ipv4() -> str | None:
    """Retourne l'adresse privée utilisée pour joindre le PC sur le LAN."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 9))
            candidate = probe.getsockname()[0]
        address = ipaddress.ip_address(candidate)
        if address.is_private and not address.is_loopback:
            return candidate
    except OSError:
        pass
    try:
        for candidate in socket.gethostbyname_ex(socket.gethostname())[2]:
            address = ipaddress.ip_address(candidate)
            if address.is_private and not address.is_loopback:
                return candidate
    except OSError:
        pass
    return None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_user_settings(Settings.load())
    lan_active = settings.lan_enabled
    tracker = LiveTracker()
    sia = SiaClient()
    faa = FaaClient()
    national_aip = {
        source.provider: NationalAipClient(source)
        for source in NATIONAL_AIP_SOURCES
    }
    demo_state: dict[str, Any] = {}
    current_plan_state: dict[str, Any] = {}
    updater = GitHubUpdater(__version__)
    aircraft_matcher = AircraftMatcher()
    resources_closed = False

    def close_resources() -> None:
        """Ferme une seule fois toutes les connexions détenues par l'API."""
        nonlocal resources_closed
        if resources_closed:
            return
        resources_closed = True
        LOGGER.info("Fermeture des connexions et sessions NaviXav")
        tracker.close()
        sia.session.close()
        faa.session.close()
        for client in national_aip.values():
            client.session.close()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            close_resources()

    app = FastAPI(
        title="NaviXav",
        version=__version__,
        docs_url="/api/docs",
        lifespan=lifespan,
    )
    # Les tests unitaires appellent directement les fonctions de route, sans
    # démarrer un serveur ASGI. Ils doivent néanmoins emprunter le même chemin
    # de fermeture que le cycle de vie FastAPI.
    app.state.close_resources = close_resources

    @app.middleware("http")
    async def log_relevant_requests(request: Request, call_next):
        """Journalise les lenteurs et erreurs sans saturer le fichier."""
        remote_client = not _is_loopback(request.client.host if request.client else None)
        if remote_client:
            # Aucun jeton n'est demandé : le service n'est joignable que si
            # l'accès réseau local a été activé, et seulement depuis le réseau
            # de la machine. En revanche, les commandes qui modifient ou
            # arrêtent l'application restent réservées au PC hôte.
            if not lan_active:
                return PlainTextResponse(
                    "Accès réseau désactivé. Active-le dans les paramètres, "
                    "sur le PC.",
                    status_code=403,
                )
            if request.url.path in {
                "/api/settings",
                "/api/aircraft/survey",
                "/api/aircraft/select-folder",
                "/api/aircraft/scaffold",
                "/api/simbrief/new",
                "/api/support/open",
                "/api/update/install",
                "/api/demo/restart",
                "/api/shutdown",
            } or (
                request.url.path == "/api/plan" and request.method == "POST"
            ):
                return PlainTextResponse(
                    "Cette commande est réservée à l’application sur le PC.",
                    status_code=403,
                )
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            LOGGER.exception(
                "Erreur API non gérée sur %s %s", request.method, request.url.path
            )
            raise
        elapsed = time.monotonic() - started
        if (
            request.url.path == "/api/plan"
            or response.status_code >= 400
            or elapsed >= 2.0
        ):
            LOGGER.info(
                "API %s %s -> %s en %.2f s",
                request.method,
                request.url.path,
                response.status_code,
                elapsed,
            )
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def official_chart_backend(
        airport: str,
    ) -> tuple[str, str, Any, type[Exception]]:
        if airport.startswith("LF"):
            return "sia", "SIA France · eAIP officiel", sia, SiaError
        if airport.startswith("K") or airport[:2] in FAA_ICAO_PREFIXES:
            return "faa", "FAA · d-TPP officiel", faa, FaaError
        source = national_source_for_icao(airport)
        if source is not None:
            return (
                source.provider,
                source.source,
                national_aip[source.provider],
                NationalAipError,
            )
        raise HTTPException(
            404,
            f"Aucune source AIS nationale officielle intégrée pour {airport}.",
        )

    def open_provider(*, allow_fetch: bool = True) -> MsfsProvider:
        try:
            return MsfsProvider(settings.navdata_store, allow_fetch=allow_fetch)
        except NavdataError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/status")
    def status(request: Request) -> dict[str, Any]:
        provider = MsfsProvider(settings.navdata_store, allow_fetch=False)
        try:
            navdata = {
                "source": provider.source_name,
                "cycle": provider.airac_cycle,
                "rnp": provider.supports_rnp_flag,
                "ground": provider.has_ground_geometry,
                **provider.stats(),
                **provider.reference_counts(),
            }
        finally:
            provider.close()

        remote_client = not _is_loopback(request.client.host if request.client else None)
        address = _local_ipv4() if lan_active and not remote_client else None
        port = request.url.port or 80
        return {
            "version": __version__,
            "simbrief_configured": bool(
                settings.simbrief_pilot_id or settings.simbrief_username
            ),
            "simbrief_target": settings.describe_simbrief_target(),
            "metar_source": settings.metar_source,
            "rnp_capable": settings.aircraft_rnp_capable,
            "demo_available": DEMO_OFP.is_file(),
            "remote_client": remote_client,
            "lan_active": lan_active,
            "lan_url": f"http://{address}:{port}/" if address else "",
            "map_basemap": settings.map_basemap,
            "map_trail_color": settings.map_trail_color,
            "navdata": navdata,
        }

    @app.get("/api/settings")
    def get_settings() -> dict[str, object]:
        values = settings.user_values()
        return values

    def aircraft_folders(explicit_path: str = "") -> list[Path]:
        raw = explicit_path.strip()
        if not raw and settings.aircraft_community_path is not None:
            raw = str(settings.aircraft_community_path)
        return community_folders([Path(raw)]) if raw else community_folders()

    def aircraft_inventory(explicit_path: str = "") -> dict[str, object]:
        return survey(aircraft_matcher, aircraft_folders(explicit_path)).to_dict()

    @app.get("/api/aircraft/survey")
    def get_aircraft_survey(community: str = "") -> dict[str, object]:
        return aircraft_inventory(community)

    @app.post("/api/aircraft/select-folder")
    def select_aircraft_folder(request: Request) -> dict[str, object]:
        if request.headers.get("X-NaviXav-Aircraft") != "browse":
            raise HTTPException(403, "Confirmation de sélection absente.")
        callback = getattr(app.state, "request_aircraft_folder", None)
        if not callable(callback):
            raise HTTPException(
                409,
                "Le sélecteur de dossier est disponible dans l’application Windows.",
            )
        detected = aircraft_folders()
        current = str(
            settings.aircraft_community_path or (detected[0] if detected else "")
        )
        selected = callback(current)
        if not selected:
            return {"cancelled": True}
        folders = community_folders([Path(selected)])
        if not folders:
            raise HTTPException(400, "Ce dossier ne contient aucun dossier Community.")
        payload = survey(aircraft_matcher, folders).to_dict()
        payload["selected_path"] = str(selected)
        return payload

    @app.post("/api/aircraft/scaffold")
    def scaffold_aircraft(
        payload: AircraftScaffoldRequest, request: Request
    ) -> dict[str, object]:
        nonlocal aircraft_matcher
        if request.headers.get("X-NaviXav-Aircraft") != "scaffold":
            raise HTTPException(403, "Confirmation de création absente.")
        folders = aircraft_folders(payload.community_path)
        report = survey(aircraft_matcher, folders)
        aircraft = next(
            (
                item for item in report.missing
                if item.label == payload.label and item.package == payload.package
            ),
            None,
        )
        if aircraft is None:
            raise HTTPException(404, "Cet appareil non couvert n’est plus présent.")
        try:
            directory = write_entry(aircraft)
        except FileExistsError as exc:
            raise HTTPException(409, str(exc)) from exc
        except (OSError, ValueError) as exc:
            LOGGER.warning("Création du canevas d’appareil refusée : %s", exc)
            raise HTTPException(400, str(exc)) from exc
        aircraft_matcher = AircraftMatcher()
        refreshed = survey(aircraft_matcher, folders).to_dict()
        refreshed["created"] = {"label": aircraft.label, "directory": str(directory)}
        return refreshed

    @app.get("/api/aircraft/procedures")
    def aircraft_procedures(title: str = "") -> dict[str, object]:
        return procedure_payload(aircraft_matcher.match(title))

    @app.get("/api/update/check")
    def check_update() -> dict[str, object]:
        try:
            update = updater.check()
        except UpdateError as exc:
            LOGGER.warning("Vérification de mise à jour impossible : %s", exc)
            return {
                "current_version": __version__,
                "available": False,
                "error": str(exc),
            }
        if update.available:
            LOGGER.info("Mise à jour NaviXav %s disponible", update.latest_version)
        return update.to_dict()

    @app.post("/api/update/install")
    def install_update(request: Request) -> dict[str, object]:
        if request.headers.get("X-NaviXav-Update") != "install":
            raise HTTPException(403, "Confirmation de mise à jour absente.")
        callback = getattr(app.state, "request_update_install", None)
        if not callable(callback):
            raise HTTPException(
                409,
                "L'installation automatique est disponible dans l'application Windows.",
            )
        try:
            update = updater.check()
            if not update.available:
                raise HTTPException(409, "NaviXav est déjà à jour.")
            installer = updater.download(update)
        except UpdateError as exc:
            LOGGER.warning("Mise à jour refusée : %s", exc)
            raise HTTPException(502, str(exc)) from exc
        callback(installer)
        return {
            "status": "starting",
            "version": update.latest_version,
        }

    @app.put("/api/settings")
    def update_settings(request: SettingsRequest) -> dict[str, object]:
        nonlocal settings
        settings = settings.with_user_values(request.model_dump())
        try:
            save_user_settings(settings)
        except OSError as exc:
            LOGGER.exception("Échec d'enregistrement des paramètres")
            raise HTTPException(
                500, f"Impossible d'enregistrer les paramètres : {exc}"
            ) from exc
        LOGGER.info(
            "Paramètres enregistrés (SimBrief configuré=%s, source METAR=%s)",
            bool(settings.simbrief_pilot_id or settings.simbrief_username),
            settings.metar_source,
        )
        values = settings.user_values()
        values["lan_restart_required"] = settings.lan_enabled != lan_active
        return values

    @app.post("/api/plan")
    def build_plan(request: PlanRequest) -> dict[str, Any]:
        total_started = time.monotonic()
        LOGGER.info("Calcul du plan démarré (démo=%s)", request.demo)
        if request.demo:
            if not DEMO_OFP.is_file():
                raise HTTPException(404, "Jeu de démonstration introuvable.")
            raw = SimBriefClient.from_file(DEMO_OFP)
        else:
            simbrief_started = time.monotonic()
            try:
                raw = SimBriefClient(
                    pilot_id=settings.simbrief_pilot_id,
                    username=settings.simbrief_username,
                ).fetch_latest()
            except SimBriefError as exc:
                LOGGER.warning(
                    "Récupération SimBrief refusée après %.2f s (%s)",
                    time.monotonic() - simbrief_started,
                    type(exc).__name__,
                )
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            LOGGER.info(
                "OFP SimBrief reçu en %.2f s",
                time.monotonic() - simbrief_started,
            )

        ofp = parse_ofp(raw)
        if not ofp.origin_icao or not ofp.destination_icao:
            raise HTTPException(422, "OFP inexploitable : origine ou destination absente.")

        # La démo embarquée est autonome : même avec un cache vierge, elle ne
        # doit jamais tenter d'ouvrir SimConnect. Les coordonnées de son OFP
        # suffisent au tracé et à DemoFlightSource.
        provider = open_provider(allow_fetch=not request.demo)
        try:
            cache_before = provider.stats()
            completion_started = time.monotonic()
            engine = CompletionEngine(
                provider, settings, AirportPreferences.load(
                    settings.airport_preferences_path
                )
            )
            plan = engine.complete(ofp, request.to_overrides())
            if request.demo:
                # Le jeu embarqué porte ses propres coordonnées LCPH/EHAM afin
                # que son animation reste disponible avant le premier import
                # MSFS. L'absence éventuelle de ces deux terrains dans le cache
                # est donc attendue et ne doit pas inquiéter pendant la démo.
                expected_missing = {
                    f"{ofp.origin_icao} absent de la base de navigation.",
                    f"{ofp.destination_icao} absent de la base de navigation.",
                }
                plan.warnings = [
                    warning for warning in plan.warnings
                    if warning not in expected_missing
                ]
            payload = plan.to_dict()
            payload["atc_route"] = plan.atc_route()
            payload["demo"] = request.demo
            current_plan_state["payload"] = copy.deepcopy(payload)
            current_plan_state["ofp"] = ofp
            # Chaque import relance la démonstration au parking de départ,
            # même si la route calculée est identique à la précédente.
            demo_state.pop("key", None)
            LOGGER.info(
                "Complétion MSFS terminée en %.2f s "
                "(cache avant: %s terrain(s), %s procédure(s); total %.2f s)",
                time.monotonic() - completion_started,
                cache_before.get("airports", 0),
                cache_before.get("procedures", 0),
                time.monotonic() - total_started,
            )
            return payload
        except HTTPException:
            raise
        except Exception:
            LOGGER.exception(
                "Échec de la complétion du plan après %.2f s",
                time.monotonic() - total_started,
            )
            raise
        finally:
            provider.close()

    @app.get("/api/plan/current")
    def current_plan() -> dict[str, Any]:
        payload = current_plan_state.get("payload")
        if payload is None:
            raise HTTPException(
                404,
                "Aucun vol n’est actuellement chargé dans NaviXav sur le PC.",
            )
        return copy.deepcopy(payload)

    @app.get("/api/weather/current")
    def current_weather() -> dict[str, Any]:
        """Actualise la météo sans recalculer la route ni les procédures."""
        payload = current_plan_state.get("payload")
        ofp = current_plan_state.get("ofp")
        if payload is None or ofp is None:
            raise HTTPException(404, "Aucun vol chargé pour actualiser la météo.")

        if settings.metar_source != "live":
            return {
                "weather": copy.deepcopy(payload.get("weather") or {}),
                "enabled": False,
                "live": False,
                "partial": False,
                "refreshed_at": None,
                "refresh_interval_seconds": WEATHER_REFRESH_SECONDS,
            }

        try:
            briefing = build_briefing(
                ofp,
                metar_source="live",
                force_live=True,
            )
        except Exception as exc:  # noqa: BLE001 - conserver la météo précédente
            LOGGER.warning(
                "Actualisation météo directe indisponible : %s",
                type(exc).__name__,
            )
            raise HTTPException(
                503,
                "La météo en direct est momentanément indisponible.",
            ) from exc

        reports = [
            report
            for report in (
                briefing.departure,
                briefing.arrival,
                briefing.alternate,
            )
            if report is not None and report.raw_metar
        ]
        live_reports = sum(report.source == "awc" for report in reports)
        weather = briefing.to_dict()
        payload["weather"] = copy.deepcopy(weather)
        refreshed_at = datetime.now(timezone.utc).isoformat()
        return {
            "weather": weather,
            "enabled": True,
            "live": live_reports > 0,
            "partial": live_reports < len(reports),
            "refreshed_at": refreshed_at,
            "refresh_interval_seconds": WEATHER_REFRESH_SECONDS,
        }

    @app.get("/api/airport/{icao}")
    def airport(icao: str) -> dict[str, Any]:
        provider = open_provider()
        try:
            found = provider.airport(icao)
            if found is None:
                raise HTTPException(404, f"{icao.upper()} absent de la base.")
            return {
                "icao": found.ident,
                "name": found.name,
                "city": found.city,
                "runways": [
                    {
                        "name": r.name,
                        "heading": round(r.heading_true_deg),
                        "length_ft": round(r.length_ft),
                        "ils": r.ils_ident,
                    }
                    for r in provider.runways(icao)
                ],
                "procedures": {
                    kind.value.lower(): [
                        {
                            "name": p.display_name,
                            "runways": list(p.runways),
                            "entry": p.entry_fix,
                            "exit": p.exit_fix,
                            "transitions": list(p.transition_idents()),
                            "requires_rnp": p.requires_rnp,
                            "vectors": p.is_vectors_entry,
                        }
                        for p in provider.procedures(icao, kind)
                    ]
                    for kind in ProcedureKind
                },
            }
        finally:
            provider.close()

    @app.get("/api/chart/{icao}")
    def chart(icao: str, runway: str | None = None) -> dict[str, Any]:
        provider = open_provider()
        try:
            return build_chart(provider, icao, runway)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        finally:
            provider.close()

    @app.get("/api/ground/{icao}/route")
    def ground_route(
        icao: str,
        parking: str,
        runway: str,
        direction: str = DEPARTURE,
    ) -> dict[str, Any]:
        """Itinéraire de roulage entre un poste de stationnement et une piste."""
        provider = open_provider()
        try:
            graph = build_graph(provider, icao)
            return plan_taxi(
                graph, parking=parking, runway=runway, direction=direction
            ).to_dict()
        except GroundError as exc:
            raise HTTPException(404, str(exc)) from exc
        finally:
            provider.close()

    @app.get("/api/ground/{icao}/guidance")
    def ground_guidance(
        icao: str,
        parking: str,
        runway: str,
        latitude: float,
        longitude: float,
        direction: str = DEPARTURE,
    ) -> dict[str, Any]:
        """Situation de l'avion sur son roulage, et consigne du moment.

        L'itinéraire est recalculé à chaque interrogation plutôt que conservé
        d'un appel à l'autre : le service ne garde aucun état de session, et le
        réseau étant en cache, le calcul complet tient en quelques
        millisecondes.
        """
        provider = open_provider()
        try:
            graph = build_graph(provider, icao)
            position = graph.to_local(latitude, longitude)
            plan = plan_taxi(
                graph, parking=parking, runway=runway, direction=direction
            )
            guidance = guide(plan, *position)
            if replan_needed(guidance):
                plan = replan(plan, *position)
                guidance = guide(plan, *position)
            return {
                "plan": plan.to_dict(),
                "guidance": guidance.to_dict(),
                "recomputed": plan.from_position,
            }
        except GroundError as exc:
            raise HTTPException(404, str(exc)) from exc
        finally:
            provider.close()

    @app.get("/api/ground/{icao}/parkings")
    def ground_parkings(icao: str) -> dict[str, Any]:
        """Postes de stationnement et pistes que le réseau au sol dessert."""
        provider = open_provider()
        try:
            graph = build_graph(provider, icao)
        except GroundError as exc:
            raise HTTPException(404, str(exc)) from exc
        else:
            return {
                "icao": graph.icao,
                "routable": graph.has_kinds,
                "named": graph.has_names,
                "runways": list(graph.runway_names()) if graph.has_kinds else [],
                "parkings": [
                    {
                        "label": parking.label,
                        "kind": parking.kind,
                        "position": {"x": parking.x, "y": parking.y},
                    }
                    for parking in graph.parkings
                ],
            }
        finally:
            provider.close()

    @app.get("/api/sia/approach")
    def sia_approach(
        icao: str,
        runway: str,
        approach: str,
    ) -> dict[str, Any]:
        try:
            chart_data, minima = sia.find_approach(icao, runway, approach)
        except SiaError as exc:
            raise HTTPException(404, str(exc)) from exc
        query = urlencode({
            "icao": icao.upper(),
            "runway": runway.upper(),
            "approach": approach,
        })
        return {
            "source": "SIA France · eAIP officiel",
            "chart": chart_data.to_dict(),
            "minima": minima.to_dict() if minima else None,
            "pdf_url": f"/api/sia/pdf?{query}",
            "requires_confirmation": True,
        }

    @app.get("/api/charts/approach")
    def official_approach_chart(
        icao: str,
        runway: str,
        approach: str,
    ) -> dict[str, Any]:
        airport = icao.strip().upper()
        provider, source, client, error_type = official_chart_backend(airport)
        if provider == "sia":
            try:
                chart_data, minima = client.find_approach(
                    airport, runway, approach
                )
            except error_type as exc:
                raise HTTPException(404, str(exc)) from exc
        else:
            try:
                chart_data = client.find_approach(airport, runway, approach)
            except error_type as exc:
                raise HTTPException(404, str(exc)) from exc
            minima = None
        query = urlencode({
            "provider": provider,
            "icao": airport,
            "chart": chart_data.filename,
        })
        chart = chart_data.to_dict()
        chart["provider"] = provider
        return {
            "source": source,
            "provider": provider,
            "chart": chart,
            "minima": minima.to_dict() if minima else None,
            "pdf_url": f"/api/charts/document?{query}",
            "requires_confirmation": True,
        }

    @app.get("/api/sia/airport/{icao}")
    def sia_airport(icao: str) -> dict[str, Any]:
        try:
            effective_date, charts = sia.list_airport_charts(icao)
        except SiaError as exc:
            raise HTTPException(404, str(exc)) from exc

        documents = []
        for chart_data in charts:
            query = urlencode({
                "icao": icao.upper(),
                "chart": chart_data.filename,
            })
            document = chart_data.to_dict()
            document["georeferenced"] = sia.has_georeference(chart_data)
            document["pdf_url"] = f"/api/sia/document?{query}"
            documents.append(document)
        documents.sort(key=lambda item: (item["category"], item["title"]))
        return {
            "icao": icao.upper(),
            "source": "SIA France · eAIP officiel",
            "effective_date": effective_date.isoformat(),
            "charts": documents,
        }

    @app.get("/api/charts/airport/{icao}")
    def official_airport_charts(icao: str) -> dict[str, Any]:
        airport = icao.strip().upper()
        provider, source, client, error_type = official_chart_backend(airport)

        try:
            effective_date, charts = client.list_airport_charts(airport)
        except error_type as exc:
            raise HTTPException(404, str(exc)) from exc

        documents = []
        for chart_data in charts:
            query = urlencode({
                "provider": provider,
                "icao": airport,
                "chart": chart_data.filename,
            })
            document = chart_data.to_dict()
            document["provider"] = provider
            document["georeferenced"] = client.has_georeference(chart_data)
            document["pdf_url"] = f"/api/charts/document?{query}"
            documents.append(document)
        documents.sort(key=lambda item: (item["category"], item["title"]))
        return {
            "icao": airport,
            "provider": provider,
            "source": source,
            "effective_date": effective_date.isoformat(),
            "charts": documents,
        }

    @app.get("/api/charts/document")
    def official_chart_document(
        provider: str,
        icao: str,
        chart: str,
    ) -> FileResponse:
        if provider == "sia":
            client = sia
            error_type = SiaError
        elif provider == "faa":
            client = faa
            error_type = FaaError
        elif provider in national_aip:
            client = national_aip[provider]
            error_type = NationalAipError
        else:
            raise HTTPException(400, "Fournisseur de cartes inconnu.")
        try:
            chart_data = client.get_airport_chart(icao, chart)
        except error_type as exc:
            raise HTTPException(404, str(exc)) from exc
        if chart_data.local_path is None:
            raise HTTPException(500, "Carte officielle absente du cache.")
        return FileResponse(
            chart_data.local_path,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{chart_data.filename}"',
                "Cache-Control": "private, max-age=86400",
            },
        )

    @app.get("/api/sia/document")
    def sia_document(icao: str, chart: str) -> FileResponse:
        try:
            chart_data = sia.get_airport_chart(icao, chart)
        except SiaError as exc:
            raise HTTPException(404, str(exc)) from exc
        if chart_data.local_path is None:
            raise HTTPException(500, "Carte SIA absente du cache.")
        return FileResponse(
            chart_data.local_path,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{chart_data.filename}"',
                "Cache-Control": "private, max-age=86400",
            },
        )

    @app.get("/api/sia/pdf")
    def sia_pdf(icao: str, runway: str, approach: str) -> FileResponse:
        try:
            chart_data, _minima = sia.find_approach(icao, runway, approach)
        except SiaError as exc:
            raise HTTPException(404, str(exc)) from exc
        if chart_data.local_path is None:
            raise HTTPException(500, "Carte SIA absente du cache.")
        return FileResponse(
            chart_data.local_path,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{chart_data.filename}"',
                "Cache-Control": "private, max-age=86400",
            },
        )

    @app.get("/api/live")
    def live(
        demo: bool = False,
        icao: str | None = None,
        runway: str | None = None,
        aircraft: str | None = None,
    ) -> dict[str, Any]:
        if demo:
            _ensure_demo_source(icao, runway)
        tracker.set_aircraft_hint(aircraft)
        try:
            state = tracker.read(allow_demo=demo)
        except PositionUnavailable as exc:
            return {"connected": False, "reason": str(exc)}
        match = aircraft_matcher.match(state.title)
        if match is None and aircraft:
            match = aircraft_matcher.match(aircraft)
        return {
            "connected": True,
            "aircraft": state.to_dict(),
            "procedures": procedure_payload(match, state),
        }

    @app.post("/api/demo/restart")
    def restart_demo() -> dict[str, object]:
        """Relance la simulation au départ du plan actuellement chargé."""
        payload = current_plan_state.get("payload") or {}
        if len(_demo_flight_path(payload)) < 2:
            raise HTTPException(
                409,
                "Le plan actuellement chargé ne contient pas de route exploitable.",
            )
        demo_state.pop("key", None)
        _ensure_demo_source(None, None)
        departure = (payload.get("departure") or {}).get("icao")
        arrival = (payload.get("arrival") or {}).get("icao")
        return {
            "started": True,
            "departure": departure,
            "arrival": arrival,
        }

    @app.get("/api/changelog")
    def changelog() -> dict[str, object]:
        """Journal complet des versions, livré avec l'application."""
        return {"version": __version__, "releases": load_changelog()}

    @app.get("/api/simulator")
    def simulator_status() -> dict[str, object]:
        try:
            state = tracker.read()
        except PositionUnavailable as exc:
            return {"connected": False, "reason": str(exc)}
        return {
            "connected": True,
            "paused": state.paused,
            "source": state.source,
        }

    @app.post("/api/shutdown")
    async def shutdown() -> dict[str, bool]:
        callback = getattr(app.state, "request_shutdown", None)
        if not callable(callback):
            raise HTTPException(503, "Arrêt contrôlé indisponible.")

        async def stop_after_response() -> None:
            await asyncio.sleep(0.1)
            callback()

        asyncio.create_task(stop_after_response())
        return {"stopping": True}

    @app.post("/api/simbrief/new")
    def open_simbrief(request: Request) -> dict[str, bool]:
        if request.headers.get("X-NaviXav-External") != "simbrief":
            raise HTTPException(403, "Confirmation d’ouverture absente.")
        callback = getattr(app.state, "request_open_simbrief", None)
        if not callable(callback):
            raise HTTPException(
                409,
                "L’ouverture de SimBrief est disponible dans l’application Windows.",
            )
        callback()
        return {"opened": True}

    @app.post("/api/support/open")
    def open_support(request: Request) -> dict[str, bool]:
        if request.headers.get("X-NaviXav-External") != "support":
            raise HTTPException(403, "Confirmation d’ouverture absente.")
        callback = getattr(app.state, "request_open_support", None)
        if not callable(callback):
            raise HTTPException(
                409,
                "La page de soutien est disponible dans l’application Windows.",
            )
        callback()
        return {"opened": True}

    def _airport_elevation_ft(
        icao: str | None, *, allow_fetch: bool = True,
    ) -> float:
        """Altitude du terrain, ou 0 ft si la base ne la fournit pas."""
        if not icao:
            return 0.0
        try:
            provider = open_provider(allow_fetch=allow_fetch)
        except HTTPException:
            # Sans base de navigation la démonstration reste possible : le
            # terrain est alors supposé au niveau de la mer.
            return 0.0
        try:
            airport = provider.airport(icao)
        except (NavdataError, LookupError):
            return 0.0
        finally:
            provider.close()
        return float(getattr(airport, "altitude_ft", None) or 0.0)

    def _ensure_demo_source(icao: str | None, runway: str | None) -> None:
        """Prépare la démonstration : vol complet du plan, sinon simple roulage.

        La clé du vol complet ne dépend que du plan : changer d'aéroport sur la
        carte ne doit pas relancer la démonstration au parking de départ.
        """
        payload = current_plan_state.get("payload") or {}
        path = _demo_flight_path(payload)
        if len(path) >= 2:
            key = ("flight", _demo_plan_key(payload), len(path))
            if demo_state.get("key") == key:
                return
            departure = payload.get("departure") or {}
            arrival = payload.get("arrival") or {}
            try:
                tracker.set_demo(
                    DemoFlightSource(
                        path=path,
                        cruise_altitude_ft=(payload.get("enroute") or {}).get(
                            "cruise_altitude_ft"
                        ),
                        departure_elevation_ft=_airport_elevation_ft(
                            departure.get("icao"), allow_fetch=False,
                        ),
                        arrival_elevation_ft=_airport_elevation_ft(
                            arrival.get("icao"), allow_fetch=False,
                        ),
                        ils_frequency_mhz=arrival.get("ils_frequency_mhz"),
                    )
                )
            except ValueError:
                LOGGER.info("Route de démonstration inexploitable, roulage simulé.")
                tracker.set_demo(None)
            demo_state["key"] = key
            return

        key = ("taxi", icao or "", runway or "")
        if demo_state.get("key") == key:
            return

        if not icao:
            tracker.set_demo(None)
            return

        provider = open_provider()
        try:
            data = build_chart(provider, icao, runway)
        except LookupError:
            tracker.set_demo(None)
            return
        finally:
            provider.close()

        origin = data["origin"]
        threshold = _threshold_for(data, runway)
        parking = data["parkings"][0]["position"] if data["parkings"] else None
        if threshold is None or parking is None:
            tracker.set_demo(None)
            return

        # Pas de cap imposé : l'avion doit pointer dans le sens du roulage,
        # pas dans l'axe de la piste qu'il rejoint.
        tracker.set_demo(
            DemoSource(
                start=_to_latlon(origin, parking),
                end=_to_latlon(origin, threshold["point"]),
            )
        )
        demo_state["key"] = key

    @app.get("/")
    def index() -> HTMLResponse:
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(
            html.replace("__NAVIXAV_VERSION__", __version__),
            headers={"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"},
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def _demo_flight_path(payload: dict[str, Any]) -> list[tuple[float, float]]:
    """Route opérationnelle complète du plan, prête pour la démonstration.

    Même assemblage que le tracé de la carte : départ, SID, route, STAR,
    approche puis arrivée, sans les extrémités déjà fournies par les
    procédures.
    """
    departure = payload.get("departure") or {}
    arrival = payload.get("arrival") or {}
    route = (payload.get("enroute") or {}).get("route_path") or []

    segments: list[dict[str, Any]] = []
    if route:
        segments.append(route[0])
    segments.extend(departure.get("sid_path") or [])
    segments.extend(route[1:-1] if len(route) > 2 else [])
    segments.extend(arrival.get("star_path") or [])
    segments.extend(arrival.get("approach_path") or [])
    if len(route) > 1:
        segments.append(route[-1])

    points: list[tuple[float, float]] = []
    for entry in segments:
        if not isinstance(entry, dict):
            continue
        latitude = entry.get("lat")
        longitude = entry.get("lon")
        if latitude is None or longitude is None:
            continue
        points.append((float(latitude), float(longitude)))
    return points


def _demo_plan_key(payload: dict[str, Any]) -> str:
    departure = (payload.get("departure") or {}).get("icao") or "----"
    arrival = (payload.get("arrival") or {}).get("icao") or "----"
    route = (payload.get("enroute") or {}).get("raw_simbrief_route") or ""
    return f"{departure}-{arrival}-{hash(route)}"


def _threshold_for(chart: dict[str, Any], runway: str | None) -> dict[str, Any] | None:
    """Seuil de la piste demandée, ou de la première piste disponible."""
    target = (runway or "").strip().upper()
    fallback: dict[str, Any] | None = None
    for entry in chart["runways"]:
        for end in entry["ends"]:
            candidate = {"point": end["threshold"], "heading": end["heading"]}
            if fallback is None:
                fallback = candidate
            if target and end["name"].upper() == target:
                return candidate
    return fallback


def _to_latlon(origin: dict[str, float], point: dict[str, float]) -> tuple[float, float]:
    """Inverse de la projection locale du plan de terrain."""
    latitude = origin["lat"] + math.degrees(point["y"] / EARTH_RADIUS_M)
    longitude = origin["lon"] + math.degrees(
        point["x"] / (EARTH_RADIUS_M * math.cos(math.radians(origin["lat"])))
    )
    return (latitude, longitude)


def create_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    settings: Settings | None = None,
) -> Any:
    import uvicorn

    application = create_app(settings)
    # L'exécutable Windows n'a pas de stdout : la configuration colorée par
    # défaut d'Uvicorn tenterait d'appeler ``isatty()`` sur une valeur nulle.
    # La version installée écrit déjà son journal dans LOCALAPPDATA.
    config = uvicorn.Config(
        application,
        host=host,
        port=port,
        log_level="warning",
        log_config=None,
        access_log=False,
    )
    server = uvicorn.Server(config)
    application.state.request_shutdown = lambda: setattr(server, "should_exit", True)
    return server


def serve(
    host: str = "127.0.0.1",
    port: int = 8765,
    settings: Settings | None = None,
) -> None:
    server = create_server(host=host, port=port, settings=settings)
    server.run()

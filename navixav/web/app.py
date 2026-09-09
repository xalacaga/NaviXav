"""API locale et service des fichiers statiques.

L'application n'écoute que sur la boucle locale : elle expose le Pilot ID et le
contenu du dispatch, qui n'ont pas à sortir de la machine.
"""

from __future__ import annotations

import asyncio
import copy
import html
import ipaddress
import logging
import re
import socket
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, AsyncIterator
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from navixav import __version__
from navixav.aircraft import AircraftMatcher
from navixav.aircraft.community import community_folders, scan, survey
from navixav.aircraft.documents import checked_document, document_inventory, search_document
from navixav.aircraft.scaffold import write_entry
from navixav.aircraft.procedures import procedure_payload
from navixav.changelog import load_changelog
from navixav.chart import build_chart
from navixav.chartfox import ChartFoxClient, ChartFoxError
from navixav.ground import (
    DEPARTURE,
    GroundError,
    build_graph,
    guide,
    parse_taxiways,
    plan_taxi,
    replan,
    replan_needed,
)

from navixav.config import (
    TRAFFIC_SOURCES,
    Settings,
    load_user_settings,
    save_user_settings,
)
from navixav.faa import FaaClient, FaaError
from navixav.live import LiveTracker, PositionUnavailable
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
from navixav.traffic.base import distance_nm, is_own_position
from navixav import msfs_panel
from navixav.navdata import msfs_store
from navixav.traffic.static_traffic import StaticTrafficProvider
from navixav.traffic.selection import CHOICES as MODEL_CHOICES, build_index, detect_models
from navixav.traffic.ivao import IvaoClient, IvaoError
from navixav.traffic.opensky import OpenSkyClient, OpenSkyError
from navixav.traffic.service import TrafficService
from navixav.vatsim import VatsimClient, VatsimError
from navixav.updater import GitHubUpdater, UpdateError
from navixav.weather.briefing import build_briefing

STATIC_DIR = resource_path("navixav", "web", "static")
FAA_ICAO_PREFIXES = {
    "PA", "PF", "PG", "PH", "PJ", "PM", "PO", "PW",
    "NS", "TI", "TJ",
}
LOGGER = logging.getLogger(__name__)
WEATHER_REFRESH_SECONDS = 300


class PanelFlightSummary(BaseModel):
    revision: int = 0
    connected: bool = False
    route: str = Field(default="", max_length=40)
    values: dict[str, Annotated[str, Field(max_length=240)]] = Field(default_factory=dict, max_length=8)
    labels: dict[str, Annotated[str, Field(max_length=400)]] = Field(default_factory=dict, max_length=32)


class PlanRequest(BaseModel):
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
    map_basemap: str = Field(default="osm", pattern="^(osm|opentopo)$")
    map_trail_color: str = Field(default="#22d3ee", pattern="^#[0-9A-Fa-f]{6}$")
    taxi_speed_limit_kt: int = Field(default=25, ge=1, le=60)
    taxi_turn_speed_limit_kt: int = Field(default=10, ge=1, le=60)
    taxi_speed_alarm_sound: bool = True
    vatsim_enabled: bool = False
    traffic_enabled: bool = False
    traffic_source: str = Field(
        default="vatsim", pattern=f"^({'|'.join(TRAFFIC_SOURCES)})$"
    )
    traffic_radius_nm: float = Field(default=40.0, ge=1.0, le=100.0)
    traffic_max_aircraft: int = Field(default=10, ge=1, le=200)
    aircraft_models: str = Field(
        default="fsltl", pattern=f"^({'|'.join(MODEL_CHOICES)})$"
    )
    fsltl_path: str = Field(default="", max_length=1000)
    aig_path: str = Field(default="", max_length=1000)
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


def create_app(
    settings: Settings | None = None,
    chartfox_client: ChartFoxClient | None = None,
    vatsim_client: VatsimClient | None = None,
    ivao_client: IvaoClient | None = None,
    opensky_client: OpenSkyClient | None = None,
) -> FastAPI:
    settings = settings or load_user_settings(Settings.load())
    lan_active = settings.lan_enabled
    tracker = LiveTracker()
    sia = SiaClient()
    faa = FaaClient()
    national_aip = {
        source.provider: NationalAipClient(source)
        for source in NATIONAL_AIP_SOURCES
    }
    chartfox = chartfox_client or ChartFoxClient()
    vatsim = vatsim_client or VatsimClient()
    ivao = ivao_client or IvaoClient()
    opensky = opensky_client or OpenSkyClient(
        lambda: (lambda state: (state.latitude, state.longitude))(tracker.read())
    )
    current_plan_state: dict[str, Any] = {}
    panel_summary: dict[str, Any] = {}
    updater = GitHubUpdater(__version__)
    aircraft_matcher = AircraftMatcher()

    def detect_configured_models():
        folders = (
            community_folders(explicit=[settings.aircraft_community_path])
            if settings.aircraft_community_path
            else None
        )
        return detect_models(
            settings.aircraft_models,
            folders,
            fsltl_path=settings.fsltl_path,
            aig_path=settings.aig_path,
        )

    resources_closed = False

    static_provider = None
    static_options = None

    def selected_traffic_provider():
        nonlocal static_provider, static_options
        if settings.traffic_source == "ivao":
            return ivao
        if settings.traffic_source == "opensky":
            return opensky
        if settings.traffic_source == "static":
            options = (settings.navdata_store, settings.traffic_radius_nm,
                       settings.traffic_max_aircraft)
            if static_provider is None or options != static_options:
                static_provider = StaticTrafficProvider(
                    player_position,
                    lambda: msfs_store.connect(settings.navdata_store or None),
                    radius_nm=settings.traffic_radius_nm,
                    max_aircraft=settings.traffic_max_aircraft,
                )
                static_options = options
            return static_provider
        return vatsim

    def player_position() -> tuple[float, float]:
        state = tracker.read()
        return state.latitude, state.longitude

    def player_altitude() -> float | None:
        return tracker.read().altitude_ft

    # L'injection possède son état plutôt que de le partager par fermeture :
    # son fil, son gestionnaire et sa détection de modèles restent
    # interrogeables, au lieu d'être invisibles depuis l'extérieur de create_app.
    traffic = TrafficService(
        detect_configured_models,
        player_position,
        player_altitude,
        models_factory=build_index,
        state=lambda: tracker.read(),
    )

    def traffic_configuration(values: Settings) -> tuple:
        return (
            values.traffic_enabled, values.traffic_source, values.aircraft_models,
            values.fsltl_path, values.aig_path, values.aircraft_community_path,
            values.traffic_radius_nm, values.traffic_max_aircraft,
            values.navdata_store if values.traffic_source == "static" else None,
        )

    configured_traffic: tuple | None = None

    def configure_traffic_injection() -> None:
        nonlocal configured_traffic
        requested = traffic_configuration(settings)
        if requested == configured_traffic:
            return
        # Choisir une source de trafic, c'est demander à la voir voler : le
        # calque de la carte est le seul interrupteur, et ce qu'il montre entre
        # dans le simulateur. Aucun second réglage ne vient le contredire.
        traffic.configure(
            enabled=settings.traffic_enabled,
            provider=selected_traffic_provider(),
            radius_nm=settings.traffic_radius_nm,
            max_aircraft=settings.traffic_max_aircraft,
        )
        configured_traffic = requested

    def close_resources() -> None:
        """Ferme une seule fois toutes les connexions détenues par l'API."""
        nonlocal resources_closed
        if resources_closed:
            return
        resources_closed = True
        LOGGER.info("Fermeture des connexions et sessions NaviXav")
        traffic.close()
        tracker.close()
        vatsim.close()
        ivao.close()
        opensky.close()
        sia.session.close()
        faa.session.close()
        chartfox.close()
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
    configure_traffic_injection()

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
            chartfox_chart_request = request.url.path.startswith("/api/charts/") and (
                request.query_params.get("source") == "chartfox"
                or request.query_params.get("provider") == "chartfox"
            )
            if request.url.path.startswith("/api/chartfox/") or chartfox_chart_request or request.url.path == (
                "/oauth/chartfox/callback"
            ) or request.url.path in {
                "/api/settings",
                "/api/aircraft/survey",
                "/api/aircraft/select-folder",
                "/api/aircraft/scaffold",
                "/api/simbrief/new",
                "/api/support/open",
                "/api/fsltl/download",
                "/api/aig/download",
                "/api/update/install",
                "/api/shutdown",
            } or request.url.path.startswith("/api/panel/") or (
                request.url.path.startswith("/api/msfs-panel/")
            ) or (
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
            "remote_client": remote_client,
            "lan_active": lan_active,
            "lan_url": f"http://{address}:{port}/" if address else "",
            "map_basemap": settings.map_basemap,
            "map_trail_color": settings.map_trail_color,
            # Un client distant ne lit pas /api/settings : sans ces valeurs son
            # plan de roulage alerterait sur des limites qui ne sont pas les
            # tiennes.
            "taxi_speed_limit_kt": settings.taxi_speed_limit_kt,
            "taxi_turn_speed_limit_kt": settings.taxi_turn_speed_limit_kt,
            "taxi_speed_alarm_sound": settings.taxi_speed_alarm_sound,
            "vatsim_enabled": settings.vatsim_enabled,
            "traffic_enabled": settings.traffic_enabled,
            "traffic_injection_active": traffic.active,
            "traffic_injection": traffic.status,
            "traffic_conflict": list(traffic.conflicts),
            "traffic_source": settings.traffic_source,
            "aircraft_models": settings.aircraft_models,
            "models": traffic.installation.to_dict(),
            "chartfox_connected": bool(chartfox.status().get("connected")),
            "navdata": navdata,
        }

    @app.get("/api/settings")
    def get_settings() -> dict[str, object]:
        values = settings.user_values()
        return values

    @app.get("/api/chartfox/status")
    def chartfox_status() -> dict[str, Any]:
        return chartfox.status()

    @app.post("/api/chartfox/connect")
    def chartfox_connect(request: Request) -> dict[str, Any]:
        if request.headers.get("X-NaviXav-ChartFox") != "connect":
            raise HTTPException(403, "Confirmation de connexion absente.")
        port = request.url.port or 8765
        if port < 8765 or port > 8775:
            raise HTTPException(409, "Port de callback ChartFox non enregistré.")
        redirect_uri = f"http://127.0.0.1:{port}/oauth/chartfox/callback"
        authorization_url = chartfox.begin_authorization(redirect_uri)
        callback = getattr(app.state, "request_open_chartfox_auth", None)
        if not callable(callback):
            raise HTTPException(
                409,
                "La connexion ChartFox est disponible dans l'application Windows.",
            )
        callback(authorization_url)
        return {"opened": True}

    @app.get("/oauth/chartfox/callback")
    def chartfox_callback(
        code: str = "",
        state: str = "",
        error: str = "",
        error_description: str = "",
    ) -> HTMLResponse:
        try:
            if error:
                raise ChartFoxError(error_description or error)
            chartfox.complete_authorization(code, state)
            title = "ChartFox connecté"
            body = "Tu peux fermer cette page et revenir dans NaviXav."
        except ChartFoxError as exc:
            title = "Connexion ChartFox impossible"
            body = str(exc)
        return HTMLResponse(
            "<!doctype html><html lang='fr'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title>"
            "<body style='font:16px system-ui;background:#07111f;color:#e5edf7;"
            "padding:3rem;max-width:42rem;margin:auto'>"
            f"<h1>{html.escape(title)}</h1><p>{html.escape(body)}</p></body></html>",
            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
        )

    @app.post("/api/chartfox/disconnect")
    def chartfox_disconnect(request: Request) -> dict[str, bool]:
        if request.headers.get("X-NaviXav-ChartFox") != "disconnect":
            raise HTTPException(403, "Confirmation de déconnexion absente.")
        chartfox.disconnect()
        return {"connected": False}

    def aircraft_folders(explicit_path: str = "") -> list[Path]:
        raw = explicit_path.strip()
        if not raw and settings.aircraft_community_path is not None:
            raw = str(settings.aircraft_community_path)
        return community_folders([Path(raw)]) if raw else community_folders()

    def aircraft_inventory(explicit_path: str = "") -> dict[str, object]:
        return survey(aircraft_matcher, aircraft_folders(explicit_path)).to_dict()

    aircraft_document_files: dict[str, tuple[Path, Path]] = {}

    @app.get("/api/aircraft/documents")
    def aircraft_documents(title: str = "", icao: str = "") -> dict[str, object]:
        nonlocal aircraft_document_files
        folders = aircraft_folders()
        packages, files = document_inventory(folders, title=title, icao=icao)
        aircraft_document_files = files
        return {"community_found": bool(folders), "packages": packages}

    @app.api_route("/api/aircraft/documents/{document_id}", methods=["GET", "HEAD"])
    def aircraft_document(document_id: str) -> FileResponse:
        location = aircraft_document_files.get(document_id)
        if location is None:
            raise HTTPException(404, "Documentation introuvable. Actualisez la liste.")
        try:
            path = checked_document(*location)
        except (OSError, RuntimeError, ValueError) as exc:
            LOGGER.warning("Ouverture d'un PDF avion impossible : %s", type(exc).__name__)
            raise HTTPException(404, "Ce PDF n’est plus disponible ou est illisible.") from exc
        return FileResponse(path, media_type="application/pdf", filename=path.name,
                            content_disposition_type="inline",
                            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    @app.get("/api/aircraft/documents/{document_id}/search")
    def search_aircraft_document(document_id: str, q: str = "") -> dict[str, object]:
        if not 2 <= len(q.strip()) <= 120:
            raise HTTPException(400, "Saisissez entre 2 et 120 caractères.")
        location = aircraft_document_files.get(document_id)
        if location is None:
            raise HTTPException(404, "Documentation introuvable. Actualisez la liste.")
        try:
            return search_document(checked_document(*location), q.strip())
        except Exception as exc:
            # Les PDF tiers peuvent être chiffrés, mal formés ou sans texte.
            LOGGER.warning("Recherche PDF avion impossible : %s", type(exc).__name__)
            raise HTTPException(422, "Recherche indisponible pour ce PDF.") from exc

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

    @app.get("/api/aircraft/photo")
    def aircraft_photo(
        icao: str = "", name: str = "", community: str = ""
    ) -> FileResponse:
        """Sert uniquement la vignette d'un appareil recensé dans Community."""
        wanted_icao = icao.strip().upper()
        wanted_words = {
            word for word in re.findall(r"[a-z0-9]+", name.lower()) if len(word) >= 3
        }
        candidates: list[tuple[int, Path]] = []
        for aircraft in scan(aircraft_folders(community)):
            thumbnail = aircraft.thumbnail
            if thumbnail is None:
                continue
            labels = " ".join((aircraft.label, *aircraft.titles)).lower()
            label_words = set(re.findall(r"[a-z0-9]+", labels))
            score = len(wanted_words & label_words)
            if wanted_icao and aircraft.icao == wanted_icao:
                score += 10
            if score:
                candidates.append((score, thumbnail))
        if not candidates:
            raise HTTPException(404, "Aucune vignette locale pour cet appareil.")
        path = max(candidates, key=lambda item: item[0])[1]
        return FileResponse(path, headers={"Cache-Control": "private, max-age=3600"})

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
        configure_traffic_injection()
        values = settings.user_values()
        values["lan_restart_required"] = settings.lan_enabled != lan_active
        return values

    @app.post("/api/plan")
    def build_plan(request: PlanRequest) -> dict[str, Any]:
        total_started = time.monotonic()
        LOGGER.info("Calcul du plan démarré")
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

        provider = open_provider()
        try:
            cache_before = provider.stats()
            completion_started = time.monotonic()
            engine = CompletionEngine(
                provider, settings, AirportPreferences.load(
                    settings.airport_preferences_path
                )
            )
            plan = engine.complete(ofp, request.to_overrides())
            payload = plan.to_dict()
            payload["atc_route"] = plan.atc_route()
            payload["panel_revision"] = current_plan_state.get("panel_revision", 0) + 1
            current_plan_state["panel_revision"] = payload["panel_revision"]
            panel_summary.clear()
            current_plan_state["payload"] = copy.deepcopy(payload)
            current_plan_state["ofp"] = ofp
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
                        "edge_lights": r.edge_lights,
                        "center_lights": r.center_lights,
                    }
                    for r in provider.runways(icao)
                ],
                "frequencies": [
                    {"code": f.code, "mhz": f.mhz, "name": f.name}
                    for f in provider.frequencies(icao)
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
            # Même forme que le roulage : le message français part dans les
            # traces, le code et ses paramètres traversent pour que le
            # navigateur affiche la raison dans la langue de l'interface.
            raise HTTPException(404, {
                "message": str(exc),
                "code": "ground_airport_absent",
                "params": {"icao": icao.upper()},
            }) from exc
        finally:
            provider.close()

    @app.get("/api/ground/{icao}/route")
    def ground_route(
        icao: str,
        parking: str,
        runway: str,
        direction: str = DEPARTURE,
        via: str = "",
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict[str, Any]:
        """Itinéraire de roulage entre un poste de stationnement et une piste.

        `via` est la suite de voies dictée par le contrôleur, telle que le
        pilote l'a saisie. Vide, l'itinéraire est celui que NaviXav calcule.
        """
        provider = open_provider()
        try:
            graph = build_graph(provider, icao)
            position = (
                graph.to_local(latitude, longitude)
                if latitude is not None and longitude is not None else None
            )
            return plan_taxi(
                graph,
                parking=parking,
                runway=runway,
                direction=direction,
                via=parse_taxiways(via),
                position=position,
            ).to_dict()
        except GroundError as exc:
            # Le détail part structuré : la langue d'affichage n'est connue
            # que du navigateur, qui recompose le message à partir du code.
            raise HTTPException(404, exc.to_dict()) from exc
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
        via: str = "",
    ) -> dict[str, Any]:
        """Situation de l'avion sur son roulage, et consigne du moment.

        L'itinéraire est recalculé à chaque interrogation plutôt que conservé
        d'un appel à l'autre : le service ne garde aucun état de session, et le
        réseau étant en cache, le calcul complet tient en quelques
        millisecondes.

        C'est ce qui permet à une clairance saisie de survivre au guidage sans
        rien stocker : le client la renvoie avec chaque position, exactement
        comme le poste et la piste.
        """
        provider = open_provider()
        try:
            graph = build_graph(provider, icao)
            position = graph.to_local(latitude, longitude)
            clearance = parse_taxiways(via)
            plan = plan_taxi(
                graph,
                parking=parking,
                runway=runway,
                direction=direction,
                via=clearance,
            )
            guidance = guide(plan, *position)
            if replan_needed(guidance, plan):
                plan = replan(plan, *position)
                guidance = guide(plan, *position)
            return {
                "plan": plan.to_dict(),
                "guidance": guidance.to_dict(),
                "recomputed": plan.from_position,
            }
        except GroundError as exc:
            # Le détail part structuré : la langue d'affichage n'est connue
            # que du navigateur, qui recompose le message à partir du code.
            raise HTTPException(404, exc.to_dict()) from exc
        finally:
            provider.close()

    @app.get("/api/ground/{icao}/parkings")
    def ground_parkings(icao: str) -> dict[str, Any]:
        """Postes de stationnement et pistes que le réseau au sol dessert."""
        provider = open_provider()
        try:
            graph = build_graph(provider, icao)
        except GroundError as exc:
            # Le détail part structuré : la langue d'affichage n'est connue
            # que du navigateur, qui recompose le message à partir du code.
            raise HTTPException(404, exc.to_dict()) from exc
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

    def official_airport_documents(airport: str) -> dict[str, Any]:
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

    def chartfox_airport_documents(airport: str) -> dict[str, Any]:
        try:
            charts = chartfox.list_airport_charts(airport)
        except ChartFoxError as exc:
            raise HTTPException(502, str(exc)) from exc
        documents = []
        for chart_data in charts:
            document = chart_data.to_dict()
            document["provider"] = "chartfox"
            document["pdf_url"] = "/api/charts/document?" + urlencode({
                "provider": "chartfox",
                "icao": airport,
                "chart": chart_data.id,
            })
            documents.append(document)
        try:
            official_provider = official_chart_backend(airport)[0]
        except HTTPException:
            official_provider = ""
        return {
            "icao": airport,
            "provider": "chartfox",
            "source": "Chart data powered by ChartFox · simulation uniquement",
            "effective_date": "",
            "official_available": bool(official_provider),
            "official_provider": official_provider,
            "charts": documents,
        }

    @app.get("/api/charts/airport/{icao}")
    def airport_charts(icao: str, source: str = "auto") -> dict[str, Any]:
        airport = icao.strip().upper()
        if len(airport) != 4 or not airport.isalnum():
            raise HTTPException(400, "Code OACI invalide.")
        selected = source.strip().lower()
        if selected not in {"auto", "official", "chartfox"}:
            raise HTTPException(400, "Source de cartes inconnue.")
        if selected == "chartfox":
            return chartfox_airport_documents(airport)
        return official_airport_documents(airport)

    @app.get("/api/charts/access")
    def chart_access(provider: str, icao: str, chart: str) -> dict[str, bool]:
        if provider != "chartfox":
            return {
                "requires_preauth": False,
                "allows_iframe": True,
                "can_embed": True,
            }
        try:
            return chartfox.chart_access(chart, icao)
        except ChartFoxError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.get("/api/charts/document")
    def official_chart_document(
        provider: str,
        icao: str,
        chart: str,
    ) -> Response:
        if provider == "chartfox":
            try:
                content, media_type, filename = chartfox.document(chart, icao)
            except ChartFoxError as exc:
                raise HTTPException(502, str(exc)) from exc
            return Response(
                content,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'inline; filename="{filename}"',
                    "Cache-Control": "private, no-store",
                    "X-Chart-Attribution": "Chart data powered by ChartFox",
                },
            )
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
        aircraft: str | None = None,
    ) -> dict[str, Any]:
        tracker.set_aircraft_hint(aircraft)
        try:
            state = tracker.read()
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

    @app.get("/api/live/traffic")
    def live_traffic() -> dict[str, Any]:
        """Trafic voisin, lu dans le simulateur.

        C'est la source du plan de roulage, et la seule qui convienne : les
        clients réseau injectent leurs appareils dans le simulateur, qui les
        rend à leur position courante. Le relevé VATSIM, vieux de quinze
        secondes, poserait un avion en dehors de la voie qu'il roule.
        """
        if not settings.traffic_enabled:
            return {"enabled": False, "traffic": []}
        try:
            reports = tracker.traffic(strict=True)
        except PositionUnavailable as exc:
            raise HTTPException(503, "Lecture du trafic temporairement indisponible.") from exc
        return {"enabled": True, "traffic": [report.to_dict() for report in reports]}

    @app.get("/api/vatsim/aircraft/{callsign}")
    def vatsim_aircraft(callsign: str) -> dict[str, Any]:
        """Fiche d'un appareil ouvert sur la carte.

        Les terrains sont nommés depuis la base MSFS quand elle les connaît :
        « EHAM » dit peu, « Amsterdam Schiphol » dit tout. Un terrain absent
        garde son code plutôt que de faire échouer la fiche.
        """
        return traffic_aircraft_detail(vatsim, callsign)

    @app.get("/api/traffic/aircraft/{callsign}")
    def selected_traffic_aircraft(callsign: str) -> dict[str, Any]:
        return traffic_aircraft_detail(selected_traffic_provider(), callsign)

    def traffic_aircraft_detail(provider, callsign: str) -> dict[str, Any]:
        if not settings.traffic_enabled:
            raise HTTPException(404, "Le trafic est éteint.")
        try:
            found = provider.detail(callsign)
        except (VatsimError, IvaoError, OpenSkyError) as exc:
            raise HTTPException(503, str(exc)) from exc
        if found is None:
            raise HTTPException(
                404, f"{callsign.upper()} n'est plus en ligne sur le réseau."
            )

        names = _airport_labels(found.departure, found.arrival)
        payload = found.to_dict()
        payload["departure_name"] = names.get(found.departure, "")
        payload["arrival_name"] = names.get(found.arrival, "")
        return payload

    def _airport_labels(*icaos: str) -> dict[str, str]:
        """Noms lisibles des terrains déjà connus de la base.

        La lecture est volontairement limitée au cache : ouvrir une fiche ne
        doit pas déclencher une extraction MSFS pour un aérodrome que le
        pilote ne fait que survoler du regard.
        """
        wanted = [icao for icao in icaos if icao]
        if not wanted:
            return {}
        try:
            provider = open_provider()
        except Exception:  # base absente : le code OACI suffit
            return {}
        try:
            lookup = getattr(provider, "airport_name", None)
            if not callable(lookup):
                return {}
            return {icao: lookup(icao) for icao in wanted}
        except Exception:
            return {}
        finally:
            provider.close()

    @app.get("/api/vatsim/traffic")
    def vatsim_traffic() -> dict[str, Any]:
        """Appareils connectés au réseau, pour la carte en route.

        Le relevé est rendu entier : la carte se déplace où le pilote veut, et
        c'est elle qui écarte ce qui sort du cadre.
        """
        return traffic_payload(vatsim)

    @app.get("/api/traffic")
    def selected_traffic() -> dict[str, Any]:
        return traffic_payload(selected_traffic_provider())

    def own_aircraft_position() -> tuple[tuple[float, float] | None, float | None]:
        """Place du joueur, quand le simulateur la donne.

        Elle sert à écarter la silhouette que le réseau rend de son propre
        appareil : sans simulateur, il n'y a rien à confondre.
        """
        try:
            state = tracker.read()
        except (PositionUnavailable, OSError, RuntimeError):
            return None, None
        return (state.latitude, state.longitude), state.altitude_ft

    def traffic_payload(provider) -> dict[str, Any]:
        if not settings.traffic_enabled:
            return {"enabled": False, "available": False, "traffic": []}

        try:
            aircraft = provider.traffic()
            updated_at = provider.updated_at()
        except (VatsimError, IvaoError, OpenSkyError) as exc:
            LOGGER.info("Trafic %s indisponible : %s", provider.name, exc)
            return {
                "enabled": True,
                "available": False,
                "reason": str(exc),
                "traffic": [],
            }

        centre, own_altitude = own_aircraft_position()
        visible = [
            entry for entry in aircraft
            if not is_own_position(entry, centre, own_altitude)
        ]
        if centre is not None:
            visible = sorted(
                (
                    entry for entry in visible
                    if distance_nm(centre, (entry.latitude, entry.longitude))
                    <= settings.traffic_radius_nm
                ),
                key=lambda entry: distance_nm(
                    centre, (entry.latitude, entry.longitude)
                ),
            )
        visible = visible[:settings.traffic_max_aircraft]
        return {
            "enabled": True,
            "available": True,
            "source": provider.name,
            "updated_at": updated_at,
            "traffic": [entry.to_dict() for entry in visible],
        }

    @app.get("/api/vatsim")
    def vatsim_positions(icao: str = "") -> dict[str, Any]:
        """Postes de contrôle en ligne pour les terrains demandés.

        Rien n'est interrogé tant que le réglage est désactivé : l'appel
        réseau n'apprend rien à qui ne vole pas sur le réseau, et le silence
        est ici la bonne valeur par défaut.
        """
        if not settings.vatsim_enabled:
            return {"enabled": False, "available": False, "positions": {}}

        wanted = [part.strip().upper() for part in icao.split(",") if part.strip()]
        if not wanted:
            return {"enabled": True, "available": True, "positions": {}}

        try:
            found = vatsim.positions(wanted)
            updated_at = vatsim.updated_at()
        except VatsimError as exc:
            # Le réseau indisponible ne doit pas teinter la rangée de
            # fréquences : sans réponse, aucun poste n'est marqué en ligne.
            LOGGER.info("Postes VATSIM indisponibles : %s", exc)
            return {
                "enabled": True,
                "available": False,
                "reason": str(exc),
                "positions": {},
            }

        return {
            "enabled": True,
            "available": True,
            "updated_at": updated_at,
            "positions": {
                key: [position.to_dict() for position in entries]
                for key, entries in found.items()
            },
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

    @app.post("/api/fsltl/download")
    def open_fsltl_download(request: Request) -> dict[str, bool]:
        if request.headers.get("X-NaviXav-External") != "fsltl":
            raise HTTPException(403, "Confirmation d’ouverture absente.")
        callback = getattr(app.state, "request_open_fsltl_download", None)
        if not callable(callback):
            raise HTTPException(
                409,
                "Le téléchargement FSLTL est disponible dans l’application Windows.",
            )
        callback()
        return {"opened": True}

    # ---------------------------------------------------------------- panneau
    # Le panneau de la barre d'outils MSFS vit dans le simulateur, sur une
    # autre origine : ses appels sont donc des requêtes croisées. Elles restent
    # locales — le pare-feu du service n'ouvre rien de plus —, n'emploient que
    # des GET simples pour éviter une requête de contrôle préalable, et ne
    # rendent rien qu'un pilote ne voie déjà sur sa propre carte.

    @app.middleware("http")
    async def allow_the_msfs_panel(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/panel/"):
            response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    def _panel_state() -> dict[str, object]:
        models = traffic.installation.to_dict()
        snapshot = panel_summary.get("snapshot", {})
        fresh = time.monotonic() - panel_summary.get("received_at", float("-inf")) <= 10
        return {
            "running": True,
            "version": __version__,
            "traffic_enabled": settings.traffic_enabled,
            "traffic_source": settings.traffic_source,
            "aircraft_models": settings.aircraft_models,
            "models_detected": bool(models.get("detected")),
            "models_version": models.get("version", ""),
            "models_count": models.get("models", 0),
            "injection_active": traffic.active,
            "injection": traffic.status,
            "flight": {**snapshot, "fresh": fresh,
                       "connected": bool(fresh and snapshot.get("connected"))},
            "conflict": list(traffic.conflicts),
        }

    def _apply_panel_values(values: dict[str, object]) -> dict[str, object]:
        nonlocal settings
        # Le panneau ne transmet que la commande qu'il vient de recevoir. Une
        # mise à jour partielle ne doit donc jamais faire passer les champs
        # absents par les valeurs par défaut de ``with_user_values`` : c'est
        # ainsi qu'un clic sur Trafic effaçait les identifiants SimBrief.
        settings = settings.with_user_values({**settings.user_values(), **values})
        try:
            save_user_settings(settings)
        except OSError as exc:
            # Un réglage non enregistré vaut mieux qu'un panneau en erreur :
            # il tiendra jusqu'à la fermeture, et le journal garde la trace.
            LOGGER.warning("Réglage du panneau non enregistré : %s", exc)
        configure_traffic_injection()
        return _panel_state()

    @app.get("/api/panel/state")
    def panel_state() -> dict[str, object]:
        return _panel_state()

    @app.post("/api/panel/flight")
    def publish_panel_flight(summary: PanelFlightSummary) -> dict[str, bool]:
        if summary.revision != current_plan_state.get("panel_revision", 0):
            raise HTTPException(409, "Le plan a changé.")
        panel_summary.update(snapshot=summary.model_dump(), received_at=time.monotonic())
        return {"ok": True}

    @app.get("/api/panel/traffic/{state}")
    def panel_set_traffic(state: str) -> dict[str, object]:
        if state not in {"on", "off"}:
            raise HTTPException(400, "État de trafic inattendu.")
        return _apply_panel_values({"traffic_enabled": state == "on"})

    @app.get("/api/panel/source/{name}")
    def panel_set_source(name: str) -> dict[str, object]:
        # La liste vient des réglages plutôt que d'être recopiée ici : une
        # source ajoutée à l'application et refusée par le panneau laisserait
        # le pilote devant un bouton sans effet.
        if name not in TRAFFIC_SOURCES:
            raise HTTPException(400, "Source de trafic inconnue.")
        return _apply_panel_values({"traffic_source": name})

    @app.get("/api/panel/show")
    def panel_show_window() -> dict[str, bool]:
        """Ramène la fenêtre NaviXav au premier plan depuis le simulateur."""
        callback = getattr(app.state, "request_show_window", None)
        if not callable(callback):
            raise HTTPException(
                409, "La fenêtre n'est disponible que dans l'application Windows."
            )
        callback()
        return {"shown": True}

    def _panel_community_folders():
        if settings.aircraft_community_path:
            return community_folders(explicit=[settings.aircraft_community_path])
        return None

    @app.get("/api/msfs-panel/status")
    def msfs_panel_status() -> dict[str, object]:
        return msfs_panel.status(_panel_community_folders()).to_dict()

    @app.post("/api/msfs-panel/install")
    def msfs_panel_install(request: Request) -> dict[str, object]:
        if request.headers.get("X-NaviXav-External") != "msfs-panel":
            raise HTTPException(403, "Confirmation d’installation absente.")
        try:
            msfs_panel.install(_panel_community_folders())
        except (FileNotFoundError, FileExistsError, OSError) as exc:
            raise HTTPException(409, str(exc)) from exc
        return msfs_panel.status(_panel_community_folders()).to_dict()

    @app.post("/api/msfs-panel/uninstall")
    def msfs_panel_uninstall(request: Request) -> dict[str, object]:
        if request.headers.get("X-NaviXav-External") != "msfs-panel":
            raise HTTPException(403, "Confirmation de retrait absente.")
        try:
            msfs_panel.uninstall(_panel_community_folders())
        except (FileExistsError, OSError) as exc:
            raise HTTPException(409, str(exc)) from exc
        return msfs_panel.status(_panel_community_folders()).to_dict()

    @app.post("/api/aig/download")
    def open_aig_download(request: Request) -> dict[str, bool]:
        if request.headers.get("X-NaviXav-External") != "aig":
            raise HTTPException(403, "Confirmation d’ouverture absente.")
        callback = getattr(app.state, "request_open_aig_download", None)
        if not callable(callback):
            raise HTTPException(
                409,
                "Le téléchargement AIG est disponible dans l’application Windows.",
            )
        callback()
        return {"opened": True}

    @app.get("/")
    def index() -> HTMLResponse:
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(
            html.replace("__NAVIXAV_VERSION__", __version__),
            headers={"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"},
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


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

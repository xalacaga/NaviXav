"""API locale et service des fichiers statiques.

L'application n'écoute que sur la boucle locale : elle expose le Pilot ID et le
contenu du dispatch, qui n'ont pas à sortir de la machine.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from navixav import __version__
from navixav.chart import EARTH_RADIUS_M, build_chart
from navixav.config import (
    Settings,
    load_user_settings,
    save_user_settings,
)
from navixav.faa import FaaClient, FaaError
from navixav.live import LiveTracker, PositionUnavailable
from navixav.live.demo import DemoSource
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

STATIC_DIR = resource_path("navixav", "web", "static")
DEMO_OFP = resource_path("tests", "data", "ofp_lfst_lfbo.json")
FAA_ICAO_PREFIXES = {
    "PA", "PF", "PG", "PH", "PJ", "PM", "PO", "PW",
    "NS", "TI", "TJ",
}
LOGGER = logging.getLogger(__name__)


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


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_user_settings(Settings.load())
    app = FastAPI(title="NaviXav", version=__version__, docs_url="/api/docs")
    tracker = LiveTracker()
    sia = SiaClient()
    faa = FaaClient()
    national_aip = {
        source.provider: NationalAipClient(source)
        for source in NATIONAL_AIP_SOURCES
    }
    demo_state: dict[str, Any] = {}

    @app.middleware("http")
    async def log_relevant_requests(request: Request, call_next):
        """Journalise les lenteurs et erreurs sans saturer le fichier."""
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
        return response

    @app.on_event("shutdown")
    def _close_tracker() -> None:
        LOGGER.info("Fermeture des connexions et sessions NaviXav")
        tracker.close()
        sia.session.close()
        faa.session.close()
        for client in national_aip.values():
            client.session.close()

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

    def open_provider() -> MsfsProvider:
        try:
            return MsfsProvider(settings.navdata_store)
        except NavdataError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/status")
    def status() -> dict[str, Any]:
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

        return {
            "version": __version__,
            "simbrief_configured": bool(
                settings.simbrief_pilot_id or settings.simbrief_username
            ),
            "simbrief_target": settings.describe_simbrief_target(),
            "metar_source": settings.metar_source,
            "rnp_capable": settings.aircraft_rnp_capable,
            "demo_available": DEMO_OFP.is_file(),
            "navdata": navdata,
        }

    @app.get("/api/settings")
    def get_settings() -> dict[str, object]:
        return settings.user_values()

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
        return settings.user_values()

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
            payload["demo"] = request.demo
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
    ) -> dict[str, Any]:
        if demo:
            _ensure_demo_source(icao, runway)
        try:
            state = tracker.read(allow_demo=demo)
        except PositionUnavailable as exc:
            return {"connected": False, "reason": str(exc)}
        return {"connected": True, "aircraft": state.to_dict()}

    @app.get("/api/simulator")
    def simulator_status() -> dict[str, object]:
        try:
            state = tracker.read()
        except PositionUnavailable as exc:
            return {"connected": False, "reason": str(exc)}
        return {"connected": True, "source": state.source}

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

    def _ensure_demo_source(icao: str | None, runway: str | None) -> None:
        """Construit un roulage simulé du premier poste vers le seuil de piste."""
        key = (icao or "", runway or "")
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
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


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

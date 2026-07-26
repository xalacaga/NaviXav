"""API locale et service des fichiers statiques.

L'application n'écoute que sur la boucle locale : elle expose le Pilot ID et le
contenu du dispatch, qui n'ont pas à sortir de la machine.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import BackgroundTasks, FastAPI, HTTPException
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
from navixav.live import LiveTracker, PositionUnavailable
from navixav.live.demo import DemoSource
from navixav.navdata.base import NavdataError, ProcedureKind
from navixav.navdata.msfs import MsfsProvider
from navixav.planner.engine import CompletionEngine, PlannerOverrides
from navixav.preferences import AirportPreferences
from navixav.simbrief.client import SimBriefClient, SimBriefError
from navixav.simbrief.parser import parse_ofp
from navixav.sia import SiaClient, SiaError

STATIC_DIR = Path(__file__).parent / "static"
DEMO_OFP = Path(__file__).resolve().parents[2] / "tests" / "data" / "ofp_lfst_lfbo.json"


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
    demo_state: dict[str, Any] = {}

    @app.on_event("shutdown")
    def _close_tracker() -> None:
        tracker.close()
        sia.session.close()

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
            raise HTTPException(
                500, f"Impossible d'enregistrer les paramètres : {exc}"
            ) from exc
        return settings.user_values()

    @app.post("/api/plan")
    def build_plan(request: PlanRequest) -> dict[str, Any]:
        if request.demo:
            if not DEMO_OFP.is_file():
                raise HTTPException(404, "Jeu de démonstration introuvable.")
            raw = SimBriefClient.from_file(DEMO_OFP)
        else:
            try:
                raw = SimBriefClient(
                    pilot_id=settings.simbrief_pilot_id,
                    username=settings.simbrief_username,
                ).fetch_latest()
            except SimBriefError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc

        ofp = parse_ofp(raw)
        if not ofp.origin_icao or not ofp.destination_icao:
            raise HTTPException(422, "OFP inexploitable : origine ou destination absente.")

        provider = open_provider()
        try:
            engine = CompletionEngine(
                provider, settings, AirportPreferences.load(
                    settings.airport_preferences_path
                )
            )
            plan = engine.complete(ofp, request.to_overrides())
            payload = plan.to_dict()
            payload["atc_route"] = plan.atc_route()
            payload["demo"] = request.demo
            return payload
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
    def shutdown(background_tasks: BackgroundTasks) -> dict[str, bool]:
        callback = getattr(app.state, "request_shutdown", None)
        if not callable(callback):
            raise HTTPException(503, "Arrêt contrôlé indisponible.")
        background_tasks.add_task(callback)
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


def serve(
    host: str = "127.0.0.1",
    port: int = 8765,
    settings: Settings | None = None,
) -> None:
    import uvicorn

    application = create_app(settings)
    config = uvicorn.Config(application, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    application.state.request_shutdown = lambda: setattr(server, "should_exit", True)
    server.run()

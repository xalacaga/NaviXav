"""Position lue directement dans MSFS, via le client SimConnect de NaviXav.

Le projet n'a qu'une seule couche SimConnect : `navixav.msfs.client`. Les
unités sont demandées explicitement au simulateur, qui se charge de la
conversion — plus fiable que de deviner l'unité native d'une variable, dont le
nom peut être trompeur (« PLANE HEADING DEGREES TRUE » est en radians).

Les variables sont réparties en trois blocs lus séparément. La position est
vitale et ne doit jamais dépendre du reste : un avion tiers qui n'expose pas
« LIGHT LOGO » ferait échouer toute la définition et couperait le suivi. Un
bloc secondaire qui échoue est simplement mis en sommeil.
"""

from __future__ import annotations

import logging
import threading
import time

from navixav.live.base import (
    AircraftCapabilities,
    AircraftConfiguration,
    AircraftState,
    PositionUnavailable,
)
from navixav.msfs.client import SimConnectClient, SimConnectError

logger = logging.getLogger(__name__)

# Bloc vital : sans lui, il n'y a pas de suivi. Variable -> unité demandée.
_VARIABLES = (
    ("PLANE LATITUDE", "Degrees"),
    ("PLANE LONGITUDE", "Degrees"),
    ("PLANE ALTITUDE", "Feet"),
    ("PLANE ALT ABOVE GROUND", "Feet"),
    ("PLANE HEADING DEGREES TRUE", "Degrees"),
    ("PLANE HEADING DEGREES MAGNETIC", "Degrees"),
    ("GROUND VELOCITY", "Knots"),
    ("AIRSPEED INDICATED", "Knots"),
    ("VERTICAL SPEED", "Feet per minute"),
    ("SIM ON GROUND", "Bool"),
)

# Bloc de configuration : confort et alarmes. Son échec est toléré.
_CONFIGURATION_VARIABLES = (
    ("GEAR HANDLE POSITION", "Bool"),
    ("GEAR TOTAL PCT EXTENDED", "Percent"),
    ("GEAR CENTER POSITION", "Percent"),
    ("GEAR LEFT POSITION", "Percent"),
    ("GEAR RIGHT POSITION", "Percent"),
    ("FLAPS HANDLE INDEX", "Number"),
    ("TRAILING EDGE FLAPS LEFT PERCENT", "Percent"),
    ("SPOILERS HANDLE POSITION", "Percent"),
    ("SPOILERS ARMED", "Bool"),
    ("BRAKE PARKING POSITION", "Bool"),
    ("LIGHT LANDING", "Bool"),
    ("LIGHT TAXI", "Bool"),
    ("LIGHT STROBE", "Bool"),
    ("LIGHT NAV", "Bool"),
    ("LIGHT BEACON", "Bool"),
    ("LIGHT LOGO", "Bool"),
    ("LIGHT WING", "Bool"),
    ("KOHLSMAN SETTING MB", "Millibars"),
    ("INDICATED ALTITUDE", "Feet"),
    ("AUTOPILOT MASTER", "Bool"),
    ("AUTOPILOT NAV1 LOCK", "Bool"),
    ("AUTOPILOT APPROACH HOLD", "Bool"),
    ("AUTOPILOT GLIDESLOPE HOLD", "Bool"),
    ("AUTOTHROTTLE ACTIVE", "Bool"),
    ("AUTOPILOT ALTITUDE LOCK VAR", "Feet"),
    ("AUTOPILOT HEADING LOCK DIR", "Degrees"),
    ("NAV ACTIVE FREQUENCY:1", "MHz"),
    ("NAV LOCALIZER:1", "Degrees"),
    ("NAV HAS LOCALIZER:1", "Bool"),
    ("NAV HAS GLIDE SLOPE:1", "Bool"),
    ("FUEL TOTAL QUANTITY WEIGHT", "Kilograms"),
    ("TOTAL WEIGHT", "Kilograms"),
    ("AMBIENT WIND DIRECTION", "Degrees"),
    ("AMBIENT WIND VELOCITY", "Knots"),
    ("TOTAL AIR TEMPERATURE", "Celsius"),
    ("AMBIENT IN CLOUD", "Bool"),
    ("ENG ANTI ICE:1", "Bool"),
    ("STALL WARNING", "Bool"),
    ("OVERSPEED WARNING", "Bool"),
    ("FLAP SPEED EXCEEDED", "Bool"),
    ("AIRSPEED BARBER POLE", "Knots"),
    ("AIRSPEED MACH", "Mach"),
    ("SIMULATION RATE", "Number"),
)

# Bloc de capacités : lu une seule fois par avion chargé.
_CAPABILITY_VARIABLES = (
    ("IS GEAR RETRACTABLE", "Bool"),
    ("FLAPS AVAILABLE", "Bool"),
    ("SPOILER AVAILABLE", "Bool"),
    ("FLAPS NUM HANDLE POSITIONS", "Number"),
)

# Une connexion qui vient d'échouer n'est pas retentée immédiatement.
_RETRY_DELAY_S = 5.0

# Un bloc secondaire refusé est mis en sommeil : le retenter à chaque sondage
# coûterait un délai d'attente complet et figerait la position.
_OPTIONAL_RETRY_DELAY_S = 30.0

# Les blocs secondaires ne doivent jamais retarder la position bien longtemps.
_OPTIONAL_TIMEOUT_S = 1.5


class SimConnectSource:
    """Lecture directe dans le simulateur, sans application intermédiaire."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._client: SimConnectClient | None = None
        self._last_failure = 0.0
        self._failure_reason = ""
        self._configuration_disabled_until = 0.0
        self._capabilities: AircraftCapabilities | None = None
        self._capabilities_disabled_until = 0.0

    @property
    def name(self) -> str:
        return "SimConnect"

    def is_available(self) -> bool:
        """Vrai si une DLL SimConnect est présente sur la machine."""
        from navixav.msfs.client import DLL_CANDIDATES

        return any(path.is_file() for path in DLL_CANDIDATES)

    # ------------------------------------------------------------------ #

    def _connect(self) -> SimConnectClient:
        if self._client is not None:
            return self._client
        if time.monotonic() - self._last_failure < _RETRY_DELAY_S:
            raise PositionUnavailable(self._failure_reason or "Simulateur injoignable.")

        try:
            self._client = SimConnectClient()
        except SimConnectError as exc:
            self._fail(str(exc))
        return self._client

    def _fail(self, reason: str) -> None:
        self._last_failure = time.monotonic()
        self._failure_reason = reason
        raise PositionUnavailable(reason)

    def read(self) -> AircraftState:
        with self._lock:
            client = self._connect()
            try:
                values = client.read_simvars(_VARIABLES)
            except SimConnectError as exc:
                self._reset()
                self._fail(
                    "Aucun vol chargé dans le simulateur, ou connexion perdue. "
                    f"({exc})"
                )

            self._failure_reason = ""
            return AircraftState(
                latitude=values["PLANE LATITUDE"],
                longitude=values["PLANE LONGITUDE"],
                altitude_ft=values["PLANE ALTITUDE"],
                height_above_ground_ft=values["PLANE ALT ABOVE GROUND"],
                heading_true_deg=values["PLANE HEADING DEGREES TRUE"] % 360,
                heading_magnetic_deg=values["PLANE HEADING DEGREES MAGNETIC"] % 360,
                ground_speed_kt=values["GROUND VELOCITY"],
                indicated_airspeed_kt=values["AIRSPEED INDICATED"],
                vertical_speed_fpm=values["VERTICAL SPEED"],
                on_ground=bool(values["SIM ON GROUND"]),
                source=self.name,
                configuration=self._read_configuration(client),
            )

    # ------------------------------------------------------------------ #

    def _read_configuration(self, client: SimConnectClient) -> AircraftConfiguration | None:
        """Lit le bloc de configuration, ou renvoie None sans faire échouer."""
        now = time.monotonic()
        if now < self._configuration_disabled_until:
            return None

        try:
            values = client.read_simvars(
                _CONFIGURATION_VARIABLES, timeout_s=_OPTIONAL_TIMEOUT_S
            )
        except SimConnectError as exc:
            self._configuration_disabled_until = now + _OPTIONAL_RETRY_DELAY_S
            logger.info(
                "Configuration avion indisponible, nouvelle tentative dans %.0f s (%s)",
                _OPTIONAL_RETRY_DELAY_S,
                exc,
            )
            return None

        # Certains appareils laissent la SimVar agrégée figée alors que les
        # positions de chaque jambe continuent d'être publiées. La plus petite
        # des trois est volontairement retenue : le train n'est « sorti » que
        # lorsque toutes les jambes le sont.
        gear_positions = (
            values["GEAR CENTER POSITION"],
            values["GEAR LEFT POSITION"],
            values["GEAR RIGHT POSITION"],
        )

        return AircraftConfiguration(
            gear_handle_down=bool(values["GEAR HANDLE POSITION"]),
            gear_extended_pct=min(gear_positions),
            flaps_handle_index=int(round(values["FLAPS HANDLE INDEX"])),
            flaps_extended_pct=values["TRAILING EDGE FLAPS LEFT PERCENT"],
            spoilers_handle_pct=values["SPOILERS HANDLE POSITION"],
            spoilers_armed=bool(values["SPOILERS ARMED"]),
            parking_brake=bool(values["BRAKE PARKING POSITION"]),
            lights={
                "landing": bool(values["LIGHT LANDING"]),
                "taxi": bool(values["LIGHT TAXI"]),
                "strobe": bool(values["LIGHT STROBE"]),
                "nav": bool(values["LIGHT NAV"]),
                "beacon": bool(values["LIGHT BEACON"]),
                "logo": bool(values["LIGHT LOGO"]),
                "wing": bool(values["LIGHT WING"]),
            },
            altimeter_hpa=values["KOHLSMAN SETTING MB"],
            indicated_altitude_ft=values["INDICATED ALTITUDE"],
            autopilot_master=bool(values["AUTOPILOT MASTER"]),
            autopilot_nav_lock=bool(values["AUTOPILOT NAV1 LOCK"]),
            autopilot_approach_hold=bool(values["AUTOPILOT APPROACH HOLD"]),
            autopilot_glideslope_hold=bool(values["AUTOPILOT GLIDESLOPE HOLD"]),
            autothrottle_active=bool(values["AUTOTHROTTLE ACTIVE"]),
            selected_altitude_ft=values["AUTOPILOT ALTITUDE LOCK VAR"],
            selected_heading_deg=values["AUTOPILOT HEADING LOCK DIR"] % 360,
            nav1_frequency_mhz=values["NAV ACTIVE FREQUENCY:1"],
            nav1_course_deg=values["NAV LOCALIZER:1"] % 360,
            nav1_has_localizer=bool(values["NAV HAS LOCALIZER:1"]),
            nav1_has_glide_slope=bool(values["NAV HAS GLIDE SLOPE:1"]),
            fuel_total_kg=values["FUEL TOTAL QUANTITY WEIGHT"],
            total_weight_kg=values["TOTAL WEIGHT"],
            wind_direction_deg=values["AMBIENT WIND DIRECTION"] % 360,
            wind_speed_kt=values["AMBIENT WIND VELOCITY"],
            total_air_temperature_c=values["TOTAL AIR TEMPERATURE"],
            in_cloud=bool(values["AMBIENT IN CLOUD"]),
            engine_anti_ice=bool(values["ENG ANTI ICE:1"]),
            stall_warning=bool(values["STALL WARNING"]),
            overspeed_warning=bool(values["OVERSPEED WARNING"]),
            flap_speed_exceeded=bool(values["FLAP SPEED EXCEEDED"]),
            barber_pole_kt=values["AIRSPEED BARBER POLE"],
            mach=values["AIRSPEED MACH"],
            simulation_rate=values["SIMULATION RATE"],
            capabilities=self._read_capabilities(client),
        )

    def _read_capabilities(self, client: SimConnectClient) -> AircraftCapabilities | None:
        """Capacités de la cellule, relues seulement après un échec."""
        if self._capabilities is not None:
            return self._capabilities

        now = time.monotonic()
        if now < self._capabilities_disabled_until:
            return None

        try:
            values = client.read_simvars(
                _CAPABILITY_VARIABLES, timeout_s=_OPTIONAL_TIMEOUT_S
            )
        except SimConnectError as exc:
            self._capabilities_disabled_until = now + _OPTIONAL_RETRY_DELAY_S
            logger.info("Capacités de l'avion indisponibles (%s)", exc)
            return None

        self._capabilities = AircraftCapabilities(
            retractable_gear=bool(values["IS GEAR RETRACTABLE"]),
            flaps=bool(values["FLAPS AVAILABLE"]),
            spoilers=bool(values["SPOILER AVAILABLE"]),
            flap_positions=int(round(values["FLAPS NUM HANDLE POSITIONS"])),
        )
        return self._capabilities

    def _reset(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # pragma: no cover - fermeture au mieux
                pass
        self._client = None
        # Les capacités appartiennent à l'avion chargé, pas à la connexion :
        # après une reconnexion, l'utilisateur a pu changer d'appareil.
        self._capabilities = None
        self._capabilities_disabled_until = 0.0
        self._configuration_disabled_until = 0.0

    def close(self) -> None:
        with self._lock:
            self._reset()

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
    TrafficReport,
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

# Trafic voisin. Le bloc est volontairement court : il est lu pour chaque
# appareil des environs, et chaque variable de plus se paie autant de fois.
_TRAFFIC_VARIABLES = (
    ("PLANE LATITUDE", "Degrees"),
    ("PLANE LONGITUDE", "Degrees"),
    ("PLANE ALTITUDE", "Feet"),
    ("PLANE ALT ABOVE GROUND", "Feet"),
    ("PLANE HEADING DEGREES TRUE", "Degrees"),
    ("GROUND VELOCITY", "Knots"),
    ("SIM ON GROUND", "Bool"),
)

# L'indicatif que le client réseau donne à l'appareil qu'il injecte. Une IA du
# simulateur en porte un aussi, celui de son vol programmé.
_TRAFFIC_CALLSIGN = "ATC ID"

# Rayon d'énumération. Au sol on regarde son terrain, pas sa région : dix
# kilomètres couvrent le plus vaste aérodrome et ses abords immédiats.
_TRAFFIC_RADIUS_M = 10000

# Un simulateur qui refuse l'énumération la refusera encore dans la seconde.
_TRAFFIC_RETRY_DELAY_S = 60.0

# État de session facultatif. Il reste séparé du bloc vital afin qu'un ancien
# simulateur qui ne connaît pas cette SimVar ne fasse jamais tomber le suivi.
_PAUSE_VARIABLES = (("MOTION SIMULATION", "Bool"),)

# Bloc de configuration : confort et alarmes. Son échec est toléré.
_CONFIGURATION_VARIABLES = (
    ("GEAR HANDLE POSITION", "Bool"),
    ("GEAR TOTAL PCT EXTENDED", "Percent"),
    ("GEAR CENTER POSITION", "Percent"),
    ("GEAR LEFT POSITION", "Percent"),
    ("GEAR RIGHT POSITION", "Percent"),
    ("FLAPS HANDLE INDEX", "Number"),
    ("FLAPS EFFECTIVE HANDLE INDEX", "Number"),
    ("TRAILING EDGE FLAPS LEFT INDEX", "Number"),
    ("FLAPS HANDLE PERCENT", "Percent"),
    ("TRAILING EDGE FLAPS LEFT PERCENT", "Percent"),
    ("TRAILING EDGE FLAPS LEFT ANGLE", "Degrees"),
    ("SPOILERS HANDLE POSITION", "Percent"),
    ("SPOILERS LEFT POSITION", "Percent"),
    ("SPOILERS RIGHT POSITION", "Percent"),
    ("SPOILERS ARMED", "Bool"),
    ("BRAKE PARKING POSITION", "Bool"),
    ("BRAKE PARKING INDICATOR", "Bool"),
    ("LIGHT LANDING", "Bool"),
    ("LIGHT TAXI", "Bool"),
    ("LIGHT STROBE", "Bool"),
    ("LIGHT NAV", "Bool"),
    ("LIGHT BEACON", "Bool"),
    ("LIGHT LOGO", "Bool"),
    ("LIGHT WING", "Bool"),
    ("KOHLSMAN SETTING MB", "Millibars"),
    ("INDICATED ALTITUDE", "Feet"),
    ("PRESSURE ALTITUDE", "Feet"),
    ("AUTOPILOT MASTER", "Bool"),
    ("AUTOPILOT NAV1 LOCK", "Bool"),
    ("AUTOPILOT APPROACH HOLD", "Bool"),
    ("AUTOPILOT GLIDESLOPE HOLD", "Bool"),
    ("AUTOTHROTTLE ACTIVE", "Bool"),
    ("AUTOPILOT ALTITUDE LOCK VAR", "Feet"),
    ("AUTOPILOT HEADING LOCK DIR", "Degrees"),
    ("COM ACTIVE FREQUENCY:1", "MHz"),
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

# SimVars ajoutées aux versions récentes de MSFS. Elles restent dans une
# définition indépendante : si un simulateur plus ancien refuse l'une d'elles,
# le reste de la configuration avion continue d'être lu normalement.
_MODERN_CONFIGURATION_VARIABLES = (
    ("KOHLSMAN SETTING STD:1", "Bool"),
    ("KOHLSMAN SETTING MB EX1:1", "Millibars"),
    ("IS ANY OPEN INTERACTIVE POINTS RISKING TO CAUSE CRASH", "Bool"),
)

# État agrégé officiel des feux extérieurs. Certains avions complexes animent
# correctement ce masque tout en laissant une ou plusieurs SimVars LIGHT ...
# individuelles à zéro. La lecture reste indépendante : son refus ne doit pas
# masquer toute la configuration avion.
_LIGHT_STATE_VARIABLES = (("LIGHT STATES", "Mask"),)

_LIGHT_STATE_BITS = {
    "nav": 0x0001,
    "beacon": 0x0002,
    "landing": 0x0004,
    "taxi": 0x0008,
    "strobe": 0x0010,
    "wing": 0x0080,
    "logo": 0x0100,
}

# Bloc de capacités : lu une seule fois par avion chargé.
_CAPABILITY_VARIABLES = (
    ("IS GEAR RETRACTABLE", "Bool"),
    ("FLAPS AVAILABLE", "Bool"),
    ("SPOILER AVAILABLE", "Bool"),
    ("FLAPS NUM HANDLE POSITIONS", "Number"),
)

# Le cockpit commun FNX_32X des A319/A320/A321 pilote ses commandes avec ces
# LVars. Elles sont lues dans un bloc séparé et seulement lorsque le plan chargé
# identifie un Fenix, afin de ne jamais créer/interpréter ces variables sur un
# autre appareil.
# B_ is the actual barometric state. S_ is the push/pull input and can be 0
# while both EFIS displays are already in STD (verified on the live Fenix).
_FENIX_BARO_VARIABLES = (("L:B_FCU_EFIS1_BARO_STD", "Number"),)
_FENIX_ILS_VARIABLES = (("NAV ACTIVE FREQUENCY:3", "MHz"),)
_NAV_SELECTION_VARIABLES = (("AUTOPILOT NAV SELECTED", "Number"),)

_FENIX_CONTROL_VARIABLES = (
    ("L:S_FC_FLAPS", "Number"),
    ("L:A_FC_SPEEDBRAKE", "Number"),
    ("L:S_MIP_PARKING_BRAKE", "Number"),
    ("L:S_OH_PNEUMATIC_ENG1_ANTI_ICE", "Number"),
    ("L:S_OH_PNEUMATIC_ENG2_ANTI_ICE", "Number"),
)

# Une connexion qui vient d'échouer n'est pas retentée immédiatement.
_RETRY_DELAY_S = 5.0

# Un bloc secondaire refusé est mis en sommeil : le retenter à chaque sondage
# coûterait un délai d'attente complet et figerait la position.
_OPTIONAL_RETRY_DELAY_S = 30.0

# Les blocs secondaires ne doivent jamais retarder la position bien longtemps.
_OPTIONAL_TIMEOUT_S = 1.5

# Le titre est relu assez souvent pour détecter un changement d'appareil sans
# ajouter une requête SimConnect à chaque rafraîchissement de l'interface.
_AIRCRAFT_TITLE_REFRESH_S = 5.0

# Quelques avions tiers laissent TITLE vide tout en publiant correctement leur
# modèle ATC. TITLE reste prioritaire car il est plus descriptif ; ATC MODEL
# fournit une identité minimale issue du simulateur au lieu de retomber sur
# l'appareil du plan SimBrief.
_AIRCRAFT_TITLE_VARIABLES = ("TITLE", "ATC MODEL")


class SimConnectSource:
    """Lecture directe dans le simulateur, sans application intermédiaire."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._client: SimConnectClient | None = None
        self._last_failure = 0.0
        self._failure_reason = ""
        self._configuration_disabled_until = 0.0
        self._modern_configuration_disabled_until = 0.0
        self._light_states_disabled_until = 0.0
        self._pause_disabled_until = 0.0
        self._capabilities: AircraftCapabilities | None = None
        self._capabilities_disabled_until = 0.0
        self._parking_brake_raw: tuple[bool, bool] | None = None
        self._parking_brake_state: bool | None = None
        self._flaps_raw: tuple[int, int, int] | None = None
        self._flaps_index: int | None = None
        self._spoilers_raw: tuple[float, float, float] | None = None
        self._spoilers_pct: float | None = None
        self._aircraft_hint = ""
        self._aircraft_title = ""
        self._aircraft_title_checked_at = 0.0
        self._aircraft_title_disabled_until = 0.0
        self._traffic_disabled_until = 0.0

    @property
    def name(self) -> str:
        return "SimConnect"

    def is_available(self) -> bool:
        """Vrai si une DLL SimConnect est présente sur la machine."""
        from navixav.msfs.client import DLL_CANDIDATES

        return any(path.is_file() for path in DLL_CANDIDATES)

    def set_aircraft_hint(self, hint: str | None) -> None:
        self._aircraft_hint = str(hint or "").strip().upper()

    def _is_fenix_family(self) -> bool:
        identity = f"{self._aircraft_title} {self._aircraft_hint}".upper()
        return "FENIX" in identity and any(
            model in identity for model in ("A319", "A320", "A321")
        )

    def _read_ils_receiver(self, client, values) -> tuple[int | None, float | None]:
        # Loaded aircraft takes precedence over an unrelated planned model.
        identity = (self._aircraft_title or self._aircraft_hint).upper()
        dedicated = (
            ("FENIX" in identity and any(m in identity for m in ("A319", "A320", "A321")))
            or "A32NX" in identity
            or ("FLYBYWIRE" in identity and "A320" in identity)
        )
        receiver = None
        try:
            if dedicated:
                # Confirmed captain ILS mapping; NAV1/2 remain independent VORs.
                receiver = 3
            else:
                selected = client.read_simvars(
                    _NAV_SELECTION_VARIABLES, timeout_s=_OPTIONAL_TIMEOUT_S
                ).get("AUTOPILOT NAV SELECTED")
                if selected not in (1, 2, 3, 4):
                    return None, None
                receiver = int(selected)
            if receiver == 1:
                frequency = values["NAV ACTIVE FREQUENCY:1"]
            else:
                name = f"NAV ACTIVE FREQUENCY:{receiver}"
                frequency = client.read_simvars(
                    ((name, "MHz"),), timeout_s=_OPTIONAL_TIMEOUT_S
                ).get(name)
            if frequency is not None and 108 <= frequency <= 117.95:
                return receiver, frequency
        except SimConnectError as exc:
            logger.info("ILS receiver unavailable (%s)", exc)
        return receiver, None

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
            title = self._read_aircraft_title(client)
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
                paused=self._read_paused(client),
                title=title,
                source=self.name,
                configuration=self._read_configuration(client),
            )

    def traffic(self, radius_m: int = _TRAFFIC_RADIUS_M, *, strict: bool = False) -> list[TrafficReport]:
        """Appareils présents autour de l'avion du joueur.

        Le simulateur inclut le joueur dans sa propre énumération : il est
        écarté par son identifiant d'objet, appris lors du dernier relevé de
        position. Le comparer par la distance ferait disparaître un appareil
        stationné au poste voisin.

        Un refus met la lecture en sommeil au lieu de la retenter chaque
        seconde : le trafic est un confort, jamais une raison de peser sur le
        simulateur.
        """
        if time.monotonic() < self._traffic_disabled_until:
            if strict:
                raise PositionUnavailable("Lecture du trafic temporairement indisponible.")
            return []

        with self._lock:
            client = self._connect()
            try:
                rows = client.read_objects(
                    _TRAFFIC_VARIABLES, radius_m, text_variable=_TRAFFIC_CALLSIGN
                )
            except SimConnectError as exc:
                self._traffic_disabled_until = time.monotonic() + _TRAFFIC_RETRY_DELAY_S
                logger.info("Trafic du simulateur indisponible : %s", exc)
                if strict:
                    raise PositionUnavailable("Lecture du trafic temporairement indisponible.") from exc
                return []

            own = client.user_object_id
            reports: list[TrafficReport] = []
            for row in rows:
                if own is not None and row.get("object_id") == own:
                    continue
                reports.append(
                    TrafficReport(
                        object_id=int(row.get("object_id", 0)),
                        latitude=row["PLANE LATITUDE"],
                        longitude=row["PLANE LONGITUDE"],
                        callsign=str(row.get(_TRAFFIC_CALLSIGN, "")).strip().upper(),
                        altitude_ft=row["PLANE ALTITUDE"],
                        height_above_ground_ft=row["PLANE ALT ABOVE GROUND"],
                        heading_true_deg=row["PLANE HEADING DEGREES TRUE"] % 360,
                        ground_speed_kt=row["GROUND VELOCITY"],
                        on_ground=bool(row["SIM ON GROUND"]),
                    )
                )
            return reports

    # ------------------------------------------------------------------ #

    def _read_aircraft_title(self, client: SimConnectClient) -> str:
        """Lit le titre MSFS sans rendre le suivi dépendant de cette SimVar."""
        now = time.monotonic()
        if now < self._aircraft_title_disabled_until:
            return self._aircraft_title
        if (
            self._aircraft_title_checked_at
            and now - self._aircraft_title_checked_at < _AIRCRAFT_TITLE_REFRESH_S
        ):
            return self._aircraft_title

        reader = getattr(client, "read_string_simvar", None)
        if not callable(reader):
            return self._aircraft_title
        errors: list[SimConnectError] = []
        title = ""
        for variable in _AIRCRAFT_TITLE_VARIABLES:
            try:
                title = str(
                    reader(variable, timeout_s=_OPTIONAL_TIMEOUT_S)
                ).strip()
            except SimConnectError as exc:
                errors.append(exc)
                continue
            if title:
                break

        if not title and len(errors) == len(_AIRCRAFT_TITLE_VARIABLES):
            self._aircraft_title_disabled_until = now + _OPTIONAL_RETRY_DELAY_S
            logger.info(
                "Titre avion indisponible, nouvelle tentative dans %.0f s (%s)",
                _OPTIONAL_RETRY_DELAY_S,
                errors[-1],
            )
        else:
            self._aircraft_title_checked_at = now
            if title:
                if self._aircraft_title and title != self._aircraft_title:
                    # Les valeurs mémorisées décrivent l'ancienne cellule.
                    self._capabilities = None
                    self._capabilities_disabled_until = 0.0
                    self._configuration_disabled_until = 0.0
                    self._modern_configuration_disabled_until = 0.0
                    self._light_states_disabled_until = 0.0
                    self._parking_brake_raw = None
                    self._parking_brake_state = None
                    self._flaps_raw = None
                    self._flaps_index = None
                    self._spoilers_raw = None
                    self._spoilers_pct = None
                self._aircraft_title = title
        return self._aircraft_title

    def _read_paused(self, client: SimConnectClient) -> bool | None:
        """Indique la pause normale ou active, si MSFS expose cet état."""
        now = time.monotonic()
        if now < self._pause_disabled_until:
            return None
        try:
            values = client.read_simvars(
                _PAUSE_VARIABLES, timeout_s=_OPTIONAL_TIMEOUT_S
            )
        except SimConnectError as exc:
            self._pause_disabled_until = now + _OPTIONAL_RETRY_DELAY_S
            logger.info(
                "État de pause indisponible, nouvelle tentative dans %.0f s (%s)",
                _OPTIONAL_RETRY_DELAY_S,
                exc,
            )
            return None
        return not bool(values["MOTION SIMULATION"])

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
        flaps_index = self._resolve_flaps_index(
            values["FLAPS HANDLE INDEX"],
            values["FLAPS EFFECTIVE HANDLE INDEX"],
            values["TRAILING EDGE FLAPS LEFT INDEX"],
        )
        spoilers_pct = self._resolve_spoilers_pct(
            values["SPOILERS HANDLE POSITION"],
            values["SPOILERS LEFT POSITION"],
            values["SPOILERS RIGHT POSITION"],
        )
        spoilers_armed = bool(values["SPOILERS ARMED"])
        parking_brake = self._resolve_parking_brake(
            values["BRAKE PARKING POSITION"],
            values["BRAKE PARKING INDICATOR"],
        )
        engine_anti_ice: bool | None = bool(values["ENG ANTI ICE:1"])

        if self._is_fenix_family():
            # Sur Fenix la SimVar standard n'est pas une source de repli
            # fiable. Si le bloc propre à l'addon manque momentanément, un
            # état inconnu vaut mieux qu'un faux OFF susceptible d'alarmer.
            engine_anti_ice = None
            try:
                fenix = client.read_simvars(
                    _FENIX_CONTROL_VARIABLES, timeout_s=_OPTIONAL_TIMEOUT_S
                )
            except SimConnectError as exc:
                logger.info("Commandes Fenix indisponibles (%s)", exc)
            else:
                flaps_index = max(0, min(4, int(round(fenix["L:S_FC_FLAPS"]))))
                speedbrake = max(0.0, min(3.0, fenix["L:A_FC_SPEEDBRAKE"]))
                spoilers_armed = speedbrake < 0.5
                spoilers_pct = max(0.0, (speedbrake - 1.0) * 50.0)
                parking_brake = bool(fenix["L:S_MIP_PARKING_BRAKE"])
                # Le Fenix anime son panneau pneumatique avec une LVar et peut
                # laisser la SimVar standard ENG ANTI ICE à zéro. Lire la
                # commande du cockpit empêche alors une fausse alarme qui
                # apparaissait et disparaissait au gré de la valeur standard.
                engine_anti_ice = all(
                    bool(fenix[name])
                    for name in (
                        "L:S_OH_PNEUMATIC_ENG1_ANTI_ICE",
                        "L:S_OH_PNEUMATIC_ENG2_ANTI_ICE",
                    )
                )

        modern = self._read_modern_configuration(client)
        altimeter_hpa = modern.get("KOHLSMAN SETTING MB EX1:1", values["KOHLSMAN SETTING MB"])
        altimeter_std = (bool(modern["KOHLSMAN SETTING STD:1"])
                         if "KOHLSMAN SETTING STD:1" in modern else None)
        if self._is_fenix_family():
            # Read the captain's EFIS mode, not the generic SimVar mirror.
            # Keeping an old QNH value while STD is selected is legitimate.
            altimeter_std = None
            try:
                baro = client.read_simvars(_FENIX_BARO_VARIABLES, timeout_s=_OPTIONAL_TIMEOUT_S)
                mode = baro.get("L:B_FCU_EFIS1_BARO_STD")
                if mode in (0, 1):
                    altimeter_std = bool(mode)
            except SimConnectError as exc:
                logger.info("Mode altimétrique Fenix indisponible (%s)", exc)
            if altimeter_std is None:
                # Both alarm rules must remain unknown, including their pressure fallback.
                altimeter_hpa = None
            elif altimeter_std:
                altimeter_hpa = 1013.25
        ils_receiver, ils_frequency = self._read_ils_receiver(client, values)
        lights = self._read_lights(client, values)
        return AircraftConfiguration(
            gear_handle_down=bool(values["GEAR HANDLE POSITION"]),
            gear_extended_pct=min(gear_positions),
            flaps_handle_index=flaps_index,
            flaps_effective_index=int(round(values["FLAPS EFFECTIVE HANDLE INDEX"])),
            flaps_surface_index=int(round(values["TRAILING EDGE FLAPS LEFT INDEX"])),
            flaps_handle_pct=values["FLAPS HANDLE PERCENT"],
            flaps_extended_pct=values["TRAILING EDGE FLAPS LEFT PERCENT"],
            flaps_angle_deg=values["TRAILING EDGE FLAPS LEFT ANGLE"],
            spoilers_handle_pct=spoilers_pct,
            spoilers_surface_pct=max(
                values["SPOILERS LEFT POSITION"],
                values["SPOILERS RIGHT POSITION"],
            ),
            spoilers_armed=spoilers_armed,
            parking_brake=parking_brake,
            lights=lights,
            altimeter_hpa=altimeter_hpa,
            altimeter_std=altimeter_std,
            indicated_altitude_ft=values["INDICATED ALTITUDE"],
            pressure_altitude_ft=values["PRESSURE ALTITUDE"],
            autopilot_master=bool(values["AUTOPILOT MASTER"]),
            autopilot_nav_lock=bool(values["AUTOPILOT NAV1 LOCK"]),
            autopilot_approach_hold=bool(values["AUTOPILOT APPROACH HOLD"]),
            autopilot_glideslope_hold=bool(values["AUTOPILOT GLIDESLOPE HOLD"]),
            autothrottle_active=bool(values["AUTOTHROTTLE ACTIVE"]),
            selected_altitude_ft=values["AUTOPILOT ALTITUDE LOCK VAR"],
            selected_heading_deg=values["AUTOPILOT HEADING LOCK DIR"] % 360,
            com1_frequency_mhz=values["COM ACTIVE FREQUENCY:1"],
            nav1_frequency_mhz=values["NAV ACTIVE FREQUENCY:1"],
            ils_frequency_mhz=ils_frequency,
            ils_receiver_index=ils_receiver,
            nav1_course_deg=values["NAV LOCALIZER:1"] % 360,
            nav1_has_localizer=bool(values["NAV HAS LOCALIZER:1"]),
            nav1_has_glide_slope=bool(values["NAV HAS GLIDE SLOPE:1"]),
            fuel_total_kg=values["FUEL TOTAL QUANTITY WEIGHT"],
            total_weight_kg=values["TOTAL WEIGHT"],
            wind_direction_deg=values["AMBIENT WIND DIRECTION"] % 360,
            wind_speed_kt=values["AMBIENT WIND VELOCITY"],
            total_air_temperature_c=values["TOTAL AIR TEMPERATURE"],
            in_cloud=bool(values["AMBIENT IN CLOUD"]),
            engine_anti_ice=engine_anti_ice,
            stall_warning=bool(values["STALL WARNING"]),
            overspeed_warning=bool(values["OVERSPEED WARNING"]),
            flap_speed_exceeded=bool(values["FLAP SPEED EXCEEDED"]),
            interactive_points_crash_risk=(
                bool(modern["IS ANY OPEN INTERACTIVE POINTS RISKING TO CAUSE CRASH"])
                if "IS ANY OPEN INTERACTIVE POINTS RISKING TO CAUSE CRASH" in modern
                else None
            ),
            barber_pole_kt=values["AIRSPEED BARBER POLE"],
            mach=values["AIRSPEED MACH"],
            simulation_rate=values["SIMULATION RATE"],
            capabilities=self._read_capabilities(client),
        )

    def _read_modern_configuration(
        self, client: SimConnectClient
    ) -> dict[str, float]:
        """Lit les SimVars récentes sans rendre le bloc historique fragile."""
        now = time.monotonic()
        if now < self._modern_configuration_disabled_until:
            return {}
        try:
            return client.read_simvars(
                _MODERN_CONFIGURATION_VARIABLES, timeout_s=_OPTIONAL_TIMEOUT_S
            )
        except SimConnectError as exc:
            self._modern_configuration_disabled_until = (
                now + _OPTIONAL_RETRY_DELAY_S
            )
            logger.info(
                "SimVars MSFS récentes indisponibles, nouvelle tentative dans %.0f s (%s)",
                _OPTIONAL_RETRY_DELAY_S,
                exc,
            )
            return {}

    def _read_lights(
        self, client: SimConnectClient, values: dict[str, float]
    ) -> dict[str, bool]:
        """Recoupe les interrupteurs individuels avec le masque officiel.

        Plusieurs avions tiers publient seulement l'une des deux formes. Un
        feu est donc actif dès qu'au moins une source officielle le confirme.
        """
        lights = {
            "landing": bool(values["LIGHT LANDING"]),
            "taxi": bool(values["LIGHT TAXI"]),
            "strobe": bool(values["LIGHT STROBE"]),
            "nav": bool(values["LIGHT NAV"]),
            "beacon": bool(values["LIGHT BEACON"]),
            "logo": bool(values["LIGHT LOGO"]),
            "wing": bool(values["LIGHT WING"]),
        }
        now = time.monotonic()
        if now < self._light_states_disabled_until:
            return lights
        try:
            aggregate = client.read_simvars(
                _LIGHT_STATE_VARIABLES, timeout_s=_OPTIONAL_TIMEOUT_S
            )
        except SimConnectError as exc:
            self._light_states_disabled_until = now + _OPTIONAL_RETRY_DELAY_S
            logger.info(
                "Masque des feux indisponible, nouvelle tentative dans %.0f s (%s)",
                _OPTIONAL_RETRY_DELAY_S,
                exc,
            )
            return lights

        mask = int(round(aggregate["LIGHT STATES"]))
        for name, bit in _LIGHT_STATE_BITS.items():
            lights[name] = lights[name] or bool(mask & bit)
        return lights

    def _resolve_parking_brake(self, position: float, indicator: float) -> bool:
        """Suit celle des deux SimVars de frein qui change réellement.

        Des avions tiers figent parfois POSITION et animent seulement
        INDICATOR. D'autres font l'inverse. Après le premier échantillon, la
        variable qui vient de bouger devient donc la référence.
        """
        raw = (bool(position), bool(indicator))
        previous = self._parking_brake_raw
        if previous is None:
            state = raw[0] if raw[0] != raw[1] else raw[1]
        elif raw[0] != previous[0] and raw[1] == previous[1]:
            state = raw[0]
        elif raw[1] != previous[1] and raw[0] == previous[0]:
            state = raw[1]
        elif raw[0] == raw[1]:
            state = raw[0]
        else:
            state = self._parking_brake_state if self._parking_brake_state is not None else raw[0]
        self._parking_brake_raw = raw
        self._parking_brake_state = state
        return state

    def _resolve_flaps_index(
        self, handle: float, effective: float, surface: float
    ) -> int:
        """Suit l'index de volets qui évolue sur l'appareil chargé."""
        raw = tuple(int(round(value)) for value in (handle, effective, surface))
        previous = self._flaps_raw
        if previous is None:
            index = raw[0]
        else:
            changed = [value for value, old in zip(raw, previous) if value != old]
            if not changed:
                index = self._flaps_index if self._flaps_index is not None else raw[0]
            elif len(set(changed)) == 1:
                index = changed[0]
            elif raw[0] != previous[0]:
                index = raw[0]
            elif raw[1] != previous[1]:
                index = raw[1]
            else:
                index = raw[2]
        self._flaps_raw = raw
        self._flaps_index = index
        return index

    def _resolve_spoilers_pct(
        self, handle: float, left_surface: float, right_surface: float
    ) -> float:
        """Suit la poignée ou les surfaces, selon ce que l'avion actualise."""
        raw = (float(handle), float(left_surface), float(right_surface))
        previous = self._spoilers_raw
        if previous is None:
            value = raw[0]
        else:
            handle_changed = abs(raw[0] - previous[0]) >= 0.5
            surfaces_changed = any(
                abs(value - old) >= 0.5
                for value, old in zip(raw[1:], previous[1:])
            )
            if handle_changed:
                value = raw[0]
            elif surfaces_changed:
                value = max(raw[1:])
            else:
                value = self._spoilers_pct if self._spoilers_pct is not None else raw[0]
        self._spoilers_raw = raw
        self._spoilers_pct = value
        return value

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

    # ------------------------------------------------------------------ #

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
        self._modern_configuration_disabled_until = 0.0
        self._light_states_disabled_until = 0.0
        self._pause_disabled_until = 0.0
        self._parking_brake_raw = None
        self._parking_brake_state = None
        self._flaps_raw = None
        self._flaps_index = None
        self._spoilers_raw = None
        self._spoilers_pct = None
        self._aircraft_title = ""
        self._aircraft_title_checked_at = 0.0
        self._aircraft_title_disabled_until = 0.0
        self._traffic_disabled_until = 0.0

    def close(self) -> None:
        with self._lock:
            self._reset()

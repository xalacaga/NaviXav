"""Position lue directement dans MSFS, via le client SimConnect de NaviXav.

Le projet n'a qu'une seule couche SimConnect : `navixav.msfs.client`. Les
unités sont demandées explicitement au simulateur, qui se charge de la
conversion — plus fiable que de deviner l'unité native d'une variable, dont le
nom peut être trompeur (« PLANE HEADING DEGREES TRUE » est en radians).
"""

from __future__ import annotations

import threading
import time

from navixav.live.base import AircraftState, PositionUnavailable
from navixav.msfs.client import SimConnectClient, SimConnectError

# Variable SimConnect -> unité demandée.
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

# Une connexion qui vient d'échouer n'est pas retentée immédiatement.
_RETRY_DELAY_S = 5.0


class SimConnectSource:
    """Lecture directe dans le simulateur, sans application intermédiaire."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._client: SimConnectClient | None = None
        self._last_failure = 0.0
        self._failure_reason = ""

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
            )

    def _reset(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # pragma: no cover - fermeture au mieux
                pass
        self._client = None

    def close(self) -> None:
        with self._lock:
            self._reset()

"""Fournisseur de navdata adossé à la base NaviXav, alimentée par MSFS.

Un terrain absent de la base est récupéré au simulateur puis conservé. Le
premier accès demande donc MSFS en fonctionnement ; les suivants non.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from navixav.msfs.client import SimConnectClient, SimConnectError
from navixav.msfs.extract import extract_airport, extract_navaid, extract_waypoint
from navixav.navdata import msfs_store
from navixav.navdata.base import (
    Airport,
    NavdataError,
    Procedure,
    ProcedureKind,
    ProcedureLeg,
    Runway,
    Transition,
    normalise_runway,
)


class MsfsProvider:
    """Base NaviXav en lecture, complétée à la demande depuis le simulateur."""

    def __init__(
        self,
        store_path: Path | str | None = None,
        allow_fetch: bool = True,
        client: SimConnectClient | None = None,
    ) -> None:
        self._conn = msfs_store.connect(store_path)
        self._path = Path(store_path) if store_path else msfs_store.DEFAULT_STORE
        self._allow_fetch = allow_fetch
        self._client = client
        self._owns_client = client is None
        self._fetched: set[str] = set()

    # ------------------------------------------------------------------ #
    # Métadonnées
    # ------------------------------------------------------------------ #

    @property
    def airac_cycle(self) -> str:
        row = self._conn.execute(
            "SELECT MAX(fetched_at) AS latest FROM airport"
        ).fetchone()
        return f"MSFS {row['latest'][:10]}" if row and row["latest"] else "MSFS (vide)"

    @property
    def source_name(self) -> str:
        return f"MSFS via SimConnect · {self._path.name}"

    @property
    def supports_rnp_flag(self) -> bool:
        """Le RNP est lu sur les segments, il n'est donc pas exhaustif.

        On ne le déclare fiable que si au moins une approche du terrain chargé
        le porte, faute de quoi le critère serait muet.
        """
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM procedure WHERE requires_rnp = 1"
        ).fetchone()
        return bool(row and row["n"])

    @property
    def has_ground_geometry(self) -> bool:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM taxi_path").fetchone()
        return bool(row and row["n"])

    def stats(self) -> dict[str, int]:
        counts = {}
        for label, table in (("airports", "airport"), ("procedures", "procedure")):
            counts[label] = self._conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
        return counts

    def airports_in_store(self) -> list[sqlite3.Row]:
        """Terrains présents en base, du plus récemment importé au plus ancien."""
        return self._conn.execute(
            "SELECT icao, name, fetched_at FROM airport ORDER BY icao"
        ).fetchall()

    def reference_counts(self) -> dict[str, int]:
        """Volumes des données de référence résolues au fil des besoins."""
        counts = {}
        for label, table in (
            ("waypoints", "waypoint"),
            ("navaids", "navaid"),
            ("airways", "airway_segment"),
        ):
            counts[label] = self._conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
        return counts

    # ------------------------------------------------------------------ #
    # Chargement à la demande
    # ------------------------------------------------------------------ #

    def ensure(self, icao: str, refresh: bool = False) -> bool:
        """Garantit la présence d'un terrain. Retourne True s'il a été récupéré."""
        key = icao.strip().upper()
        if not refresh and self._has(key):
            return False
        if not self._allow_fetch:
            raise NavdataError(
                f"{key} absent de la base NaviXav",
                "lance « navixav import » avec le simulateur ouvert",
            )
        extracted = extract_airport(self._client_or_open(), key)
        msfs_store.store_airport(self._conn, extracted)
        self._fetched.add(key)
        return True

    def _has(self, icao: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM airport WHERE icao = ?", (icao,)
        ).fetchone()
        return row is not None

    def _client_or_open(self) -> SimConnectClient:
        if self._client is None:
            try:
                self._client = SimConnectClient()
            except SimConnectError as exc:
                raise NavdataError(str(exc)) from exc
        return self._client

    # ------------------------------------------------------------------ #
    # Protocole NavdataProvider
    # ------------------------------------------------------------------ #

    def airport(self, icao: str) -> Airport | None:
        key = icao.strip().upper()
        try:
            self.ensure(key)
        except (NavdataError, SimConnectError):
            if not self._has(key):
                return None

        row = self._conn.execute(
            "SELECT * FROM airport WHERE icao = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        return Airport(
            ident=row["icao"],
            name=row["name"],
            city=None,
            country=None,
            lat=row["lat"],
            lon=row["lon"],
            altitude_ft=row["altitude_ft"],
            mag_var=None,
            transition_altitude_ft=row["transition_altitude_ft"],
            transition_level_ft=row["transition_level_ft"],
        )

    def runways(self, icao: str) -> list[Runway]:
        key = icao.strip().upper()
        rows = self._conn.execute(
            "SELECT * FROM runway WHERE icao = ? ORDER BY name", (key,)
        ).fetchall()
        return [
            Runway(
                name=row["name"],
                heading_true_deg=row["heading_true"],
                length_ft=row["length_ft"],
                width_ft=row["width_ft"],
                surface=row["surface"],
                ils_ident=row["ils_ident"],
                is_landing=True,
                is_takeoff=True,
                lat=row["lat"],
                lon=row["lon"],
            )
            for row in rows
        ]

    def procedures(self, icao: str, kind: ProcedureKind) -> list[Procedure]:
        key = icao.strip().upper()
        rows = self._conn.execute(
            "SELECT * FROM procedure WHERE icao = ? AND kind = ? ORDER BY ident",
            (key, kind.value),
        ).fetchall()
        return [self._procedure(row, kind) for row in rows]

    def _procedure(self, row: sqlite3.Row, kind: ProcedureKind) -> Procedure:
        legs = self._legs(row["id"], transition_id=None)

        # Seules les transitions nommées d'après un repère sont des transitions
        # au sens du plan de vol. Une transition de piste est une variante de la
        # procédure, déjà décrite par `runways` : l'exposer ferait apparaître
        # « 32L » là où l'on attend « AFRIC ».
        wanted = (
            ("APPROACH",)
            if kind is ProcedureKind.APPROACH
            else ("ENROUTE",)
        )
        placeholders = ",".join("?" * len(wanted))
        transitions = tuple(
            Transition(
                ident=entry["ident"],
                transition_type=entry["kind"],
                legs=self._legs(row["id"], transition_id=entry["id"]),
            )
            for entry in self._conn.execute(
                f"SELECT * FROM transition WHERE procedure_id = ? "
                f"AND kind IN ({placeholders}) ORDER BY ident",
                (row["id"], *wanted),
            ).fetchall()
        )
        runways = tuple(
            normalise_runway(name) for name in json.loads(row["runways"] or "[]")
        )
        return Procedure(
            provider_id=row["id"],
            kind=kind,
            ident=row["ident"],
            arinc_name=row["runway_name"],
            proc_type=row["proc_type"],
            suffix=row["suffix"] or None,
            runway_name=row["runway_name"],
            runways=runways or tuple(r.name for r in self.runways(row["icao"])),
            legs=legs,
            transitions=transitions,
            requires_rnp=bool(row["requires_rnp"]),
            missed_altitude_ft=row["missed_altitude_ft"],
        )

    def _legs(self, procedure_id: int, transition_id: int | None) -> tuple[ProcedureLeg, ...]:
        if transition_id is None:
            rows = self._conn.execute(
                "SELECT * FROM leg WHERE procedure_id = ? AND transition_id IS NULL "
                "ORDER BY is_missed, sequence",
                (procedure_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM leg WHERE transition_id = ? ORDER BY sequence",
                (transition_id,),
            ).fetchall()
        return tuple(
            ProcedureLeg(
                leg_type=str(row["leg_type"] or ""),
                fix_ident=row["fix_ident"],
                fix_type=row["fix_region"],
                is_missed=bool(row["is_missed"]),
                alt_descriptor="+" if row["altitude1_ft"] else None,
                altitude1_ft=row["altitude1_ft"],
                altitude2_ft=row["altitude2_ft"],
                speed_limit_kt=row["speed_limit_kt"],
                speed_limit_type="-",
                course_deg=row["course"],
                distance_nm=row["distance_nm"],
                lat=None,
                lon=None,
                is_faf=bool(row["is_faf"]),
            )
            for row in rows
        )

    def ils_frequency(self, icao: str, runway_name: str) -> float | None:
        """Fréquence ILS de la piste.

        La piste ne porte que l'identifiant de l'installation ; la fréquence se
        lit sur l'installation elle-même, interrogée comme un VOR.
        """
        target = normalise_runway(runway_name)
        row = self._conn.execute(
            "SELECT ils_ident FROM runway WHERE icao = ? AND name = ?",
            (icao.strip().upper(), target),
        ).fetchone()
        if row is None or not row["ils_ident"]:
            return None
        navaid = self._navaid(row["ils_ident"])
        return navaid["frequency_mhz"] if navaid else None

    def ils_details(self, icao: str, runway_name: str) -> dict[str, float | str | None]:
        target = normalise_runway(runway_name)
        row = self._conn.execute(
            "SELECT ils_ident FROM runway WHERE icao = ? AND name = ?",
            (icao.strip().upper(), target),
        ).fetchone()
        if row is None or not row["ils_ident"]:
            return {}
        navaid = self._navaid(row["ils_ident"])
        if not navaid:
            return {"ident": row["ils_ident"]}
        return {
            "ident": navaid["ident"],
            "frequency_mhz": navaid["frequency_mhz"],
            "course_deg": navaid["localizer_course"],
            "glide_slope_deg": (
                abs(navaid["glide_slope"]) if navaid["glide_slope"] else None
            ),
        }

    def _navaid(self, ident: str) -> dict | None:
        key = ident.strip().upper()
        row = self._conn.execute(
            "SELECT * FROM navaid WHERE ident = ? LIMIT 1", (key,)
        ).fetchone()
        if row is not None:
            return dict(row)
        if not self._allow_fetch or self._missed(key, "navaid"):
            return None

        for region in self._candidate_regions(key):
            try:
                found = extract_navaid(self._client_or_open(), key, region)
            except (NavdataError, SimConnectError):
                return None
            if found is not None:
                msfs_store.store_navaid(self._conn, found)
                return found
        msfs_store.store_miss(self._conn, key, "navaid")
        return None

    def _candidate_regions(self, ident: str) -> list[str]:
        """Régions à essayer pour un identifiant.

        Le simulateur exige la région pour lever l'ambiguïté : un même
        identifiant peut désigner plusieurs installations dans le monde. Les
        segments de procédure déjà en base la portent ; à défaut, on tente les
        régions des terrains chargés, puis une recherche sans région.
        """
        regions: list[str] = []
        row = self._conn.execute(
            "SELECT fix_region FROM leg WHERE fix_ident = ? AND fix_region IS NOT NULL "
            "AND fix_region <> '' LIMIT 1",
            (ident,),
        ).fetchone()
        if row and row["fix_region"]:
            regions.append(row["fix_region"])

        for candidate in self._conn.execute(
            "SELECT DISTINCT fix_region FROM leg WHERE fix_region IS NOT NULL "
            "AND fix_region <> '' LIMIT 8"
        ).fetchall():
            if candidate["fix_region"] not in regions:
                regions.append(candidate["fix_region"])

        regions.append("")
        return regions

    def is_airway(self, name: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM airway_segment WHERE airway = ? LIMIT 1",
            (name.strip().upper(),),
        ).fetchone()
        return row is not None

    def fix_position(self, ident: str) -> tuple[float, float] | None:
        """Position d'un repère, récupérée au simulateur si nécessaire."""
        key = ident.strip().upper()
        row = self._conn.execute(
            "SELECT lat, lon FROM waypoint WHERE ident = ? LIMIT 1", (key,)
        ).fetchone()
        if row is not None:
            return (row["lat"], row["lon"])

        if self._allow_fetch and not self._missed(key, "waypoint"):
            for region in self._candidate_regions(key):
                try:
                    found = extract_waypoint(self._client_or_open(), key, region)
                except (NavdataError, SimConnectError):
                    found = None
                    break
                if found is not None:
                    msfs_store.store_waypoint(self._conn, found)
                    return (found["lat"], found["lon"])
            msfs_store.store_miss(self._conn, key, "waypoint")

        # Repli : un seuil de piste peut porter cet identifiant.
        row = self._conn.execute(
            "SELECT lat, lon FROM runway WHERE name = ? LIMIT 1", (key,)
        ).fetchone()
        return (row["lat"], row["lon"]) if row else None

    def _missed(self, ident: str, kind: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM lookup_miss WHERE ident = ? AND kind = ?", (ident, kind)
        ).fetchone()
        return row is not None

    def close(self) -> None:
        self._conn.close()
        if self._client is not None and self._owns_client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "MsfsProvider":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

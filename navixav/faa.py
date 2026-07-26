"""Cartes terminales officielles FAA publiées dans le produit d-TPP."""

from __future__ import annotations

import re
import threading
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests

from navixav.paths import user_data_path
from navixav.sia import AIRAC_INTERVAL_DAYS, airac_effective_date

FAA_DTPP_ROOT = "https://aeronav.faa.gov/d-tpp"
DEFAULT_CACHE_DIR = user_data_path("cache", "faa")
USER_AGENT = "NaviXav/0.1 (local flight simulation tool)"


class FaaError(RuntimeError):
    """Le catalogue ou une carte officielle FAA n'est pas disponible."""


@dataclass(frozen=True)
class FaaChart:
    icao: str
    title: str
    filename: str
    url: str
    effective_date: str
    category: str
    chart_code: str
    procedure_ident: str = ""
    local_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("local_path", None)
        payload["georeferenced"] = bool(
            self.local_path
            and self.local_path.with_suffix(".georef.json").is_file()
        )
        return payload


def faa_cycle_id(effective: date) -> str:
    """Identifiant FAA YYNN du cycle AIRAC correspondant à une date."""
    first = airac_effective_date(date(effective.year, 1, 1))
    if first.year < effective.year:
        first += timedelta(days=AIRAC_INTERVAL_DAYS)
    cycle = ((effective - first).days // AIRAC_INTERVAL_DAYS) + 1
    return f"{effective.year % 100:02d}{cycle:02d}"


def faa_chart_category(chart_code: str) -> str:
    return {
        "IAP": "Approches IAC",
        "DP": "Départs SID",
        "ODP": "Départs SID",
        "STR": "Arrivées STAR",
        "APD": "Aérodrome et roulage",
        "DAU": "Données aéroport",
        "MIN": "Minima",
        "HOT": "Points sensibles",
        "LAH": "LAHSO",
    }.get(chart_code.upper(), "Autres cartes")


def choose_faa_approach(
    charts: list[FaaChart],
    runway: str,
    approach: str,
) -> FaaChart | None:
    target_runway = re.sub(r"[^0-9LRC]", "", runway.upper())
    target_runway_short = target_runway.lstrip("0") or "0"
    target_type = next(
        (
            kind
            for kind in ("ILS", "RNP", "RNAV", "LOC", "VOR", "NDB")
            if kind in approach.upper()
        ),
        None,
    )
    ranked: list[tuple[int, FaaChart]] = []
    for chart in charts:
        if chart.chart_code != "IAP":
            continue
        name = re.sub(r"[^A-Z0-9]+", "", chart.title.upper())
        score = 100
        if (
            f"RWY{target_runway}" in name
            or f"RWY{target_runway_short}" in name
        ):
            score += 100
        else:
            score -= 100
        if target_type:
            score += 50 if target_type in name else -30
        ranked.append((score, chart))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1] if ranked and ranked[0][0] >= 150 else None


class FaaClient:
    def __init__(
        self,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        session: requests.Session | None = None,
        today: date | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)
        self.today = today
        self._catalogue_lock = threading.Lock()

    def _issues(self) -> list[date]:
        current = airac_effective_date(self.today)
        return [
            current - timedelta(days=AIRAC_INTERVAL_DAYS * offset)
            for offset in range(3)
        ]

    def _catalogue_path(self, effective: date) -> Path:
        return self.cache_dir / faa_cycle_id(effective) / "d-tpp_Metafile.xml"

    def _catalogue_url(self, effective: date) -> str:
        cycle = faa_cycle_id(effective)
        return f"{FAA_DTPP_ROOT}/{cycle}/xml_data/d-tpp_Metafile.xml"

    def _load_catalogue(self, effective: date) -> Path | None:
        target = self._catalogue_path(effective)
        if target.is_file() and target.stat().st_size > 1000:
            return target

        with self._catalogue_lock:
            if target.is_file() and target.stat().st_size > 1000:
                return target
            response = self.session.get(self._catalogue_url(effective), timeout=60)
            if response.status_code == 404:
                return None
            try:
                response.raise_for_status()
            except requests.RequestException as exc:
                raise FaaError(f"Catalogue FAA indisponible : {exc}") from exc
            if not response.content.lstrip().startswith(b"<?xml"):
                raise FaaError("La FAA n'a pas renvoyé son catalogue XML.")

            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(".tmp")
            temporary.write_bytes(response.content)
            temporary.replace(target)
            return target

    def _catalogue(self, icao: str, effective: date) -> list[FaaChart]:
        path = self._load_catalogue(effective)
        if path is None:
            return []
        cycle = faa_cycle_id(effective)
        charts: list[FaaChart] = []
        try:
            for _event, airport in ET.iterparse(path, events=("end",)):
                if airport.tag != "airport_name":
                    continue
                if airport.attrib.get("icao_ident", "").upper() != icao:
                    airport.clear()
                    continue
                for record in airport.findall("record"):
                    code = (record.findtext("chart_code") or "").strip().upper()
                    filename = (record.findtext("pdf_name") or "").strip()
                    title = (record.findtext("chart_name") or "").strip()
                    procedure_ident = (
                        record.findtext("faanfd18") or ""
                    ).strip().split(".")[-1]
                    if (
                        not re.fullmatch(r"[A-Za-z0-9_.-]+\.PDF", filename, re.I)
                        or not code
                    ):
                        continue
                    charts.append(
                        FaaChart(
                            icao=icao,
                            title=title or Path(filename).stem,
                            filename=filename,
                            url=f"{FAA_DTPP_ROOT}/{cycle}/{filename}",
                            effective_date=effective.isoformat(),
                            category=faa_chart_category(code),
                            chart_code=code,
                            procedure_ident=procedure_ident,
                        )
                    )
                airport.clear()
                break
        except (ET.ParseError, OSError) as exc:
            raise FaaError(f"Catalogue FAA illisible : {exc}") from exc

        unique: dict[tuple[str, str], FaaChart] = {}
        for chart in charts:
            unique.setdefault((chart.filename.upper(), chart.title), chart)
        return list(unique.values())

    def list_airport_charts(self, icao: str) -> tuple[date, list[FaaChart]]:
        icao = icao.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{4}", icao):
            raise FaaError("Code OACI invalide.")
        for effective in self._issues():
            charts = self._catalogue(icao, effective)
            if charts:
                return effective, charts
        raise FaaError(f"Aucune publication FAA trouvée pour {icao}.")

    def has_georeference(self, chart: FaaChart) -> bool:
        sidecar = (
            self.cache_dir
            / faa_cycle_id(date.fromisoformat(chart.effective_date))
            / chart.icao
            / chart.filename
        ).with_suffix(".georef.json")
        return sidecar.is_file()

    def get_airport_chart(self, icao: str, filename: str) -> FaaChart:
        safe_name = Path(filename).name
        if safe_name != filename or not safe_name.lower().endswith(".pdf"):
            raise FaaError("Nom de carte FAA invalide.")
        _effective, charts = self.list_airport_charts(icao)
        selected = next(
            (chart for chart in charts if chart.filename.upper() == safe_name.upper()),
            None,
        )
        if selected is None:
            raise FaaError("Carte absente du catalogue FAA courant.")
        local_path = self._download(selected)
        return FaaChart(
            icao=selected.icao,
            title=selected.title,
            filename=selected.filename,
            url=selected.url,
            effective_date=selected.effective_date,
            category=selected.category,
            chart_code=selected.chart_code,
            procedure_ident=selected.procedure_ident,
            local_path=local_path,
        )

    def find_approach(self, icao: str, runway: str, approach: str) -> FaaChart:
        _effective, charts = self.list_airport_charts(icao)
        selected = choose_faa_approach(charts, runway, approach)
        if selected is None:
            raise FaaError(
                f"Aucune carte finale FAA trouvée pour "
                f"{icao.upper()}, RWY {runway.upper()}, {approach}."
            )
        return self.get_airport_chart(icao.upper(), selected.filename)

    def _download(self, chart: FaaChart) -> Path:
        cycle = faa_cycle_id(date.fromisoformat(chart.effective_date))
        target = self.cache_dir / cycle / chart.icao / chart.filename
        if target.is_file() and target.stat().st_size > 1000:
            return target
        response = self.session.get(chart.url, timeout=30)
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FaaError(f"Carte FAA indisponible : {exc}") from exc
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type and not response.content.startswith(b"%PDF"):
            raise FaaError("La FAA n'a pas renvoyé un document PDF.")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(response.content)
        temporary.replace(target)
        return target

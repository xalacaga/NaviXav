"""Cartes d'approche officielles du SIA et extraction prudente des minima.

Le SIA publie une page eAIP par aérodrome et une carte PDF distincte par
procédure. Les publications AIRAC étant immuables, NaviXav les conserve dans
son cache local. Les minima extraits restent à confirmer dans l'interface.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

import requests

AIRAC_ANCHOR = date(2020, 1, 2)
AIRAC_INTERVAL_DAYS = 28
SIA_ROOT = "https://www.sia.aviation-civile.gouv.fr/media/dvd"
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache" / "sia"
USER_AGENT = "NaviXav/0.1 (local flight simulation tool)"


class SiaError(RuntimeError):
    """Le catalogue ou une carte officielle du SIA n'est pas disponible."""


@dataclass(frozen=True)
class SiaChart:
    icao: str
    title: str
    filename: str
    url: str
    effective_date: str
    local_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("local_path", None)
        return payload


@dataclass(frozen=True)
class SiaMinima:
    category: str
    mode: str
    dh_ft: int
    altitude_ft: int
    rvr_m: int
    confidence: str = "à confirmer"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _PdfLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        values = dict(attrs)
        href = values.get("href")
        if href and ".pdf" in href.lower():
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._href = None
            self._text = []


def airac_effective_date(day: date | None = None) -> date:
    """Dernière date AIRAC en vigueur pour un jour donné."""
    day = day or date.today()
    if day < AIRAC_ANCHOR:
        return AIRAC_ANCHOR
    cycles = (day - AIRAC_ANCHOR).days // AIRAC_INTERVAL_DAYS
    return AIRAC_ANCHOR + timedelta(days=cycles * AIRAC_INTERVAL_DAYS)


def _issue_root(effective: date) -> str:
    folder = effective.strftime("%d_%b_%Y").upper()
    iso = effective.isoformat()
    return f"{SIA_ROOT}/eAIP_{folder}/FRANCE/AIRAC-{iso}/html/eAIP/"


def _normalise(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def _chart_score(chart: SiaChart, runway: str, approach: str) -> int:
    name = _normalise(chart.title or chart.filename)
    runway = _normalise(runway).replace("_", "")
    if f"RWY{runway}" not in name.replace("_", ""):
        return -1

    target = _normalise(approach)
    score = 100
    if "_FNA_" in f"_{name}_":
        score += 30

    procedure_types = ("ILS", "RNP", "RNAV", "LOC", "VOR", "NDB")
    target_type = next((kind for kind in procedure_types if kind in target), None)
    if target_type:
        if f"_{target_type}_" in f"_{name}_":
            score += 40
        elif target_type == "LOC" and "_ILS_" in f"_{name}_":
            score += 20
        else:
            score -= 35

    variant = re.search(r"\b(?:ILS|RNP|RNAV|LOC|VOR|NDB)\s+([XYZ])\b", approach.upper())
    if variant:
        suffix = variant.group(1)
        if re.search(rf"_(?:ILS|RNP|RNAV|LOC|VOR|NDB)_{suffix}(?:_|$)", name):
            score += 35
        elif f"_{suffix}_" in f"_{name}_":
            score += 10
        else:
            score -= 25
    return score


def choose_chart(
    charts: list[SiaChart], runway: str, approach: str
) -> SiaChart | None:
    """Carte la plus proche de la procédure choisie par le moteur NaviXav."""
    ranked = sorted(
        ((_chart_score(chart, runway, approach), chart) for chart in charts),
        key=lambda item: item[0],
        reverse=True,
    )
    return ranked[0][1] if ranked and ranked[0][0] >= 100 else None


def _decode_sia_glyphs(text: str) -> str:
    """Transforme les noms de glyphes /MT233 en caractères Windows-1252."""

    def replace(match: re.Match[str]) -> str:
        value = int(match.group(1))
        if not 0 <= value <= 255:
            return match.group(0)
        return bytes([value]).decode("cp1252", "replace")

    return re.sub(r"/MT(\d+)", replace, text)


def extract_primary_ils_minima(path: Path) -> SiaMinima | None:
    """Extrait la ligne de minima ILS CAT I publiée dans une carte SIA.

    Le tableau SIA fusionne généralement DA(H) et RVR sur les catégories A-D.
    On utilise leur position dans le PDF pour ne pas confondre ces valeurs avec
    le profil vertical ou les minima LOC/MVL voisins.
    """
    try:
        from pypdf import PdfReader

        page = PdfReader(path).pages[0]
    except Exception as exc:
        raise SiaError(f"Carte SIA illisible : {exc}") from exc

    items: list[tuple[float, float, str]] = []

    def visitor(
        text: str,
        _cm: list[float],
        tm: list[float],
        _font: dict[str, Any] | None,
        _size: float,
    ) -> None:
        decoded = _decode_sia_glyphs(text).strip()
        if decoded:
            items.append((float(tm[4]), float(tm[5]), decoded))

    page.extract_text(visitor_text=visitor)
    return _minima_from_items(items)


def _minima_from_items(
    items: list[tuple[float, float, str]],
) -> SiaMinima | None:
    """Interprète les cellules DA(H)/RVR déjà positionnées."""
    combined = re.compile(r"(?:(\d{3,4})\s*)?\((\d{2,4})\)\s*(\d{3,4})")
    for x, y, text in items:
        if not 65 <= x <= 125:
            continue
        match = combined.search(text.replace(" ", ""))
        if not match:
            continue
        altitude = int(match.group(1)) if match.group(1) else None
        height = int(match.group(2))
        rvr = int(match.group(3))
        if altitude is None:
            preceding = [
                (other_x, other_text)
                for other_x, other_y, other_text in items
                if 60 <= other_x < x
                and abs(other_y - y) <= 2.5
                and re.fullmatch(r"\d{3,4}", other_text.strip())
            ]
            if preceding:
                altitude = int(max(preceding, key=lambda item: item[0])[1])
        if (
            altitude is not None
            and 300 <= altitude <= 10_000
            and 20 <= height <= 1_500
            and 100 <= rvr <= 5_000
            and altitude > height
        ):
            return SiaMinima(
                category="CAT I",
                mode="RADIO",
                dh_ft=height,
                altitude_ft=altitude,
                rvr_m=rvr,
            )
    return None


class SiaClient:
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

    def _issues(self) -> list[date]:
        current = airac_effective_date(self.today)
        return [current - timedelta(days=AIRAC_INTERVAL_DAYS * offset) for offset in range(3)]

    def _catalogue(self, icao: str, effective: date) -> list[SiaChart]:
        root = _issue_root(effective)
        url = urljoin(root, f"FR-AD-2.{icao}-fr-FR.html")
        cache = self.cache_dir / effective.isoformat() / icao / "catalogue.html"
        if cache.is_file():
            html = cache.read_text(encoding="utf-8")
        else:
            response = self.session.get(url, timeout=20)
            if response.status_code == 404:
                return []
            try:
                response.raise_for_status()
            except requests.RequestException as exc:
                raise SiaError(f"Catalogue SIA indisponible : {exc}") from exc
            html = response.text
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(html, encoding="utf-8")

        parser = _PdfLinks()
        parser.feed(html)
        charts: list[SiaChart] = []
        for href, title in parser.links:
            decoded_href = unquote(href)
            filename = Path(urlsplit(decoded_href).path).name
            normalised = _normalise(title or filename)
            if "_IAC_" not in f"_{normalised}_" or "_FNA_" not in f"_{normalised}_":
                continue
            charts.append(
                SiaChart(
                    icao=icao,
                    title=title or Path(filename).stem,
                    filename=filename,
                    url=urljoin(url, href),
                    effective_date=effective.isoformat(),
                )
            )
        return charts

    def find_approach(
        self, icao: str, runway: str, approach: str
    ) -> tuple[SiaChart, SiaMinima | None]:
        icao = icao.strip().upper()
        runway = runway.strip().upper()
        if not re.fullmatch(r"[A-Z]{4}", icao):
            raise SiaError("Code OACI invalide.")
        if not runway or not approach.strip():
            raise SiaError("Piste ou approche absente.")

        for effective in self._issues():
            charts = self._catalogue(icao, effective)
            selected = choose_chart(charts, runway, approach)
            if selected is None:
                continue
            local_path = self._download(selected)
            selected = SiaChart(
                **selected.to_dict(),
                local_path=local_path,
            )
            minima = (
                extract_primary_ils_minima(local_path)
                if re.search(r"\bILS\b", approach.upper())
                else None
            )
            return selected, minima
        raise SiaError(
            f"Aucune carte finale SIA trouvée pour {icao}, RWY {runway}, {approach}."
        )

    def _download(self, chart: SiaChart) -> Path:
        target = (
            self.cache_dir
            / chart.effective_date
            / chart.icao
            / chart.filename
        )
        if target.is_file() and target.stat().st_size > 1000:
            return target
        response = self.session.get(chart.url, timeout=30)
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SiaError(f"Carte SIA indisponible : {exc}") from exc
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type and not response.content.startswith(b"%PDF"):
            raise SiaError("Le SIA n'a pas renvoyé un document PDF.")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(response.content)
        temporary.replace(target)
        return target

"""Connecteurs directs vers des publications AIS nationales officielles.

Ce module ne passe volontairement par aucun agrégateur. Chaque connecteur est
activé seulement lorsque le portail national expose un catalogue et des PDF
publics dont NaviXav peut vérifier l'origine.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

import requests

from navixav.paths import user_data_path
from navixav.sia import airac_effective_date

USER_AGENT = "NaviXav/0.1 (local flight simulation tool)"
DEFAULT_CACHE_DIR = user_data_path("cache", "national-aip")


class NationalAipError(RuntimeError):
    """Une publication AIS nationale n'est pas disponible."""


@dataclass(frozen=True)
class NationalAipSource:
    provider: str
    source: str
    prefixes: tuple[str, ...]
    catalogue_url: str
    strategy: str
    hosts: tuple[str, ...]


NATIONAL_AIP_SOURCES = (
    NationalAipSource(
        provider="enaire",
        source="ENAIRE Espagne · AIP officiel",
        prefixes=("LE", "GC", "GE"),
        catalogue_url="https://aip.enaire.es/AIP/",
        strategy="enaire",
        hosts=("aip.enaire.es",),
    ),
    NationalAipSource(
        provider="lvnl",
        source="LVNL Pays-Bas · eAIP officiel",
        prefixes=("EH",),
        catalogue_url="https://eaip.lvnl.nl/web/eaip/default.html",
        strategy="lvnl",
        hosts=("eaip.lvnl.nl",),
    ),
    NationalAipSource(
        provider="lfv",
        source="LFV Suède · eAIP officiel",
        prefixes=("ES",),
        catalogue_url="https://www.aro.lfv.se/content/eaip/default_offline.html",
        strategy="lfv",
        hosts=("www.aro.lfv.se", "aro.lfv.se"),
    ),
    NationalAipSource(
        provider="skeyes",
        source="skeyes Belgique et Luxembourg · eAIP officiel",
        prefixes=("EB", "EL"),
        catalogue_url=(
            "https://ops.skeyes.be/html/belgocontrol_static/eaip/"
            "eAIP_Main/html/"
        ),
        strategy="skeyes",
        hosts=("ops.skeyes.be",),
    ),
    NationalAipSource(
        provider="austrocontrol",
        source="Austro Control Autriche · eAIP officiel",
        prefixes=("LO",),
        catalogue_url="https://eaip.austrocontrol.at/",
        strategy="austrocontrol",
        hosts=("eaip.austrocontrol.at",),
    ),
    NationalAipSource(
        provider="nats",
        source="NATS Royaume-Uni · eAIP officiel",
        prefixes=("EG",),
        catalogue_url=(
            "https://nats-uk.ead-it.com/cms-nats/opencms/en/"
            "Publications/AIP/"
        ),
        strategy="nats",
        hosts=("nats-uk.ead-it.com", "www.aurora.nats.co.uk"),
    ),
)


@dataclass(frozen=True)
class NationalAipChart:
    icao: str
    title: str
    filename: str
    url: str
    effective_date: str
    category: str
    chart_code: str = ""
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


class _Links(HTMLParser):
    """Extrait les liens en conservant le libellé de leur ligne de tableau."""

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[tuple[str, str]] = []
        self._rows: list[dict[str, list[Any]]] = []
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.lower()
        if tag == "tr":
            self._rows.append({"text": [], "links": []})
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href and ".pdf" in href.lower():
            self._href = urljoin(self.base_url, href)
            self._link_text = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._rows:
            self._rows[-1]["text"].append(text)
        if self._href:
            self._link_text.append(text)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._href:
            item = (self._href, " ".join(self._link_text).strip())
            if self._rows:
                self._rows[-1]["links"].append(item)
            else:
                self.links.append(item)
            self._href = None
            self._link_text = []
        if tag == "tr" and self._rows:
            row = self._rows.pop()
            row_title = " ".join(row["text"])
            for href, title in row["links"]:
                self.links.append((href, row_title or title))


class _AllLinks(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(urljoin(self.base_url, href.replace("\\", "/")))


def national_source_for_icao(icao: str) -> NationalAipSource | None:
    airport = icao.strip().upper()
    return next(
        (
            source
            for source in NATIONAL_AIP_SOURCES
            if airport.startswith(source.prefixes)
        ),
        None,
    )


def national_chart_category(value: str) -> str:
    name = re.sub(r"[^A-Z0-9]+", "_", value.upper())
    padded = f"_{name}_"
    if "_IAC_" in padded or "_INSTRUMENT_APPROACH_" in padded:
        return "Approches IAC"
    if "_SID_" in padded or "_STANDARD_DEPARTURE_" in padded:
        return "Départs SID"
    if (
        "_STAR_" in padded
        or "_TRAN_" in padded
        or "_STANDARD_ARRIVAL_" in padded
        or "_ARRIVAL_CHART_" in padded
    ):
        return "Arrivées STAR"
    if any(
        token in padded
        for token in (
            "_ADC_",
            "_APDC_",
            "_GMC_",
            "_PDC_",
            "_AERODROME_CHART_",
            "_GROUND_MOVEMENT_",
            "_PARKING_DOCKING_",
        )
    ):
        return "Aérodrome et roulage"
    if any(token in padded for token in ("_AOC_", "_PATC_", "_OBSTACLE_CHART_")):
        return "Obstacles"
    if (
        "_VAC_" in padded
        or "_VFR_" in padded
        or "_VISUAL_APPROACH_" in padded
    ):
        return "Approches à vue"
    return "Autres cartes"


def choose_national_approach(
    charts: list[NationalAipChart], runway: str, approach: str
) -> NationalAipChart | None:
    target_runway = re.sub(r"[^0-9LRC]", "", runway.upper()).lstrip("0") or "0"
    target_type = next(
        (
            kind
            for kind in ("ILS", "RNP", "RNAV", "LOC", "VOR", "NDB")
            if kind in approach.upper()
        ),
        None,
    )
    ranked: list[tuple[int, NationalAipChart]] = []
    for chart in charts:
        if chart.category != "Approches IAC":
            continue
        name = re.sub(r"[^A-Z0-9]+", "", f"{chart.title} {chart.filename}".upper())
        score = 100
        score += 100 if f"RWY{target_runway}" in name else -100
        if target_type:
            score += 50 if target_type in name else -30
        ranked.append((score, chart))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1] if ranked and ranked[0][0] >= 150 else None


class NationalAipClient:
    def __init__(
        self,
        source: NationalAipSource,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        session: requests.Session | None = None,
        today: date | None = None,
    ) -> None:
        self.source = source
        self.cache_dir = Path(cache_dir) / source.provider
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)
        self.today = today or date.today()

    def _get_text(self, url: str, cache: Path) -> str:
        if not self._is_official_url(url):
            raise NationalAipError("Adresse AIS nationale non autorisée.")
        if cache.is_file() and cache.stat().st_size > 100:
            return cache.read_text(encoding="utf-8")
        try:
            response = self.session.get(url, timeout=45)
            response.raise_for_status()
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if self.source.strategy == "skeyes" and status == 403:
                raise NationalAipError(
                    "Le portail skeyes refuse actuellement l’accès automatique "
                    "aux cartes (HTTP 403)."
                ) from exc
            raise NationalAipError(
                f"Catalogue {self.source.source} indisponible : {exc}"
            ) from exc
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(response.text, encoding="utf-8")
        return response.text

    def _is_official_url(self, url: str) -> bool:
        parsed = urlsplit(url)
        return parsed.scheme == "https" and (parsed.hostname or "").lower() in {
            host.lower() for host in self.source.hosts
        }

    def _dated_issue(
        self,
        pattern: str,
        date_format: str,
    ) -> tuple[date, str]:
        cache = self.cache_dir / self.today.isoformat() / "issues.html"
        html = self._get_text(self.source.catalogue_url, cache)
        parser = _AllLinks(self.source.catalogue_url)
        parser.feed(html)
        issues: list[tuple[date, str]] = []
        for url in parser.links:
            if not self._is_official_url(url):
                continue
            match = re.search(pattern, unquote(urlsplit(url).path), re.I)
            if not match:
                continue
            try:
                effective = date.fromisoformat(
                    date_format.format(*match.groups())
                )
            except ValueError:
                continue
            if effective <= self.today:
                issues.append((effective, url))
        if not issues:
            raise NationalAipError(
                f"Aucun cycle {self.source.source} en vigueur n’a été trouvé."
            )
        return max(issues, key=lambda item: item[0])

    def _enaire_catalogue(self, icao: str) -> tuple[date, list[NationalAipChart]]:
        effective = airac_effective_date(self.today)
        cache = self.cache_dir / effective.isoformat() / "catalogue.html"
        html = self._get_text(self.source.catalogue_url, cache)
        parser = _Links(self.source.catalogue_url)
        parser.feed(html)
        marker = f"/AD/AD2/{icao}/"
        return effective, self._charts_from_links(
            icao,
            effective,
            [
                (href, title)
                for href, title in parser.links
                if marker in urlsplit(href).path.upper()
            ],
        )

    def _lvnl_issue(self) -> tuple[date, str]:
        cache = self.cache_dir / self.today.isoformat() / "issues.html"
        html = self._get_text(self.source.catalogue_url, cache)
        parser = _AllLinks(self.source.catalogue_url)
        parser.feed(html)
        issues: list[tuple[date, str]] = []
        for url in parser.links:
            match = re.search(r"_(\d{4})_(\d{2})_(\d{2})/index\.html$", url, re.I)
            if not match:
                continue
            effective = date(*(int(value) for value in match.groups()))
            if effective <= self.today:
                issues.append((effective, url))
        if not issues:
            raise NationalAipError("Aucun cycle LVNL en vigueur n'a été trouvé.")
        return max(issues, key=lambda item: item[0])

    def _lvnl_catalogue(self, icao: str) -> tuple[date, list[NationalAipChart]]:
        effective, issue_url = self._lvnl_issue()
        page_url = urljoin(
            issue_url,
            f"eAIP/EH-AD%202%20{icao}%201-en-GB.html",
        )
        cache = self.cache_dir / effective.isoformat() / icao / "catalogue.html"
        html = self._get_text(page_url, cache)
        parser = _Links(page_url)
        parser.feed(html)
        marker = f"/CHARTS/AD/{icao}/"
        return effective, self._charts_from_links(
            icao,
            effective,
            [
                (href, title)
                for href, title in parser.links
                if marker in urlsplit(href).path.upper()
            ],
        )

    def _lfv_catalogue(self, icao: str) -> tuple[date, list[NationalAipChart]]:
        effective, issue_url = self._dated_issue(
            r"_(\d{4})_(\d{2})_(\d{2})/index-v2\.html$",
            "{}-{}-{}",
        )
        datasource_url = urljoin(issue_url, "v2/js/datasource.js")
        cache_root = self.cache_dir / effective.isoformat() / icao
        datasource = self._get_text(
            datasource_url,
            cache_root / "datasource.js",
        )
        page_pattern = re.compile(
            rf'"href"\s*:\s*"([^"#]*ES-AD 2 {re.escape(icao)} '
            r'[^"#]*-en-GB\.html)(?:#[^"]*)?"',
            re.I,
        )
        pages = sorted(
            {
                urljoin(issue_url, f"eAIP/{match.group(1)}")
                for match in page_pattern.finditer(datasource)
            }
        )
        links: list[tuple[str, str]] = []
        for index, page_url in enumerate(pages, start=1):
            html = self._get_text(page_url, cache_root / f"page-{index:02d}.html")
            parser = _Links(page_url)
            parser.feed(html)
            links.extend(
                (href, title)
                for href, title in parser.links
                if f"/CHARTS/AD/{icao}/" in urlsplit(href).path.upper()
            )
        return effective, self._charts_from_links(icao, effective, links)

    def _skeyes_catalogue(self, icao: str) -> tuple[date, list[NationalAipChart]]:
        effective = airac_effective_date(self.today)
        page_url = urljoin(
            self.source.catalogue_url,
            f"eAIP/EB-AD-2.{icao}-en-GB.html",
        )
        cache = self.cache_dir / effective.isoformat() / icao / "catalogue.html"
        html = self._get_text(page_url, cache)
        parser = _Links(page_url)
        parser.feed(html)
        return effective, self._charts_from_links(
            icao,
            effective,
            [
                (href, title)
                for href, title in parser.links
                if icao in urlsplit(href).path.upper()
            ],
        )

    def _austrocontrol_catalogue(
        self, icao: str
    ) -> tuple[date, list[NationalAipChart]]:
        effective, issue_url = self._dated_issue(
            r"/lo/(\d{2})(\d{2})(\d{2})/index\.htm$",
            "20{}-{}-{}",
        )
        page_url = urljoin(issue_url, f"ad_2_{icao.lower()}.htm")
        cache = self.cache_dir / effective.isoformat() / icao / "catalogue.html"
        html = self._get_text(page_url, cache)
        parser = _Links(page_url)
        parser.feed(html)
        return effective, self._charts_from_links(
            icao,
            effective,
            [
                (href, title)
                for href, title in parser.links
                if f"/CHARTS/{icao}/" in urlsplit(href).path.upper()
            ],
        )

    def _nats_catalogue(self, icao: str) -> tuple[date, list[NationalAipChart]]:
        effective, issue_url = self._dated_issue(
            r"/(\d{4})-(\d{2})-(\d{2})-AIRAC/html/index-en-GB\.html$",
            "{}-{}-{}",
        )
        page_url = urljoin(issue_url, f"eAIP/EG-AD-2.{icao}-en-GB.html")
        cache = self.cache_dir / effective.isoformat() / icao / "catalogue.html"
        html = self._get_text(page_url, cache)
        parser = _Links(page_url)
        parser.feed(html)
        return effective, self._charts_from_links(
            icao,
            effective,
            [
                (href, title)
                for href, title in parser.links
                if "/GRAPHICS/" in urlsplit(href).path.upper()
            ],
        )

    def _charts_from_links(
        self,
        icao: str,
        effective: date,
        links: list[tuple[str, str]],
    ) -> list[NationalAipChart]:
        unique: dict[str, NationalAipChart] = {}
        for href, title in links:
            if not self._is_official_url(href):
                continue
            filename = Path(unquote(urlsplit(href).path)).name
            if not re.fullmatch(r"[A-Za-z0-9_. -]+\.pdf", filename, re.I):
                continue
            clean_title = " ".join(title.split()) or Path(filename).stem
            category = national_chart_category(f"{clean_title} {filename}")
            unique.setdefault(
                filename.upper(),
                NationalAipChart(
                    icao=icao,
                    title=clean_title,
                    filename=filename,
                    url=href,
                    effective_date=effective.isoformat(),
                    category=category,
                    chart_code=category,
                ),
            )
        return list(unique.values())

    def list_airport_charts(
        self, icao: str
    ) -> tuple[date, list[NationalAipChart]]:
        airport = icao.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{4}", airport):
            raise NationalAipError("Code OACI invalide.")
        if not airport.startswith(self.source.prefixes):
            raise NationalAipError(
                f"{airport} n'appartient pas à la couverture {self.source.source}."
            )
        if self.source.strategy == "enaire":
            effective, charts = self._enaire_catalogue(airport)
        elif self.source.strategy == "lvnl":
            effective, charts = self._lvnl_catalogue(airport)
        elif self.source.strategy == "lfv":
            effective, charts = self._lfv_catalogue(airport)
        elif self.source.strategy == "skeyes":
            effective, charts = self._skeyes_catalogue(airport)
        elif self.source.strategy == "austrocontrol":
            effective, charts = self._austrocontrol_catalogue(airport)
        elif self.source.strategy == "nats":
            effective, charts = self._nats_catalogue(airport)
        else:
            raise NationalAipError("Connecteur AIS national inconnu.")
        if not charts:
            raise NationalAipError(
                f"Aucune publication {self.source.source} trouvée pour {airport}."
            )
        return effective, charts

    def has_georeference(self, chart: NationalAipChart) -> bool:
        return (
            self.cache_dir
            / chart.effective_date
            / chart.icao
            / chart.filename
        ).with_suffix(".georef.json").is_file()

    def get_airport_chart(self, icao: str, filename: str) -> NationalAipChart:
        safe_name = Path(filename).name
        if safe_name != filename or not safe_name.lower().endswith(".pdf"):
            raise NationalAipError("Nom de carte AIS invalide.")
        _effective, charts = self.list_airport_charts(icao)
        selected = next(
            (
                chart
                for chart in charts
                if chart.filename.upper() == safe_name.upper()
            ),
            None,
        )
        if selected is None:
            raise NationalAipError("Carte absente du catalogue AIS courant.")
        local_path = self._download(selected)
        return NationalAipChart(
            **{
                **asdict(selected),
                "local_path": local_path,
            }
        )

    def find_approach(
        self, icao: str, runway: str, approach: str
    ) -> NationalAipChart:
        _effective, charts = self.list_airport_charts(icao)
        selected = choose_national_approach(charts, runway, approach)
        if selected is None:
            raise NationalAipError(
                f"Aucune carte finale trouvée pour {icao.upper()}, "
                f"RWY {runway.upper()}, {approach}."
            )
        return self.get_airport_chart(icao.upper(), selected.filename)

    def _download(self, chart: NationalAipChart) -> Path:
        if not self._is_official_url(chart.url):
            raise NationalAipError("Adresse de carte AIS non autorisée.")
        target = (
            self.cache_dir
            / chart.effective_date
            / chart.icao
            / chart.filename
        )
        if target.is_file() and target.stat().st_size > 1000:
            return target
        try:
            response = self.session.get(chart.url, timeout=45)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise NationalAipError(
                f"Carte {self.source.source} indisponible : {exc}"
            ) from exc
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type and not response.content.startswith(b"%PDF"):
            raise NationalAipError("Le portail AIS n'a pas renvoyé un PDF.")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(response.content)
        temporary.replace(target)
        return target

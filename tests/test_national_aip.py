"""Connecteurs directs vers les publications AIS nationales."""

from datetime import date

import pytest
import requests

from navixav.national_aip import (
    NATIONAL_AIP_SOURCES,
    NationalAipChart,
    NationalAipClient,
    NationalAipError,
    choose_national_approach,
    national_chart_category,
    national_source_for_icao,
)


def _source(provider):
    return next(item for item in NATIONAL_AIP_SOURCES if item.provider == provider)


def test_national_source_registry_routes_only_validated_countries():
    assert national_source_for_icao("LEBL").provider == "enaire"
    assert national_source_for_icao("GCLP").provider == "enaire"
    assert national_source_for_icao("EHAM").provider == "lvnl"
    assert national_source_for_icao("ESSA").provider == "lfv"
    assert national_source_for_icao("EBBR").provider == "skeyes"
    assert national_source_for_icao("ELLX").provider == "skeyes"
    assert national_source_for_icao("LOWW").provider == "austrocontrol"
    assert national_source_for_icao("EGLL").provider == "nats"
    assert national_source_for_icao("EDDF") is None


def test_national_chart_categories():
    assert national_chart_category("EHAM-IAC-27-ILS-LOC.pdf") == "Approches IAC"
    assert national_chart_category("LEBL SID 1") == "Départs SID"
    assert national_chart_category("EHAM-STAR.pdf") == "Arrivées STAR"
    assert national_chart_category("EHAM-ADC.pdf") == "Aérodrome et roulage"
    assert (
        national_chart_category("Instrument Approach Chart - ILS RWY 27")
        == "Approches IAC"
    )
    assert (
        national_chart_category("Standard Departure Chart - Instrument")
        == "Départs SID"
    )


def test_enaire_catalogue_uses_the_row_description(tmp_path):
    effective = date(2026, 7, 9)
    path = tmp_path / "enaire" / effective.isoformat() / "catalogue.html"
    path.parent.mkdir(parents=True)
    path.write_text(
        """
        <table><tr>
          <td>AD 2 LEBL IAC 1</td>
          <td class="desc">IAC 1 - ILS Z RWY 24R</td>
          <td><a href="contenido_AIP/AD/AD2/LEBL/LE_AD_2_LEBL_IAC_1_en.pdf">
          </a></td>
        </tr><tr>
          <td class="desc">SID 1 - RWY 24R RNAV1</td>
          <td><a href="contenido_AIP/AD/AD2/LEBL/LE_AD_2_LEBL_SID_1_en.pdf">
          </a></td>
        </tr></table>
        """,
        encoding="utf-8",
    )
    client = NationalAipClient(
        _source("enaire"), tmp_path, today=date(2026, 7, 26)
    )
    found_date, charts = client.list_airport_charts("LEBL")
    assert found_date == effective
    assert charts[0].title == "AD 2 LEBL IAC 1 IAC 1 - ILS Z RWY 24R"
    assert charts[0].category == "Approches IAC"
    assert charts[1].category == "Départs SID"


def test_lvnl_resolves_current_issue_and_airport_page(tmp_path):
    today = date(2026, 7, 26)
    issue_cache = tmp_path / "lvnl" / today.isoformat() / "issues.html"
    issue_cache.parent.mkdir(parents=True)
    issue_cache.write_text(
        """
        <a href="AIRAC AMDT 07-2026_2026_07_09\\index.html">Current</a>
        <a href="AIRAC AMDT 08-2026_2026_08_06\\index.html">Future</a>
        <a href="AIRAC AMDT 06-2026_2026_06_11\\index.html">Previous</a>
        """,
        encoding="utf-8",
    )
    airport_cache = (
        tmp_path / "lvnl" / "2026-07-09" / "EHAM" / "catalogue.html"
    )
    airport_cache.parent.mkdir(parents=True)
    airport_cache.write_text(
        """
        <table><tr><td>
          <a href="../documents/Root_WePub/Charts/AD/EHAM/EHAM-IAC-27-ILS-LOC.pdf">
            ILS OR LOC RWY 27
          </a>
        </td></tr></table>
        """,
        encoding="utf-8",
    )
    client = NationalAipClient(_source("lvnl"), tmp_path, today=today)
    effective, charts = client.list_airport_charts("EHAM")
    assert effective == date(2026, 7, 9)
    assert charts[0].title == "ILS OR LOC RWY 27"
    assert charts[0].url.endswith("/EHAM/EHAM-IAC-27-ILS-LOC.pdf")


def test_lfv_resolves_pages_from_the_official_datasource(tmp_path):
    today = date(2026, 7, 26)
    issue_cache = tmp_path / "lfv" / today.isoformat() / "issues.html"
    issue_cache.parent.mkdir(parents=True)
    issue_cache.write_text(
        """
        <a href="AIRAC AIP AMDT 4-2026_2026_06_11/index-v2.html">Current</a>
        <a href="AIRAC AIP AMDT 5-2026_2026_08_06/index-v2.html">Future</a>
        <p>Official LFV electronic aeronautical information publication.</p>
        """,
        encoding="utf-8",
    )
    airport_cache = tmp_path / "lfv" / "2026-06-11" / "ESSA"
    airport_cache.mkdir(parents=True)
    (airport_cache / "datasource.js").write_text(
        """
        const DATASOURCE = {"menu": [
          {"href": "ES-AD 2 ESSA STOCKHOLM-ARLANDA 8-en-GB.html#AD-2-ESSA-8"},
          {"href": "ES-AD 2 ESGG GÖTEBORG-LANDVETTER 8-en-GB.html"}
        ]}; // Official LFV navigation datasource for the current AIP issue.
        """,
        encoding="utf-8",
    )
    (airport_cache / "page-01.html").write_text(
        """
        <table><tr><td>ESSA AD 2 8-10</td><td>Instrument Approach Chart - ICAO
        (ILS or LOC RWY 19L)</td><td><a href="../documents/Root/SWEDEN/Charts/AD/
        ESSA/ESSA-IAC-19L-ILS-LOC.pdf">PDF</a></td></tr></table>
        """.replace("AD/\n        ESSA", "AD/ESSA"),
        encoding="utf-8",
    )
    client = NationalAipClient(_source("lfv"), tmp_path, today=today)
    effective, charts = client.list_airport_charts("ESSA")
    assert effective == date(2026, 6, 11)
    assert charts[0].category == "Approches IAC"
    assert "ILS or LOC RWY 19L" in charts[0].title


def test_austrocontrol_selects_the_issue_in_force(tmp_path):
    today = date(2026, 8, 6)
    issue_cache = tmp_path / "austrocontrol" / today.isoformat() / "issues.html"
    issue_cache.parent.mkdir(parents=True)
    issue_cache.write_text(
        """
        <a href="lo/260710/index.htm">Current until 05 AUG 2026</a>
        <a href="lo/260806/index.htm">Current on 06 AUG 2026</a>
        <a href="lo/260807/index.htm">Future from 07 AUG 2026</a>
        """,
        encoding="utf-8",
    )
    airport_cache = (
        tmp_path / "austrocontrol" / "2026-08-06" / "LOWW" / "catalogue.html"
    )
    airport_cache.parent.mkdir(parents=True)
    airport_cache.write_text(
        """
        <table><tr><td><a href="Charts/LOWW/LO_AD_2_LOWW_13-1-1_en.pdf">
        LOWW AD 2 MAP 13-1-1</a></td><td>Instrument Approach Chart - ICAO
        (ILS or LOC RWY 11)</td></tr></table>
        """,
        encoding="utf-8",
    )
    client = NationalAipClient(_source("austrocontrol"), tmp_path, today=today)
    effective, charts = client.list_airport_charts("LOWW")
    assert effective == date(2026, 8, 6)
    assert charts[0].category == "Approches IAC"
    assert charts[0].url.endswith("/lo/260806/Charts/LOWW/LO_AD_2_LOWW_13-1-1_en.pdf")


def test_nats_resolves_opaque_pdf_names_from_the_airport_page(tmp_path):
    today = date(2026, 7, 26)
    issue_cache = tmp_path / "nats" / today.isoformat() / "issues.html"
    issue_cache.parent.mkdir(parents=True)
    issue_cache.write_text(
        """
        <a href="https://www.aurora.nats.co.uk/htmlAIP/Publications/
        2026-07-09-AIRAC/html/index-en-GB.html">Online Version</a>
        <a href="https://www.aurora.nats.co.uk/htmlAIP/Publications/
        2026-08-06-AIRAC/html/index-en-GB.html">Future Version</a>
        """.replace("Publications/\n        ", "Publications/"),
        encoding="utf-8",
    )
    airport_cache = tmp_path / "nats" / "2026-07-09" / "EGLL" / "catalogue.html"
    airport_cache.parent.mkdir(parents=True)
    airport_cache.write_text(
        """
        <table><tr><td><a href="../../graphics/500815.pdf">AD2.EGLL-8-1</a></td>
        <td>Instrument Approach Chart - ICAO (ILS RWY 27L)</td></tr>
        <tr><td><a href="https://charts.example/third-party.pdf">Mirror</a></td>
        <td>Third-party copy</td></tr></table>
        """,
        encoding="utf-8",
    )
    client = NationalAipClient(_source("nats"), tmp_path, today=today)
    effective, charts = client.list_airport_charts("EGLL")
    assert effective == date(2026, 7, 9)
    assert len(charts) == 1
    assert charts[0].filename == "500815.pdf"
    assert charts[0].category == "Approches IAC"


def test_skeyes_catalogue_supports_belgium_and_luxembourg(tmp_path):
    effective = date(2026, 7, 9)
    airport_cache = (
        tmp_path / "skeyes" / effective.isoformat() / "ELLX" / "catalogue.html"
    )
    airport_cache.parent.mkdir(parents=True)
    airport_cache.write_text(
        """
        <table><tr><td>Instrument Approach Chart - ILS RWY 24</td>
        <td><a href="../../graphics/ELLX/ELLX_IAC01_v4.pdf">ELLX IAC 01</a>
        </td></tr></table>
        """,
        encoding="utf-8",
    )
    client = NationalAipClient(
        _source("skeyes"), tmp_path, today=date(2026, 7, 26)
    )
    found_date, charts = client.list_airport_charts("ELLX")
    assert found_date == effective
    assert charts[0].category == "Approches IAC"


def test_skeyes_reports_the_live_403_cleanly(tmp_path):
    class ForbiddenSession:
        headers = {}

        @staticmethod
        def get(_url, timeout):
            assert timeout == 45
            response = requests.Response()
            response.status_code = 403
            response.url = _url
            return response

    client = NationalAipClient(
        _source("skeyes"),
        tmp_path,
        session=ForbiddenSession(),
        today=date(2026, 7, 26),
    )
    with pytest.raises(NationalAipError, match="HTTP 403"):
        client.list_airport_charts("EBBR")


def test_national_approach_matches_runway_and_type():
    charts = [
        NationalAipChart(
            "EHAM",
            title,
            f"{index}.pdf",
            "https://ais.test/chart.pdf",
            "2026-07-09",
            "Approches IAC",
        )
        for index, title in enumerate(
            (
                "RNP RWY 27",
                "ILS OR LOC RWY 24",
                "ILS OR LOC RWY 27",
            )
        )
    ]
    selected = choose_national_approach(charts, "27", "ILS RWY 27")
    assert selected is not None
    assert selected.title == "ILS OR LOC RWY 27"


def test_national_document_must_belong_to_current_catalogue(
    monkeypatch, tmp_path
):
    chart = NationalAipChart(
        "EHAM",
        "ILS OR LOC RWY 27",
        "EHAM-IAC-27-ILS-LOC.pdf",
        "https://ais.test/chart.pdf",
        "2026-07-09",
        "Approches IAC",
    )
    client = NationalAipClient(_source("lvnl"), tmp_path)
    monkeypatch.setattr(
        client,
        "list_airport_charts",
        lambda _icao: (date(2026, 7, 9), [chart]),
    )
    monkeypatch.setattr(client, "_download", lambda _chart: tmp_path / chart.filename)
    assert client.get_airport_chart("EHAM", chart.filename).local_path is not None
    with pytest.raises(NationalAipError, match="invalide"):
        client.get_airport_chart("EHAM", "../secret.pdf")

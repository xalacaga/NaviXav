"""Connecteurs directs vers les publications AIS nationales."""

from datetime import date

import pytest

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
    assert national_source_for_icao("EDDF") is None
    assert national_source_for_icao("LOWW") is None


def test_national_chart_categories():
    assert national_chart_category("EHAM-IAC-27-ILS-LOC.pdf") == "Approches IAC"
    assert national_chart_category("LEBL SID 1") == "Départs SID"
    assert national_chart_category("EHAM-STAR.pdf") == "Arrivées STAR"
    assert national_chart_category("EHAM-ADC.pdf") == "Aérodrome et roulage"


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

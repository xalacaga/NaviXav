"""Catalogue officiel FAA d-TPP et résolution sécurisée des PDF."""

from datetime import date

import pytest

from navixav.faa import (
    FaaChart,
    FaaClient,
    FaaError,
    faa_chart_category,
    faa_cycle_id,
    choose_faa_approach,
)


def _write_catalogue(tmp_path):
    cycle = "2607"
    path = tmp_path / cycle / "d-tpp_Metafile.xml"
    path.parent.mkdir(parents=True)
    path.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
        <digital_tpp cycle="2607" from_edate="0901Z 07/09/26">
          <state_code ID="NY">
            <city_name ID="NEW YORK">
              <airport_name ID="JOHN F KENNEDY INTL" apt_ident="JFK"
                            icao_ident="KJFK">
                <record>
                  <chart_code>APD</chart_code>
                  <chart_name>AIRPORT DIAGRAM</chart_name>
                  <pdf_name>00610AD.PDF</pdf_name>
                </record>
                <record>
                  <chart_code>STR</chart_code>
                  <chart_name>CAMRN FIVE</chart_name>
                  <pdf_name>00610CAMRN.PDF</pdf_name>
                  <faanfd18>SIE.CAMRN5</faanfd18>
                </record>
                <record>
                  <chart_code>IAP</chart_code>
                  <chart_name>ILS OR LOC RWY 04R</chart_name>
                  <pdf_name>00610IL4R.PDF</pdf_name>
                </record>
              </airport_name>
            </city_name>
          </state_code>
        </digital_tpp>
        """,
        encoding="utf-8",
    )
    return path


def test_faa_cycle_identifier():
    assert faa_cycle_id(date(2026, 1, 22)) == "2601"
    assert faa_cycle_id(date(2026, 7, 9)) == "2607"
    assert faa_cycle_id(date(2025, 12, 25)) == "2513"


def test_faa_categories():
    assert faa_chart_category("IAP") == "Approches IAC"
    assert faa_chart_category("DP") == "Départs SID"
    assert faa_chart_category("STR") == "Arrivées STAR"
    assert faa_chart_category("APD") == "Aérodrome et roulage"


def test_faa_approach_matches_runway_and_type():
    charts = [
        FaaChart(
            "KJFK",
            title,
            f"{index}.PDF",
            "https://faa.test/chart.pdf",
            "2026-07-09",
            "Approches IAC",
            "IAP",
        )
        for index, title in enumerate((
            "RNAV (GPS) RWY 04R",
            "ILS OR LOC RWY 04L",
            "ILS OR LOC RWY 04R",
        ))
    ]
    selected = choose_faa_approach(charts, "04R", "ILS RWY 04R")
    assert selected is not None
    assert selected.title == "ILS OR LOC RWY 04R"


def test_airport_catalogue_is_filtered_by_icao(tmp_path):
    _write_catalogue(tmp_path)
    client = FaaClient(tmp_path, today=date(2026, 7, 26))
    effective, charts = client.list_airport_charts("KJFK")
    assert effective == date(2026, 7, 9)
    assert [(chart.chart_code, chart.title) for chart in charts] == [
        ("APD", "AIRPORT DIAGRAM"),
        ("STR", "CAMRN FIVE"),
        ("IAP", "ILS OR LOC RWY 04R"),
    ]
    assert charts[0].url == "https://aeronav.faa.gov/d-tpp/2607/00610AD.PDF"
    assert charts[1].procedure_ident == "CAMRN5"


def test_faa_document_is_resolved_from_catalogue(monkeypatch, tmp_path):
    chart = FaaChart(
        icao="KJFK",
        title="AIRPORT DIAGRAM",
        filename="00610AD.PDF",
        url="https://aeronav.faa.gov/d-tpp/2607/00610AD.PDF",
        effective_date="2026-07-09",
        category="Aérodrome et roulage",
        chart_code="APD",
    )
    client = FaaClient(tmp_path)
    local_path = tmp_path / chart.filename
    monkeypatch.setattr(
        client,
        "list_airport_charts",
        lambda _icao: (date(2026, 7, 9), [chart]),
    )
    monkeypatch.setattr(client, "_download", lambda _chart: local_path)

    assert client.get_airport_chart("KJFK", chart.filename).local_path == local_path
    with pytest.raises(FaaError, match="invalide"):
        client.get_airport_chart("KJFK", "../secret.pdf")


def test_faa_georeference_requires_sidecar(tmp_path):
    chart = FaaChart(
        icao="KJFK",
        title="AIRPORT DIAGRAM",
        filename="00610AD.PDF",
        url="https://aeronav.faa.gov/d-tpp/2607/00610AD.PDF",
        effective_date="2026-07-09",
        category="Aérodrome et roulage",
        chart_code="APD",
    )
    client = FaaClient(tmp_path)
    assert client.has_georeference(chart) is False
    sidecar = tmp_path / "2607" / "KJFK" / "00610AD.georef.json"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text("{}", encoding="utf-8")
    assert client.has_georeference(chart) is True

"""Catalogue officiel SIA, sélection de carte et minima publiés."""

from datetime import date
import pytest

from navixav.sia import (
    SiaChart,
    SiaClient,
    SiaError,
    _decode_sia_glyphs,
    _issue_root,
    _minima_from_items,
    airac_effective_date,
    chart_category,
    choose_chart,
)


def test_current_airac_cycle():
    assert airac_effective_date(date(2026, 7, 26)) == date(2026, 7, 9)
    assert "eAIP_09_JUL_2026" in _issue_root(date(2026, 7, 9))
    assert "AIRAC-2026-07-09" in _issue_root(date(2026, 7, 9))


def test_catalogue_keeps_all_airport_charts(tmp_path):
    effective = date(2026, 7, 9)
    catalogue = tmp_path / effective.isoformat() / "LFBO" / "catalogue.html"
    catalogue.parent.mkdir(parents=True)
    catalogue.write_text(
        """
        <a href="Cartes/LFBO/AD_2_LFBO_IAC_RWY32R_FNA_ILS_Z_LOC_Z.pdf">
          AD_2_LFBO_IAC_RWY32R_FNA_ILS_Z_LOC_Z
        </a>
        <a href="Cartes/LFBO/AD_2_LFBO_IAC_RWY32R_INA_GNSS.pdf">
          AD_2_LFBO_IAC_RWY32R_INA_GNSS
        </a>
        <a href="Cartes/LFBO/AD_2_LFBO_ADC_01.pdf">AD_2_LFBO_ADC_01</a>
        """,
        encoding="utf-8",
    )
    charts = SiaClient(tmp_path, today=date(2026, 7, 26))._catalogue(
        "LFBO", effective
    )
    assert [chart.title for chart in charts] == [
        "AD_2_LFBO_IAC_RWY32R_FNA_ILS_Z_LOC_Z",
        "AD_2_LFBO_IAC_RWY32R_INA_GNSS",
        "AD_2_LFBO_ADC_01",
    ]


def test_chart_categories_are_suitable_for_the_interface():
    assert chart_category("AD_2_LFBO_IAC_RWY32R_FNA_ILS_Z") == "Approches IAC"
    assert chart_category("AD_2_LFBO_SID_RWY14") == "Départs SID"
    assert chart_category("AD_2_LFBO_STAR_RWY32") == "Arrivées STAR"
    assert chart_category("AD_2_LFBO_ADC_01") == "Aérodrome et roulage"


def test_georeference_is_reported_only_when_a_sidecar_exists(tmp_path):
    chart = SiaChart(
        "LFBO",
        "AD_2_LFBO_ADC_01",
        "AD_2_LFBO_ADC_01.pdf",
        "https://sia.test/chart.pdf",
        "2026-07-09",
    )
    client = SiaClient(tmp_path)
    assert client.has_georeference(chart) is False
    sidecar = (
        tmp_path / chart.effective_date / chart.icao / chart.filename
    ).with_suffix(".georef.json")
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text("{}", encoding="utf-8")
    assert client.has_georeference(chart) is True


def test_airport_document_is_resolved_from_catalogue(monkeypatch, tmp_path):
    chart = SiaChart(
        "LFBO",
        "AD_2_LFBO_ADC_01",
        "AD_2_LFBO_ADC_01.pdf",
        "https://sia.test/chart.pdf",
        "2026-07-09",
    )
    client = SiaClient(tmp_path)
    local_path = tmp_path / chart.filename
    monkeypatch.setattr(
        client,
        "list_airport_charts",
        lambda _icao: (date(2026, 7, 9), [chart]),
    )
    monkeypatch.setattr(client, "_download", lambda _chart: local_path)

    resolved = client.get_airport_chart("LFBO", chart.filename)
    assert resolved.local_path == local_path
    with pytest.raises(SiaError, match="invalide"):
        client.get_airport_chart("LFBO", "../secret.pdf")


def test_exact_runway_and_approach_variant_are_selected():
    charts = [
        SiaChart("LFBO", name, f"{name}.pdf", "https://sia.test/x", "2026-07-09")
        for name in (
            "AD_2_LFBO_IAC_RWY32L_FNA_ILS_Z_LOC_Z",
            "AD_2_LFBO_IAC_RWY32R_FNA_ILS_Y_LOC_Y",
            "AD_2_LFBO_IAC_RWY32R_FNA_ILS_Z_LOC_Z",
            "AD_2_LFBO_IAC_RWY32R_FNA_RNP",
        )
    ]
    selected = choose_chart(charts, "32R", "ILS Z RWY 32R")
    assert selected is not None
    assert selected.title.endswith("RWY32R_FNA_ILS_Z_LOC_Z")


def test_sia_font_glyph_names_are_decoded():
    assert _decode_sia_glyphs("/MT68/MT65 /MT40/MT72/MT41") == "DA (H)"
    assert _decode_sia_glyphs("/MT54/MT57/MT48 /MT40/MT50/MT48/MT48/MT41") == (
        "690 (200)"
    )


def test_primary_ils_minima_are_read_from_positioned_cells():
    items = [
        (80.7, 152.6, "DA"),
        (90.0, 152.6, "(H)"),
        (115.1, 152.6, "RVR"),
        (61.6, 121.6, "C"),
        (76.4, 119.7, "690"),
        (89.2, 119.7, "(200)550"),
        # Valeurs LOC voisines, qui ne doivent pas être retenues.
        (175.6, 126.1, "890"),
        (186.5, 126.1, "(400)"),
        (213.6, 126.5, "1100"),
    ]
    minima = _minima_from_items(items)
    assert minima is not None
    assert minima.to_dict() == {
        "category": "CAT I",
        "mode": "RADIO",
        "dh_ft": 200,
        "altitude_ft": 690,
        "rvr_m": 550,
        "confidence": "à confirmer",
    }

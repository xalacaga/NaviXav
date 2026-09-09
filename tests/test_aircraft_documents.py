"""Manuels locaux : association par paquet, accès borné et recherche multipage."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from navixav.aircraft.documents import checked_document, document_inventory, search_document
from navixav.config import Settings
from navixav.web.app import create_app


def package(community, name="vendor-jet", title="Vendor Jet"):
    root = community / name
    aircraft = root / "SimObjects" / "Airplanes" / "jet"
    aircraft.mkdir(parents=True)
    (aircraft / "aircraft.cfg").write_text(
        f'[GENERAL]\nicao_type_designator="JET1"\n[FLTSIM.0]\n'
        f'title="{title}"\nui_manufacturer="Vendor"\nui_type="Jet"\n', encoding="utf-8")
    return root


def pdf(path, texts=("Normal procedures", "Fuel pump on. Fuel pressure check.")):
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    for text in texts:
        page = writer.add_blank_page(width=600, height=800)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        content = DecodedStreamObject()
        content.set_data(f"BT /F1 12 Tf 40 700 Td ({text}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(content)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


def test_lists_nested_pdfs_and_keeps_same_model_packages_separate(tmp_path):
    community = tmp_path / "Community"
    first = package(community)
    second = package(community, "other-jet", "Other Jet")
    pdf(first / "Manual.PDF")
    pdf(first / "Docs" / "Manual.pdf")
    pdf(second / "Guide.pdf")
    pdf(community / "scenery" / "Readme.pdf")
    (first / "not-a-pdf.txt").write_text("text")
    packages, files = document_inventory([community])
    assert len(packages) == 2
    assert len(files) == 3
    jet = next(item for item in packages if item["package"] == "vendor-jet")
    assert [doc["relative_path"] for doc in jet["documents"]] == ["Docs/Manual.pdf", "Manual.PDF"]
    assert jet["titles"] == ["Vendor Jet"]
    assert all(doc["size"] > 0 for doc in jet["documents"])


def test_search_finds_each_occurrence_on_later_pages_and_invalidates_cache(tmp_path):
    path = pdf(tmp_path / "manual.pdf")
    result = search_document(path, "FUEL")
    assert result["total"] == 2
    assert [match["page"] for match in result["matches"]] == [2, 2]
    assert "Fuel pump" in result["matches"][0]["snippet"]
    assert search_document(path, "missing")["total"] == 0
    pdf(path, ("New replacement manual",))
    assert search_document(path, "Fuel")["total"] == 0


def test_search_reports_image_only_and_limits_results(tmp_path):
    path = pdf(tmp_path / "empty.pdf", ("",))
    assert not search_document(path, "fuel")["text_available"]
    path = pdf(tmp_path / "long.pdf", ("fuel " * 125,))
    result = search_document(path, "fuel")
    assert result["total"] == 125
    assert len(result["matches"]) == 100
    assert result["limited"]


def test_rejects_files_outside_package_and_fake_pdf(tmp_path):
    root = tmp_path / "package"
    root.mkdir()
    with pytest.raises(ValueError):
        checked_document(root, pdf(tmp_path / "outside.pdf"))
    fake = root / "fake.pdf"
    fake.write_text("not a PDF")
    with pytest.raises(ValueError):
        checked_document(root, fake)


def test_http_inline_head_range_search_and_deleted_document(tmp_path):
    community = tmp_path / "Community"
    path = pdf(package(community) / "Docs" / "Guide.pdf")
    app = create_app(Settings(aircraft_community_path=community))
    try:
        with TestClient(app) as client:
            assert client.get("/api/aircraft/documents").json()["packages"] == []
            report = client.get("/api/aircraft/documents", params={"title": "Vendor Jet", "icao": "JET1"}).json()
            assert report["community_found"]
            url = report["packages"][0]["documents"][0]["url"]
            response = client.get(url)
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert response.headers["content-disposition"].startswith("inline;")
            assert client.head(url).status_code == 200
            response = client.get(url, headers={"Range": "bytes=0-4"})
            assert response.status_code == 206
            assert response.content == b"%PDF-"
            result = client.get(url + "/search", params={"q": "fuel"})
            assert result.json()["matches"][0]["page"] == 2
            assert client.get(url + "/search", params={"q": "x"}).status_code == 400
            assert client.get("/api/aircraft/documents/unknown").status_code == 404
            path.unlink()
            assert client.get(url).status_code == 404
            assert client.get(url + "/search", params={"q": "fuel"}).status_code == 422
    finally:
        app.state.close_resources()


def test_linked_package_supported_but_nested_escape_rejected(tmp_path):
    # Les jonctions Windows ne demandent pas le privilège des liens symboliques.
    import os
    import subprocess

    source = tmp_path / "addons"
    root = package(source)
    pdf(root / "Guide.pdf")
    outside = tmp_path / "outside"
    pdf(outside / "Secret.pdf")
    community = tmp_path / "Community"
    community.mkdir()

    def link(target, destination):
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", str(destination), str(target)],
                           check=True, capture_output=True)
        else:
            destination.symlink_to(target, target_is_directory=True)

    link(root, community / "linked-jet")
    link(outside, root / "escape")
    packages, files = document_inventory([community])
    assert len(packages) == 1
    assert len(files) == 1
    assert packages[0]["documents"][0]["name"] == "Guide.pdf"


def test_simbrief_profile_filters_type_and_provider(tmp_path):
    community = tmp_path / "Community"
    for name, title, code in (("fenix-a320", "Fenix A320", "A320"),
                              ("inibuilds-a320", "iniBuilds A320", "A320"),
                              ("fenix-a321", "Fenix A321", "A321")):
        root = package(community, name, title)
        config = root / "SimObjects" / "Airplanes" / "jet" / "aircraft.cfg"
        config.write_text(config.read_text().replace("JET1", code).replace('ui_type="Jet"', f'ui_type="{title}"'))
        pdf(root / "Manual.pdf")
    found, files = document_inventory([community], title="Airbus A320 Fenix profile", icao="A320")
    assert [item["package"] for item in found] == ["fenix-a320"]
    assert len(files) == 1
    assert document_inventory([community], title="Airbus A320", icao="A320") == ([], {})
    assert document_inventory([community], title="Boeing 737", icao="B738") == ([], {})
    assert document_inventory([community], title="", icao="") == ([], {})


def test_generic_simbrief_type_uses_only_matching_installed_aircraft(tmp_path):
    community = tmp_path / "Community"
    pdf(package(community, "vendor-jet") / "Manual.pdf")
    other = package(community, "other-plane", "Other Plane")
    config = other / "SimObjects" / "Airplanes" / "jet" / "aircraft.cfg"
    config.write_text(config.read_text().replace("JET1", "PROP"))
    pdf(other / "Other.pdf")
    found, files = document_inventory([community], title="SimBrief Jet variant", icao="JET1")
    assert [item["package"] for item in found] == ["vendor-jet"]
    assert len(files) == 1

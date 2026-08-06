"""Journal des versions relu par les Paramètres.

`CHANGELOG.md` est l'histoire du dépôt. Les Paramètres l'affichent tel quel :
le texte des puces reste en anglais, seuls le cadre et les intitulés de
rubrique suivent la langue de l'interface.
"""

from __future__ import annotations

from pathlib import Path

import navixav
from navixav.changelog import changelog_path, load_changelog, parse_changelog
from navixav.config import Settings
from navixav.web.app import create_app

PROJECT_ROOT = Path(__file__).parent.parent
STATIC = PROJECT_ROOT / "navixav" / "web" / "static"

LOCALES = ("en", "fr", "de", "es", "it", "pt", "nl", "pl")


# --------------------------------------------------------------------------- #
# La lecture du fichier
# --------------------------------------------------------------------------- #


def test_a_version_is_recognised_whatever_the_heading_level():
    """1.4.8 et 1.4.9 écrivent leurs rubriques au rang de la version.

    Le niveau de titre ne distingue donc rien : seul « [x.y.z] - date » fait
    une version. Les entrées plus anciennes, correctement imbriquées, doivent
    se lire de la même façon.
    """
    releases = parse_changelog(
        "# Changelog\n\n"
        "## [1.4.9] - 2026-08-05\n\n"
        "## Fixed\n\n"
        "- Arrêt propre.\n\n"
        "## [1.4.7] - 2026-08-05\n\n"
        "### Added\n\n"
        "- Rail de modules.\n"
    )
    assert [release.version for release in releases] == ["1.4.9", "1.4.7"]
    assert [section.title for release in releases for section in release.sections] == [
        "Fixed", "Added",
    ]


def test_a_paragraph_without_a_bullet_is_still_a_change():
    """Les premières versions décrivent parfois un changement en prose."""
    releases = parse_changelog(
        "## [1.0.0] - 2026-07-29\n\n"
        "## Changed\n\n"
        "- Correction bug.\n\n"
        "L'installeur est vérifié par sa somme SHA-256.\n"
    )
    assert releases[0].sections[0].items == [
        "Correction bug.",
        "L'installeur est vérifié par sa somme SHA-256.",
    ]


def test_a_wrapped_bullet_stays_one_item():
    releases = parse_changelog(
        "## [1.0.0] - 2026-07-29\n\n"
        "## Fixed\n\n"
        "- Une puce longue\n  repliée sur deux lignes.\n"
    )
    assert releases[0].sections[0].items == ["Une puce longue repliée sur deux lignes."]


def test_the_section_kind_survives_translation():
    """L'intitulé traduit se choisit sur « kind », jamais sur le texte anglais."""
    releases = parse_changelog(
        "## [1.0.0] - 2026-07-29\n\n### Maintenance\n\n- Installeur.\n"
    )
    assert releases[0].sections[0].kind == "maintenance"


def test_an_empty_version_is_not_announced():
    """Une version sans rien à dire n'a rien à montrer."""
    assert parse_changelog("## [1.0.0] - 2026-07-29\n\n### Added\n") == []


def test_a_missing_file_is_not_an_error(monkeypatch, tmp_path):
    """L'absence du journal ferme la fenêtre, elle ne casse pas les Paramètres."""
    monkeypatch.setattr(
        "navixav.changelog.changelog_path", lambda: tmp_path / "absent.md"
    )
    assert load_changelog() == []


# --------------------------------------------------------------------------- #
# Le journal réellement livré
# --------------------------------------------------------------------------- #


def test_the_repository_changelog_is_readable_from_the_first_version():
    releases = load_changelog()
    assert len(releases) > 20
    assert releases[0]["version"] == navixav.__version__
    assert releases[-1]["version"] == "0.2.0"
    assert all(release["date"] for release in releases)
    assert all(release["sections"] for release in releases)


def test_every_section_kind_is_translated():
    """Une rubrique sans traduction retomberait sur son titre anglais."""
    kinds = {
        section["kind"]
        for release in load_changelog()
        for section in release["sections"]
    }
    translations = (STATIC / "i18n.js").read_text(encoding="utf-8")
    for kind in kinds:
        assert translations.count(f"changelog_kind_{kind}:") == len(LOCALES), kind


def test_the_changelog_ships_with_the_application():
    """Sans entrée dans le .spec, la fenêtre s'ouvrirait vide une fois installée."""
    spec = (PROJECT_ROOT / "NaviXav.spec").read_text(encoding="utf-8")
    assert 'project_root / "CHANGELOG.md"' in spec
    assert changelog_path().name == "CHANGELOG.md"


def test_prepare_release_nests_the_sections_under_the_version():
    """« ## Added » au rang de « ## [1.4.9] » casserait la hiérarchie."""
    prepare = (PROJECT_ROOT / "scripts" / "prepare_release.ps1").read_text(
        encoding="utf-8"
    )
    assert 'if ($_ -like "## *") { "#" + $_ }' in prepare


# --------------------------------------------------------------------------- #
# Le raccordement à l'interface
# --------------------------------------------------------------------------- #


def test_the_endpoint_returns_the_history_and_the_installed_version():
    app = create_app(Settings(metar_source="simbrief"))
    endpoint = next(
        route.endpoint for route in app.routes if route.path == "/api/changelog"
    )
    payload = endpoint()
    assert payload["version"] == navixav.__version__
    assert payload["releases"][0]["version"] == navixav.__version__
    section = payload["releases"][0]["sections"][0]
    assert {"kind", "title", "items"} <= set(section)


def test_the_settings_carry_a_changelog_button():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    css = (STATIC / "app.css").read_text(encoding="utf-8")

    head = html.split('<div class="settings-head">')[1].split("</div>")[0:6]
    assert 'id="changelog-open"' in "".join(head)
    assert 'id="changelog-dialog"' in html
    assert '$("changelog-open").addEventListener("click", openChangelog)' in javascript
    assert 'fetch("/api/changelog"' in javascript
    # Icône seule, sans libellé, comme les autres boutons de la boîte.
    assert ".changelog-btn" in css
    assert 'aria-label="Journal des versions"' in html


def test_the_panel_is_labelled_in_every_language():
    translations = (STATIC / "i18n.js").read_text(encoding="utf-8")
    for key in (
        "changelog_title", "changelog_intro", "changelog_loading",
        "changelog_empty", "changelog_failed", "changelog_installed",
    ):
        assert translations.count(f"{key}:") == len(LOCALES), key
    assert '"#changelog-open": "changelog_title"' in translations
    assert '"#changelog-title": "changelog_title"' in translations
    assert '"#changelog-intro": "changelog_intro"' in translations
    assert 'changelog.setAttribute("aria-label", t("changelog_title"))' in translations


def test_only_the_history_scrolls():
    """Trente et une versions défilent, le cadre de la fenêtre reste fixe."""
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    body = css.split(".changelog-body {")[1].split("}")[0]
    assert "overflow-y: auto" in body

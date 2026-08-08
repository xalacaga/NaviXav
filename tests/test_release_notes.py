"""Notes de version dans la langue de l'interface.

Une note de version est un texte que l'utilisateur lit : elle suit donc la même
règle que le reste de l'interface et existe dans toutes les langues que NaviXav
parle. Le chemin complet est vérifié ici :

    RELEASE_HIGHLIGHTS.json  (rédaction, 8 langues)
        -> prepare_release.ps1
            -> RELEASE_NOTES.<langue>.md   (publiées avec la Release)

Les notes vivent sur la page de la Release GitHub, pas dans l'application :
NaviXav affiche un plan de vol, pas son propre journal des modifications.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
STATIC = PROJECT_ROOT / "navixav" / "web" / "static"

# L'ordre est celui de i18n.js. « en » est le repli de toutes les autres.
LOCALES = ("en", "fr", "de", "es", "it", "pt", "nl", "pl")


def _highlights() -> dict:
    return json.loads(
        (PROJECT_ROOT / "RELEASE_HIGHLIGHTS.json").read_text(encoding="utf-8")
    )


def _entries(data: dict) -> list[dict]:
    return list(data.get("added") or []) + list(data.get("fixed") or [])


# --------------------------------------------------------------------------- #
# Le fichier de rédaction
# --------------------------------------------------------------------------- #


def test_highlights_is_readable_and_has_both_sections():
    data = _highlights()
    assert isinstance(data.get("added"), list)
    assert isinstance(data.get("fixed"), list)


def test_every_highlight_is_written_in_every_interface_language():
    """Une puce absente d'une langue s'afficherait en anglais chez cet utilisateur.

    Le repli existe pour ne jamais bloquer une publication, pas pour servir de
    norme : le dépôt exige les huit langues.
    """
    missing = [
        (index, locale)
        for index, entry in enumerate(_entries(_highlights()))
        for locale in LOCALES
        if not str(entry.get(locale) or "").strip()
    ]
    assert not missing, f"puces sans traduction : {missing}"


def test_no_unknown_language_slips_into_the_highlights():
    """« ne » au lieu de « nl » passerait silencieusement en repli anglais."""
    for entry in _entries(_highlights()):
        unknown = set(entry) - set(LOCALES)
        assert not unknown, f"langues inconnues : {sorted(unknown)}"


def test_aviation_identifiers_survive_translation():
    """Les identifiants ne se traduisent pas, quelle que soit la langue."""
    for entry in _entries(_highlights()):
        if "ILS RWY 29" not in entry["fr"]:
            continue
        for locale in LOCALES:
            assert "ILS RWY 29" in entry[locale]
            assert "BSC" in entry[locale]


# --------------------------------------------------------------------------- #
# L'application n'affiche pas son propre journal
# --------------------------------------------------------------------------- #


def test_the_interface_carries_no_release_notes_panel():
    """Le panneau « Nouveautés » a été retiré : rien ne doit en subsister.

    Un bouton sans panneau, ou un panneau sans bouton, sont deux façons de
    laisser du code mort dans une barre d'outils déjà chargée.
    """
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    translations = (STATIC / "i18n.js").read_text(encoding="utf-8")

    assert not (STATIC / "release_notes.js").exists()
    for source in (html, javascript, css, translations):
        assert "release_notes.js" not in source
        assert "release-notes-open" not in source
        assert "RELEASE_NOTES" not in source
        assert "whats_new" not in source
    assert ".notes-btn" not in css


# --------------------------------------------------------------------------- #
# La chaîne de publication
# --------------------------------------------------------------------------- #


def test_prepare_reads_the_structured_highlights():
    prepare = (PROJECT_ROOT / "scripts" / "prepare_release.ps1").read_text(
        encoding="utf-8"
    )
    assert "RELEASE_HIGHLIGHTS.json" in prepare
    assert "RELEASE_HIGHLIGHTS.md" not in prepare
    assert '$Locales = @("en", "fr", "de", "es", "it", "pt", "nl", "pl")' in prepare


def test_prepare_keeps_empty_release_categories_in_their_named_parameters():
    """Un tableau vide ne doit pas décaler les arguments PowerShell suivants."""
    prepare = (PROJECT_ROOT / "scripts" / "prepare_release.ps1").read_text(
        encoding="utf-8"
    )

    assert "$FeatureItems = @(" in prepare
    assert "$FixItems = @(" in prepare
    assert "Where-Object { $null -ne $_ }" in prepare
    assert "-AddedEntries $FeatureItems" in prepare
    assert "-FixedEntries $FixItems" in prepare
    assert "-ChangedItems $Other" in prepare


def test_prepare_writes_one_note_per_language():
    prepare = (PROJECT_ROOT / "scripts" / "prepare_release.ps1").read_text(
        encoding="utf-8"
    )
    assert '"RELEASE_NOTES.$Locale.md"' in prepare
    # L'anglais reste le corps de la Release GitHub.
    assert 'if ($Locale -eq "en") { $Targets += "RELEASE_NOTES.md" }' in prepare
    # Plus rien n'est écrit dans les fichiers servis par l'interface.
    assert "web\\static\\release_notes.js" not in prepare


def test_french_typography_is_never_applied_to_another_language():
    """Les espaces insécables devant « : » sont une règle française."""
    prepare = (PROJECT_ROOT / "scripts" / "prepare_release.ps1").read_text(
        encoding="utf-8"
    )
    assert 'if ($Locale -eq "fr") { return Format-FrenchSentence $Text }' in prepare
    assert "return Format-PlainSentence $Text" in prepare


def test_publish_tracks_every_generated_file():
    publish = (PROJECT_ROOT / "scripts" / "publish_release.ps1").read_text(
        encoding="utf-8"
    )
    assert '"RELEASE_HIGHLIGHTS.json"' in publish
    assert "release_notes.js" not in publish
    for locale in LOCALES:
        assert f'"RELEASE_NOTES.{locale}.md"' in publish


def test_localised_notes_are_attached_to_the_github_release():
    publish = (PROJECT_ROOT / "scripts" / "publish_release.ps1").read_text(
        encoding="utf-8"
    )
    assert '"RELEASE_NOTES.$_.md"' in publish
    assert "$Assets = $Packages + $LocalisedNotes" in publish

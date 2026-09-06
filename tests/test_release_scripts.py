from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent


def test_publish_release_tracks_every_publishing_file_updated_by_prepare():
    publish = (PROJECT_ROOT / "scripts" / "publish_release.ps1").read_text(
        encoding="utf-8"
    )

    for relative_path in (
        "publishing/flightsim-to-description.txt",
        "publishing/flightsim-to-installer/README-FIRST.txt",
        "publishing/flightsim-to-listing.md",
    ):
        assert f'"{relative_path}"' in publish


def test_portable_archive_tolerates_transient_windows_file_locks():
    build = (PROJECT_ROOT / "scripts" / "build_windows.ps1").read_text(
        encoding="utf-8"
    )

    assert "$MaxAttempts = 30" in build
    assert "$Attempt -le $MaxAttempts" in build
    assert "Start-Sleep -Seconds 2" in build
    assert "sans arrêter de processus utilisateur" in build


def test_fastapi_uses_its_supported_lifespan_lifecycle():
    application = (PROJECT_ROOT / "navixav" / "web" / "app.py").read_text(
        encoding="utf-8"
    )

    assert "@app.on_event" not in application
    assert "@asynccontextmanager" in application
    assert "lifespan=lifespan" in application
    assert "app.state.close_resources = close_resources" in application


def test_release_version_check_ignores_license_historical_tags_and_ipv4_addresses():
    prepare = (PROJECT_ROOT / "scripts" / "prepare_release.ps1").read_text(
        encoding="utf-8"
    )

    assert '"(?<!v)" + [regex]::Escape($Current)' in prepare
    assert "$Content[$Match.Index - 1] -eq 'v'" in prepare
    assert "PolyForm\\s+Noncommercial(?:\\s+License)?\\s*$" in prepare
    assert "$Suffix -match '^\\.\\d{1,3}(?!\\d)'" in prepare
    assert "if ($Match.Value -ne $Next)" not in prepare


def test_release_version_check_skips_the_regenerated_flightsim_to_changelog():
    """Le journal de la fiche porte l'historique, pas la version préparée.

    Il est reconstruit depuis CHANGELOG.md à la fin de la préparation : l'y
    aligner réécrirait le titre de la version précédente, et le garde-fou y
    verrait autant de publications oubliées qu'il existe de versions.
    """
    prepare = (PROJECT_ROOT / "scripts" / "prepare_release.ps1").read_text(
        encoding="utf-8"
    )

    assert '$Generated = @("flightsim-to-changelog.txt")' in prepare
    assert "$Generated -notcontains $_.Name" in prepare
    assert prepare.count("foreach ($File in $Files) {") == 2


def test_release_version_check_leaves_dated_announcements_alone():
    """Une annonce « what's new » porte le numéro de sa propre version.

    L'aligner sur la version préparée transformerait l'annonce d'une version
    déjà publiée en annonce de la suivante, et la construction échouerait sur
    un fichier modifié hors de la liste des fichiers de Release.
    """
    prepare = (PROJECT_ROOT / "scripts" / "prepare_release.ps1").read_text(
        encoding="utf-8"
    )

    assert (
        r"$Historical = '^flightsim-to-whats-new-\d+\.\d+\.\d+\.txt$'"
        in prepare
    )
    assert "$_.Name -notmatch $Historical" in prepare


def test_windows_distribution_includes_aircraft_photo_credits():
    collect = (PROJECT_ROOT / "scripts" / "collect_licenses.ps1").read_text(
        encoding="utf-8"
    )
    credits = (PROJECT_ROOT / "AIRCRAFT_PHOTO_CREDITS.md").read_text(
        encoding="utf-8"
    )

    assert '"AIRCRAFT_PHOTO_CREDITS.md"' in collect
    assert "GFDL" not in credits
    assert credits.count("commons.wikimedia.org/wiki/File:") == 31


def test_prepare_release_produces_the_flightsim_to_changelog():
    prepare = (PROJECT_ROOT / "scripts" / "prepare_release.ps1").read_text(
        encoding="utf-8"
    )

    assert "function ConvertTo-FlightsimToChangelog" in prepare
    # Les émojis sont assemblés depuis leur point de code : écrits en clair,
    # ils ne survivraient pas à un script relu en Windows-1252.
    assert "[char]::ConvertFromUtf32(0x1F4D1)" in prepare
    assert r"publishing\flightsim-to-changelog.txt" in prepare
    # Le journal est reconstruit après l'écriture de CHANGELOG.md : la version
    # qui vient d'être publiée doit y figurer.
    assert prepare.index("CHANGELOG.md") < prepare.index(
        "ConvertTo-FlightsimToChangelog ("
    )


def test_publish_release_commits_the_flightsim_to_changelog():
    """Un journal régénéré mais non commité repartirait sur l'ancien texte."""
    publish = (PROJECT_ROOT / "scripts" / "publish_release.ps1").read_text(
        encoding="utf-8"
    )

    assert '"publishing/flightsim-to-changelog.txt"' in publish


def _changelog_versions() -> dict[str, dict[str, int]]:
    """Versions du journal et nombre de puces par rubrique.

    Les titres de rubrique sont acceptés aux niveaux 2 et 3 : les versions
    1.4.8 et 1.4.9 datent d'avant que le format ne se fixe.
    """
    versions: dict[str, dict[str, int]] = {}
    current: dict[str, int] | None = None
    section: str | None = None
    for line in (PROJECT_ROOT / "CHANGELOG.md").read_text(
        encoding="utf-8"
    ).splitlines():
        if line.startswith("## ["):
            current = versions.setdefault(line[4:].split("]")[0], {})
            section = None
        elif line.startswith(("## ", "### ")) and current is not None:
            section = line.lstrip("#").strip()
            current.setdefault(section, 0)
        elif line.startswith("- ") and current is not None and section:
            current[section] += 1
    return versions


def test_the_flightsim_to_changelog_carries_every_publishable_version():
    """Le fichier collé sur la fiche doit porter tout l'historique publiable.

    Il est régénéré par prepare_release.ps1 ; un CHANGELOG.md retouché à la
    main sans régénération laisserait la fiche en arrière d'une version. Une
    version dont il ne reste rien une fois « Changed » écarté est la seule à
    pouvoir manquer : un titre seul n'apprendrait rien.
    """
    listing = (PROJECT_ROOT / "publishing" / "flightsim-to-changelog.txt").read_text(
        encoding="utf-8"
    )
    versions = _changelog_versions()
    assert versions, "aucune version dans CHANGELOG.md"

    missing = [
        version
        for version, sections in versions.items()
        if sum(n for name, n in sections.items() if name != "Changed") > 0
        and f"[{version}]" not in listing
    ]
    assert not missing, f"versions absentes de la fiche Flightsim.to : {missing}"


def test_the_flightsim_to_changelog_leaves_out_repository_vocabulary():
    """« Changed » ne contient que des sujets de commit, parfois en français."""
    listing = (PROJECT_ROOT / "publishing" / "flightsim-to-changelog.txt").read_text(
        encoding="utf-8"
    )

    assert "Changed" not in listing
    assert "Ajout fonctionnalites" not in listing
    # Une version réduite à « Changed » ne laisse pas de titre orphelin.
    empty = [
        version
        for version, sections in _changelog_versions().items()
        if sum(n for name, n in sections.items() if name != "Changed") == 0
    ]
    for version in empty:
        assert f"[{version}]" not in listing, f"{version} n'a rien à publier"

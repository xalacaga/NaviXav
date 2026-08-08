from __future__ import annotations

import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
README_FILES = (
    "README.md",
    "README.fr.md",
    "README.de.md",
    "README.es.md",
    "README.it.md",
    "README.pt.md",
    "README.nl.md",
    "README.pl.md",
)
PUBLISHING_FILES = (
    "publishing/flightsim-to-description.txt",
    "publishing/flightsim-to-installer/README-FIRST.txt",
    "publishing/flightsim-to-listing.md",
)


def _text(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def _prose(relative_path: str) -> str:
    return " ".join(_text(relative_path).split())


def test_primary_license_is_the_standard_polyform_text():
    license_text = _text("LICENSE")

    assert license_text.startswith("# PolyForm Noncommercial License 1.0.0\n")
    assert "https://polyformproject.org/licenses/noncommercial/1.0.0" in license_text
    assert "Required Notice: Copyright 2026 Xavier BEGUE (xalacaga)." in license_text
    for heading in (
        "## Copyright License",
        "## Distribution License",
        "## Changes and New Works License",
        "## Noncommercial Purposes",
        "## Violations",
        "## No Liability",
    ):
        assert heading in license_text


def test_package_metadata_and_distribution_include_commercial_terms():
    metadata = tomllib.loads(_text("pyproject.toml"))["project"]

    assert metadata["license"] == "PolyForm-Noncommercial-1.0.0"
    assert "COMMERCIAL_LICENSE.md" in metadata["license-files"]
    assert "COMMERCIAL_LICENSE.md" in _text("scripts/collect_licenses.ps1")


def test_every_localized_readme_states_the_current_model():
    for relative_path in README_FILES:
        readme = _text(relative_path)
        assert "PolyForm Noncommercial" in readme, relative_path
        assert "COMMERCIAL_LICENSE.md" in readme, relative_path
        assert "CONTRIBUTING.md" in readme, relative_path
        assert "GPLv3" not in readme, relative_path


def test_publication_copy_does_not_describe_current_code_as_apache_open_source():
    forbidden_current_claims = (
        "is distributed under the Apache License 2.0",
        "is licensed under the Apache License 2.0",
        "source is published under the Apache License 2.0",
    )
    for relative_path in PUBLISHING_FILES:
        copy = _text(relative_path)
        assert "PolyForm Noncommercial" in copy, relative_path
        for claim in forbidden_current_claims:
            assert claim not in copy, (relative_path, claim)


def test_previous_apache_grants_and_third_party_terms_are_preserved():
    notice = _prose("NOTICE")
    commercial = _prose("COMMERCIAL_LICENSE.md")

    assert "Git releases tagged v1.4.12 and earlier" in notice
    assert "Rights already granted for those releases remain in force" in notice
    assert "Git releases tagged v1.4.12 and earlier" in commercial
    assert "THIRD_PARTY_NOTICES" in commercial


def test_contributions_require_prior_dual_licensing_agreement():
    contributing = _prose("CONTRIBUTING.md")

    assert "signed a separate contributor agreement" in contributing
    assert "does not by itself transfer copyright" in contributing

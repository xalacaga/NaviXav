"""Statistiques publiques des téléchargements GitHub Releases."""

from datetime import UTC, datetime

import pytest
import requests

from navixav.release_dashboard import (
    ReleaseDashboardError,
    fetch_release_downloads,
    render_dashboard,
    write_dashboard,
)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def release_payload():
    return [
        {
            "tag_name": "v1.2.0",
            "name": "NaviXav 1.2.0",
            "published_at": "2026-07-29T12:00:00Z",
            "html_url": "https://github.com/xalacaga/NaviXav/releases/tag/v1.2.0",
            "prerelease": False,
            "assets": [
                {
                    "name": "NaviXav-Setup-1.2.0.exe",
                    "download_count": 42,
                    "browser_download_url": "https://example.invalid/setup.exe",
                },
                {
                    "name": "NaviXav-1.2.0-windows-x64-portable.zip",
                    "download_count": 8,
                    "browser_download_url": "https://example.invalid/portable.zip",
                },
                {
                    "name": "NaviXav-Setup-1.2.0.exe.sha256",
                    "download_count": 99,
                    "browser_download_url": "https://example.invalid/checksum",
                },
            ],
        }
    ]


def test_dashboard_counts_only_distributable_release_assets(tmp_path):
    session = FakeSession([FakeResponse(release_payload())])

    releases = fetch_release_downloads(session=session)
    page = render_dashboard(
        releases,
        generated_at=datetime(2026, 7, 29, 12, 30, tzinfo=UTC),
    )
    destination = write_dashboard(releases, tmp_path / "downloads.html")

    assert releases[0].installer_downloads == 42
    assert releases[0].portable_downloads == 8
    assert releases[0].total_downloads == 50
    assert ".sha256" not in page
    assert "utilisateurs uniques" in page
    assert "Aucune télémétrie NaviXav" in page
    assert destination.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert session.calls[0][1]["params"] == {"per_page": 100, "page": 1}


def test_dashboard_rejects_invalid_repository_names():
    with pytest.raises(ReleaseDashboardError, match="invalide"):
        fetch_release_downloads("../secret")


def test_dashboard_reports_invalid_github_responses():
    session = FakeSession([FakeResponse({"message": "rate limit"})])
    with pytest.raises(ReleaseDashboardError, match="invalide"):
        fetch_release_downloads(session=session)

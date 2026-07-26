"""Mise à jour depuis une Release GitHub contrôlée."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import requests

from navixav.updater import GitHubUpdater, UpdateError


class FakeResponse:
    def __init__(self, *, payload=None, content=b"", text="", status=200):
        self.payload = payload
        self.content = content
        self.text = text
        self.status_code = status

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def iter_content(self, chunk_size):
        del chunk_size
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def release_payload(version: str, data: bytes, *, digest: str | None = None):
    name = f"NaviXav-Setup-{version}.exe"
    return {
        "tag_name": f"v{version}",
        "html_url": f"https://github.com/xalacaga/NaviXav/releases/tag/v{version}",
        "body": "Corrections et nouveautés",
        "assets": [
            {
                "name": name,
                "browser_download_url": (
                    "https://github.com/xalacaga/NaviXav/releases/download/"
                    f"v{version}/{name}"
                ),
                "size": len(data),
                "digest": digest,
            },
            {
                "name": f"{name}.sha256",
                "browser_download_url": (
                    "https://github.com/xalacaga/NaviXav/releases/download/"
                    f"v{version}/{name}.sha256"
                ),
                "size": 90,
            },
        ],
    }


def test_update_is_detected_and_verified_from_github_digest(tmp_path):
    data = b"MZ" + b"NaviXav installer" * 20
    digest = hashlib.sha256(data).hexdigest()
    session = FakeSession(
        [
            FakeResponse(
                payload=release_payload("0.2.0", data, digest=f"sha256:{digest}")
            ),
            FakeResponse(content=data),
        ]
    )
    updater = GitHubUpdater("0.1.0", session=session, download_dir=tmp_path)

    update = updater.check()
    installer = updater.download(update)

    assert update.available is True
    assert update.latest_version == "0.2.0"
    assert update.to_dict()["integrity_verified"] is True
    assert installer.read_bytes() == data


def test_checksum_asset_is_used_when_github_digest_is_missing(tmp_path):
    data = b"MZ fallback checksum"
    digest = hashlib.sha256(data).hexdigest()
    session = FakeSession(
        [
            FakeResponse(payload=release_payload("0.1.1", data)),
            FakeResponse(text=f"{digest}  NaviXav-Setup-0.1.1.exe"),
            FakeResponse(content=data),
        ]
    )
    updater = GitHubUpdater("0.1.0", session=session, download_dir=tmp_path)

    assert updater.download(updater.check()).is_file()


def test_corrupt_installer_is_deleted(tmp_path):
    expected = b"MZ expected"
    corrupt = b"MZ corrupt!"
    digest = hashlib.sha256(expected).hexdigest()
    payload = release_payload("0.1.1", corrupt, digest=f"sha256:{digest}")
    # La taille reste cohérente afin de tester spécifiquement l'empreinte.
    session = FakeSession(
        [FakeResponse(payload=payload), FakeResponse(content=corrupt)]
    )
    updater = GitHubUpdater("0.1.0", session=session, download_dir=tmp_path)

    with pytest.raises(UpdateError, match="SHA-256"):
        updater.download(updater.check())
    assert not list(Path(tmp_path).glob("*"))


def test_same_or_older_release_is_not_offered():
    session = FakeSession(
        [FakeResponse(payload={"tag_name": "v0.1.0", "assets": []})]
    )
    update = GitHubUpdater("0.1.0", session=session).check()
    assert update.available is False

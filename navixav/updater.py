"""Mises à jour de NaviXav depuis les Releases GitHub officielles."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

from navixav.paths import user_data_path

GITHUB_REPOSITORY = "xalacaga/NaviXav"
LATEST_RELEASE_URL = (
    f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
)
MAX_INSTALLER_BYTES = 300 * 1024 * 1024
REQUEST_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "NaviXav-Updater",
}
LOGGER = logging.getLogger(__name__)


class UpdateError(RuntimeError):
    """Erreur contrôlée pendant la recherche ou le téléchargement."""


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str | None = None
    available: bool = False
    installer_name: str | None = None
    installer_url: str | None = None
    installer_size: int | None = None
    digest: str | None = None
    checksum_url: str | None = None
    release_url: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        # Les URL de téléchargement ne sont utiles qu'au serveur local.
        payload.pop("installer_url")
        payload.pop("checksum_url")
        payload["integrity_verified"] = bool(self.digest or self.checksum_url)
        return payload


def _version_tuple(value: str) -> tuple[int, int, int, int]:
    match = re.fullmatch(
        r"\s*v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?(?:[-+][0-9A-Za-z.-]+)?\s*",
        value,
    )
    if not match:
        raise UpdateError(f"Version GitHub non reconnue : {value!r}")
    return tuple(int(part or 0) for part in match.groups())


def _sha256_digest(value: object) -> str | None:
    raw = str(value or "").strip().lower()
    if raw.startswith("sha256:"):
        raw = raw[7:]
    return raw if re.fullmatch(r"[0-9a-f]{64}", raw) else None


def _asset_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assets = payload.get("assets")
    if not isinstance(assets, list):
        return {}
    return {
        str(asset.get("name")): asset
        for asset in assets
        if isinstance(asset, dict) and asset.get("name")
    }


class GitHubUpdater:
    """Client minimal, sans clé GitHub, destiné aux dépôts publics."""

    def __init__(
        self,
        current_version: str,
        *,
        session: requests.Session | None = None,
        download_dir: Path | None = None,
    ) -> None:
        self.current_version = current_version
        self.session = session or requests.Session()
        self.download_dir = download_dir or user_data_path("updates")

    def check(self) -> UpdateInfo:
        try:
            response = self.session.get(
                LATEST_RELEASE_URL,
                headers=REQUEST_HEADERS,
                timeout=8,
            )
        except requests.RequestException as exc:
            raise UpdateError(
                "GitHub est momentanément inaccessible."
            ) from exc
        if response.status_code == 404:
            return UpdateInfo(current_version=self.current_version)
        try:
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise UpdateError(
                "Réponse de mise à jour GitHub invalide."
            ) from exc
        if not isinstance(payload, dict):
            raise UpdateError("Réponse de mise à jour GitHub invalide.")

        latest = str(payload.get("tag_name") or "").strip().removeprefix("v")
        if not latest:
            raise UpdateError("La Release GitHub ne contient pas de version.")
        available = _version_tuple(latest) > _version_tuple(self.current_version)
        base = UpdateInfo(
            current_version=self.current_version,
            latest_version=latest,
            available=False,
            release_url=str(payload.get("html_url") or "") or None,
            notes=str(payload.get("body") or "")[:4000],
        )
        if not available:
            return base

        assets = _asset_map(payload)
        installer_name = f"NaviXav-Setup-{latest}.exe"
        installer = assets.get(installer_name)
        if installer is None:
            raise UpdateError(
                f"La Release {latest} ne contient pas {installer_name}."
            )
        installer_url = str(installer.get("browser_download_url") or "")
        size = int(installer.get("size") or 0)
        if (
            not installer_url.startswith(
                f"https://github.com/{GITHUB_REPOSITORY}/releases/download/"
            )
            or size <= 0
            or size > MAX_INSTALLER_BYTES
        ):
            raise UpdateError("L'installateur GitHub annoncé est invalide.")

        digest = _sha256_digest(installer.get("digest"))
        checksum = assets.get(f"{installer_name}.sha256")
        checksum_url = (
            str(checksum.get("browser_download_url") or "")
            if checksum is not None
            else None
        )
        if not digest and not checksum_url:
            raise UpdateError(
                "La Release ne fournit aucune empreinte SHA-256."
            )
        return UpdateInfo(
            current_version=self.current_version,
            latest_version=latest,
            available=True,
            installer_name=installer_name,
            installer_url=installer_url,
            installer_size=size,
            digest=digest,
            checksum_url=checksum_url,
            release_url=base.release_url,
            notes=base.notes,
        )

    def _expected_digest(self, update: UpdateInfo) -> str:
        if update.digest:
            return update.digest
        if not update.checksum_url:
            raise UpdateError("Empreinte SHA-256 absente.")
        try:
            response = self.session.get(
                update.checksum_url,
                headers=REQUEST_HEADERS,
                timeout=8,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise UpdateError(
                "Impossible de télécharger l'empreinte SHA-256."
            ) from exc
        digest = _sha256_digest(response.text.split()[0] if response.text else "")
        if not digest:
            raise UpdateError("Le fichier SHA-256 de la Release est invalide.")
        return digest

    def download(self, update: UpdateInfo) -> Path:
        if (
            not update.available
            or not update.installer_name
            or not update.installer_url
        ):
            raise UpdateError("Aucune mise à jour installable.")
        expected_digest = self._expected_digest(update)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        destination = self.download_dir / update.installer_name
        temporary = destination.with_suffix(".part")
        hasher = hashlib.sha256()
        received = 0
        try:
            with self.session.get(
                update.installer_url,
                headers=REQUEST_HEADERS,
                timeout=(8, 90),
                stream=True,
            ) as response:
                response.raise_for_status()
                with temporary.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        received += len(chunk)
                        if received > MAX_INSTALLER_BYTES:
                            raise UpdateError("L'installateur dépasse la taille autorisée.")
                        hasher.update(chunk)
                        output.write(chunk)
        except UpdateError:
            temporary.unlink(missing_ok=True)
            raise
        except (OSError, requests.RequestException):
            temporary.unlink(missing_ok=True)
            raise UpdateError(
                "Le téléchargement de la mise à jour a échoué."
            ) from None

        if update.installer_size and received != update.installer_size:
            temporary.unlink(missing_ok=True)
            raise UpdateError("Le téléchargement de l'installateur est incomplet.")
        if hasher.hexdigest() != expected_digest:
            temporary.unlink(missing_ok=True)
            raise UpdateError(
                "La vérification SHA-256 de l'installateur a échoué."
            )
        temporary.replace(destination)
        LOGGER.info(
            "Mise à jour %s téléchargée et vérifiée (%s octets)",
            update.latest_version,
            received,
        )
        return destination

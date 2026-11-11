"""Téléchargement du moteur vocal facultatif depuis l'application.

Qui a déjà installé NaviXav reçoit ses mises à jour par l'installateur en mode
silencieux : il reprend les choix d'origine et n'ajoutera jamais le moteur de
lui-même. Les Paramètres proposent donc de le télécharger : l'archive
`NaviXav-<version>-voice-engine.zip` de la Release GitHub de *cette* version
— le moteur porte des bibliothèques compilées pour son Python — vérifiée par
SHA-256 comme l'installateur, puis décompressée à côté de l'application.

Le travail se fait dans un fil à part ; l'interface en suit l'avancement.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import threading
import time
import zipfile
from pathlib import Path

import requests

from navixav.paths import user_data_path
from navixav.updater import GITHUB_REPOSITORY, REQUEST_HEADERS, _asset_map, _sha256_digest

LOGGER = logging.getLogger(__name__)
MAX_ENGINE_BYTES = 400 * 1024 * 1024
FOLDER = "voice_engine"
# Mode de test : une archive locale, construite comme celle de la Release, à
# la place du téléchargement GitHub. Il ne s'active que si cette variable est
# posée (scripts/test_voice_engine.ps1) ; une version publiée ne la pose pas.
TEST_ARCHIVE_VARIABLE = "NAVIXAV_VOICE_ENGINE_ARCHIVE"
# Renommage retenté pendant une trentaine de secondes avant de copier.
RENAME_ATTEMPTS = 15
RENAME_PAUSE_S = 2.0


def _writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".navixav-write-test"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


class VoiceEngineInstaller:
    def __init__(self, version: str, target: Path, *, session: requests.Session | None = None) -> None:
        self.version = version
        self._preferred = target
        self.target = target
        self.session = session or requests.Session()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._state = {"state": "idle", "received": 0, "size": 0, "error": ""}

    def status(self) -> dict[str, object]:
        with self._lock:
            return dict(self._state)

    def _set(self, **values: object) -> None:
        with self._lock:
            self._state.update(values)

    def start(self) -> bool:
        """Lance le téléchargement ; faux s'il est déjà en cours."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False
            self._state = {"state": "downloading", "received": 0, "size": 0, "error": ""}
            # À côté de l'application si elle est inscriptible (installation
            # par utilisateur, cas par défaut), sinon dans le dossier de données.
            self.target = self._preferred if _writable(self._preferred.parent) else user_data_path(FOLDER)
            self._thread = threading.Thread(target=self._run, name="voice-engine-install", daemon=True)
            self._thread.start()
            return True

    # ------------------------------------------------------------------ #

    def _asset(self) -> tuple[str, int, str]:
        """URL, taille et empreinte SHA-256 de l'archive de cette version."""
        name = f"NaviXav-{self.version}-voice-engine.zip"
        response = self.session.get(
            f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/tags/v{self.version}",
            headers=REQUEST_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        assets = _asset_map(response.json())
        asset = assets.get(name)
        if asset is None:
            raise RuntimeError("archive absente de la Release")
        url = str(asset.get("browser_download_url") or "")
        size = int(asset.get("size") or 0)
        if not url.startswith(f"https://github.com/{GITHUB_REPOSITORY}/releases/download/") \
                or not 0 < size <= MAX_ENGINE_BYTES:
            raise RuntimeError("archive annoncée invalide")
        digest = _sha256_digest(asset.get("digest"))
        if not digest and (checksum := assets.get(f"{name}.sha256")):
            text = self.session.get(
                str(checksum.get("browser_download_url")), headers=REQUEST_HEADERS, timeout=10
            ).text
            digest = _sha256_digest(text.split()[0] if text else "")
        if not digest:
            raise RuntimeError("empreinte SHA-256 absente")
        return url, size, digest

    def _local_asset(self, archive: Path) -> tuple[Path, int, str]:
        """Archive de test : son empreinte vient du fichier .sha256 voisin,
        exactement comme sur la Release."""
        checksum = archive.with_name(archive.name + ".sha256")
        if not archive.is_file() or not checksum.is_file():
            raise RuntimeError("archive de test ou son fichier .sha256 introuvable")
        digest = _sha256_digest(checksum.read_text(encoding="ascii").split()[0])
        if not digest:
            raise RuntimeError("fichier .sha256 de test invalide")
        return archive, archive.stat().st_size, digest

    def _chunks(self, source: str | Path):
        """Blocs de l'archive, depuis GitHub ou depuis le fichier de test."""
        if isinstance(source, Path):
            with source.open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    # Rythme d'un vrai téléchargement, pour voir la progression.
                    time.sleep(0.02)
                    yield chunk
            return
        with self.session.get(source, headers=REQUEST_HEADERS, timeout=(10, 120), stream=True) as response:
            response.raise_for_status()
            yield from response.iter_content(chunk_size=1024 * 1024)

    def _run(self) -> None:
        download = user_data_path("updates", f"NaviXav-{self.version}-voice-engine.zip.part")
        try:
            test_archive = os.environ.get(TEST_ARCHIVE_VARIABLE, "").strip()
            if test_archive:
                LOGGER.info("Moteur vocal : mode de test, archive locale %s", test_archive)
                source, size, digest = self._local_asset(Path(test_archive))
            else:
                source, size, digest = self._asset()
            self._set(size=size)
            download.parent.mkdir(parents=True, exist_ok=True)
            hasher = hashlib.sha256()
            received = 0
            with download.open("wb") as output:
                for chunk in self._chunks(source):
                    if not chunk:
                        continue
                    received += len(chunk)
                    if received > MAX_ENGINE_BYTES:
                        raise RuntimeError("archive trop volumineuse")
                    hasher.update(chunk)
                    output.write(chunk)
                    self._set(received=received)
            if received != size or hasher.hexdigest() != digest:
                raise RuntimeError("vérification SHA-256 échouée")
            self._set(state="installing")
            self._extract(download)
            self._set(state="done")
            LOGGER.info("Moteur vocal de la tour installé dans %s", self.target)
        except Exception as exc:  # noqa: BLE001 - l'état porte l'échec à l'interface
            LOGGER.warning("Installation du moteur vocal impossible : %s", exc)
            self._set(state="error", error=str(exc))
        finally:
            download.unlink(missing_ok=True)

    def _extract(self, archive: Path) -> None:
        """Décompresse dans un dossier voisin puis remplace l'ancien d'un coup."""
        staging = self.target.with_name(self.target.name + ".new")
        shutil.rmtree(staging, ignore_errors=True)
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                parts = Path(member.filename).parts
                # Archive attendue : tout sous voice_engine/, aucun chemin qui
                # sorte du dossier (« .. » ou chemin absolu).
                if not parts or parts[0] != FOLDER or ".." in parts or Path(member.filename).is_absolute():
                    raise RuntimeError("archive au contenu inattendu")
                relative = Path(*parts[1:]) if len(parts) > 1 else None
                if relative is None or member.is_dir():
                    continue
                destination = staging / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
        if not (staging / "espeak" / "espeak-ng.exe").is_file():
            shutil.rmtree(staging, ignore_errors=True)
            raise RuntimeError("archive incomplète")
        shutil.rmtree(self.target, ignore_errors=True)
        self._move_into_place(staging)

    def _move_into_place(self, staging: Path) -> None:
        """Met le dossier décompressé à sa place, malgré l'antivirus.

        Relevé sur Windows : l'antivirus analyse les exécutables fraîchement
        écrits (espeak-ng.exe, les DLL d'onnxruntime) et verrouille quelques
        secondes leur dossier ; le renommer échoue alors par « Accès refusé ».
        Le renommage est retenté, puis, s'il reste refusé, les fichiers sont
        copiés à leur place — une copie ne demande que la lecture, que
        l'analyse laisse passer.
        """
        for attempt in range(RENAME_ATTEMPTS):
            try:
                staging.replace(self.target)
                return
            except PermissionError:
                time.sleep(RENAME_PAUSE_S)
        LOGGER.info("Dossier du moteur verrouillé, copie à la place du renommage")
        shutil.copytree(staging, self.target, dirs_exist_ok=True)
        shutil.rmtree(staging, ignore_errors=True)

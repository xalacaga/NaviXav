"""Téléchargement de la voix naturelle depuis les Paramètres, en mode test local."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

import navixav.voice_engine_installer as installer_module
from navixav.voice_engine_installer import TEST_ARCHIVE_VARIABLE, VoiceEngineInstaller


def make_archive(folder: Path, entries: dict[str, bytes], *, digest: str | None = None) -> Path:
    archive = folder / "NaviXav-9.9.9-voice-engine.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for name, data in entries.items():
            bundle.writestr(name, data)
    real = hashlib.sha256(archive.read_bytes()).hexdigest().upper()
    (folder / (archive.name + ".sha256")).write_text(f"{digest or real}  {archive.name}", encoding="ascii")
    return archive


@pytest.fixture
def run(monkeypatch, tmp_path):
    monkeypatch.setattr(installer_module, "user_data_path", lambda *parts: tmp_path.joinpath("data", *parts))
    monkeypatch.setattr(installer_module.time, "sleep", lambda _seconds: None)

    def go(archive: Path) -> tuple[VoiceEngineInstaller, Path]:
        monkeypatch.setenv(TEST_ARCHIVE_VARIABLE, str(archive))
        target = tmp_path / "app" / "voice_engine"
        target.parent.mkdir()
        installer = VoiceEngineInstaller("9.9.9", target)
        installer.target = target
        installer._run()
        return installer, target

    return go


def test_a_verified_archive_is_installed_beside_the_application(run, tmp_path):
    archive = make_archive(tmp_path, {
        "voice_engine/espeak/espeak-ng.exe": b"exe",
        "voice_engine/model/vocab.json": b"{}",
    })
    installer, target = run(archive)
    assert installer.status()["state"] == "done"
    assert (target / "espeak" / "espeak-ng.exe").read_bytes() == b"exe"
    assert installer.status()["received"] == archive.stat().st_size


def test_a_wrong_checksum_installs_nothing(run, tmp_path):
    archive = make_archive(tmp_path, {"voice_engine/espeak/espeak-ng.exe": b"exe"}, digest="0" * 64)
    installer, target = run(archive)
    assert installer.status()["state"] == "error"
    assert "SHA-256" in installer.status()["error"]
    assert not target.exists()


def test_an_archive_escaping_its_folder_is_refused(run, tmp_path):
    archive = make_archive(tmp_path, {"voice_engine/../../evil.exe": b"x"})
    installer, _target = run(archive)
    assert installer.status()["state"] == "error"
    assert not (tmp_path / "evil.exe").exists()


def test_an_archive_without_espeak_is_incomplete(run, tmp_path):
    archive = make_archive(tmp_path, {"voice_engine/model/vocab.json": b"{}"})
    installer, target = run(archive)
    assert installer.status()["error"] == "archive incomplète"
    assert not target.exists()


def test_a_folder_locked_by_the_antivirus_is_copied_into_place(run, tmp_path, monkeypatch):
    """Relevé réel : « Accès refusé » au renommage, l'antivirus analysant les .exe."""
    original = Path.replace

    def locked(self, target):
        if self.name.endswith(".new"):
            raise PermissionError(5, "Accès refusé")
        return original(self, target)

    monkeypatch.setattr(Path, "replace", locked)
    monkeypatch.setattr(installer_module, "RENAME_PAUSE_S", 0)
    archive = make_archive(tmp_path, {"voice_engine/espeak/espeak-ng.exe": b"exe"})
    installer, target = run(archive)
    assert installer.status()["state"] == "done"
    assert (target / "espeak" / "espeak-ng.exe").read_bytes() == b"exe"
    assert not target.with_name("voice_engine.new").exists()

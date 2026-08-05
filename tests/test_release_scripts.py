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

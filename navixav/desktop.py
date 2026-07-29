"""Point d'entrée Windows de l'application distribuable NaviXav."""

from __future__ import annotations

import argparse
import ctypes
import json
import logging
import multiprocessing
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path

from navixav import __version__
from navixav.config import Settings, load_user_settings
from navixav.logging_setup import configure_logging
from navixav.paths import resource_path, user_data_path
from navixav.web.app import create_server, serve

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
LAST_PORT = 8775
WEBVIEW2_CLIENT_ID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
APP_USER_MODEL_ID = "Galvo.NaviXav"
SUPPORT_URL = "https://buymeacoffee.com/xalacaga"


def _show_error(message: str) -> None:
    """Affiche une erreur même lorsque l'exécutable n'a pas de console."""
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(  # type: ignore[attr-defined]
            0, message, "NaviXav", 0x10
        )
    else:  # pragma: no cover - point d'entrée destiné à Windows
        print(message, file=sys.stderr)


def _show_info(message: str) -> None:
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(  # type: ignore[attr-defined]
            0, message, "NaviXav", 0x40
        )
    else:  # pragma: no cover
        print(message)


def _configure_logging() -> Path:
    return configure_logging()


def _configure_windows_app_identity() -> None:
    """Associe la fenêtre et la barre des tâches à l'application NaviXav."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
            APP_USER_MODEL_ID
        )
    except Exception:
        logging.warning("Impossible de définir l'identité Windows NaviXav")


def _webview2_version() -> str | None:
    if sys.platform != "win32":
        return None
    import winreg

    candidates = (
        (
            winreg.HKEY_LOCAL_MACHINE,
            rf"Software\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_CLIENT_ID}",
            winreg.KEY_READ | winreg.KEY_WOW64_32KEY,
        ),
        (
            winreg.HKEY_CURRENT_USER,
            rf"Software\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_CLIENT_ID}",
            winreg.KEY_READ,
        ),
    )
    for root, path, access in candidates:
        try:
            with winreg.OpenKey(root, path, 0, access) as key:
                version = str(winreg.QueryValueEx(key, "pv")[0]).strip()
        except OSError:
            continue
        if version and version != "0.0.0.0":
            return version
    return None


def _running_navixav(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://{HOST}:{port}/api/status", timeout=0.8
        ) as response:
            payload = json.load(response)
        return isinstance(payload, dict) and bool(payload.get("version"))
    except Exception:
        return False


def _port_available(port: int, host: str = HOST) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def _select_port(preferred: int, bind_host: str = HOST) -> tuple[int, bool]:
    """Retourne le port et indique si une instance NaviXav l'utilise déjà."""
    if _running_navixav(preferred):
        return preferred, True
    candidates = [preferred, *range(DEFAULT_PORT, LAST_PORT + 1)]
    for port in dict.fromkeys(candidates):
        if _port_available(port, bind_host):
            return port, False
    raise RuntimeError(
        f"Aucun port local libre entre {DEFAULT_PORT} et {LAST_PORT}. "
        "Ferme l'ancienne instance de NaviXav ou l'application qui les utilise."
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="NaviXav")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="mode serveur sans fenêtre, réservé au diagnostic",
    )
    return parser


def _wait_until_ready(url: str, timeout_s: float = 12.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _running_navixav(int(url.rsplit(":", 1)[1])):
            return
        time.sleep(0.1)
    raise RuntimeError("Le service local NaviXav n'a pas démarré à temps.")


def _run_desktop_window(url: str, server: object) -> None:
    if sys.platform == "win32" and _webview2_version() is None:
        raise RuntimeError(
            "Microsoft WebView2 Runtime est absent. Relance l'installateur "
            "NaviXav : il installera automatiquement ce prérequis."
        )
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError(
            "Le composant d'interface pywebview est absent. "
            "Réinstalle NaviXav avec l'installateur officiel."
        ) from exc

    server_thread = threading.Thread(
        target=server.run,
        name="NaviXav-local-server",
        daemon=False,
    )
    server_thread.start()
    try:
        _wait_until_ready(url)
        window = webview.create_window(
            "NaviXav",
            url,
            width=1500,
            height=920,
            min_size=(720, 560),
            background_color="#07111f",
            text_select=True,
            confirm_close=False,
        )

        def stop_server() -> None:
            server.should_exit = True

        def stop_from_interface() -> None:
            """Ferme d'abord la fenêtre pour interrompre ses requêtes périodiques."""
            server.should_exit = True
            try:
                window.destroy()
            except Exception:
                pass

        def install_update(installer: Path) -> None:
            """Lance l'installateur vérifié, puis ferme l'instance courante."""
            def launch() -> None:
                try:
                    flags = (
                        subprocess.CREATE_NEW_PROCESS_GROUP
                        | subprocess.DETACHED_PROCESS
                    )
                    subprocess.Popen(
                        [
                            str(installer),
                            "/SILENT",
                            "/SP-",
                            "/CLOSEAPPLICATIONS",
                            "/RESTARTAPPLICATIONS",
                        ],
                        close_fds=True,
                        creationflags=flags,
                    )
                    logging.info(
                        "Installateur de mise à jour lancé : %s",
                        installer.name,
                    )
                    stop_from_interface()
                except Exception:
                    logging.exception(
                        "Impossible de lancer l'installateur de mise à jour"
                    )

            # Laisse le temps à la réponse HTTP d'atteindre l'interface.
            threading.Timer(0.8, launch).start()

        def open_simbrief() -> None:
            """Ouvre l'éditeur SimBrief uniquement après une action explicite."""
            webbrowser.open("https://dispatch.simbrief.com/options/new", new=2)

        def open_support() -> None:
            """Ouvre la page de soutien uniquement après une action explicite."""
            webbrowser.open(SUPPORT_URL, new=2)

        def close_window_when_server_stops() -> None:
            server_thread.join()
            try:
                window.destroy()
            except Exception:
                pass

        window.events.closed += stop_server
        server.config.app.state.request_shutdown = stop_from_interface
        server.config.app.state.request_update_install = install_update
        server.config.app.state.request_open_simbrief = open_simbrief
        server.config.app.state.request_open_support = open_support
        watcher = threading.Thread(
            target=close_window_when_server_stops,
            name="NaviXav-window-watcher",
            daemon=True,
        )
        watcher.start()
        webview.start(
            gui="edgechromium",
            debug=False,
            private_mode=False,
            storage_path=str(user_data_path("webview")),
            icon=str(resource_path("assets", "navixav.ico")),
        )
        logging.info("Boucle de fenêtre WebView2 terminée")
    finally:
        server.should_exit = True
        server_thread.join(timeout=3)
        if server_thread.is_alive():
            logging.warning("Arrêt forcé du serveur local après 3 secondes")
            server.force_exit = True
            server_thread.join(timeout=2)
        logging.info(
            "Threads restants : %s",
            ", ".join(
                f"{thread.name}(daemon={thread.daemon})"
                for thread in threading.enumerate()
            ),
        )


def main(argv: list[str] | None = None) -> int:
    multiprocessing.freeze_support()
    args = _parser().parse_args(argv)
    log_file = _configure_logging()
    _configure_windows_app_identity()
    try:
        settings = load_user_settings(Settings.load())
        bind_host = "0.0.0.0" if settings.lan_enabled else HOST
        port, already_running = _select_port(args.port, bind_host)
        url = f"http://{HOST}:{port}"
        if already_running:
            if not args.no_open:
                _show_info("NaviXav est déjà ouvert.")
            return 0

        logging.info("Démarrage de NaviXav %s sur %s", __version__, url)
        if args.no_open:
            serve(host=bind_host, port=port, settings=settings)
        else:
            server = create_server(host=bind_host, port=port, settings=settings)
            _run_desktop_window(url, server)
        logging.info("Arrêt normal, port %s libéré", port)
        if not args.no_open and sys.platform == "win32":
            # FastAPI/AnyIO peut conserver quelques workers non-daemon après
            # la fin de sa boucle. À ce stade la fenêtre, Uvicorn, SimConnect
            # et les sessions HTTP sont déjà fermés : on termine le processus
            # hôte afin de ne jamais laisser une instance fantôme.
            logging.shutdown()
            os._exit(0)
        return 0
    except Exception as exc:  # noqa: BLE001 - dernier rempart de l'application
        logging.critical("Erreur fatale\n%s", traceback.format_exc())
        _show_error(
            f"NaviXav n'a pas pu démarrer.\n\n{exc}\n\n"
            f"Journal : {log_file}"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

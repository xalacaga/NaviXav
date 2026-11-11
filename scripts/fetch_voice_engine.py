"""Construit le moteur vocal facultatif de la tour : dossier `voice_engine/`.

Le moteur n'est pas dans l'application de base : c'est une option de
l'installateur. Le dossier réunit tout ce qu'il faut pour synthétiser les
messages de la tour en direct, hors ligne :

    voice_engine/
      model/       Kokoro-82M (int8, Apache 2.0), deux voix, vocabulaire
      espeak/      eSpeak NG (GPL v3), programme séparé : texte -> phonèmes
      python/      onnxruntime et numpy, chargés par NaviXav s'il trouve le dossier
      licenses/    textes des licences et provenance des sources
      VERSION.json

eSpeak NG est livré et appelé comme un programme distinct (espeak-ng.exe),
jamais chargé dans le processus de NaviXav : la GPL reste à ce programme.

Chaque téléchargement est vérifié par SHA-256. Usage :

    python scripts/fetch_voice_engine.py [--out voice_engine]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ESPEAK_VERSION = "1.52.0"
ESPEAK_MSI = (
    f"https://github.com/espeak-ng/espeak-ng/releases/download/{ESPEAK_VERSION}/espeak-ng.msi",
    "7F673C709EA5DD579D3B5EBB98688CC575328A6AB7438D2BC405B88CEDAEAFB9",
)
ESPEAK_SOURCE = f"https://github.com/espeak-ng/espeak-ng/archive/refs/tags/{ESPEAK_VERSION}.tar.gz"
KOKORO_MODEL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx",
    "6E742170D309016E5891A994E1CE1559C702A2CCD0075E67EF7157974F6406CB",
)
KOKORO_VOICES = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
    None,  # vérifié par son contenu : les deux voix retenues doivent y être
)
# Vocabulaire phonème -> jeton de Kokoro v1.0 (hexgrad/Kokoro-82M, config.json).
KOKORO_CONFIG = (
    "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/config.json",
    None,
)
sys.path.insert(0, str(ROOT))
from navixav.tower_phraseology import ENGINE_VOICES  # noqa: E402

# Voix des personnages de la radio et de l'interphone : délivrance, sol, tour,
# chef de cabine, mécanicien au casque. Les autres voix Kokoro sont retirées.
VOICES = tuple(ENGINE_VOICES)
# Seules ces langues sont parlées par la tour : le reste des dictionnaires
# eSpeak est retiré (une vingtaine de Mo).
ESPEAK_LANGUAGES = ("en", "fr")
PYTHON_PACKAGES = ("onnxruntime>=1.20,<2", "numpy>=1.26,<3")


def download(url: str, sha256: str | None) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    if sha256:
        digest = hashlib.sha256(data).hexdigest().upper()
        if digest != sha256:
            raise SystemExit(f"Somme SHA-256 inattendue pour {url} : {digest}")
    return data


def build_espeak(target: Path) -> None:
    with tempfile.TemporaryDirectory() as temp:
        msi = Path(temp) / "espeak-ng.msi"
        msi.write_bytes(download(*ESPEAK_MSI))
        extract = Path(temp) / "x"
        # Installation administrative : extrait les fichiers sans rien
        # installer sur le système.
        subprocess.run(["msiexec", "/a", str(msi), "/qn", f"TARGETDIR={extract}"], check=True)
        source = next(extract.rglob("espeak-ng.exe")).parent
        target.mkdir(parents=True, exist_ok=True)
        for name in ("espeak-ng.exe", "libespeak-ng.dll"):
            shutil.copy2(source / name, target / name)
        data = source / "espeak-ng-data"
        out = target / "espeak-ng-data"
        out.mkdir()
        for item in data.iterdir():
            # Dictionnaires des autres langues : inutiles à la tour.
            if item.is_file() and item.name.endswith("_dict") and item.name.split("_")[0] not in ESPEAK_LANGUAGES:
                continue
            if item.is_dir():
                shutil.copytree(item, out / item.name, dirs_exist_ok=True)
            else:
                shutil.copy2(item, out / item.name)


def build_model(target: Path) -> None:
    import numpy as np

    target.mkdir(parents=True, exist_ok=True)
    (target / "kokoro-v1.0.int8.onnx").write_bytes(download(*KOKORO_MODEL))
    voices = np.load(io.BytesIO(download(*KOKORO_VOICES)))
    missing = [name for name in VOICES if name not in voices.files]
    if missing:
        raise SystemExit(f"Voix absentes du fichier Kokoro : {missing}")
    np.savez(target / "voices.npz", **{name: voices[name] for name in VOICES})
    config = json.loads(download(*KOKORO_CONFIG))
    (target / "vocab.json").write_text(
        json.dumps(config["vocab"], ensure_ascii=False), encoding="utf-8"
    )


def build_python(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--quiet",
         "--only-binary=:all:", "--target", str(target), *PYTHON_PACKAGES],
        check=True,
    )
    # Ce qui ne sert qu'aux développeurs de ces bibliothèques : tests, outils
    # de conversion et de quantification des modèles, scripts f2py.
    for relative in ("numpy/_core/tests", "numpy/tests", "numpy/f2py", "numpy/testing",
                     "onnxruntime/transformers", "onnxruntime/tools", "onnxruntime/quantization",
                     "onnxruntime/datasets", "bin"):
        shutil.rmtree(target / relative, ignore_errors=True)
    for tests in list(target.glob("numpy/**/tests")):
        shutil.rmtree(tests, ignore_errors=True)


def write_licenses(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    gpl = download("https://www.gnu.org/licenses/gpl-3.0.txt", None)
    (target / "eSpeak-NG-GPL-3.0.txt").write_bytes(gpl)
    apache = download("https://www.apache.org/licenses/LICENSE-2.0.txt", None)
    (target / "Kokoro-82M-Apache-2.0.txt").write_bytes(apache)
    (target / "SOURCES.txt").write_text(
        "Composants du moteur vocal facultatif de NaviXav\n"
        "================================================\n\n"
        f"eSpeak NG {ESPEAK_VERSION} - GNU General Public License v3 (eSpeak-NG-GPL-3.0.txt)\n"
        "  Livré comme programme séparé (espeak-ng.exe), appelé par NaviXav pour\n"
        "  convertir le texte en phonèmes. Il n'est pas lié à NaviXav.\n"
        "  Binaires : distribution Windows officielle, " + ESPEAK_MSI[0] + "\n"
        "  Code source correspondant : " + ESPEAK_SOURCE + "\n"
        "  Seuls les dictionnaires anglais et français sont conservés.\n\n"
        "Kokoro-82M v1.0 (int8) - Apache License 2.0 (Kokoro-82M-Apache-2.0.txt)\n"
        "  https://huggingface.co/hexgrad/Kokoro-82M\n"
        "  Export ONNX : https://github.com/thewh1teagle/kokoro-onnx (MIT)\n"
        "  La voix française ff_siwis est dérivée de la base SIWIS (CC BY 4.0).\n\n"
        "onnxruntime - MIT ; numpy - BSD 3-Clause : licences dans python/*.dist-info.\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "voice_engine")
    args = parser.parse_args(argv)
    out: Path = args.out
    if out.exists():
        shutil.rmtree(out)
    build_espeak(out / "espeak")
    build_model(out / "model")
    build_python(out / "python")
    write_licenses(out / "licenses")
    (out / "VERSION.json").write_text(json.dumps({
        "espeak_ng": ESPEAK_VERSION,
        "kokoro": "v1.0-int8",
        "voices": list(VOICES),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
    }, indent=1) + "\n", encoding="utf-8")
    size = sum(path.stat().st_size for path in out.rglob("*") if path.is_file())
    print(f"Moteur vocal prêt : {out} ({size / 1024 / 1024:.0f} Mo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

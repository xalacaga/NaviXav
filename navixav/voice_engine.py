"""Moteur vocal facultatif : synthèse en direct des messages de la tour.

Le moteur n'est présent que si l'utilisateur l'a choisi à l'installation :
un dossier `voice_engine/` à côté de l'application (voir
scripts/fetch_voice_engine.py). Sans lui, NaviXav garde ses voix
pré-enregistrées et rien ne change.

Deux étapes, comme kokoro-onnx, sans en dépendre :

1. eSpeak NG convertit le texte en phonèmes. Il tourne comme un programme
   séparé (espeak-ng.exe) et n'est jamais chargé dans ce processus : sa licence
   GPL reste la sienne. Chaque clause est convertie à part puis sa ponctuation
   remise, ce qui reproduit à l'identique ce que kokoro-onnx obtient de
   phonemizer (vérifié en anglais et en français).
2. Kokoro-82M, modèle ONNX, transforme les phonèmes en voix.

onnxruntime et numpy voyagent dans le dossier du moteur et ne sont importés
qu'à la première synthèse, sous verrou : l'application de base ne les embarque
pas et ne paie leur chargement que si la tour parle.
"""

from __future__ import annotations

import importlib
import io
import json
import logging
import re
import subprocess
import sys
import tempfile
import threading
import wave
from collections import OrderedDict
from pathlib import Path

from navixav.paths import is_frozen, resource_root, user_data_path

LOGGER = logging.getLogger(__name__)
SAMPLE_RATE = 24000
MAX_TOKENS = 510
_PUNCTUATION = re.compile(r"([,.;:!?])")
_CACHE_SIZE = 32
# Une fenêtre de console par appel d'espeak-ng serait visible : jamais.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def default_engine_root() -> Path:
    """Où le moteur s'installe : à côté de l'exécutable, à la racine en développement."""
    if is_frozen():
        return Path(sys.executable).resolve().parent / "voice_engine"
    return resource_root() / "voice_engine"


def engine_root() -> Path:
    """Dossier du moteur s'il existe ; à défaut, celui où il s'installerait.

    Une installation dans un dossier protégé (Program Files) ne permet pas de
    le télécharger à côté de l'application : il va alors dans le dossier de
    données de l'utilisateur, qui est consulté aussi.
    """
    candidates = (default_engine_root(), user_data_path("voice_engine"))
    for candidate in candidates:
        if (candidate / "espeak" / "espeak-ng.exe").is_file():
            return candidate
    return candidates[0]


class VoiceEngine:
    def __init__(self, root: Path | None = None) -> None:
        self._fixed_root = root
        self.root = root or engine_root()
        self._lock = threading.Lock()
        self._session = None
        self._np = None
        self._voices = None
        self._vocab: dict[str, int] = {}
        self._inputs: dict[str, object] = {}
        self._cache: OrderedDict[tuple, bytes] = OrderedDict()

    # ------------------------------------------------------------------ #

    @property
    def espeak(self) -> Path:
        return self.root / "espeak" / "espeak-ng.exe"

    def available(self) -> bool:
        """Vrai si le moteur a été installé : ses fichiers essentiels sont là.

        Le dossier est recherché à chaque fois tant que le moteur n'est pas
        chargé : un téléchargement depuis les Paramètres prend effet sans
        relancer NaviXav.
        """
        if self._session is None and self._fixed_root is None:
            self.root = engine_root()
        return all(path.is_file() for path in (
            self.espeak,
            self.root / "model" / "kokoro-v1.0.int8.onnx",
            self.root / "model" / "voices.npz",
            self.root / "model" / "vocab.json",
        ))

    def _load(self) -> None:
        if self._session is not None:
            return
        python = str(self.root / "python")
        if python not in sys.path:
            sys.path.insert(0, python)
        # Imports dynamiques : PyInstaller ne doit pas embarquer ces paquets
        # dans l'application de base, ils viennent du dossier du moteur.
        np = importlib.import_module("numpy")
        onnxruntime = importlib.import_module("onnxruntime")
        options = onnxruntime.SessionOptions()
        # Deux cœurs suffisent : la tour ne doit pas disputer le processeur au
        # simulateur pour une phrase de quelques secondes.
        options.intra_op_num_threads = 2
        session = onnxruntime.InferenceSession(
            str(self.root / "model" / "kokoro-v1.0.int8.onnx"),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        types = {"tensor(float)": np.float32, "tensor(int64)": np.int64, "tensor(int32)": np.int32}
        self._inputs = {item.name: types.get(item.type, np.float32) for item in session.get_inputs()}
        self._voices = np.load(self.root / "model" / "voices.npz")
        self._vocab = json.loads((self.root / "model" / "vocab.json").read_text(encoding="utf-8"))
        self._np = np
        self._session = session
        LOGGER.info("Moteur vocal de la tour chargé")

    # ------------------------------------------------------------------ #

    def phonemize(self, text: str, language: str) -> str:
        """Texte -> phonèmes IPA, clause par clause, ponctuation conservée."""
        out: list[str] = []
        for piece in _PUNCTUATION.split(text):
            if not piece.strip():
                continue
            if _PUNCTUATION.fullmatch(piece):
                if out:
                    out[-1] += piece
                continue
            out.append(self._espeak_ipa(piece.strip(), language))
        return " ".join(out)

    def _espeak_ipa(self, text: str, language: str) -> str:
        """Une clause par appel, lue dans un fichier UTF-8.

        Relevé sur Windows : en argument, la page de code mange les caractères
        hors ANSI (« nœuds » perdait son « œ ») ; par l'entrée standard,
        espeak-ng restait parfois bloqué. Le fichier n'a aucun des deux défauts.
        """
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False)
        try:
            with handle:
                handle.write(text)
            result = subprocess.run(
                [str(self.espeak), f"--path={self.espeak.parent}", "-q", "-v", language,
                 "--ipa", "-f", handle.name],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                check=True,
                timeout=10,
                creationflags=_NO_WINDOW,
            )
        finally:
            Path(handle.name).unlink(missing_ok=True)
        return " ".join(result.stdout.decode("utf-8").split())

    def synthesize(self, text: str, language: str, voice: str, speed: float = 1.0) -> bytes:
        """Une phrase entière en WAV 24 kHz mono, mise en cache."""
        key = (text, language, voice, round(speed, 3))
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            self._load()
            np = self._np
            phonemes = self.phonemize(text, language)
            tokens = [self._vocab[p] for p in phonemes if p in self._vocab][:MAX_TOKENS]
            if not tokens:
                raise ValueError("Aucun phonème synthétisable.")
            style = self._voices[voice][len(tokens) - 1]
            token_input = "input_ids" if "input_ids" in self._inputs else "tokens"
            inputs = {
                token_input: np.array([[0, *tokens, 0]], dtype=self._inputs[token_input]),
                "style": np.asarray(style, dtype=self._inputs.get("style", np.float32)),
                "speed": np.array([speed], dtype=self._inputs.get("speed", np.float32)),
            }
            audio = np.asarray(self._session.run(None, inputs)[0], dtype=np.float32).ravel()
            data = _wav(_trim(np, audio), np)
            self._cache[key] = data
            if len(self._cache) > _CACHE_SIZE:
                self._cache.popitem(last=False)
            return data


def _trim(np, audio):
    """Silences de tête et de queue retirés, quelques ms gardées pour l'attaque."""
    level = np.abs(audio)
    loud = np.flatnonzero(level > max(0.01, float(level.max()) * 0.02))
    if loud.size:
        pad = int(0.03 * SAMPLE_RATE)
        audio = audio[max(0, loud[0] - pad): loud[-1] + pad]
    peak = float(np.abs(audio).max()) or 1.0
    return audio * (0.89 / peak)


def _wav(audio, np) -> bytes:
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm)
    return buffer.getvalue()

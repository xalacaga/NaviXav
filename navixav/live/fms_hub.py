"""Le FMS de l'avion, quel que soit l'avion : un point d'entrée, plusieurs connecteurs.

Chaque connecteur sait s'il a quelque chose à dire — passerelle Fenix,
SimBridge FlyByWire, diffusion CDU PMDG — et rend le même format, plus ou
moins rempli : le Fenix donne le plan complet, les autres l'écran du MCDU et
parfois la phase. L'interface ne connaît que ``/api/fms`` ; ajouter un avion,
c'est ajouter un connecteur ici.

Le premier connecteur disponible l'emporte : deux avions ne volent pas en
même temps, et chacun sonde son canal à son rythme quand il est absent.
"""

from __future__ import annotations

from typing import Any, Callable

from navixav.live.fbw_fms import FbwFmsReader
from navixav.live.fenix_fms import FenixFmsReader
from navixav.live.pmdg_fms import PmdgFmsReader

Reader = Callable[[], dict[str, Any]]


class FmsHub:
    def __init__(self, readers: list[Any] | None = None) -> None:
        self._readers = readers if readers is not None else [
            FenixFmsReader(), FbwFmsReader(), PmdgFmsReader(),
        ]

    def read(self) -> dict[str, Any]:
        reasons: dict[str, str] = {}
        for reader in self._readers:
            state = reader.read()
            if state.get("available"):
                return state
            reasons[str(state.get("source", "?"))] = str(state.get("reason", ""))
        return {"available": False, "sources": reasons}

    def close(self) -> None:
        for reader in self._readers:
            close = getattr(reader, "close", None)
            if close is not None:
                close()

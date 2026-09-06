"""Choix du jeu de modèles injecté.

Le réglage désigne FSLTL ou AIG, jamais les deux : deux bibliothèques
sollicitées dans le même vol se marcheraient dessus, et un appareil changerait
de livrée selon celle qui répond la première. Un vol, un jeu de modèles.

Les deux détections sont en revanche toujours faites — elles coûtent un
parcours de dossier, et l'interface doit pouvoir dire à l'utilisateur ce qu'il
a réellement sur le disque, y compris le jeu qu'il n'a pas choisi.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from navixav.traffic.aig import AigInstallation, AigModelIndex, detect_aig
from navixav.traffic.base import InstallationStatus, ModelIndex
from navixav.traffic.fsltl import FsltlInstallation, FsltlModelIndex, detect_fsltl

CHOICES = ("fsltl", "aig")
DEFAULT_CHOICE = "fsltl"


def normalise_choice(value: str) -> str:
    choice = str(value or "").strip().casefold()
    return choice if choice in CHOICES else DEFAULT_CHOICE


@dataclass(frozen=True)
class ModelSetup:
    """Les deux détections, et celle que le réglage retient.

    Se présente au service comme une installation unique : c'est le statut du
    jeu choisi qui autorise ou non l'injection, et sa raison qui l'explique
    quand elle reste éteinte.
    """

    choice: str
    fsltl: FsltlInstallation
    aig: AigInstallation

    @property
    def selected(self) -> FsltlInstallation | AigInstallation:
        return self.aig if self.choice == "aig" else self.fsltl

    @property
    def label(self) -> str:
        return "AIG" if self.choice == "aig" else "FSLTL"

    @property
    def status(self) -> InstallationStatus:
        return self.selected.status

    @property
    def reason(self) -> str:
        return self.selected.reason

    @property
    def config_count(self) -> int:
        return self.selected.config_count

    @property
    def version(self) -> str:
        if self.status is not InstallationStatus.DETECTED:
            return ""
        return f"{self.label} {self.selected.version}".strip()

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "detected": self.status is InstallationStatus.DETECTED,
            "choice": self.choice,
            "version": self.version,
            "reason": self.reason,
            "models": self.config_count,
            "vmr": bool(self.selected.to_dict().get("vmr")),
            "sets": {"fsltl": self.fsltl.to_dict(), "aig": self.aig.to_dict()},
        }


def detect_models(
    choice: str,
    folders: Iterable[Path] | None = None,
    *,
    fsltl_path: Path | None = None,
    aig_path: Path | None = None,
) -> ModelSetup:
    """Relève les deux jeux sur le disque, sans rien y modifier."""
    folders = list(folders) if folders is not None else None
    return ModelSetup(
        normalise_choice(choice),
        detect_fsltl(folders, explicit_path=fsltl_path),
        detect_aig(folders, explicit_path=aig_path),
    )


def build_index(setup: ModelSetup) -> ModelIndex:
    """Construit l'index du jeu choisi, une fois par démarrage d'injection."""
    if setup.choice == "aig":
        return AigModelIndex(setup.aig)
    return FsltlModelIndex(setup.fsltl)

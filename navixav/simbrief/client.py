"""Client de l'endpoint public SimBrief « dernier OFP ».

    https://www.simbrief.com/api/xml.fetcher.php?userid=<PILOT_ID>&json=1

Cet endpoint ne génère pas de vol : il renvoie le dernier plan produit par
l'utilisateur. Aucune clé API n'est nécessaire pour cette lecture.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

FETCH_URL = "https://www.simbrief.com/api/xml.fetcher.php"
DEFAULT_TIMEOUT = 20


class SimBriefError(RuntimeError):
    """Erreur de récupération ou de contenu côté SimBrief."""


class SimBriefClient:
    def __init__(
        self,
        pilot_id: str = "",
        username: str = "",
        timeout: int = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
    ) -> None:
        if not pilot_id and not username:
            raise SimBriefError(
                "Aucun identifiant SimBrief. Renseigne SIMBRIEF_PILOT_ID "
                "(ou SIMBRIEF_USERNAME) dans le fichier .env."
            )
        self.pilot_id = pilot_id
        self.username = username
        self.timeout = timeout
        self._session = session or requests.Session()

    def fetch_latest(self) -> dict[str, Any]:
        """Récupère le dernier OFP au format JSON."""
        params: dict[str, Any] = {"json": 1}
        if self.pilot_id:
            params["userid"] = self.pilot_id
        else:
            params["username"] = self.username

        try:
            response = self._session.get(
                FETCH_URL, params=params, timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise SimBriefError(f"Requête SimBrief impossible : {exc}") from exc

        # SimBrief renvoie ses erreurs métier avec un code HTTP 400 et le détail
        # dans le corps JSON : il faut le lire avant de traiter le statut HTTP.
        try:
            data = response.json()
        except ValueError:
            data = None

        if isinstance(data, dict):
            _raise_on_fetch_error(data)
            if response.ok:
                return data

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            snippet = response.text[:200].replace("\n", " ")
            raise SimBriefError(
                f"SimBrief a répondu {response.status_code} : {snippet}"
            ) from exc

        snippet = response.text[:200].replace("\n", " ")
        raise SimBriefError(f"Réponse SimBrief illisible (JSON attendu) : {snippet}")

    @staticmethod
    def from_file(path: Path | str) -> dict[str, Any]:
        """Charge un OFP déjà enregistré (tests, mode hors ligne)."""
        raw = Path(path).read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SimBriefError(f"Fichier OFP illisible : {path}") from exc
        _raise_on_fetch_error(data)
        return data


# Messages SimBrief courants, traduits et accompagnés de la marche à suivre.
_KNOWN_ERRORS: tuple[tuple[str, str], ...] = (
    (
        "no flight plan on file",
        "Le Pilot ID est reconnu, mais aucun plan de vol n'a été généré sur ce "
        "compte. Cet endpoint ne fait que relire le dernier OFP produit : "
        "génère un vol sur simbrief.com (bouton « Generate OFP »), puis relance "
        "la commande.",
    ),
    (
        "unknown userid",
        "Pilot ID inconnu de SimBrief. Il se trouve dans Account Settings > "
        "SimBrief Pilot ID (une suite de chiffres). Si tu utilises un alias, "
        "renseigne SIMBRIEF_USERNAME plutôt que SIMBRIEF_PILOT_ID.",
    ),
    (
        "expired",
        "Le dernier OFP SimBrief a expiré. Régénère un vol sur simbrief.com.",
    ),
)


def _raise_on_fetch_error(data: dict[str, Any]) -> None:
    fetch = data.get("fetch")
    if not isinstance(fetch, dict):
        return
    status = str(fetch.get("status", "")).strip()
    if not status or status.lower() in {"success", "ok"}:
        return

    lowered = status.lower()
    for needle, explanation in _KNOWN_ERRORS:
        if needle in lowered:
            raise SimBriefError(f"{explanation}\n(réponse SimBrief : {status})")
    raise SimBriefError(f"SimBrief : {status}")

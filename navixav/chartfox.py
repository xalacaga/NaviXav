"""Client ChartFox OAuth et API pour l'application Windows locale.

Le client OAuth est public : le ``client_id`` est distribuable, mais aucun
secret d'organisation ni jeton utilisateur ne doit atteindre JavaScript ou les
journaux. Les jetons sont protégés par DPAPI et les PDF ne sont jamais conservés
sur disque.
"""

from __future__ import annotations

import base64
import ctypes
import hashlib
import ipaddress
import json
import secrets
import socket
import sys
import time
import uuid
from ctypes import wintypes
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlencode, urljoin, urlsplit

import requests

from navixav.paths import user_data_path

API_ROOT = "https://api.chartfox.org"
AUTHORIZE_URL = f"{API_ROOT}/oauth/authorize"
TOKEN_URL = f"{API_ROOT}/oauth/token"
CLIENT_ID = "01a041eb-a76c-7333-89eb-d3ad7bf50b18"
SCOPES = (
    "oauth:user:name",
    "airports:view",
    "charts:index",
    "charts:view",
    "charts:view_source_url",
    "charts:files",
)
TOKEN_PATH = user_data_path("credentials", "chartfox.oauth")
CATALOGUE_TTL_SECONDS = 15 * 60
OAUTH_PENDING_SECONDS = 10 * 60
MAX_DOCUMENT_BYTES = 50 * 1024 * 1024


class ChartFoxError(RuntimeError):
    """ChartFox n'est pas disponible ou refuse la demande."""


@dataclass(frozen=True)
class OAuthTokens:
    access_token: str
    refresh_token: str = ""
    expires_at: float = 0.0
    token_type: str = "Bearer"
    user_name: str = ""

    @classmethod
    def from_response(
        cls,
        payload: dict[str, Any],
        *,
        previous: "OAuthTokens | None" = None,
    ) -> "OAuthTokens":
        access_token = str(payload.get("access_token") or "").strip()
        if not access_token:
            raise ChartFoxError("ChartFox n'a pas renvoyé de jeton d'accès.")
        try:
            expires_in = max(0, int(payload.get("expires_in") or 0))
        except (TypeError, ValueError):
            expires_in = 0
        return cls(
            access_token=access_token,
            refresh_token=str(
                payload.get("refresh_token")
                or (previous.refresh_token if previous else "")
            ).strip(),
            expires_at=time.time() + expires_in if expires_in else 0.0,
            token_type=str(payload.get("token_type") or "Bearer"),
            user_name=previous.user_name if previous else "",
        )

    def expired(self, *, leeway_seconds: int = 60) -> bool:
        return bool(self.expires_at and self.expires_at <= time.time() + leeway_seconds)


class TokenStore(Protocol):
    def load(self) -> OAuthTokens | None: ...

    def save(self, tokens: OAuthTokens) -> None: ...

    def clear(self) -> None: ...


class MemoryTokenStore:
    """Stockage injecté dans les tests, sans écriture ni dépendance Windows."""

    def __init__(self, tokens: OAuthTokens | None = None) -> None:
        self.tokens = tokens

    def load(self) -> OAuthTokens | None:
        return self.tokens

    def save(self, tokens: OAuthTokens) -> None:
        self.tokens = tokens

    def clear(self) -> None:
        self.tokens = None


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _dpapi(data: bytes, *, protect: bool) -> bytes:
    if sys.platform != "win32":
        raise ChartFoxError(
            "Le stockage OAuth ChartFox protégé est disponible sous Windows."
        )
    source_buffer = ctypes.create_string_buffer(data)
    source = _DataBlob(
        len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_ubyte))
    )
    target = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    operation = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    description = "NaviXav ChartFox OAuth" if protect else None
    if not operation(
        ctypes.byref(source),
        description,
        None,
        None,
        None,
        0x01,  # CRYPTPROTECT_UI_FORBIDDEN
        ctypes.byref(target),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(target.pbData)


class WindowsTokenStore:
    def __init__(self, path: Path | str = TOKEN_PATH) -> None:
        self.path = Path(path)

    def load(self) -> OAuthTokens | None:
        if not self.path.is_file():
            return None
        try:
            payload = json.loads(_dpapi(self.path.read_bytes(), protect=False))
            return OAuthTokens(**payload)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ChartFoxError(
                "Les identifiants ChartFox enregistrés sont illisibles. "
                "Déconnecte puis reconnecte le compte."
            ) from exc

    def save(self, tokens: OAuthTokens) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            clear = json.dumps(asdict(tokens), separators=(",", ":")).encode("utf-8")
            self.path.write_bytes(_dpapi(clear, protect=True))
        except (OSError, ChartFoxError) as exc:
            raise ChartFoxError(
                "Impossible de protéger les identifiants ChartFox sur cet ordinateur."
            ) from exc

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)


@dataclass(frozen=True)
class PendingAuthorization:
    state: str
    verifier: str
    redirect_uri: str
    created_at: float


@dataclass(frozen=True)
class ChartFoxChart:
    id: str
    icao: str
    title: str
    code: str
    type: int
    type_key: str
    procedure_ident: str
    runways: tuple[str, ...]
    view_url: str
    georeferenced: bool

    @property
    def category(self) -> str:
        return {
            3: "Aérodrome et roulage",
            4: "Départs SID",
            5: "Arrivées STAR",
            6: "Approches IAC",
        }.get(self.type, "Autres cartes")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "icao": self.icao,
            "title": self.title,
            "filename": self.code or self.id,
            "category": self.category,
            "chart_code": self.type_key,
            "procedure_ident": self.procedure_ident,
            "runways": list(self.runways),
            "external_url": self.view_url,
            # Le scope charts:geos n'est pas encore accordé à NaviXav. Le
            # catalogue indique seulement qu'une calibration existe.
            "georeferenced": False,
            "chartfox_georeference_available": self.georeferenced,
        }


def _meta_values(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    for item in payload.get("meta") or []:
        if str(item.get("type_key") or "").lower() != key.lower():
            continue
        values = item.get("value") or []
        return tuple(str(value) for value in values if str(value).strip())
    return ()


def _chart(payload: dict[str, Any], airport: str) -> ChartFoxChart:
    chart_id = str(payload.get("id") or "")
    try:
        uuid.UUID(chart_id)
    except ValueError as exc:
        raise ChartFoxError("ChartFox a renvoyé un identifiant de carte invalide.") from exc
    icao = str(payload.get("airport_icao") or airport).upper()
    if icao != airport:
        raise ChartFoxError("La carte ChartFox appartient à un autre aérodrome.")
    procedure = _meta_values(payload, "ProcedureIdent")
    return ChartFoxChart(
        id=chart_id,
        icao=icao,
        title=str(payload.get("name") or payload.get("code") or chart_id),
        code=str(payload.get("code") or ""),
        type=int(payload.get("type") or 0),
        type_key=str(payload.get("type_key") or "Unknown"),
        procedure_ident=procedure[0] if procedure else "",
        runways=_meta_values(payload, "Runways"),
        view_url=str(payload.get("view_url") or ""),
        georeferenced=bool(payload.get("has_georeferences")),
    )


def _public_http_url(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"}:
        return False
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443)}
    except OSError:
        return False
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            return False
    return True


class ChartFoxClient:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        token_store: TokenStore | None = None,
        client_id: str = CLIENT_ID,
    ) -> None:
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", "NaviXav/1 ChartFox integration")
        self.token_store = token_store or WindowsTokenStore()
        self.client_id = client_id
        self.pending: PendingAuthorization | None = None
        self._catalogues: dict[str, tuple[float, list[ChartFoxChart]]] = {}
        self._details: dict[str, tuple[float, dict[str, Any]]] = {}

    def close(self) -> None:
        self.session.close()

    def begin_authorization(self, redirect_uri: str) -> str:
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).decode("ascii").rstrip("=")
        state = secrets.token_urlsafe(32)
        self.pending = PendingAuthorization(state, verifier, redirect_uri, time.time())
        return f"{AUTHORIZE_URL}?{urlencode({
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(SCOPES),
            'state': state,
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
        })}"

    def complete_authorization(self, code: str, state: str) -> OAuthTokens:
        pending = self.pending
        self.pending = None
        if (
            pending is None
            or not secrets.compare_digest(state, pending.state)
            or time.time() - pending.created_at > OAUTH_PENDING_SECONDS
        ):
            raise ChartFoxError("La demande de connexion ChartFox a expiré.")
        response = self.session.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "redirect_uri": pending.redirect_uri,
                "code": code,
                "code_verifier": pending.verifier,
            },
            timeout=30,
        )
        payload = self._json_response(response, "Connexion ChartFox refusée")
        tokens = OAuthTokens.from_response(payload)
        self.token_store.save(tokens)
        try:
            user = self._api_json("/v2/user", tokens=tokens)
            tokens = OAuthTokens(**{**asdict(tokens), "user_name": str(user.get("full_name") or "")})
            self.token_store.save(tokens)
        except ChartFoxError:
            # Le nom est décoratif ; une connexion valable ne doit pas être
            # annulée si ce scope optionnel est momentanément indisponible.
            pass
        return tokens

    def disconnect(self) -> None:
        self.pending = None
        self._catalogues.clear()
        self._details.clear()
        self.token_store.clear()

    def status(self) -> dict[str, Any]:
        try:
            tokens = self._tokens(refresh=True)
        except ChartFoxError as exc:
            return {"connected": False, "error": str(exc)}
        if tokens is None:
            return {"connected": False}
        return {
            "connected": True,
            "user_name": tokens.user_name,
            "expires_at": tokens.expires_at or None,
        }

    def _tokens(self, *, refresh: bool) -> OAuthTokens | None:
        tokens = self.token_store.load()
        if tokens is None or not tokens.expired():
            return tokens
        if not refresh or not tokens.refresh_token:
            self.token_store.clear()
            raise ChartFoxError("La connexion ChartFox a expiré. Reconnecte le compte.")
        response = self.session.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "refresh_token": tokens.refresh_token,
                "scope": " ".join(SCOPES),
            },
            timeout=30,
        )
        refreshed = OAuthTokens.from_response(
            self._json_response(response, "Renouvellement ChartFox refusé"),
            previous=tokens,
        )
        self.token_store.save(refreshed)
        return refreshed

    @staticmethod
    def _json_response(response: Any, message: str) -> dict[str, Any]:
        try:
            payload = response.json()
        except (TypeError, ValueError) as exc:
            raise ChartFoxError(f"{message} : réponse illisible.") from exc
        if not isinstance(payload, dict):
            raise ChartFoxError(f"{message} : réponse inattendue.")
        if not getattr(response, "ok", False):
            detail = payload.get("message") or payload.get("error_description") or payload.get("error")
            raise ChartFoxError(f"{message} : {detail or response.status_code}.")
        return payload

    def _api_json(
        self,
        path: str,
        *,
        tokens: OAuthTokens | None = None,
    ) -> dict[str, Any]:
        active = tokens or self._tokens(refresh=True)
        if active is None:
            raise ChartFoxError("Connecte un compte ChartFox dans les paramètres.")
        response = self.session.get(
            f"{API_ROOT}{path}",
            headers={"Authorization": f"Bearer {active.access_token}"},
            timeout=30,
        )
        if getattr(response, "status_code", 0) == 401 and tokens is None:
            self.token_store.save(
                OAuthTokens(**{**asdict(active), "expires_at": time.time() - 1})
            )
            active = self._tokens(refresh=True)
            if active is None:
                raise ChartFoxError("La connexion ChartFox a expiré.")
            response = self.session.get(
                f"{API_ROOT}{path}",
                headers={"Authorization": f"Bearer {active.access_token}"},
                timeout=30,
            )
        return self._json_response(response, "API ChartFox indisponible")

    def list_airport_charts(self, icao: str) -> list[ChartFoxChart]:
        airport = icao.strip().upper()
        if len(airport) != 4 or not airport.isalnum():
            raise ChartFoxError("Code OACI invalide.")
        cached = self._catalogues.get(airport)
        if cached and time.time() - cached[0] < CATALOGUE_TTL_SECONDS:
            return list(cached[1])
        payload = self._api_json(f"/v2/airports/{airport}/charts/grouped")
        groups = payload.get("data") or {}
        if not isinstance(groups, dict):
            raise ChartFoxError("Catalogue ChartFox inattendu.")
        charts = [
            _chart(item, airport)
            for items in groups.values()
            if isinstance(items, list)
            for item in items
            if isinstance(item, dict)
        ]
        charts.sort(key=lambda item: (item.category, item.title))
        self._catalogues[airport] = (time.time(), charts)
        return list(charts)

    def chart_detail(self, chart_id: str, icao: str) -> dict[str, Any]:
        airport = icao.strip().upper()
        try:
            safe_id = str(uuid.UUID(chart_id))
        except ValueError as exc:
            raise ChartFoxError("Identifiant de carte ChartFox invalide.") from exc
        catalogue = self.list_airport_charts(airport)
        if safe_id not in {chart.id for chart in catalogue}:
            raise ChartFoxError("Cette carte n'appartient pas au catalogue demandé.")
        cached = self._details.get(safe_id)
        if cached and time.time() - cached[0] < CATALOGUE_TTL_SECONDS:
            return dict(cached[1])
        payload = self._api_json(f"/v2/charts/{safe_id}")
        if str(payload.get("id") or "") != safe_id:
            raise ChartFoxError("ChartFox a renvoyé une autre carte.")
        if str(payload.get("airport_icao") or "").upper() != airport:
            raise ChartFoxError("La carte ChartFox appartient à un autre aérodrome.")
        self._details[safe_id] = (time.time(), payload)
        return dict(payload)

    def chart_access(self, chart_id: str, icao: str) -> dict[str, bool]:
        """Expose uniquement les contraintes d'affichage utiles à l'interface."""
        detail = self.chart_detail(chart_id, icao)
        requires_preauth = bool(detail.get("requires_preauth"))
        allows_iframe = detail.get("allows_iframe") is not False
        return {
            "requires_preauth": requires_preauth,
            "allows_iframe": allows_iframe,
            "can_embed": allows_iframe and not requires_preauth,
        }

    def document(self, chart_id: str, icao: str) -> tuple[bytes, str, str]:
        detail = self.chart_detail(chart_id, icao)
        if detail.get("requires_preauth"):
            raise ChartFoxError(
                "Cette publication exige une autorisation préalable chez ChartFox."
            )
        if detail.get("allows_iframe") is False:
            raise ChartFoxError(
                "La source de cette publication interdit l'affichage intégré."
            )
        candidates: list[tuple[str, int | None]] = [
            (str(item.get("url") or ""), item.get("type"))
            for item in detail.get("files") or []
            if isinstance(item, dict)
        ]
        candidates.extend(
            (
                (str(detail.get("url") or ""), None),
                (str(detail.get("source_url") or ""), detail.get("source_url_type")),
            )
        )
        url = next(
            (
                candidate
                for candidate, kind in candidates
                if candidate and kind in {None, 0, 1} and _public_http_url(candidate)
            ),
            "",
        )
        if not url:
            raise ChartFoxError("Aucun fichier affichable n'est fourni pour cette carte.")
        response = None
        for _redirect in range(4):
            host = (urlsplit(url).hostname or "").lower()
            headers = {}
            if host == "chartfox.org" or host.endswith(".chartfox.org"):
                tokens = self._tokens(refresh=True)
                if tokens:
                    headers["Authorization"] = f"Bearer {tokens.access_token}"
            response = self.session.get(
                url,
                headers=headers,
                timeout=45,
                allow_redirects=False,
                stream=True,
            )
            if getattr(response, "status_code", 0) not in {301, 302, 303, 307, 308}:
                break
            location = str(response.headers.get("Location") or "")
            redirected = urljoin(url, location)
            response.close()
            if not _public_http_url(redirected):
                raise ChartFoxError("Redirection de document ChartFox refusée.")
            url = redirected
        else:
            raise ChartFoxError("Trop de redirections pour ce document ChartFox.")
        assert response is not None
        if not getattr(response, "ok", False):
            response.close()
            raise ChartFoxError(
                f"Téléchargement de la carte ChartFox refusé ({response.status_code})."
            )
        content = bytearray()
        try:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                content.extend(chunk)
                if len(content) > MAX_DOCUMENT_BYTES:
                    raise ChartFoxError("Le document ChartFox est trop volumineux.")
        finally:
            response.close()
        document = bytes(content)
        if not document:
            raise ChartFoxError("Le document ChartFox a une taille invalide.")
        content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0]
        if document.startswith(b"%PDF-"):
            content_type = "application/pdf"
        elif content_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise ChartFoxError("Le document ChartFox n'est ni un PDF ni une image.")
        filename = f"{icao.upper()}-{chart_id}.{ 'pdf' if content_type == 'application/pdf' else 'img' }"
        return document, content_type, filename

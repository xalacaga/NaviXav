"""Client SimConnect unique de NaviXav, en ctypes.

Les facilities et les variables de simulation passent toutes par cette couche.
NaviXav utilise son propre client ctypes et la DLL officielle du SDK MSFS.
Le protocole Facilities est le suivant :

    AddToFacilityDefinition(id, "OPEN AIRPORT")
    AddToFacilityDefinition(id, "LATITUDE")        champs du bloc courant
    AddToFacilityDefinition(id, "OPEN RUNWAY")     descente dans les enfants
    ...
    AddToFacilityDefinition(id, "CLOSE RUNWAY")
    AddToFacilityDefinition(id, "CLOSE AIRPORT")
    RequestFacilityData_EX1(id, requête, "LFPO")

Chaque bloc revient en message distinct, porteur de son type et de la charge
binaire correspondant exactement aux champs déclarés pour ce type.
"""

from __future__ import annotations

import ctypes as ct
import math
import os
import struct
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

from navixav.msfs.fields import TYPE_AIRPORT, TYPE_NAMES, Field
from navixav.paths import resource_path

RECV_ID_EXCEPTION = 1
RECV_ID_QUIT = 3
RECV_ID_SIMOBJECT_DATA = 8
RECV_ID_SIMOBJECT_DATA_BYTYPE = 9
RECV_ID_ASSIGNED_OBJECT_ID = 12
RECV_ID_CLIENT_DATA = 16
RECV_ID_FACILITY_DATA = 28
RECV_ID_FACILITY_DATA_END = 29
RECV_ID_CAMERA_DATA = 40
RECV_ID_CAMERA_STATUS = 41
RECV_ID_CAMERA_WORLD_LOCKER = 44

# En-tête SIMCONNECT_RECV (3 DWORD) + 7 DWORD, identique pour FACILITY_DATA
# et SIMOBJECT_DATA.
_PAYLOAD_OFFSET = (3 + 7) * 4

DATATYPE_FLOAT64 = 4
DATATYPE_STRING32 = 6
DATATYPE_STRING256 = 9
DATATYPE_INITPOSITION = 12
PERIOD_NEVER = 0
PERIOD_ONCE = 1
PERIOD_SIM_FRAME = 3
OBJECT_ID_USER = 0
SIMCONNECT_UNUSED = 0xFFFFFFFF
SIMCONNECT_OPEN_CONFIGINDEX_LOCAL = 0xFFFFFFFF
SIMCONNECT_GROUP_PRIORITY_HIGHEST = 1
SIMCONNECT_EVENT_FLAG_GROUPID_IS_PRIORITY = 0x00000010

# Après AIReleaseControl, le moteur de simulation continue sinon à intégrer la
# physique de l'objet pendant que NaviXav lui donne une position. Les deux
# contrôleurs se corrigent alors mutuellement, ce qui fait vibrer surtout les
# appareils posés sur leur train.
AI_POSITION_FREEZE_EVENTS = (
    "FREEZE_LATITUDE_LONGITUDE_SET",
    "FREEZE_ALTITUDE_SET",
    "FREEZE_ATTITUDE_SET",
)

# Catégories d'objets énumérables autour de l'avion. Le trafic réseau et le
# trafic généré par le simulateur arrivent tous deux en AIRCRAFT : SimConnect
# ne distingue pas l'origine d'un appareil, seulement sa nature.
SIMOBJECT_TYPE_AIRCRAFT = 2

# Largeur fixe d'un champ STRING32 dans la charge renvoyée.
STRING32_SIZE = 32
MSFS2024_REQUIRED_EXPORTS = (
    "SimConnect_AICreateNonATCAircraft_EX1",
    "SimConnect_EnumerateSimObjectsAndLiveries",
)

# API caméra de MSFS 2024. Elle est facultative : une DLL qui ne la porte pas
# reste utilisable pour tout le reste, seule la caméra est alors indisponible.
CAMERA_EXPORTS = (
    "SimConnect_CameraAcquire",
    "SimConnect_CameraRelease",
    "SimConnect_CameraSet",
    "SimConnect_CameraGetStatus",
    "SimConnect_CameraEnableFlag",
    "SimConnect_SubscribeToCameraStatusUpdate",
    "SimConnect_RequestCameraWorldLocker",
    "SimConnect_DeleteCameraWorldLocker",
)
CAMERA_REFERENTIAL_SIMOBJECT = 1
CAMERA_REFERENTIAL_WORLD = 2
CAMERA_MASK_POSITION = 1
CAMERA_MASK_ROTATION = 2
CAMERA_MASK_TARGETED = 4
CAMERA_MASK_FOV = 8
# Le simulateur garde lui-même la caméra au-dessus du relief.
CAMERA_FLAG_ABOVE_GROUND = 2
CAMERA_AVAILABILITY_USER_DISABLED = 3
CAMERA_LOCKER_FAIL = 4
EXCEPTION_CAMERA_API = 46
# SIMCONNECT_DATA_CAMERA, compactée sur 84 octets : position (3 double),
# référentiel et objet, cible (3 double), tangage/inclinaison/cap (3 float),
# référentiel et objet de la rotation, champ de vision (double).
_CAMERA_LAYOUT = struct.Struct("<3diI3d3fiId")


def _dll_candidates() -> tuple[Path, ...]:
    """Emplacements possibles de la DLL officielle SimConnect."""
    candidates = [
        resource_path("SimConnect", "SimConnect.dll"),
        resource_path("SimConnect.dll"),
    ]
    sdk_root = os.getenv("MSFS2024_SDK", "").strip()
    if sdk_root:
        candidates.append(
            Path(sdk_root) / "SimConnect SDK" / "lib" / "SimConnect.dll"
        )
    candidates.append(
        Path(r"C:\MSFS 2024 SDK\SimConnect SDK\lib\SimConnect.dll")
    )
    return tuple(candidates)


DLL_CANDIDATES = _dll_candidates()

EXCEPTION_NAMES = {
    1: "ERROR", 2: "SIZE_MISMATCH", 3: "UNRECOGNIZED_ID", 4: "UNOPENED",
    5: "VERSION_MISMATCH", 7: "NAME_UNRECOGNIZED", 18: "INVALID_DATA_TYPE",
    19: "INVALID_DATA_SIZE", 20: "DATA_ERROR", 21: "INVALID_ARRAY",
    EXCEPTION_CAMERA_API: "CAMERA_API",
}

# Un refus du simulateur arrive avant les blocs déjà émis pour la même
# requête : on laisse ce court sursis pour les récupérer, puis on abandonne.
# Attendre la fin du délai complet figerait l'application pendant vingt
# secondes à chaque identifiant inconnu.
EXCEPTION_GRACE_S = 0.25


class SimConnectError(RuntimeError):
    """Le simulateur est absent, ou refuse la définition demandée."""


class SimConnectRefused(SimConnectError):
    """Le simulateur a répondu, en refusant la demande.

    À distinguer d'une absence de réponse : un refus renseigne sur la donnée
    demandée et arrive immédiatement, alors qu'un silence n'est constaté qu'au
    bout du délai d'attente.
    """

    def __init__(self, message: str, codes: Sequence[int] = ()) -> None:
        super().__init__(message)
        self.codes = tuple(codes)


class SimConnectLayout(SimConnectError):
    """La charge reçue ne fait pas la taille annoncée par la définition.

    Une version du simulateur peut changer la largeur d'un champ. Le bloc reste
    inexploitable, mais la définition, elle, peut être rejouée sans le champ
    optionnel fautif : c'est une erreur de forme, pas une absence de réponse.
    """


class _RECV(ct.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("dwVersion", wintypes.DWORD),
        ("dwID", wintypes.DWORD),
    ]


class _RECV_EXCEPTION(ct.Structure):
    _fields_ = _RECV._fields_ + [
        ("dwException", wintypes.DWORD),
        ("dwSendID", wintypes.DWORD),
        ("dwIndex", wintypes.DWORD),
    ]


class _RECV_FACILITY_DATA(ct.Structure):
    _fields_ = _RECV._fields_ + [
        ("UserRequestId", wintypes.DWORD),
        ("UniqueRequestId", wintypes.DWORD),
        ("ParentUniqueRequestId", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("IsListItem", wintypes.DWORD),
        ("ItemIndex", wintypes.DWORD),
        ("ListSize", wintypes.DWORD),
    ]


class _RECV_SIMOBJECT_DATA(ct.Structure):
    _fields_ = _RECV._fields_ + [
        ("dwRequestID", wintypes.DWORD),
        ("dwObjectID", wintypes.DWORD),
        ("dwDefineID", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("dwentrynumber", wintypes.DWORD),
        ("dwoutof", wintypes.DWORD),
        ("dwDefineCount", wintypes.DWORD),
    ]


class _RECV_ASSIGNED_OBJECT_ID(ct.Structure):
    _fields_ = _RECV._fields_ + [
        ("dwRequestID", wintypes.DWORD),
        ("dwObjectID", wintypes.DWORD),
    ]


class _DATA_INITPOSITION(ct.Structure):
    _fields_ = [
        ("Latitude", ct.c_double),
        ("Longitude", ct.c_double),
        ("Altitude", ct.c_double),
        ("Pitch", ct.c_double),
        ("Bank", ct.c_double),
        ("Heading", ct.c_double),
        ("OnGround", wintypes.DWORD),
        ("Airspeed", wintypes.DWORD),
    ]


class FacilityDefinition:
    """Assemble la définition et retient le décodage de chaque type de bloc."""

    def __init__(self) -> None:
        self.tokens: list[str] = []
        self.layouts: dict[int, tuple[Field, ...]] = {}
        self._stack: list[str] = []

    def open(self, block: str, block_type: int, fields: Sequence[Field]) -> "FacilityDefinition":
        self.tokens.append(f"OPEN {block}")
        self.tokens.extend(field.name for field in fields)
        self.layouts[block_type] = tuple(fields)
        self._stack.append(block)
        return self

    def close(self) -> "FacilityDefinition":
        self.tokens.append(f"CLOSE {self._stack.pop()}")
        return self

    def close_all(self) -> "FacilityDefinition":
        while self._stack:
            self.close()
        return self


def unpack_camera_fov(raw: bytes, header: int) -> float | None:
    """Champ de vision contenu dans une réponse RECV_ID_CAMERA_DATA."""
    if len(raw) < header + _CAMERA_LAYOUT.size:
        return None
    fov = _CAMERA_LAYOUT.unpack_from(raw, header)[-1]
    return fov if math.isfinite(fov) and fov > 0 else None


def pack_camera(
    position: Sequence[float],
    referential: int,
    target: Sequence[float] = (0.0, 0.0, 0.0),
    *,
    object_id: int = OBJECT_ID_USER,
    target_referential: int = CAMERA_REFERENTIAL_SIMOBJECT,
    target_object_id: int = OBJECT_ID_USER,
    fov_deg: float = 0.0,
) -> bytes:
    """Charge de SIMCONNECT_DATA_CAMERA : une position et un point visé.

    En référentiel avion, la position est en mètres, x vers la droite, y vers
    le haut, z vers l'avant. En référentiel monde, c'est latitude, longitude
    en degrés et altitude en mètres. La cible, exprimée dans son propre
    référentiel, oriente la caméra : MSFS calcule lui-même l'orientation.
    """
    x, y, z = (float(value) for value in position)
    tx, ty, tz = (float(value) for value in target)
    return _CAMERA_LAYOUT.pack(
        x, y, z, int(referential), int(object_id),
        tx, ty, tz,
        0.0, 0.0, 0.0, int(target_referential), int(target_object_id),
        float(fov_deg),
    )


def decode(payload: bytes, fields: Sequence[Field]) -> dict[str, Any]:
    """Découpe la charge binaire selon les champs déclarés.

    La taille est vérifiée avant tout découpage : un champ refusé par le
    simulateur raccourcit la charge et décalerait toutes les valeurs
    suivantes. Mieux vaut une erreur franche qu'une donnée fausse.
    """
    expected = sum(field.size for field in fields)
    if len(payload) != expected:
        names = ", ".join(field.name for field in fields)
        raise SimConnectLayout(
            f"Charge de {len(payload)} octets pour {expected} attendus. "
            f"Un champ a été refusé ou a changé de largeur parmi : {names}"
        )

    values: dict[str, Any] = {}
    offset = 0
    for field in fields:
        chunk = payload[offset : offset + field.size]
        offset += field.size
        if field.kind == "f64":
            values[field.name] = struct.unpack("<d", chunk)[0]
        elif field.kind == "f32":
            values[field.name] = struct.unpack("<f", chunk)[0]
        elif field.kind == "i32":
            values[field.name] = struct.unpack("<i", chunk)[0]
        elif field.kind == "u8":
            values[field.name] = chunk[0]
        else:
            values[field.name] = chunk.split(b"\x00")[0].decode("utf-8", "replace").strip()
    return values


class SimConnectClient:
    """Connexion unique au simulateur, réutilisée entre les requêtes."""

    def __init__(self, dll_path: Path | str | None = None) -> None:
        self._dll = self._load(dll_path)
        self._handle = ct.c_void_p()
        self._next_id = 1
        # Une définition de données est réutilisable : la déclarer à chaque
        # lecture les accumulerait côté simulateur pour toute la connexion.
        self._simvar_definitions: dict[tuple[tuple[str, str], ...], int] = {}
        self._string_simvar_definitions: dict[str, int] = {}
        self._client_data_definitions: dict[str, tuple[int, int]] = {}
        self._object_definitions: dict[tuple[Any, str | None], int] = {}
        self._ai_position_definition: int | None = None
        self._client_events: dict[str, int] = {}
        # Identifiant réel de l'avion du joueur, appris au premier relevé.
        # SimConnect l'inclut dans ses énumérations sans le distinguer : c'est
        # le seul moyen sûr de ne pas le compter deux fois.
        self.user_object_id: int | None = None
        if self._dll.SimConnect_Open(
            ct.byref(self._handle), b"NaviXav", None, 0, None,
            SIMCONNECT_OPEN_CONFIGINDEX_LOCAL,
        ) != 0:
            raise SimConnectError(
                "Microsoft Flight Simulator ne répond pas. Lance le simulateur "
                "et charge un vol avant d'importer les données."
            )

    # ------------------------------------------------------------------ #

    @staticmethod
    def _load(dll_path: Path | str | None):
        candidates = [Path(dll_path)] if dll_path else list(DLL_CANDIDATES)
        outdated: list[Path] = []
        for path in candidates:
            if not path.is_file():
                continue
            dll = ct.WinDLL(str(path))
            if any(not hasattr(dll, name) for name in MSFS2024_REQUIRED_EXPORTS):
                outdated.append(path)
                continue
            _declare(dll)
            return dll
        if outdated:
            paths = ", ".join(str(path) for path in outdated)
            raise SimConnectError(
                "DLL SimConnect incompatible avec MSFS 2024 (API EX1 absente) : "
                f"{paths}. Installe le SDK MSFS 2024 à jour avant de lancer NaviXav."
            )
        raise SimConnectError(
            "SimConnect.dll MSFS 2024 introuvable. Installe le SDK MSFS 2024, "
            "ou indique son "
            "chemin explicitement."
        )

    def request(
        self, definition: FacilityDefinition, icao: str, timeout_s: float = 20.0
    ) -> list[tuple[int, int, bytes]]:
        """Interroge un aéroport."""
        return self.request_raw(definition, icao, "", b"\x00", timeout_s)

    def request_raw(
        self,
        definition: FacilityDefinition,
        icao: str,
        region: str = "",
        type_char: bytes = b"\x00",
        timeout_s: float = 20.0,
    ) -> list[tuple[int, int, bytes]]:
        """Envoie la définition et collecte les blocs jusqu'au marqueur de fin.

        `type_char` lève l'ambiguïté quand un même identifiant désigne
        plusieurs sortes d'installation : « V » pour un VOR ou un ILS, « N »
        pour un NDB, « W » pour un point de report, « A » pour un aéroport.

        Retourne des triplets (type, index dans la liste, charge binaire).
        """
        self._next_id += 1
        request_id = self._next_id

        for token in definition.tokens:
            self._dll.SimConnect_AddToFacilityDefinition(
                self._handle, request_id, token.encode()
            )
        self._dll.SimConnect_RequestFacilityData_EX1(
            self._handle,
            request_id,
            request_id,
            icao.upper().encode(),
            region.upper().encode(),
            type_char,
        )

        blocks: list[tuple[int, int, bytes]] = []
        exceptions: list[int] = []
        pointer = ct.POINTER(_RECV)()
        size = wintypes.DWORD()
        deadline = time.monotonic() + timeout_s

        while time.monotonic() < deadline:
            if self._dll.SimConnect_GetNextDispatch(
                self._handle, ct.byref(pointer), ct.byref(size)
            ) != 0:
                time.sleep(0.002)
                continue

            recv = pointer.contents
            if recv.dwID == RECV_ID_FACILITY_DATA:
                data = ct.cast(pointer, ct.POINTER(_RECV_FACILITY_DATA)).contents
                raw = ct.string_at(pointer, recv.dwSize)
                blocks.append((data.Type, data.ItemIndex, raw[_PAYLOAD_OFFSET:]))
            elif recv.dwID == RECV_ID_FACILITY_DATA_END:
                return blocks
            elif recv.dwID == RECV_ID_EXCEPTION:
                exception = ct.cast(pointer, ct.POINTER(_RECV_EXCEPTION)).contents
                if exception.dwException not in exceptions:
                    exceptions.append(exception.dwException)
                deadline = min(deadline, time.monotonic() + EXCEPTION_GRACE_S)
            elif recv.dwID == RECV_ID_QUIT:
                raise SimConnectError("Le simulateur s'est fermé.")

        if exceptions:
            names = ", ".join(
                EXCEPTION_NAMES.get(code, str(code)) for code in exceptions
            )
            raise SimConnectRefused(
                f"SimConnect a refusé la définition ({names}).", exceptions
            )
        raise SimConnectError(
            f"Aucune réponse pour {icao.upper()} après {timeout_s:.0f} s. "
            "L'aéroport est peut-être hors de la zone chargée par le simulateur."
        )

    def read_simvars(
        self, variables: Sequence[tuple[str, str]], timeout_s: float = 3.0
    ) -> dict[str, float]:
        """Lit des variables de simulation de l'avion du joueur.

        `variables` associe un nom SimConnect à son unité, ex.
        ``("PLANE LATITUDE", "Degrees")``. Demander l'unité explicitement évite
        toute conversion après coup : c'est le simulateur qui convertit.

        Toutes les valeurs sont demandées en FLOAT64 ; un booléen revient donc
        en 0.0 ou 1.0.

        La définition est mise en cache et réutilisée : le suivi temps réel
        appelle cette méthode plusieurs fois par seconde pendant des heures.
        """
        if not variables:
            return {}

        definition_id = self._definition_for(variables)
        self._next_id += 1
        request_id = self._next_id

        result = self._dll.SimConnect_RequestDataOnSimObject(
            self._handle, request_id, definition_id, OBJECT_ID_USER,
            PERIOD_ONCE, 0, 0, 0, 0,
        )
        if result != 0:
            self._forget_definition(variables)
            raise SimConnectError("Impossible de demander les données de vol.")

        expected = len(variables) * 8
        pointer = ct.POINTER(_RECV)()
        size = wintypes.DWORD()
        deadline = time.monotonic() + timeout_s
        exceptions: list[int] = []

        while time.monotonic() < deadline:
            if self._dll.SimConnect_GetNextDispatch(
                self._handle, ct.byref(pointer), ct.byref(size)
            ) != 0:
                time.sleep(0.002)
                continue

            recv = pointer.contents
            if recv.dwID == RECV_ID_SIMOBJECT_DATA:
                data = ct.cast(pointer, ct.POINTER(_RECV_SIMOBJECT_DATA)).contents
                if data.dwRequestID != request_id:
                    continue
                self.user_object_id = int(data.dwObjectID)
                payload = ct.string_at(pointer, recv.dwSize)[_PAYLOAD_OFFSET:]
                if len(payload) < expected:
                    raise SimConnectError(
                        f"Réponse de {len(payload)} octets pour {expected} attendus."
                    )
                values = struct.unpack(f"<{len(variables)}d", payload[:expected])
                return {name: value for (name, _unit), value in zip(variables, values)}
            if recv.dwID == RECV_ID_EXCEPTION:
                exception = ct.cast(pointer, ct.POINTER(_RECV_EXCEPTION)).contents
                if exception.dwException not in exceptions:
                    exceptions.append(exception.dwException)
                deadline = min(deadline, time.monotonic() + EXCEPTION_GRACE_S)
            elif recv.dwID == RECV_ID_QUIT:
                raise SimConnectError("Le simulateur s'est fermé.")

        if exceptions:
            # Une variable refusée rend la définition inutilisable : l'oublier
            # permet à l'appelant de retenter avec un jeu réduit.
            self._forget_definition(variables)
            names = ", ".join(
                EXCEPTION_NAMES.get(code, str(code)) for code in exceptions
            )
            raise SimConnectRefused(
                f"SimConnect a refusé la demande ({names}).", exceptions
            )
        raise SimConnectError("Aucune donnée de vol reçue du simulateur.")

    def subscribe_simvars(self, variables: Sequence[tuple[str, str]]) -> int:
        """Abonne la connexion aux variables de l'avion, une réponse par image.

        À réserver à une connexion dédiée : chaque image de simulation dépose
        un message dans la file, que seul `next_frame` sait vider. Une
        connexion partagée verrait ses lectures ponctuelles noyées.
        """
        definition_id = self._definition_for(variables)
        self._next_id += 1
        request_id = self._next_id
        result = self._dll.SimConnect_RequestDataOnSimObject(
            self._handle, request_id, definition_id, OBJECT_ID_USER,
            PERIOD_SIM_FRAME, 0, 0, 0, 0,
        )
        if result != 0:
            self._forget_definition(variables)
            raise SimConnectError("Impossible de s'abonner aux données de vol.")
        return request_id

    def next_frame(
        self,
        request_id: int,
        variables: Sequence[tuple[str, str]],
        timeout_s: float = 1.0,
        on_message: Callable[[int, bytes], None] | None = None,
    ) -> dict[str, float] | None:
        """Dernière image reçue pour un abonnement, ou None si rien n'arrive.

        La file est vidée jusqu'au message le plus récent : appliquer une
        image en retard ferait réagir l'avion à un état déjà dépassé. Le
        silence n'est pas une erreur — le simulateur en pause n'émet plus
        d'image. Un refus, en revanche, remonte : il vise souvent une écriture.
        Les autres messages (état de la caméra, par exemple) sont confiés à
        `on_message`, avec leur identifiant et leurs octets complets.
        """
        expected = len(variables) * 8
        pointer = ct.POINTER(_RECV)()
        size = wintypes.DWORD()
        deadline = time.monotonic() + timeout_s
        latest: bytes | None = None
        while True:
            if self._dll.SimConnect_GetNextDispatch(
                self._handle, ct.byref(pointer), ct.byref(size)
            ) != 0:
                if latest is not None or time.monotonic() >= deadline:
                    break
                time.sleep(0.001)
                continue
            recv = pointer.contents
            if recv.dwID == RECV_ID_SIMOBJECT_DATA:
                data = ct.cast(pointer, ct.POINTER(_RECV_SIMOBJECT_DATA)).contents
                if data.dwRequestID == request_id:
                    latest = ct.string_at(pointer, recv.dwSize)[_PAYLOAD_OFFSET:]
            elif recv.dwID == RECV_ID_EXCEPTION:
                exception = ct.cast(pointer, ct.POINTER(_RECV_EXCEPTION)).contents
                name = EXCEPTION_NAMES.get(exception.dwException, str(exception.dwException))
                raise SimConnectRefused(
                    f"SimConnect a refusé une demande ({name}).", [exception.dwException]
                )
            elif recv.dwID == RECV_ID_QUIT:
                raise SimConnectError("Le simulateur s'est fermé.")
            elif on_message is not None:
                on_message(recv.dwID, ct.string_at(pointer, recv.dwSize))
        if latest is None:
            return None
        if len(latest) < expected:
            raise SimConnectLayout(
                f"Réponse de {len(latest)} octets pour {expected} attendus."
            )
        values = struct.unpack(f"<{len(variables)}d", latest[:expected])
        return {name: value for (name, _unit), value in zip(variables, values)}

    def write_simvars(
        self, variables: Sequence[tuple[str, str]], values: Sequence[float]
    ) -> None:
        """Écrit des variables réglables sur l'avion du joueur, en FLOAT64.

        L'envoi est sans accusé de réception : un refus du simulateur arrive
        plus tard dans la file, sous forme d'exception, et c'est la boucle qui
        la vide qui la signale.
        """
        if len(variables) != len(values):
            raise ValueError("Autant de valeurs que de variables sont attendues.")
        definition_id = self._definition_for(variables)
        buffer = (ct.c_double * len(values))(*[float(value) for value in values])
        result = self._dll.SimConnect_SetDataOnSimObject(
            self._handle, definition_id, OBJECT_ID_USER, 0, 0,
            ct.sizeof(buffer), ct.byref(buffer),
        )
        if result != 0:
            raise SimConnectError("Impossible d'écrire les variables de l'avion.")

    # ------------------------------------------------------------------ #
    # Caméra MSFS 2024. Toutes ces commandes sont sans accusé de réception :
    # un refus arrive plus tard dans la file, en exception CAMERA_API.

    @property
    def camera_supported(self) -> bool:
        return all(hasattr(self._dll, name) for name in CAMERA_EXPORTS)

    def _camera_call(self, name: str, *args: Any) -> None:
        if not self.camera_supported:
            raise SimConnectError("Cette DLL SimConnect ne porte pas l'API caméra.")
        if getattr(self._dll, name)(self._handle, *args) != 0:
            raise SimConnectError(f"Commande caméra refusée ({name}).")

    def camera_acquire(self, client_name: str = "NaviXav") -> None:
        self._camera_call("SimConnect_CameraAcquire", client_name.encode("ascii"))

    def camera_release(self, camera_definition: str = "Pilot") -> None:
        """Rend la caméra ; MSFS bascule sur la définition de caméra nommée."""
        self._camera_call("SimConnect_CameraRelease", camera_definition.encode("ascii"))

    def camera_subscribe_status(self) -> None:
        """État de la caméra à chaque changement, puis tout de suite une fois."""
        self._camera_call("SimConnect_SubscribeToCameraStatusUpdate")
        self._camera_call("SimConnect_CameraGetStatus")

    def camera_enable_flag(self, flag: int) -> None:
        self._camera_call("SimConnect_CameraEnableFlag", int(flag))

    def camera_set(
        self,
        position: Sequence[float],
        referential: int,
        target: Sequence[float] = (0.0, 0.0, 0.0),
        fov_deg: float | None = None,
    ) -> None:
        """Place la caméra et la braque sur un point lié à l'avion du joueur.

        Le champ de vision est exprimé dans l'unité de MSFS : celle que
        renvoie `camera_get`. Une valeur posée reste en place dans le
        simulateur pour les images suivantes.

        Une structure de 84 octets passée « par valeur » est transmise, en
        64 bits, par adresse d'une copie : on passe donc directement l'adresse
        d'un tampon, sans dépendre de la façon dont ctypes traite une
        structure compactée.
        """
        payload = pack_camera(position, referential, target, fov_deg=fov_deg or 0.0)
        buffer = ct.create_string_buffer(payload, _CAMERA_LAYOUT.size)
        mask = CAMERA_MASK_POSITION | CAMERA_MASK_TARGETED
        if fov_deg is not None and fov_deg > 0:
            mask |= CAMERA_MASK_FOV
        self._camera_call("SimConnect_CameraSet", buffer, mask)

    @property
    def camera_get_supported(self) -> bool:
        return self._dll is not None and hasattr(self._dll, "SimConnect_CameraGet")

    def camera_get(self, referential: int = CAMERA_REFERENTIAL_SIMOBJECT) -> None:
        """Demande l'état de la caméra active ; la réponse arrive en RECV_ID_CAMERA_DATA."""
        self._camera_call("SimConnect_CameraGet", int(referential))

    def camera_lock_world(self, latitude: float, longitude: float, altitude_m: float) -> None:
        """Demande au simulateur de tenir chargé le décor autour d'un point fixe."""
        point = ct.create_string_buffer(struct.pack("<3d", latitude, longitude, altitude_m), 24)
        self._camera_call(
            "SimConnect_RequestCameraWorldLocker", point, CAMERA_REFERENTIAL_WORLD, OBJECT_ID_USER
        )

    def camera_unlock_world(self) -> None:
        self._camera_call("SimConnect_DeleteCameraWorldLocker")

    def read_towers(self, icaos: Sequence[str], timeout_s: float = 5.0) -> dict[str, tuple[float, float, float]]:
        """Position de la vigie de chaque aérodrome : latitude, longitude, altitude (m).

        Un aérodrome sans tour connue de MSFS (coordonnées nulles) ou inconnu
        est simplement absent du résultat.
        """
        fields = (Field("TOWER_LATITUDE", "f64"), Field("TOWER_LONGITUDE", "f64"), Field("TOWER_ALTITUDE", "f64"))
        definition = FacilityDefinition().open("AIRPORT", TYPE_AIRPORT, fields).close_all()
        towers: dict[str, tuple[float, float, float]] = {}
        for icao in icaos:
            try:
                blocks = self.request(definition, icao, timeout_s)
            except SimConnectError:
                continue
            for name, values in group_blocks(blocks, definition.layouts):
                if name != "AIRPORT":
                    continue
                latitude, longitude = values["TOWER_LATITUDE"], values["TOWER_LONGITUDE"]
                if abs(latitude) > 1e-6 or abs(longitude) > 1e-6:
                    towers[icao] = (latitude, longitude, values["TOWER_ALTITUDE"])
        return towers

    def read_client_data(self, name: str, size: int, timeout_s: float = 3.0) -> bytes:
        """Lit une zone ClientData d'un tiers, par exemple le CDU diffusé par PMDG.

        La zone est nommée par son créateur ; l'identifiant est local au
        client et n'a pas à coïncider avec le sien. Une zone absente revient
        en exception SimConnect, ce qui permet de sonder sans conséquence.
        """
        area_id, definition_id = self._client_data_definition_for(name, size)
        self._next_id += 1
        request_id = self._next_id
        result = self._dll.SimConnect_RequestClientData(
            self._handle, area_id, request_id, definition_id, PERIOD_ONCE, 0, 0, 0, 0,
        )
        if result != 0:
            raise SimConnectError(f"Impossible de demander la zone {name}.")

        pointer = ct.POINTER(_RECV)()
        recv_size = wintypes.DWORD()
        deadline = time.monotonic() + timeout_s
        exceptions: list[int] = []
        while time.monotonic() < deadline:
            if self._dll.SimConnect_GetNextDispatch(
                self._handle, ct.byref(pointer), ct.byref(recv_size)
            ) != 0:
                time.sleep(0.002)
                continue
            recv = pointer.contents
            if recv.dwID == RECV_ID_CLIENT_DATA:
                data = ct.cast(pointer, ct.POINTER(_RECV_SIMOBJECT_DATA)).contents
                if data.dwRequestID != request_id:
                    continue
                payload = ct.string_at(pointer, recv.dwSize)[_PAYLOAD_OFFSET:]
                if len(payload) < size:
                    raise SimConnectError(
                        f"Zone {name} : {len(payload)} octets pour {size} attendus."
                    )
                return payload[:size]
            if recv.dwID == RECV_ID_EXCEPTION:
                exception = ct.cast(pointer, ct.POINTER(_RECV_EXCEPTION)).contents
                if exception.dwException not in exceptions:
                    exceptions.append(exception.dwException)
                deadline = min(deadline, time.monotonic() + EXCEPTION_GRACE_S)
            elif recv.dwID == RECV_ID_QUIT:
                raise SimConnectError("Le simulateur s'est fermé.")
        if exceptions:
            names = ", ".join(EXCEPTION_NAMES.get(code, str(code)) for code in exceptions)
            raise SimConnectRefused(f"SimConnect a refusé la zone {name} ({names}).", exceptions)
        raise SimConnectError(f"Aucune donnée reçue pour la zone {name}.")

    def _client_data_definition_for(self, name: str, size: int) -> tuple[int, int]:
        existing = self._client_data_definitions.get(name)
        if existing is not None:
            return existing
        self._next_id += 1
        area_id = self._next_id
        if self._dll.SimConnect_MapClientDataNameToID(self._handle, name.encode(), area_id) != 0:
            raise SimConnectError(f"Impossible d'associer la zone {name}.")
        self._next_id += 1
        definition_id = self._next_id
        result = self._dll.SimConnect_AddToClientDataDefinition(
            self._handle, definition_id, 0, size, 0.0, SIMCONNECT_UNUSED,
        )
        if result != 0:
            self._dll.SimConnect_ClearClientDataDefinition(self._handle, definition_id)
            raise SimConnectError(f"Impossible de déclarer la zone {name}.")
        self._client_data_definitions[name] = (area_id, definition_id)
        return area_id, definition_id

    def read_string_simvar(self, name: str, timeout_s: float = 3.0) -> str:
        """Lit une SimVar texte fixe de l'avion du joueur.

        Les blocs numériques de NaviXav restent exclusivement en FLOAT64. Le
        titre de l'appareil chargé utilise donc sa propre définition STRING256,
        afin de ne pas décaler la structure binaire des relevés de vol.
        """
        definition_id = self._string_definition_for(name)
        self._next_id += 1
        request_id = self._next_id

        result = self._dll.SimConnect_RequestDataOnSimObject(
            self._handle, request_id, definition_id, OBJECT_ID_USER,
            PERIOD_ONCE, 0, 0, 0, 0,
        )
        if result != 0:
            self._forget_string_definition(name)
            raise SimConnectError(f"Impossible de demander la variable {name}.")

        pointer = ct.POINTER(_RECV)()
        size = wintypes.DWORD()
        deadline = time.monotonic() + timeout_s
        exceptions: list[int] = []

        while time.monotonic() < deadline:
            if self._dll.SimConnect_GetNextDispatch(
                self._handle, ct.byref(pointer), ct.byref(size)
            ) != 0:
                time.sleep(0.002)
                continue

            recv = pointer.contents
            if recv.dwID == RECV_ID_SIMOBJECT_DATA:
                data = ct.cast(pointer, ct.POINTER(_RECV_SIMOBJECT_DATA)).contents
                if data.dwRequestID != request_id:
                    continue
                payload = ct.string_at(pointer, recv.dwSize)[_PAYLOAD_OFFSET:]
                if len(payload) < 256:
                    raise SimConnectError(
                        f"Réponse de {len(payload)} octets pour 256 attendus."
                    )
                return payload[:256].split(b"\0", 1)[0].decode(
                    "utf-8", errors="replace"
                )
            if recv.dwID == RECV_ID_EXCEPTION:
                exception = ct.cast(pointer, ct.POINTER(_RECV_EXCEPTION)).contents
                if exception.dwException not in exceptions:
                    exceptions.append(exception.dwException)
                deadline = min(deadline, time.monotonic() + EXCEPTION_GRACE_S)
            elif recv.dwID == RECV_ID_QUIT:
                raise SimConnectError("Le simulateur s'est fermé.")

        if exceptions:
            self._forget_string_definition(name)
            names = ", ".join(
                EXCEPTION_NAMES.get(code, str(code)) for code in exceptions
            )
            raise SimConnectRefused(
                f"SimConnect a refusé la demande ({names}).", exceptions
            )
        raise SimConnectError(f"Aucune valeur reçue pour {name}.")

    def read_objects(
        self,
        variables: Sequence[tuple[str, str]],
        radius_m: int,
        text_variable: str | None = None,
        object_type: int = SIMOBJECT_TYPE_AIRCRAFT,
        timeout_s: float = 2.0,
    ) -> list[dict[str, Any]]:
        """Énumère les objets d'un type autour de l'avion du joueur.

        Là où `read_simvars` interroge un objet connu, celle-ci demande une
        catégorie : le simulateur répond par autant de messages qu'il a
        d'objets, chacun annonçant son rang et le total. L'avion du joueur en
        fait partie — SimConnect ne l'écarte pas de sa propre énumération — et
        c'est à l'appelant de le reconnaître.

        `text_variable` ajoute une SimVar texte en fin de définition, en
        STRING32 : de quoi porter un indicatif sans allonger la charge de
        chaque appareil de deux cent cinquante octets.

        Un relevé partiel est rendu tel quel plutôt que perdu : mieux vaut la
        moitié du trafic que rien du tout, et le rayon demandé fait de toute
        façon du plus proche le plus utile.
        """
        if not variables:
            return []

        definition_id = self._object_definition_for(variables, text_variable)
        self._next_id += 1
        request_id = self._next_id

        result = self._dll.SimConnect_RequestDataOnSimObjectType(
            self._handle, request_id, definition_id,
            max(0, int(radius_m)), object_type,
        )
        if result != 0:
            self._forget_object_definition(variables, text_variable)
            raise SimConnectError("Impossible d'énumérer les objets du simulateur.")

        numeric = len(variables) * 8
        expected = numeric + (STRING32_SIZE if text_variable else 0)
        found: dict[int, dict[str, Any]] = {}
        total: int | None = None
        pointer = ct.POINTER(_RECV)()
        size = wintypes.DWORD()
        deadline = time.monotonic() + timeout_s
        exceptions: list[int] = []

        while time.monotonic() < deadline:
            if self._dll.SimConnect_GetNextDispatch(
                self._handle, ct.byref(pointer), ct.byref(size)
            ) != 0:
                time.sleep(0.002)
                continue

            recv = pointer.contents
            if recv.dwID == RECV_ID_SIMOBJECT_DATA_BYTYPE:
                data = ct.cast(pointer, ct.POINTER(_RECV_SIMOBJECT_DATA)).contents
                if data.dwRequestID != request_id:
                    continue
                total = int(data.dwoutof)
                if total == 0:
                    return []
                payload = ct.string_at(pointer, recv.dwSize)[_PAYLOAD_OFFSET:]
                if len(payload) < expected:
                    self._forget_object_definition(variables, text_variable)
                    raise SimConnectError(
                        f"Réponse de {len(payload)} octets pour {expected} attendus."
                    )
                values = struct.unpack(f"<{len(variables)}d", payload[:numeric])
                entry: dict[str, Any] = {
                    name: value for (name, _unit), value in zip(variables, values)
                }
                entry["object_id"] = int(data.dwObjectID)
                if text_variable:
                    entry[text_variable] = payload[
                        numeric : numeric + STRING32_SIZE
                    ].split(b"\0", 1)[0].decode("utf-8", errors="replace").strip()
                found[int(data.dwentrynumber)] = entry
                if len(found) >= total:
                    break
            elif recv.dwID == RECV_ID_EXCEPTION:
                exception = ct.cast(pointer, ct.POINTER(_RECV_EXCEPTION)).contents
                if exception.dwException not in exceptions:
                    exceptions.append(exception.dwException)
                deadline = min(deadline, time.monotonic() + EXCEPTION_GRACE_S)
            elif recv.dwID == RECV_ID_QUIT:
                raise SimConnectError("Le simulateur s'est fermé.")

        if exceptions and not found:
            self._forget_object_definition(variables, text_variable)
            names = ", ".join(
                EXCEPTION_NAMES.get(code, str(code)) for code in exceptions
            )
            raise SimConnectRefused(
                f"SimConnect a refusé l'énumération ({names}).", exceptions
            )
        if total is None and not found:
            # Le silence n'est pas une erreur : hors de tout terrain, il n'y a
            # simplement personne dans le rayon demandé.
            return []
        return [found[rank] for rank in sorted(found)]

    def create_ai_aircraft(
        self,
        title: str,
        callsign: str,
        *,
        latitude: float,
        longitude: float,
        altitude_ft: float,
        heading_deg: float,
        airspeed_kt: float,
        on_ground: bool,
        timeout_s: float = 5.0,
    ) -> tuple[int, int]:
        """Crée un non-ATC AI et rend son (RequestID, ObjectID) attribué."""
        self._next_id += 1
        request_id = self._next_id
        position = _DATA_INITPOSITION(
            latitude, longitude, altitude_ft, 0.0, 0.0, heading_deg % 360,
            int(on_ground), max(0, int(round(airspeed_kt))),
        )
        result = self._dll.SimConnect_AICreateNonATCAircraft_EX1(
            self._handle,
            title.encode("utf-8"),
            b"",  # FSLTL est un paquet legacy : la livrée est portée par title.
            callsign[:12].encode("ascii", errors="ignore"),
            position,
            request_id,
        )
        if result != 0:
            raise SimConnectError(f"Impossible de créer l'appareil AI {callsign}.")

        pointer = ct.POINTER(_RECV)()
        size = wintypes.DWORD()
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self._dll.SimConnect_GetNextDispatch(
                self._handle, ct.byref(pointer), ct.byref(size)
            ) != 0:
                time.sleep(0.002)
                continue
            recv = pointer.contents
            if recv.dwID == RECV_ID_ASSIGNED_OBJECT_ID:
                data = ct.cast(pointer, ct.POINTER(_RECV_ASSIGNED_OBJECT_ID)).contents
                if data.dwRequestID != request_id:
                    continue
                object_id = int(data.dwObjectID)
                release_id = request_id + 1
                self._next_id = max(self._next_id, release_id)
                release = self._dll.SimConnect_AIReleaseControl(
                    self._handle, object_id, release_id
                )
                if release != 0:
                    self.remove_ai_object(object_id)
                    raise SimConnectError(
                        f"Impossible de prendre le contrôle de l'appareil AI {callsign}."
                    )
                try:
                    self.freeze_ai_aircraft(object_id)
                except SimConnectError:
                    self.remove_ai_object(object_id)
                    raise
                return request_id, object_id
            if recv.dwID == RECV_ID_EXCEPTION:
                exception = ct.cast(pointer, ct.POINTER(_RECV_EXCEPTION)).contents
                name = EXCEPTION_NAMES.get(exception.dwException, str(exception.dwException))
                raise SimConnectError(f"Création AI refusée ({name}).")
            if recv.dwID == RECV_ID_QUIT:
                raise SimConnectError("Le simulateur s'est fermé.")
        raise SimConnectError(f"Aucun ObjectID reçu pour l'appareil AI {callsign}.")

    def _client_event(self, name: str) -> int:
        """Associe une seule fois un événement MSFS à cette connexion."""
        existing = self._client_events.get(name)
        if existing is not None:
            return existing
        self._next_id += 1
        event_id = self._next_id
        result = self._dll.SimConnect_MapClientEventToSimEvent(
            self._handle, event_id, name.encode("ascii")
        )
        if result != 0:
            raise SimConnectError(f"Impossible de déclarer l'événement AI {name}.")
        self._client_events[name] = event_id
        return event_id

    def freeze_ai_aircraft(self, object_id: int) -> None:
        """Empêche MSFS et NaviXav de déplacer simultanément le même objet."""
        for name in AI_POSITION_FREEZE_EVENTS:
            event_id = self._client_event(name)
            result = self._dll.SimConnect_TransmitClientEvent(
                self._handle,
                int(object_id),
                event_id,
                1,
                SIMCONNECT_GROUP_PRIORITY_HIGHEST,
                SIMCONNECT_EVENT_FLAG_GROUPID_IS_PRIORITY,
            )
            if result != 0:
                raise SimConnectError(
                    f"Impossible de stabiliser l'objet AI {object_id} ({name})."
                )

    def update_ai_aircraft(
        self,
        object_id: int,
        *,
        latitude: float,
        longitude: float,
        altitude_ft: float,
        heading_deg: float,
        airspeed_kt: float,
        on_ground: bool,
    ) -> None:
        """Replace un objet AI connu sans toucher aux objets seulement observés."""
        if self._ai_position_definition is None:
            self._next_id += 1
            definition_id = self._next_id
            result = self._dll.SimConnect_AddToDataDefinition(
                self._handle, definition_id, b"Initial Position", None,
                DATATYPE_INITPOSITION, 0.0, SIMCONNECT_UNUSED,
            )
            if result != 0:
                raise SimConnectError("Impossible de définir la position AI.")
            self._ai_position_definition = definition_id
        position = _DATA_INITPOSITION(
            latitude, longitude, altitude_ft, 0.0, 0.0, heading_deg % 360,
            int(on_ground), max(0, int(round(airspeed_kt))),
        )
        result = self._dll.SimConnect_SetDataOnSimObject(
            self._handle, self._ai_position_definition, int(object_id),
            0, 0, ct.sizeof(position), ct.byref(position),
        )
        if result != 0:
            raise SimConnectError(f"Impossible de mettre à jour l'objet AI {object_id}.")

    def remove_ai_object(self, object_id: int) -> None:
        """Supprime un objet dont l'appelant a établi la propriété."""
        self._next_id += 1
        request_id = self._next_id
        result = self._dll.SimConnect_AIRemoveObject(
            self._handle, int(object_id), request_id
        )
        if result != 0:
            raise SimConnectError(f"Impossible de supprimer l'objet AI {object_id}.")

    def _object_definition_for(
        self, variables: Sequence[tuple[str, str]], text_variable: str | None
    ) -> int:
        """Définition d'énumération, chiffres puis texte, mise en cache.

        Elle est distincte de celle des relevés de vol : le champ texte final
        décalerait la structure purement FLOAT64 sur laquelle ceux-ci
        s'appuient.
        """
        key = (tuple(variables), text_variable)
        existing = self._object_definitions.get(key)
        if existing is not None:
            return existing

        self._next_id += 1
        definition_id = self._next_id
        for name, unit in variables:
            result = self._dll.SimConnect_AddToDataDefinition(
                self._handle, definition_id, name.encode(), unit.encode(),
                DATATYPE_FLOAT64, 0.0, SIMCONNECT_UNUSED,
            )
            if result != 0:
                self._dll.SimConnect_ClearDataDefinition(self._handle, definition_id)
                raise SimConnectError(
                    f"Impossible de déclarer la variable {name} ({unit})."
                )
        if text_variable:
            result = self._dll.SimConnect_AddToDataDefinition(
                self._handle, definition_id, text_variable.encode(), None,
                DATATYPE_STRING32, 0.0, SIMCONNECT_UNUSED,
            )
            if result != 0:
                self._dll.SimConnect_ClearDataDefinition(self._handle, definition_id)
                raise SimConnectError(
                    f"Impossible de déclarer la variable texte {text_variable}."
                )
        self._object_definitions[key] = definition_id
        return definition_id

    def _forget_object_definition(
        self, variables: Sequence[tuple[str, str]], text_variable: str | None
    ) -> None:
        definition_id = self._object_definitions.pop(
            (tuple(variables), text_variable), None
        )
        if definition_id is not None:
            self._dll.SimConnect_ClearDataDefinition(self._handle, definition_id)

    def _definition_for(self, variables: Sequence[tuple[str, str]]) -> int:
        """Renvoie l'identifiant de définition de ce jeu de variables."""
        key = tuple(variables)
        existing = self._simvar_definitions.get(key)
        if existing is not None:
            return existing

        self._next_id += 1
        definition_id = self._next_id
        for name, unit in variables:
            result = self._dll.SimConnect_AddToDataDefinition(
                self._handle, definition_id, name.encode(), unit.encode(),
                DATATYPE_FLOAT64, 0.0, SIMCONNECT_UNUSED,
            )
            if result != 0:
                self._dll.SimConnect_ClearDataDefinition(self._handle, definition_id)
                raise SimConnectError(
                    f"Impossible de déclarer la variable {name} ({unit})."
                )
        self._simvar_definitions[key] = definition_id
        return definition_id

    def _forget_definition(self, variables: Sequence[tuple[str, str]]) -> None:
        definition_id = self._simvar_definitions.pop(tuple(variables), None)
        if definition_id is not None:
            self._dll.SimConnect_ClearDataDefinition(self._handle, definition_id)

    def _string_definition_for(self, name: str) -> int:
        existing = self._string_simvar_definitions.get(name)
        if existing is not None:
            return existing

        self._next_id += 1
        definition_id = self._next_id
        result = self._dll.SimConnect_AddToDataDefinition(
            self._handle, definition_id, name.encode(), None,
            DATATYPE_STRING256, 0.0, SIMCONNECT_UNUSED,
        )
        if result != 0:
            self._dll.SimConnect_ClearDataDefinition(self._handle, definition_id)
            raise SimConnectError(f"Impossible de déclarer la variable texte {name}.")
        self._string_simvar_definitions[name] = definition_id
        return definition_id

    def _forget_string_definition(self, name: str) -> None:
        definition_id = self._string_simvar_definitions.pop(name, None)
        if definition_id is not None:
            self._dll.SimConnect_ClearDataDefinition(self._handle, definition_id)

    def close(self) -> None:
        if self._handle:
            self._dll.SimConnect_Close(self._handle)
            self._handle = ct.c_void_p()
        self._simvar_definitions.clear()
        self._string_simvar_definitions.clear()
        self._object_definitions.clear()
        self._ai_position_definition = None
        self._client_events.clear()

    def __enter__(self) -> "SimConnectClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def group_blocks(
    blocks: Sequence[tuple[int, int, bytes]],
    layouts: dict[int, tuple[Field, ...]],
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Décode chaque bloc selon la disposition déclarée pour son type."""
    for block_type, _index, payload in blocks:
        fields = layouts.get(block_type)
        if not fields or not payload:
            continue
        yield TYPE_NAMES.get(block_type, str(block_type)), decode(payload, fields)


def _declare(dll) -> None:
    """Signatures explicites : indispensables en 64 bits.

    `restype` reste un entier brut plutôt que HRESULT : GetNextDispatch renvoie
    un échec quand la file est vide, ce qui est le cas normal et ne doit pas
    lever d'exception.
    """
    signatures = [
        ("SimConnect_Open",
         [ct.POINTER(ct.c_void_p), ct.c_char_p, ct.c_void_p, ct.c_ulong,
          ct.c_void_p, ct.c_ulong]),
        ("SimConnect_AddToFacilityDefinition",
         [ct.c_void_p, ct.c_ulong, ct.c_char_p]),
        ("SimConnect_RequestFacilityData_EX1",
         [ct.c_void_p, ct.c_ulong, ct.c_ulong, ct.c_char_p, ct.c_char_p, ct.c_char]),
        ("SimConnect_GetNextDispatch",
         [ct.c_void_p, ct.POINTER(ct.POINTER(_RECV)), ct.POINTER(wintypes.DWORD)]),
        ("SimConnect_AddToDataDefinition",
         [ct.c_void_p, ct.c_ulong, ct.c_char_p, ct.c_char_p, ct.c_ulong,
          ct.c_float, ct.c_ulong]),
        ("SimConnect_RequestDataOnSimObject",
         [ct.c_void_p, ct.c_ulong, ct.c_ulong, ct.c_ulong, ct.c_ulong,
          ct.c_ulong, ct.c_ulong, ct.c_ulong, ct.c_ulong]),
        ("SimConnect_RequestDataOnSimObjectType",
         [ct.c_void_p, ct.c_ulong, ct.c_ulong, ct.c_ulong, ct.c_ulong]),
        ("SimConnect_AICreateNonATCAircraft_EX1",
         [ct.c_void_p, ct.c_char_p, ct.c_char_p, ct.c_char_p,
          _DATA_INITPOSITION, ct.c_ulong]),
        ("SimConnect_AIReleaseControl",
         [ct.c_void_p, ct.c_ulong, ct.c_ulong]),
        ("SimConnect_MapClientEventToSimEvent",
         [ct.c_void_p, ct.c_ulong, ct.c_char_p]),
        ("SimConnect_TransmitClientEvent",
         [ct.c_void_p, ct.c_ulong, ct.c_ulong, ct.c_ulong, ct.c_ulong,
          ct.c_ulong]),
        ("SimConnect_SetDataOnSimObject",
         [ct.c_void_p, ct.c_ulong, ct.c_ulong, ct.c_ulong, ct.c_ulong,
          ct.c_ulong, ct.c_void_p]),
        ("SimConnect_AIRemoveObject",
         [ct.c_void_p, ct.c_ulong, ct.c_ulong]),
        ("SimConnect_ClearDataDefinition", [ct.c_void_p, ct.c_ulong]),
        ("SimConnect_MapClientDataNameToID", [ct.c_void_p, ct.c_char_p, ct.c_ulong]),
        ("SimConnect_AddToClientDataDefinition",
         [ct.c_void_p, ct.c_ulong, ct.c_ulong, ct.c_ulong, ct.c_float, ct.c_ulong]),
        ("SimConnect_RequestClientData",
         [ct.c_void_p, ct.c_ulong, ct.c_ulong, ct.c_ulong, ct.c_ulong,
          ct.c_ulong, ct.c_ulong, ct.c_ulong, ct.c_ulong]),
        ("SimConnect_ClearClientDataDefinition", [ct.c_void_p, ct.c_ulong]),
        ("SimConnect_Close", [ct.c_void_p]),
    ]
    # Les structures passées par valeur (caméra, point du décor) le sont par
    # adresse en 64 bits : c_void_p reçoit l'adresse du tampon.
    camera_signatures = [
        ("SimConnect_CameraAcquire", [ct.c_void_p, ct.c_char_p]),
        ("SimConnect_CameraRelease", [ct.c_void_p, ct.c_char_p]),
        ("SimConnect_CameraSet", [ct.c_void_p, ct.c_void_p, ct.c_ulong]),
        ("SimConnect_CameraGetStatus", [ct.c_void_p]),
        ("SimConnect_CameraGet", [ct.c_void_p, ct.c_ulong]),
        ("SimConnect_CameraEnableFlag", [ct.c_void_p, ct.c_ulong]),
        ("SimConnect_SubscribeToCameraStatusUpdate", [ct.c_void_p]),
        ("SimConnect_RequestCameraWorldLocker", [ct.c_void_p, ct.c_void_p, ct.c_int, ct.c_ulong]),
        ("SimConnect_DeleteCameraWorldLocker", [ct.c_void_p]),
    ]
    signatures += [entry for entry in camera_signatures if hasattr(dll, entry[0])]
    for name, argtypes in signatures:
        function = getattr(dll, name)
        function.restype = ct.c_long
        function.argtypes = argtypes

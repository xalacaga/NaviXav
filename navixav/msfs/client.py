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
import struct
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Iterator, Sequence

from navixav.msfs.fields import TYPE_NAMES, Field
from navixav.paths import resource_path

RECV_ID_EXCEPTION = 1
RECV_ID_QUIT = 3
RECV_ID_SIMOBJECT_DATA = 8
RECV_ID_FACILITY_DATA = 28
RECV_ID_FACILITY_DATA_END = 29

# En-tête SIMCONNECT_RECV (3 DWORD) + 7 DWORD, identique pour FACILITY_DATA
# et SIMOBJECT_DATA.
_PAYLOAD_OFFSET = (3 + 7) * 4

DATATYPE_FLOAT64 = 4
PERIOD_ONCE = 1
OBJECT_ID_USER = 0
SIMCONNECT_UNUSED = 0xFFFFFFFF


def _dll_candidates() -> tuple[Path, ...]:
    """Emplacements possibles de la DLL officielle SimConnect."""
    return (
        resource_path("SimConnect", "SimConnect.dll"),
        resource_path("SimConnect.dll"),
        Path(r"C:\MSFS SDK\SimConnect SDK\lib\SimConnect.dll"),
    )


DLL_CANDIDATES = _dll_candidates()

EXCEPTION_NAMES = {
    1: "ERROR", 2: "SIZE_MISMATCH", 3: "UNRECOGNIZED_ID", 4: "UNOPENED",
    5: "VERSION_MISMATCH", 7: "NAME_UNRECOGNIZED", 18: "INVALID_DATA_TYPE",
    19: "INVALID_DATA_SIZE", 20: "DATA_ERROR", 21: "INVALID_ARRAY",
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


def decode(payload: bytes, fields: Sequence[Field]) -> dict[str, Any]:
    """Découpe la charge binaire selon les champs déclarés.

    La taille est vérifiée avant tout découpage : un champ refusé par le
    simulateur raccourcit la charge et décalerait toutes les valeurs
    suivantes. Mieux vaut une erreur franche qu'une donnée fausse.
    """
    expected = sum(field.size for field in fields)
    if len(payload) != expected:
        names = ", ".join(field.name for field in fields)
        raise SimConnectError(
            f"Charge de {len(payload)} octets pour {expected} attendus. "
            f"Un champ a été refusé parmi : {names}"
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
        if self._dll.SimConnect_Open(
            ct.byref(self._handle), b"NaviXav", None, 0, None, 0
        ) != 0:
            raise SimConnectError(
                "Microsoft Flight Simulator ne répond pas. Lance le simulateur "
                "et charge un vol avant d'importer les données."
            )

    # ------------------------------------------------------------------ #

    @staticmethod
    def _load(dll_path: Path | str | None):
        candidates = [Path(dll_path)] if dll_path else list(DLL_CANDIDATES)
        for path in candidates:
            if not path.is_file():
                continue
            dll = ct.WinDLL(str(path))
            _declare(dll)
            return dll
        raise SimConnectError(
            "SimConnect.dll introuvable. Installe le SDK MSFS, ou indique son "
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

    def close(self) -> None:
        if self._handle:
            self._dll.SimConnect_Close(self._handle)
            self._handle = ct.c_void_p()
        self._simvar_definitions.clear()

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
        ("SimConnect_ClearDataDefinition", [ct.c_void_p, ct.c_ulong]),
        ("SimConnect_Close", [ct.c_void_p]),
    ]
    for name, argtypes in signatures:
        function = getattr(dll, name)
        function.restype = ct.c_long
        function.argtypes = argtypes

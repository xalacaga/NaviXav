"""Injecteurs de trafic concurrents, à ne jamais laisser tourner en parallèle.

FSLTL Traffic Injector et AIG Traffic Controller font exactement ce que fait
NaviXav : ils lisent un réseau et créent des objets AI par SimConnect. Deux
injecteurs actifs, ce sont deux appareils pour un seul vol réel, superposés au
même endroit — et ni l'un ni l'autre ne voit les objets de l'autre, puisque
chacun ne possède que les siens.

Rien, dans SimConnect, ne dit qui d'autre est connecté. Le seul indice fiable
est le processus lui-même. On l'énumère donc, sans jamais l'arrêter : couper le
programme d'un tiers ne nous appartient pas. NaviXav renonce à injecter, le dit,
et laisse l'utilisateur choisir lequel des deux il veut.
"""

from __future__ import annotations

import ctypes as ct
import logging
import sys
from ctypes import wintypes
from typing import Iterable

LOGGER = logging.getLogger(__name__)

# Noms relevés sur une installation réelle pour FSLTL, et publiés par AIG pour
# son Traffic Controller. La comparaison est insensible à la casse.
KNOWN_INJECTORS = {
    "fsltl-trafficinjector.exe": "FSLTL Traffic Injector",
    "aigtc.exe": "AIG Traffic Controller",
    "aig traffic controller.exe": "AIG Traffic Controller",
}

TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = ct.c_void_p(-1).value
MAX_PROCESSES = 8192


class _PROCESSENTRY32(ct.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ct.POINTER(ct.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ct.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ct.c_char * 260),
    ]


def process_names() -> tuple[str, ...]:
    """Noms des processus en cours, ou rien si le système ne les donne pas.

    L'énumération n'ouvre aucun processus et ne lit aucune mémoire : elle ne
    demande que la liste des noms, ce qu'un compte sans privilège obtient.
    """
    if sys.platform != "win32":
        return ()
    kernel32 = ct.WinDLL("kernel32", use_last_error=True)
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot in (None, INVALID_HANDLE_VALUE, -1):
        LOGGER.debug("Énumération des processus indisponible")
        return ()
    entry = _PROCESSENTRY32()
    entry.dwSize = ct.sizeof(_PROCESSENTRY32)
    found: list[str] = []
    try:
        if not kernel32.Process32First(snapshot, ct.byref(entry)):
            return ()
        while len(found) < MAX_PROCESSES:
            found.append(entry.szExeFile.decode("latin-1", errors="replace"))
            if not kernel32.Process32Next(snapshot, ct.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snapshot)
    return tuple(found)


def running_injectors(processes: Iterable[str] | None = None) -> tuple[str, ...]:
    """Injecteurs concurrents visibles, nommés comme l'utilisateur les connaît.

    Un relevé impossible rend un tuple vide : mieux vaut injecter que refuser
    sur une énumération qui n'a rien pu dire.
    """
    names = tuple(processes) if processes is not None else process_names()
    seen: list[str] = []
    for name in names:
        label = KNOWN_INJECTORS.get(str(name).strip().casefold())
        if label and label not in seen:
            seen.append(label)
    return tuple(seen)

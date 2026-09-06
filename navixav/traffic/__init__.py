"""Trafic réseau, model matching et injection AI dans MSFS."""

from navixav.traffic.base import (
    GenericFallbackIndex,
    InstallationStatus,
    MatchKind,
    ModelIndex,
    ModelInstallation,
    ResolvedAircraftModel,
    TrafficAircraft,
    TrafficProvider,
)
from navixav.traffic.aig import AigInstallation, AigModelIndex, detect_aig
from navixav.traffic.fsltl import FsltlInstallation, FsltlModelIndex, detect_fsltl

__all__ = [
    "AigInstallation",
    "AigModelIndex",
    "FsltlInstallation",
    "FsltlModelIndex",
    "GenericFallbackIndex",
    "InstallationStatus",
    "MatchKind",
    "ModelIndex",
    "ModelInstallation",
    "ResolvedAircraftModel",
    "TrafficAircraft",
    "TrafficProvider",
    "detect_aig",
    "detect_fsltl",
]

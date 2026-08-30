"""Trafic réseau, model matching et injection AI dans MSFS."""

from navixav.traffic.base import (
    MatchKind,
    ResolvedAircraftModel,
    TrafficAircraft,
    TrafficProvider,
)
from navixav.traffic.fsltl import FsltlInstallation, FsltlModelIndex, detect_fsltl

__all__ = [
    "FsltlInstallation",
    "FsltlModelIndex",
    "MatchKind",
    "ResolvedAircraftModel",
    "TrafficAircraft",
    "TrafficProvider",
    "detect_fsltl",
]

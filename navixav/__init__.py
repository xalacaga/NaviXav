"""NaviXav — compléteur de plan de vol IFR.

Récupère le dernier OFP SimBrief, puis complète les éléments terminaux
manquants (piste, SID, STAR, approche et transitions) à partir d'une base
de navigation locale.
"""

from __future__ import annotations

__version__ = "0.1.0"

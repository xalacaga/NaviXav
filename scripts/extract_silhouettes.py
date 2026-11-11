"""Extrait les tracés des silhouettes plane-watch vers un module JS compact.

Seule la silhouette est gardée : le calque « Reference Artwork » (l'image qui
a servi de calque, non licenciée par plane-watch) et les métadonnées Inkscape
sont retirés. Les transformations de groupes sont conservées telles quelles.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(sys.argv[1])
OUT = Path(sys.argv[2])
SVG = "{http://www.w3.org/2000/svg}"
INK = "{http://www.inkscape.org/namespaces/inkscape}"


def number(value: str) -> str:
    """Nombres raccourcis à 3 décimales : invisible à cette taille, -60 % de poids."""
    return re.sub(r"-?\d+\.\d{4,}", lambda m: f"{float(m.group()):.3f}".rstrip("0").rstrip("."), value)


def shapes(path: Path):
    root = ET.parse(path).getroot()
    view_box = root.get("viewBox")
    out = []

    def walk(node, transforms):
        for child in node:
            tag = child.tag.replace(SVG, "")
            if child.get(f"{INK}label") == "Reference Artwork" or tag in ("image", "metadata", "defs"):
                continue
            if tag.endswith("namedview"):
                continue
            style = child.get("style", "")
            if "display:none" in style.replace(" ", ""):
                continue
            here = transforms + ([child.get("transform")] if child.get("transform") else [])
            if tag == "g":
                walk(child, here)
            elif tag == "path" and child.get("d"):
                out.append({"d": number(child.get("d")), "t": " ".join(here)})
    walk(root, [])
    return view_box, out


airframes = {}
for file in sorted((REPO / "airframes").glob("*.json")):
    data = json.loads(file.read_text(encoding="utf-8"))
    # Le nom du fichier fait foi : B737.json déclare par erreur « B77W ».
    airframes[file.stem] = data

selected = {}
aliases = {}
for code, data in airframes.items():
    type_code = str(data["icao"].get("typeCode") or "")
    if not re.match(r"^L\d[JT]$", type_code):
        continue
    if data.get("aliasOf"):
        aliases[code] = data["aliasOf"]
        continue
    frames = data.get("art", {}).get("frames") or []
    if not frames:
        continue
    source = REPO / frames[0]["src"]
    view_box, paths = shapes(source)
    if paths:
        selected[code] = {"viewBox": view_box, "paths": paths}

vehicle_box, vehicle_paths = shapes(REPO / "silhouettes" / "Airport_Baggage_Tug.svg")
payload = {
    "aircraft": selected,
    "aliases": {k: v for k, v in aliases.items() if v in selected},
    "vehicles": {"baggage_tug": {"viewBox": vehicle_box, "paths": vehicle_paths}},
}
source_commit = sys.argv[3]
header = f"""\"use strict\";

/*
 * Silhouettes d'avions vues de dessus, et tracteur à bagages.
 *
 * Source : plane-watch/pw-silhouettes, commit {source_commit}
 * https://github.com/plane-watch/pw-silhouettes
 * Copyright (c) 2026 Plane Watch Contributors.
 * Licence : Creative Commons Attribution-NonCommercial-ShareAlike 4.0
 * International (https://creativecommons.org/licenses/by-nc-sa/4.0/).
 *
 * Adaptation : seuls les tracés sont repris, sans le calque de référence ni
 * les métadonnées Inkscape, et leurs nombres arrondis à trois décimales. Ce
 * fichier, en tant qu'adaptation, est distribué sous la même licence
 * CC BY-NC-SA 4.0 ; il n'est pas couvert par la licence de NaviXav.
 *
 * Généré par scripts/extract_silhouettes.py ; ne pas modifier à la main.
 */
const SILHOUETTES = """
OUT.write_text(header + json.dumps(payload, separators=(",", ":")) + ";\n", encoding="utf-8")
print(len(selected), "avions,", len(payload["aliases"]), "alias,", f"{OUT.stat().st_size / 1024:.0f} Ko")
print(" ".join(sorted(selected)))

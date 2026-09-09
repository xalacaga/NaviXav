"""Documentation PDF locale des paquets d'avions Community."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from functools import lru_cache
from pathlib import Path

from navixav.aircraft.community import read_aircraft

LOGGER = logging.getLogger(__name__)


def matching_packages(packages: dict[Path, dict], title: str, icao: str) -> dict[Path, dict]:
    """Retient l'avion SimBrief, jamais un autre type ni un éditeur arbitraire."""
    normalise = lambda value: " ".join(re.findall(r"[a-z0-9]+", value.casefold()))
    wanted = normalise(title)
    code = icao.strip().upper()
    if not wanted and not code:
        return {}
    exact = {root: item for root, item in packages.items()
             if (not code or code in item["icaos"]) and wanted and any(normalise(value) == wanted
                               for value in item["titles"] + item["labels"])}
    if len(exact) == 1:
        return exact
    candidates = exact or {root: item for root, item in packages.items()
                  if code and code in item["icaos"]}
    if not candidates:
        return {}
    # Le nom du profil peut préciser l'éditeur (Fenix, iniBuilds, etc.). Les
    # termes génériques et le type ICAO ne départagent pas deux add-ons.
    words = {word for word in wanted.split() if not any(char.isdigit() for char in word)}
    words -= {"airbus", "boeing", "aircraft", "airplane", "neo", "ceo", code.lower()}
    ranked = [(len(words & set(normalise(" ".join(
        [item["package"], *item["labels"], *item["titles"]])).split())), root, item)
        for root, item in candidates.items()]
    best = max(score for score, _, _ in ranked)
    candidates = {root: item for score, root, item in ranked if score == best}
    # Avec un profil générique partagé par plusieurs fournisseurs, ne pas
    # afficher la documentation d'un fournisseur choisi au hasard.
    providers = {normalise(item["package"]).split()[0] for item in candidates.values()}
    return candidates if len(candidates) == 1 or (best and len(providers) == 1) else {}


def document_inventory(folders: list[Path], title: str | None = None, icao: str = "") -> tuple[list[dict], dict[str, tuple[Path, Path]]]:
    """Conserve les paquets distincts, même pour deux variantes du même modèle.

    Les jonctions de paquets (Addons Linker) sont acceptées. Les liens internes
    ne peuvent pas conduire hors du paquet ni créer une boucle de parcours.
    """
    started = time.monotonic()
    packages: dict[Path, dict] = {}
    files: dict[str, tuple[Path, Path]] = {}
    for folder in folders:
        for config in sorted(folder.glob("*/SimObjects/Airplanes/*/aircraft.cfg")):
            try:
                root = config.parents[3].resolve(strict=True)
                aircraft = read_aircraft(config.parent, config.parents[3].name)
                if aircraft is None:
                    continue
                package = packages.setdefault(root, {
                    "package": config.parents[3].name, "labels": [], "titles": [],
                    "icaos": [], "manufacturers": [], "documents": [],
                })
                for key, values in (("labels", [aircraft.label]),
                                    ("titles", aircraft.titles), ("icaos", [aircraft.icao]),
                                    ("manufacturers", [aircraft.manufacturer.casefold()])):
                    package[key] = list(dict.fromkeys(package[key] + list(values)))
            except (OSError, RuntimeError):
                LOGGER.warning("Lecture d'un paquet avion impossible", exc_info=True)

    if title is not None:
        packages = matching_packages(packages, title, icao)
    for root, package in packages.items():
        visited: set[Path] = set()
        for directory, dirs, names in os.walk(root, followlinks=False):
            base = Path(directory)
            try:
                resolved = base.resolve(strict=True)
                if not resolved.is_relative_to(root) or resolved in visited:
                    dirs[:] = []
                    continue
                visited.add(resolved)
                # Écarte aussi les jonctions Windows vers un autre dossier.
                safe_dirs = []
                for name in dirs:
                    try:
                        target = (base / name).resolve(strict=True)
                        if target.is_relative_to(root) and target not in visited:
                            safe_dirs.append(name)
                    except (OSError, RuntimeError):
                        continue
                dirs[:] = safe_dirs
                for name in names:
                    if Path(name).suffix.lower() != ".pdf":
                        continue
                    path = base / name
                    try:
                        target = path.resolve(strict=True)
                        if not target.is_relative_to(root) or not target.is_file():
                            continue
                        size = target.stat().st_size
                    except (OSError, RuntimeError):
                        continue
                    token = hashlib.sha256(str(path).encode("utf-8")).hexdigest()
                    files[token] = (root, path)
                    package["documents"].append({
                        "id": token, "name": name,
                        "relative_path": path.relative_to(root).as_posix(), "size": size,
                        "url": f"/api/aircraft/documents/{token}",
                    })
            except (OSError, RuntimeError):
                LOGGER.warning("Lecture de la documentation avion impossible", exc_info=True)
        package["documents"].sort(key=lambda doc: doc["relative_path"].casefold())
    LOGGER.info("Documentation avion : %d paquets, %d PDF en %.3fs",
                len(packages), len(files), time.monotonic() - started)
    return sorted(packages.values(), key=lambda item: item["labels"][0].casefold()), files


def checked_document(root: Path, path: Path) -> Path:
    """Revérifie les liens à l'ouverture ; aucun chemin client n'est accepté."""
    target = path.resolve(strict=True)
    if not target.is_relative_to(root) or target.suffix.lower() != ".pdf":
        raise ValueError("Document hors du paquet")
    with target.open("rb") as stream:
        if not stream.read(1024).lstrip().startswith(b"%PDF-"):
            raise ValueError("Document PDF invalide")
    return target


@lru_cache(maxsize=3)
def _document_text(path: Path, modified: int, size: int) -> tuple[str, ...]:
    # Le cache est uniquement en mémoire et invalidé si le manuel change.
    from pypdf import PdfReader

    started = time.monotonic()
    with path.open("rb") as stream:
        reader = PdfReader(stream)
        pages = tuple(re.sub(r"\s+", " ", page.extract_text() or "").strip()
                      for page in reader.pages)
    LOGGER.info("Indexation PDF avion : %d pages en %.3fs", len(pages), time.monotonic() - started)
    return pages


def search_document(path: Path, query: str) -> dict:
    stat = path.stat()
    pages = _document_text(path, stat.st_mtime_ns, stat.st_size)
    pattern = re.compile(re.escape(" ".join(query.split())), re.IGNORECASE)
    matches = []
    total = 0
    for number, text in enumerate(pages, 1):
        for match in pattern.finditer(text):
            total += 1
            if len(matches) < 100:
                start, end = max(0, match.start() - 65), min(len(text), match.end() + 100)
                matches.append({"page": number, "snippet":
                    ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")})
    return {"matches": matches, "total": total, "pages": len(pages),
            "text_available": any(pages), "limited": total > len(matches)}

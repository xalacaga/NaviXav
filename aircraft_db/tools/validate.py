"""Validateur de la NaviXav Aircraft Database.

Sans dépendance et sans réseau : la base doit rester vérifiable par un
contributeur qui n'a pas installé NaviXav.

    python aircraft_db/tools/validate.py [racine]

Le contrôle central est celui du vocabulaire : une procédure ne peut observer
qu'une propriété déclarée dans `schema/properties.json`. C'est ce qui garantit
qu'aucune procédure ne dépend d'un avion, d'un addon ou d'une SimVar.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PHASES = frozenset(
    {
        "cold_and_dark",
        "preflight",
        "before_start",
        "start",
        "after_start",
        "taxi",
        "before_takeoff",
        "takeoff",
        "after_takeoff",
        "climb",
        "cruise",
        "descent",
        "approach",
        "landing",
        "after_landing",
        "shutdown",
    }
)

KINDS = frozenset({"normal", "abnormal", "emergency"})
MODES = frozenset({"auto", "manual", "info"})

# Une condition porte exactement un comparateur.
COMPARATORS = frozenset({"is", "at_least", "at_most", "between", "one_of"})
COMBINATORS = frozenset({"all_of", "any_of", "not"})

AIRCRAFT_FILES = (
    "metadata.json",
    "systems.json",
    "procedures.json",
    "limitations.json",
    "mapping.json",
)

METADATA_REQUIRED = (
    "id",
    "manufacturer",
    "family",
    "model",
    "category",
    "engine_count",
    "propulsion",
    "match",
)


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_number(value: Any) -> bool:
    # `bool` est un `int` en Python : sans ce garde, `true` passerait pour un
    # nombre et une comparaison numérique sur un booléen serait acceptée.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class Validator:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.errors: list[str] = []
        self.properties: dict[str, dict[str, Any]] = {}
        self.systems: frozenset[str] = frozenset()

    # ------------------------------------------------------------------ #

    def fail(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}")

    def load(self, path: Path) -> Any | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.fail(self._label(path), "fichier absent")
        except json.JSONDecodeError as exc:
            self.fail(self._label(path), f"JSON invalide ({exc})")
        return None

    def _label(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    # ------------------------------------------------------------------ #

    def run(self) -> list[str]:
        self.check_version()
        self.load_vocabulary()
        if self.errors:
            # Sans vocabulaire, tout le reste produirait du bruit.
            return self.errors

        directories = self.aircraft_directories()
        if not directories:
            self.fail("aircraft/", "aucun avion trouvé")
        for directory in directories:
            self.check_aircraft(directory)
        return self.errors

    def check_version(self) -> None:
        path = self.root / "VERSION.json"
        # Une base d'appoint — celle de l'utilisateur — n'a pas de version
        # propre : elle complète la base livrée, elle ne la remplace pas.
        if not path.is_file():
            return
        data = self.load(path)
        if data is None:
            return
        if not isinstance(data.get("version"), str):
            self.fail("VERSION.json", "`version` doit être une chaîne")
        if not isinstance(data.get("schema_version"), int):
            self.fail("VERSION.json", "`schema_version` doit être un entier")

    def load_vocabulary(self) -> None:
        # Le vocabulaire appartient au format, pas à la base : une base
        # d'appoint n'a pas à le recopier pour être vérifiable.
        path = self.root / "schema" / "properties.json"
        if not path.is_file():
            path = Path(__file__).resolve().parent.parent / "schema" / "properties.json"
        data = self.load(path)
        if data is None:
            return
        properties = data.get("properties")
        if not isinstance(properties, dict) or not properties:
            self.fail("schema/properties.json", "`properties` doit être un objet non vide")
            return
        systems = data.get("systems")
        if not isinstance(systems, list) or not systems:
            self.fail("schema/properties.json", "`systems` doit être une liste non vide")
            return

        self.properties = properties
        self.systems = frozenset(systems)

        for name, spec in properties.items():
            where = f"schema/properties.json[{name}]"
            if spec.get("type") not in {"boolean", "number", "integer"}:
                self.fail(where, "`type` doit valoir boolean, number ou integer")
            if not isinstance(spec.get("source"), str):
                self.fail(where, "`source` manquant")
            required = spec.get("requires_system")
            if required is not None and required not in self.systems:
                self.fail(where, f"système inconnu « {required} »")

    def aircraft_directories(self) -> list[Path]:
        base = self.root / "aircraft"
        if not base.is_dir():
            return []
        return sorted(p.parent for p in base.glob("*/*/metadata.json"))

    # ------------------------------------------------------------------ #

    def check_aircraft(self, directory: Path) -> None:
        label = self._label(directory)
        for name in AIRCRAFT_FILES:
            if not (directory / name).is_file():
                self.fail(label, f"{name} manquant")

        self.check_metadata(directory)
        declared = self.check_systems(directory)
        self.check_procedures(directory, declared)
        self.check_mapping(directory, declared)
        self.check_limitations(directory)

    def check_metadata(self, directory: Path) -> None:
        path = directory / "metadata.json"
        data = self.load(path)
        if data is None:
            return
        where = self._label(path)

        for key in METADATA_REQUIRED:
            if key not in data:
                self.fail(where, f"`{key}` manquant")

        expected_id = "/".join(directory.parts[-2:])
        if data.get("id") != expected_id:
            self.fail(where, f"`id` doit valoir « {expected_id} »")

        # `authored` : procédures écrites depuis le manuel de l'appareil.
        # `draft` : canevas de classe, juste pour le type mais pas pour le modèle.
        # La distinction doit être lisible par l'interface, pas seulement par un
        # commentaire — un pilote a le droit de savoir ce qu'il lit.
        maturity = data.get("maturity")
        if maturity not in {"draft", "authored"}:
            self.fail(where, "`maturity` doit valoir draft ou authored")

        match = data.get("match")
        if not isinstance(match, dict):
            self.fail(where, "`match` doit être un objet")
            return
        self.check_patterns(where, match, required=True)
        if not isinstance(match.get("priority"), int):
            self.fail(where, "`match.priority` doit être un entier")

    def check_patterns(self, where: str, match: dict[str, Any], *, required: bool) -> None:
        """Contrôle les listes de motifs d'un bloc `match`.

        `title_contains` et `title_also_contains` sont deux disjonctions : au
        moins un motif de chaque liste présente doit apparaître dans le titre.
        C'est ce « et » entre les deux listes qui distingue une variante d'une
        famille.
        """
        for key in ("title_contains", "title_also_contains"):
            patterns = match.get(key)
            if patterns is None:
                if key == "title_contains" and required:
                    self.fail(where, f"`match.{key}` doit être une liste non vide")
                continue
            if not isinstance(patterns, list) or not patterns:
                self.fail(where, f"`match.{key}` doit être une liste non vide")
                continue
            for pattern in patterns:
                if not isinstance(pattern, str) or not pattern:
                    self.fail(where, f"`match.{key}` doit contenir des chaînes")
                elif pattern != pattern.lower():
                    # La comparaison se fait en minuscules côté moteur ; un motif
                    # capitalisé ne matcherait jamais.
                    self.fail(where, f"motif « {pattern} » doit être en minuscules")

    def check_systems(self, directory: Path) -> dict[str, bool]:
        path = directory / "systems.json"
        data = self.load(path)
        if data is None:
            return {}
        where = self._label(path)

        systems = data.get("systems")
        if not isinstance(systems, dict):
            self.fail(where, "`systems` doit être un objet")
            return {}

        declared: dict[str, bool] = {}
        for name, value in systems.items():
            if name not in self.systems:
                self.fail(where, f"système inconnu « {name} »")
                continue
            if not _is_bool(value):
                self.fail(where, f"« {name} » doit être un booléen")
                continue
            declared[name] = value

        missing = sorted(self.systems - set(systems))
        if missing:
            self.fail(where, f"systèmes non déclarés : {', '.join(missing)}")
        return declared

    def check_procedures(self, directory: Path, declared: dict[str, bool]) -> None:
        path = directory / "procedures.json"
        data = self.load(path)
        if data is None:
            return
        where = self._label(path)

        procedures = data.get("procedures")
        if not isinstance(procedures, list) or not procedures:
            self.fail(where, "`procedures` doit être une liste non vide")
            return

        seen_ids: set[str] = set()
        for index, procedure in enumerate(procedures):
            if not isinstance(procedure, dict):
                self.fail(where, f"procédure #{index} n'est pas un objet")
                continue

            identifier = procedure.get("id")
            scope = f"{where}[{identifier or index}]"
            if not isinstance(identifier, str) or not identifier:
                self.fail(scope, "`id` manquant")
            elif identifier in seen_ids:
                self.fail(scope, "`id` en double")
            else:
                seen_ids.add(identifier)

            if procedure.get("phase") not in PHASES:
                self.fail(scope, f"phase inconnue « {procedure.get('phase')} »")
            if procedure.get("kind") not in KINDS:
                self.fail(scope, f"`kind` inconnu « {procedure.get('kind')} »")
            if not isinstance(procedure.get("title"), str):
                self.fail(scope, "`title` manquant")

            steps = procedure.get("steps")
            if not isinstance(steps, list) or not steps:
                self.fail(scope, "`steps` doit être une liste non vide")
                continue

            seen_steps: set[str] = set()
            for position, step in enumerate(steps):
                self.check_step(scope, position, step, seen_steps, declared)

    def check_step(
        self,
        scope: str,
        position: int,
        step: Any,
        seen: set[str],
        declared: dict[str, bool],
    ) -> None:
        if not isinstance(step, dict):
            self.fail(scope, f"étape #{position} n'est pas un objet")
            return

        identifier = step.get("id")
        where = f"{scope}.{identifier or position}"
        if not isinstance(identifier, str) or not identifier:
            self.fail(where, "`id` manquant")
        elif identifier in seen:
            self.fail(where, "`id` en double dans la procédure")
        else:
            seen.add(identifier)

        if not isinstance(step.get("title"), str) or not step.get("title"):
            self.fail(where, "`title` manquant")

        mode = step.get("mode")
        if mode not in MODES:
            self.fail(where, f"mode inconnu « {mode} »")
            return

        required = step.get("requires_system")
        if required is not None and required not in self.systems:
            self.fail(where, f"système inconnu « {required} »")
            required = None

        group = step.get("group")
        if group is not None and (not isinstance(group, str) or not group):
            self.fail(where, "`group` doit être une chaîne non vide")

        note = step.get("note")
        if note is not None:
            if not isinstance(note, dict) or not note:
                self.fail(where, "`note` doit être un objet localisé non vide")
            elif "en" not in note:
                self.fail(where, "`note` doit au moins porter la clé « en »")

        check = step.get("check")
        if mode == "auto":
            if check is None:
                self.fail(where, "une étape `auto` doit porter un `check`")
            else:
                self.check_condition(where, check, declared, required)
        elif check is not None:
            self.fail(where, f"une étape `{mode}` ne doit pas porter de `check`")

    def check_condition(
        self,
        where: str,
        condition: Any,
        declared: dict[str, bool],
        waived: str | None,
        depth: int = 0,
    ) -> None:
        if depth > 8:
            self.fail(where, "condition trop imbriquée")
            return
        if not isinstance(condition, dict) or not condition:
            self.fail(where, "condition invalide")
            return

        present = COMBINATORS & set(condition)
        if present:
            if len(condition) != 1:
                self.fail(where, "un combinateur doit être seul dans son objet")
                return
            name = next(iter(present))
            branches = condition[name]
            if name == "not":
                self.check_condition(where, branches, declared, waived, depth + 1)
                return
            if not isinstance(branches, list) or not branches:
                self.fail(where, f"`{name}` doit être une liste non vide")
                return
            for branch in branches:
                self.check_condition(where, branch, declared, waived, depth + 1)
            return

        name = condition.get("property")
        if not isinstance(name, str):
            self.fail(where, "`property` manquant")
            return
        spec = self.properties.get(name)
        if spec is None:
            self.fail(where, f"propriété hors vocabulaire « {name} »")
            return

        # Une procédure ne doit pas observer un système que l'avion n'a pas :
        # la propriété resterait muette pour toujours et l'étape ne se
        # cocherait jamais. L'étape peut lever le contrôle avec
        # `requires_system`, puisqu'elle disparaît alors de la checklist.
        needed = spec.get("requires_system")
        if needed is not None and needed != waived and declared.get(needed) is False:
            self.fail(
                where,
                f"« {name} » exige le système « {needed} », déclaré absent ; "
                "ajoute `requires_system` à l'étape ou retire la vérification",
            )

        operators = COMPARATORS & set(condition)
        if len(operators) != 1:
            self.fail(where, f"il faut exactement un comparateur, {len(operators)} trouvé(s)")
            return

        operator = next(iter(operators))
        value = condition[operator]
        kind = spec.get("type")

        if operator == "is":
            if kind == "boolean" and not _is_bool(value):
                self.fail(where, f"« {name} » est booléen : `is` attend true ou false")
            elif kind in {"number", "integer"} and not _is_number(value):
                self.fail(where, f"« {name} » est numérique : `is` attend un nombre")
        elif operator in {"at_least", "at_most"}:
            if kind == "boolean":
                self.fail(where, f"« {name} » est booléen : `{operator}` n'a pas de sens")
            elif not _is_number(value):
                self.fail(where, f"`{operator}` attend un nombre")
        elif operator == "between":
            if kind == "boolean":
                self.fail(where, f"« {name} » est booléen : `between` n'a pas de sens")
            elif (
                not isinstance(value, list)
                or len(value) != 2
                or not all(_is_number(item) for item in value)
            ):
                self.fail(where, "`between` attend deux nombres")
            elif value[0] > value[1]:
                self.fail(where, "`between` attend [minimum, maximum]")
        elif operator == "one_of":
            if not isinstance(value, list) or not value:
                self.fail(where, "`one_of` attend une liste non vide")
            elif kind == "boolean":
                self.fail(where, f"« {name} » est booléen : `one_of` n'a pas de sens")
            elif not all(_is_number(item) for item in value):
                self.fail(where, "`one_of` attend des nombres")

    def check_mapping(self, directory: Path, declared: dict[str, bool]) -> None:
        path = directory / "mapping.json"
        data = self.load(path)
        if data is None:
            return
        where = self._label(path)

        variants = data.get("variants")
        if not isinstance(variants, list) or not variants:
            self.fail(where, "`variants` doit être une liste non vide")
            return

        seen: set[str] = set()
        for index, variant in enumerate(variants):
            if not isinstance(variant, dict):
                self.fail(where, f"variante #{index} n'est pas un objet")
                continue
            identifier = variant.get("id")
            scope = f"{where}[{identifier or index}]"
            if not isinstance(identifier, str) or not identifier:
                self.fail(scope, "`id` manquant")
            elif identifier in seen:
                self.fail(scope, "`id` en double")
            else:
                seen.add(identifier)

            match = variant.get("match")
            if not isinstance(match, dict) or not match:
                self.fail(scope, "`match` doit être un objet non vide")
            else:
                self.check_patterns(scope, match, required=False)

            systems = variant.get("systems", {})
            if not isinstance(systems, dict):
                self.fail(scope, "`systems` doit être un objet")
            else:
                for name, value in systems.items():
                    if name not in self.systems:
                        self.fail(scope, f"système inconnu « {name} »")
                    elif not _is_bool(value):
                        self.fail(scope, f"« {name} » doit être un booléen")

            overrides = variant.get("overrides", {})
            if not isinstance(overrides, dict):
                self.fail(scope, "`overrides` doit être un objet")
            else:
                for name, override in overrides.items():
                    self.check_override(scope, name, override)

        default = data.get("default_variant")
        if default is not None and default not in seen:
            self.fail(where, f"`default_variant` inconnu « {default} »")

    def check_override(self, scope: str, name: str, override: Any) -> None:
        """Contrôle une source de remplacement déclarée par une variante.

        Une LVar est toujours lue comme un nombre. `as` dit comment la ramener
        au type de la propriété : un booléen se déduit d'un seuil ou du non-nul,
        un nombre passe par `offset`, puis `scale`, puis `clamp`.
        """
        spec = self.properties.get(name)
        if spec is None:
            self.fail(scope, f"propriété hors vocabulaire « {name} »")
            return
        where = f"{scope}.overrides[{name}]"

        if not isinstance(override, dict):
            self.fail(where, "un override doit être un objet")
            return
        if not isinstance(override.get("lvar"), str) or not override["lvar"]:
            self.fail(where, "`lvar` manquant")

        conversion = override.get("as")
        if conversion not in {"boolean", "integer", "number"}:
            self.fail(where, "`as` doit valoir boolean, integer ou number")
            return

        kind = spec.get("type")
        if (kind == "boolean") != (conversion == "boolean"):
            self.fail(
                where,
                f"« {name} » est de type {kind} : `as` ne peut pas valoir {conversion}",
            )

        numeric_keys = {"offset", "scale", "clamp"} & set(override)
        threshold_keys = {"below", "above"} & set(override)

        if conversion == "boolean":
            if numeric_keys:
                self.fail(where, f"`{', '.join(sorted(numeric_keys))}` n'a pas de sens sur un booléen")
            if len(threshold_keys) > 1:
                self.fail(where, "`below` et `above` s'excluent")
            for key in threshold_keys:
                if not _is_number(override[key]):
                    self.fail(where, f"`{key}` attend un nombre")
            return

        if threshold_keys:
            self.fail(where, f"`{', '.join(sorted(threshold_keys))}` ne s'applique qu'à un booléen")
        for key in ("offset", "scale"):
            if key in override and not _is_number(override[key]):
                self.fail(where, f"`{key}` attend un nombre")
        clamp = override.get("clamp")
        if clamp is not None:
            if (
                not isinstance(clamp, list)
                or len(clamp) != 2
                or not all(_is_number(item) for item in clamp)
            ):
                self.fail(where, "`clamp` attend deux nombres")
            elif clamp[0] > clamp[1]:
                self.fail(where, "`clamp` attend [minimum, maximum]")

    def check_limitations(self, directory: Path) -> None:
        path = directory / "limitations.json"
        data = self.load(path)
        if data is None:
            return
        where = self._label(path)
        if not isinstance(data.get("source"), str):
            self.fail(where, "`source` manquant : une limitation sans origine n'est pas exploitable")
        if not isinstance(data.get("speeds"), dict):
            self.fail(where, "`speeds` doit être un objet")


def validate_database(root: Path) -> list[str]:
    """Renvoie la liste des défauts, vide si la base est conforme."""
    return Validator(Path(root)).run()


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    errors = validate_database(root)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"\n{len(errors)} défaut(s).", file=sys.stderr)
        return 1
    print(f"Base conforme : {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

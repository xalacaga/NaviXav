"""Moteur de complétion : SimBrief + navdata -> plan de vol terminal complet.

Principe de chaînage, celui qu'utilise un FMS :

    SID  --[fix de sortie]-->  premier point en route
    dernier point en route  --[fix d'entrée]-->  STAR
    STAR --[fix de sortie]-->  transition d'approche  -->  approche

Chaque maillon retrouvé par égalité de fix donne une confiance élevée ; un
maillon reconstitué par géométrie donne une confiance modérée, et l'absence de
lien une confiance faible. Le moteur ne masque jamais un choix incertain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from navixav.config import Settings
from navixav.constraints import format_altitude, procedure_constraints, procedure_path
from navixav.geo import distance_nm
from navixav.models import (
    ArrivalBlock,
    Choice,
    Confidence,
    DepartureBlock,
    EnrouteBlock,
    FlightPlan,
    RunwayChoice,
    WindInfo,
)
from navixav.navdata.base import (
    NavdataProvider,
    Procedure,
    ProcedureKind,
    Runway,
    normalise_runway,
)
from navixav.planner.runway import RunwayScore, margin_between_best_two, score_runways
from navixav.preferences import AirportPreferences
from navixav.simbrief.parser import OfpSummary
from navixav.weather.metar import fetch_metar, parse_wind

VECTORS = "VECTORS"


@dataclass
class PlannerOverrides:
    """Forçages manuels ; chaque champ renseigné court-circuite le moteur."""

    departure_runway: str | None = None
    sid: str | None = None
    sid_transition: str | None = None
    arrival_runway: str | None = None
    star: str | None = None
    star_transition: str | None = None
    approach: str | None = None
    approach_transition: str | None = None
    departure_metar: str | None = None
    arrival_metar: str | None = None
    prefer_ils: bool = True
    # None = valeur de la configuration ; sinon force la capacité RNP de l'avion.
    rnp_capable: bool | None = None


@dataclass
class _Candidate:
    procedure: Procedure
    score: float
    reason: str
    confidence: Confidence
    linking_fix: str | None = None
    transition_ident: str | None = None


class CompletionEngine:
    def __init__(
        self,
        provider: NavdataProvider,
        settings: Settings,
        preferences: AirportPreferences | None = None,
    ) -> None:
        self.provider = provider
        self.settings = settings
        self.preferences = preferences or AirportPreferences.load(
            settings.airport_preferences_path
        )
        self._warnings: list[str] = []

    # ------------------------------------------------------------------ #
    # Entrée principale
    # ------------------------------------------------------------------ #

    def complete(
        self, ofp: OfpSummary, overrides: PlannerOverrides | None = None
    ) -> FlightPlan:
        overrides = overrides or PlannerOverrides()
        self._warnings = []

        plan = FlightPlan(
            source={
                "simbrief": True,
                "simbrief_generated_at": ofp.generated_at.isoformat()
                if ofp.generated_at
                else None,
                "simbrief_airac": ofp.airac or None,
                "navdata_source": self.provider.source_name,
                "navdata_airac": self.provider.airac_cycle,
            },
            aircraft=ofp.aircraft_icao,
            aircraft_name=ofp.aircraft_name,
            callsign=ofp.callsign,
            alternate_icao=ofp.alternate_icao,
            dispatch=ofp.dispatch,
        )

        self._check_airac_alignment(ofp)

        route_legs = [dict(leg) for leg in ofp.enroute_route]
        route_path: list[dict] = []
        origin = self.provider.airport(ofp.origin_icao)
        if origin is not None:
            route_path.append({
                "ident": origin.ident, "lat": origin.lat, "lon": origin.lon, "via": "",
            })
        for leg in route_legs:
            position = self.provider.fix_position(leg["to"])
            if position is not None:
                leg["lat"], leg["lon"] = position
                route_path.append({
                    "ident": leg["to"],
                    "lat": position[0],
                    "lon": position[1],
                    "via": leg["via"],
                })
        destination = self.provider.airport(ofp.destination_icao)
        if destination is not None:
            route_path.append({
                "ident": destination.ident,
                "lat": destination.lat,
                "lon": destination.lon,
                "via": "",
            })

        plan.enroute = EnrouteBlock(
            raw_simbrief_route=ofp.route,
            first_fix=ofp.first_enroute_fix,
            last_fix=ofp.last_enroute_fix,
            waypoints=ofp.enroute_fixes,
            route_legs=route_legs,
            route_path=route_path,
            cruise_altitude_ft=ofp.cruise_altitude_ft,
        )

        plan.departure = self._build_departure(ofp, overrides)
        plan.arrival = self._build_arrival(ofp, overrides)
        plan.warnings = self._warnings
        return plan

    # ------------------------------------------------------------------ #
    # Départ
    # ------------------------------------------------------------------ #

    def _build_departure(
        self, ofp: OfpSummary, overrides: PlannerOverrides
    ) -> DepartureBlock:
        icao = ofp.origin_icao
        airport = self.provider.airport(icao)
        block = DepartureBlock(icao=icao, name=airport.name if airport else "")
        if airport is None:
            self._warn(f"{icao} absent de la base de navigation.")
            return block

        block.transition_altitude_ft = airport.transition_altitude_ft
        block.wind = self._wind_for(icao, overrides.departure_metar, ofp.origin_metar)

        runways = self.provider.runways(icao)
        block.runway = self._choose_runway(
            icao=icao,
            runways=runways,
            wind=block.wind,
            for_landing=False,
            forced=overrides.departure_runway,
            simbrief_runway=ofp.origin_planned_runway,
        )
        if block.runway is None or not block.runway.choice.value:
            self._warn(f"Aucune piste de départ déterminable à {icao}.")
            return block

        runway_name = block.runway.choice.value
        sids = self.provider.procedures(icao, ProcedureKind.SID)
        if not sids:
            self._warn(f"Aucune SID publiée pour {icao} dans la base.")
            block.sid = Choice(None, Confidence.NONE, reason="aucune SID en base")
            return block

        # Le point que la SID doit atteindre : celui filé par SimBrief en fin
        # de bloc SID, sinon le premier point en route.
        target_fix = ofp.sid_exit_hint or ofp.first_enroute_fix
        block.sid, block.sid_transition = self._choose_departure_procedure(
            sids=sids,
            runway_name=runway_name,
            target_fix=target_fix,
            simbrief_name=ofp.simbrief_sid,
            forced_name=overrides.sid,
            forced_transition=overrides.sid_transition,
        )

        selected = _find_by_ident(sids, block.sid.value) if block.sid.value else None
        if selected is not None:
            # La transition d'une SID se parcourt après la procédure.
            block.sid_constraints = procedure_constraints(
                selected, block.sid_transition.value, transition_first=False
            )
            block.sid_path = procedure_path(
                selected,
                block.sid_transition.value,
                transition_first=False,
                position_lookup=self.provider.fix_position,
            )
        return block

    def _choose_departure_procedure(
        self,
        sids: list[Procedure],
        runway_name: str,
        target_fix: str | None,
        simbrief_name: str | None,
        forced_name: str | None,
        forced_transition: str | None,
    ) -> tuple[Choice, Choice]:
        compatible = [p for p in sids if p.serves_runway(runway_name)]
        if not compatible:
            self._warn(
                f"Aucune SID compatible avec la piste {runway_name} ; "
                "recherche élargie à toutes les pistes."
            )
            compatible = sids

        if forced_name:
            picked = _find_by_ident(compatible, forced_name) or _find_by_ident(
                sids, forced_name
            )
            if picked is None:
                self._warn(f"SID forcée « {forced_name} » introuvable en base.")
                return (
                    Choice(forced_name, Confidence.LOW, "utilisateur", "forcée, non vérifiée"),
                    Choice(forced_transition, Confidence.LOW, "utilisateur"),
                )
            return self._departure_choice_from(
                picked, target_fix, forced_transition, "utilisateur",
                Confidence.HIGH, "SID imposée",
            )

        if simbrief_name:
            picked = _find_by_ident(compatible, simbrief_name)
            if picked is not None:
                return self._departure_choice_from(
                    picked, target_fix, forced_transition, "simbrief",
                    Confidence.HIGH, "SID filée par SimBrief et validée en base",
                )
            if _find_by_ident(sids, simbrief_name) is not None:
                self._warn(
                    f"La SID SimBrief « {simbrief_name} » n'est pas publiée "
                    f"pour la piste {runway_name}."
                )

        candidates = self._rank_by_fix(
            compatible, target_fix, use_exit_fix=True
        )
        if not candidates:
            best = compatible[0]
            return self._departure_choice_from(
                best, target_fix, forced_transition, "moteur",
                Confidence.LOW, "aucun lien avec le premier point en route",
            )

        best = candidates[0]
        alternatives = _alternatives(candidates[1:4])
        choice, transition = self._departure_choice_from(
            best.procedure, target_fix, forced_transition, "moteur",
            best.confidence, best.reason,
        )
        choice.alternatives = alternatives
        return choice, transition

    def _departure_choice_from(
        self,
        procedure: Procedure,
        target_fix: str | None,
        forced_transition: str | None,
        source: str,
        confidence: Confidence,
        reason: str,
    ) -> tuple[Choice, Choice]:
        sid_choice = Choice(procedure.ident, confidence, source, reason)

        if forced_transition:
            return sid_choice, Choice(
                forced_transition, Confidence.HIGH, "utilisateur", "transition imposée"
            )

        # Cas 1 : la SID publie des transitions explicites.
        if procedure.transitions:
            idents = procedure.transition_idents()
            if target_fix and target_fix in idents:
                return sid_choice, Choice(
                    target_fix, Confidence.HIGH, "moteur",
                    "transition rejoignant le premier point en route",
                )
            picked = self._nearest_transition(procedure, target_fix)
            if picked:
                return sid_choice, Choice(
                    picked, Confidence.MEDIUM, "moteur",
                    "transition la plus proche du premier point en route",
                )
            return sid_choice, Choice(
                idents[0], Confidence.LOW, "moteur", "première transition publiée"
            )

        # Cas 2 : SID sans transition publiée (usage européen courant).
        # Le point de sortie de la SID tient lieu de transition.
        exit_fix = procedure.exit_fix
        if exit_fix:
            matches = target_fix is not None and exit_fix == target_fix
            return sid_choice, Choice(
                exit_fix,
                Confidence.HIGH if matches else Confidence.MEDIUM,
                "moteur",
                "point de sortie de la SID"
                + (" ; rejoint la route" if matches else ""),
            )

        return sid_choice, Choice(
            None, Confidence.NONE, "moteur", "SID sans point de sortie identifiable"
        )

    # ------------------------------------------------------------------ #
    # Arrivée
    # ------------------------------------------------------------------ #

    def _build_arrival(
        self, ofp: OfpSummary, overrides: PlannerOverrides
    ) -> ArrivalBlock:
        icao = ofp.destination_icao
        airport = self.provider.airport(icao)
        block = ArrivalBlock(icao=icao, name=airport.name if airport else "")
        if airport is None:
            self._warn(f"{icao} absent de la base de navigation.")
            return block

        block.transition_level_ft = airport.transition_level_ft
        block.wind = self._wind_for(icao, overrides.arrival_metar, ofp.destination_metar)

        runways = self.provider.runways(icao)
        approaches = self.provider.procedures(icao, ProcedureKind.APPROACH)
        runways_with_approach = {
            r for p in approaches for r in p.runways
        }
        landable = [r for r in runways if r.name in runways_with_approach] or runways

        block.runway = self._choose_runway(
            icao=icao,
            runways=landable,
            wind=block.wind,
            for_landing=True,
            forced=overrides.arrival_runway,
            simbrief_runway=ofp.destination_planned_runway,
        )
        if block.runway is None or not block.runway.choice.value:
            self._warn(f"Aucune piste d'arrivée déterminable à {icao}.")
            return block

        runway_name = block.runway.choice.value
        block.ils_frequency_mhz = self.provider.ils_frequency(icao, runway_name)

        stars = self.provider.procedures(icao, ProcedureKind.STAR)
        star_exit_fix: str | None = None
        if stars:
            block.star, block.star_transition, star_exit_fix = self._choose_star(
                stars=stars,
                runway_name=runway_name,
                target_fix=ofp.star_entry_hint or ofp.last_enroute_fix,
                simbrief_name=ofp.simbrief_star,
                forced_name=overrides.star,
                forced_transition=overrides.star_transition,
            )
            selected_star = (
                _find_by_ident(stars, block.star.value) if block.star.value else None
            )
            if selected_star is not None:
                # Une transition de STAR précède la procédure.
                block.star_constraints = procedure_constraints(
                    selected_star, block.star_transition.value, transition_first=True
                )
                block.star_path = procedure_path(
                    selected_star,
                    block.star_transition.value,
                    transition_first=True,
                    position_lookup=self.provider.fix_position,
                )
        else:
            self._warn(f"Aucune STAR publiée pour {icao} dans la base.")
            block.star = Choice(None, Confidence.NONE, reason="aucune STAR en base")

        if approaches:
            block.approach, block.approach_transition = self._choose_approach(
                approaches=approaches,
                runway_name=runway_name,
                star_exit_fix=star_exit_fix,
                forced_name=overrides.approach,
                forced_transition=overrides.approach_transition,
                prefer_ils=overrides.prefer_ils,
                rnp_capable=(
                    overrides.rnp_capable
                    if overrides.rnp_capable is not None
                    else self.settings.aircraft_rnp_capable
                ),
            )
            selected_approach = (
                _find_approach_by_name(approaches, block.approach.value)
                if block.approach.value
                else None
            )
            if selected_approach is not None:
                # La VIA est survolée avant les segments de l'approche.
                block.approach_constraints = procedure_constraints(
                    selected_approach,
                    block.approach_transition.value,
                    transition_first=True,
                )
                block.approach_path = procedure_path(
                    selected_approach,
                    block.approach_transition.value,
                    transition_first=True,
                    position_lookup=self.provider.fix_position,
                )
                block.missed_approach_altitude_ft = (
                    selected_approach.missed_approach_altitude_ft
                )
                self._fill_final_approach_guidance(block, selected_approach)
        else:
            self._warn(f"Aucune procédure d'approche publiée pour {icao}.")
            block.approach = Choice(None, Confidence.NONE, reason="aucune approche en base")

        return block

    def _fill_final_approach_guidance(
        self, block: ArrivalBlock, approach: Procedure
    ) -> None:
        """Sépare les données de finale de celles de l'approche interrompue."""
        details_reader = getattr(self.provider, "ils_details", None)
        details = (
            details_reader(block.icao, block.runway.choice.value)
            if callable(details_reader) and block.runway and block.runway.choice.value
            else {}
        )
        block.ils_ident = details.get("ident") or approach.ils_ident
        block.ils_frequency_mhz = (
            details.get("frequency_mhz") or block.ils_frequency_mhz
        )
        block.ils_course_deg = details.get("course_deg")
        block.glide_slope_deg = details.get("glide_slope_deg")

        final_legs = [leg for leg in approach.legs if not leg.is_missed]
        faf_index = next(
            (index for index, leg in enumerate(final_legs) if leg.is_faf),
            None,
        )
        if faf_index is not None:
            intercept_leg = final_legs[faf_index]
            glide_index = min(faf_index + 1, len(final_legs) - 1)
            block.glide_intercept_fix = intercept_leg.fix_ident
            block.glide_intercept_altitude = format_altitude(intercept_leg)
        else:
            intercept_leg = None
        glide_index = next(
            (
                index
                for index, leg in enumerate(final_legs)
                if leg.vertical_angle_deg
            ),
            glide_index if faf_index is not None else None,
        )
        if glide_index is None and len(final_legs) >= 2:
            glide_index = len(final_legs) - 1
        if glide_index is None:
            return

        glide_leg = final_legs[glide_index]
        if block.ils_course_deg is None and glide_leg.course_deg:
            block.ils_course_deg = glide_leg.course_deg
        if block.glide_slope_deg is None and glide_leg.vertical_angle_deg:
            block.glide_slope_deg = abs(glide_leg.vertical_angle_deg)
        if glide_leg.distance_nm:
            block.final_approach_distance_nm = round(glide_leg.distance_nm, 1)

        if intercept_leg is None and glide_index > 0:
            intercept_leg = final_legs[glide_index - 1]
            block.glide_intercept_fix = intercept_leg.fix_ident
            block.glide_intercept_altitude = format_altitude(intercept_leg)

    def _choose_star(
        self,
        stars: list[Procedure],
        runway_name: str,
        target_fix: str | None,
        simbrief_name: str | None,
        forced_name: str | None,
        forced_transition: str | None,
    ) -> tuple[Choice, Choice, str | None]:
        compatible = [p for p in stars if p.serves_runway(runway_name)]
        if not compatible:
            self._warn(
                f"Aucune STAR compatible avec la piste {runway_name} ; "
                "recherche élargie à toutes les pistes."
            )
            compatible = stars

        picked: Procedure | None = None
        confidence = Confidence.MEDIUM
        source = "moteur"
        reason = ""
        alternatives: list[dict] = []

        if forced_name:
            picked = _find_by_ident(compatible, forced_name) or _find_by_ident(
                stars, forced_name
            )
            if picked is None:
                self._warn(f"STAR forcée « {forced_name} » introuvable en base.")
                return (
                    Choice(forced_name, Confidence.LOW, "utilisateur", "forcée, non vérifiée"),
                    Choice(forced_transition, Confidence.LOW, "utilisateur"),
                    None,
                )
            confidence, source, reason = Confidence.HIGH, "utilisateur", "STAR imposée"

        if picked is None and simbrief_name:
            match = _find_by_ident(compatible, simbrief_name)
            if match is not None:
                picked = match
                confidence = Confidence.HIGH
                source = "simbrief"
                reason = "STAR filée par SimBrief et validée en base"
            elif _find_by_ident(stars, simbrief_name) is not None:
                self._warn(
                    f"La STAR SimBrief « {simbrief_name} » n'est pas publiée "
                    f"pour la piste {runway_name}."
                )

        if picked is None:
            candidates = self._rank_by_fix(compatible, target_fix, use_exit_fix=False)
            if not candidates:
                picked = compatible[0]
                confidence = Confidence.LOW
                reason = "aucun lien avec le dernier point en route"
            else:
                best = candidates[0]
                picked = best.procedure
                confidence = best.confidence
                reason = best.reason
                alternatives = _alternatives(candidates[1:4])

        star_choice = Choice(picked.ident, confidence, source, reason, alternatives)
        transition_choice = self._star_transition(picked, target_fix, forced_transition)
        return star_choice, transition_choice, picked.exit_fix

    def _star_transition(
        self,
        procedure: Procedure,
        target_fix: str | None,
        forced_transition: str | None,
    ) -> Choice:
        if forced_transition:
            return Choice(
                forced_transition, Confidence.HIGH, "utilisateur", "transition imposée"
            )

        if procedure.transitions:
            idents = procedure.transition_idents()
            if target_fix and target_fix in idents:
                return Choice(
                    target_fix, Confidence.HIGH, "moteur",
                    "transition partant du dernier point en route",
                )
            picked = self._nearest_transition(procedure, target_fix)
            if picked:
                return Choice(
                    picked, Confidence.MEDIUM, "moteur",
                    "transition la plus proche du dernier point en route",
                )
            return Choice(idents[0], Confidence.LOW, "moteur", "première transition publiée")

        entry_fix = procedure.entry_fix
        if entry_fix:
            matches = target_fix is not None and entry_fix == target_fix
            return Choice(
                entry_fix,
                Confidence.HIGH if matches else Confidence.MEDIUM,
                "moteur",
                "point d'entrée de la STAR"
                + (" ; enchaîne avec la route" if matches else ""),
            )
        return Choice(None, Confidence.NONE, "moteur", "STAR sans point d'entrée")

    def _choose_approach(
        self,
        approaches: list[Procedure],
        runway_name: str,
        star_exit_fix: str | None,
        forced_name: str | None,
        forced_transition: str | None,
        prefer_ils: bool,
        rnp_capable: bool,
    ) -> tuple[Choice, Choice]:
        compatible = [p for p in approaches if p.serves_runway(runway_name)]
        if not compatible:
            self._warn(f"Aucune approche publiée pour la piste {runway_name}.")
            return (
                Choice(None, Confidence.NONE, "moteur", "aucune approche pour cette piste"),
                Choice(None, Confidence.NONE),
            )

        if forced_name:
            picked = _find_approach_by_name(compatible, forced_name)
            if picked is None:
                self._warn(f"Approche forcée « {forced_name} » introuvable.")
                return (
                    Choice(forced_name, Confidence.LOW, "utilisateur", "forcée, non vérifiée"),
                    Choice(forced_transition, Confidence.LOW, "utilisateur"),
                )
            return (
                Choice(picked.display_name, Confidence.HIGH, "utilisateur", "approche imposée"),
                self._approach_transition(picked, star_exit_fix, forced_transition),
            )

        preference = self.settings.approach_preference
        if not prefer_ils:
            preference = tuple(p for p in preference if p != "ILS") + ("ILS",)

        # Une base qui ne renseigne pas l'exigence RNP ne peut pas trancher :
        # mieux vaut le dire que d'appliquer un critère muet.
        if not rnp_capable and not self.provider.supports_rnp_flag:
            self._warn(
                "L'avion est déclaré non RNP, mais aucune approche de ce terrain "
                "ne publie d'exigence RNP : critère ignoré. Vérifie la carte "
                "d'approche avant de t'y fier."
            )
            rnp_capable = True

        def rank(procedure: Procedure) -> tuple[int, int, int, int, str]:
            """Classement structurel. La lettre X/Y/Z n'entre jamais en compte.

            Elle n'est qu'un identifiant attribué à rebours depuis Z lorsque
            plusieurs procédures du même type desservent la même piste ; s'y
            fier reviendrait à choisir au hasard.
            """
            # 1. Équipement : une approche exigeant le RNP est inutilisable
            #    par un avion non qualifié. Critère éliminatoire.
            equipment = 0 if (rnp_capable or not procedure.requires_rnp) else 1

            # 2. Raccord direct depuis la fin de la STAR.
            connects = (
                0
                if star_exit_fix and star_exit_fix in procedure.transition_idents()
                else 1
            )

            # 3. Cohérence du mode d'arrivée : avec une STAR on veut une entrée
            #    publiée ; sans STAR on sera vectoré vers l'axe.
            if star_exit_fix:
                entry = 0 if procedure.has_published_transitions else 1
            else:
                entry = 0 if procedure.is_vectors_entry else 1

            proc_type = (procedure.proc_type or "").upper()
            try:
                type_rank = preference.index(proc_type)
            except ValueError:
                type_rank = len(preference)

            # Dernier critère : stabilité du tri uniquement, aucune sémantique.
            return (equipment, connects, entry, type_rank, procedure.ident)

        ordered = sorted(compatible, key=rank)
        best = ordered[0]
        connects = bool(star_exit_fix and star_exit_fix in best.transition_idents())
        blocked_by_rnp = [
            p for p in compatible if p.requires_rnp and not rnp_capable
        ]

        reasons: list[str] = [f"type {best.proc_type} selon la préférence"]
        if connects:
            reasons.insert(0, f"transition publiée depuis {star_exit_fix}")
        elif best.is_vectors_entry:
            reasons.insert(0, "variante guidage radar (entrée sur repère d'interception)")
        if best.requires_rnp:
            reasons.append("RNP requis, avion qualifié")
        if blocked_by_rnp and best not in blocked_by_rnp:
            names = ", ".join(p.display_name for p in blocked_by_rnp)
            reasons.append(f"écartées faute de qualification RNP : {names}")
            self._warn(
                f"Avion déclaré non RNP : {names} écartée(s). "
                "Régler AIRCRAFT_RNP_CAPABLE si c'est inexact."
            )

        confidence = Confidence.HIGH if connects else Confidence.MEDIUM
        if not star_exit_fix and best.is_vectors_entry:
            # Aucune STAR à raccorder, mais la structure choisie est la bonne.
            confidence = Confidence.HIGH

        approach_choice = Choice(
            best.display_name,
            confidence,
            "moteur",
            " ; ".join(reasons),
            alternatives=[_approach_alternative(p, star_exit_fix) for p in ordered[1:4]],
        )
        return approach_choice, self._approach_transition(
            best, star_exit_fix, forced_transition
        )

    def _approach_transition(
        self,
        procedure: Procedure,
        star_exit_fix: str | None,
        forced_transition: str | None,
    ) -> Choice:
        if forced_transition:
            return Choice(
                forced_transition, Confidence.HIGH, "utilisateur", "transition imposée"
            )

        idents = procedure.transition_idents()
        if not idents:
            return Choice(
                VECTORS, Confidence.MEDIUM, "moteur",
                "aucune transition publiée : guidage radar attendu",
            )

        if star_exit_fix and star_exit_fix in idents:
            return Choice(
                star_exit_fix, Confidence.HIGH, "moteur",
                "transition partant du point de sortie de la STAR",
            )

        picked = self._nearest_transition(procedure, star_exit_fix)
        if picked:
            return Choice(
                picked, Confidence.MEDIUM, "moteur",
                "transition la plus proche de la fin de la STAR",
            )
        return Choice(
            idents[0], Confidence.LOW, "moteur",
            "première transition publiée, aucun lien avec la STAR",
        )

    # ------------------------------------------------------------------ #
    # Briques communes
    # ------------------------------------------------------------------ #

    def _choose_runway(
        self,
        icao: str,
        runways: list[Runway],
        wind: WindInfo,
        for_landing: bool,
        forced: str | None,
        simbrief_runway: str | None,
    ) -> RunwayChoice | None:
        if not runways:
            return None

        preferred = self.preferences.runways(icao, for_landing=for_landing)
        scores = score_runways(
            runways,
            wind,
            for_landing=for_landing,
            max_tailwind_kt=self.settings.max_tailwind_kt,
            max_crosswind_kt=self.settings.max_crosswind_kt,
            min_length_ft=self.settings.min_runway_length_ft,
            preferred=preferred,
        )
        by_name = {s.runway.name: s for s in scores}

        def build(entry: RunwayScore, choice: Choice) -> RunwayChoice:
            return RunwayChoice(
                choice=choice,
                headwind_kt=round(entry.headwind_kt, 1),
                crosswind_kt=round(entry.crosswind_kt, 1),
                length_ft=entry.runway.length_ft,
                ils_ident=entry.runway.ils_ident,
            )

        if forced:
            name = normalise_runway(forced)
            entry = by_name.get(name)
            if entry is None:
                self._warn(f"Piste forcée « {forced} » inconnue à {icao}.")
                return RunwayChoice(
                    choice=Choice(name, Confidence.LOW, "utilisateur", "forcée, non vérifiée")
                )
            return build(entry, Choice(name, Confidence.HIGH, "utilisateur", "piste imposée"))

        if simbrief_runway:
            name = normalise_runway(simbrief_runway)
            entry = by_name.get(name)
            if entry is not None:
                best = scores[0]
                agrees = best.runway.name == name
                if not agrees and not entry.disqualified:
                    self._warn(
                        f"{icao} : SimBrief a prévu la piste {name}, le vent "
                        f"favoriserait {best.runway.name}."
                    )
                confidence = Confidence.HIGH if agrees else Confidence.MEDIUM
                if entry.disqualified:
                    confidence = Confidence.LOW
                    self._warn(
                        f"{icao} : la piste {name} prévue par SimBrief est hors "
                        f"limites ({'; '.join(entry.notes)})."
                    )
                return build(
                    entry,
                    Choice(
                        name, confidence, "simbrief",
                        "piste planifiée par SimBrief"
                        + (" et confirmée par le vent" if agrees else ""),
                    ),
                )
            self._warn(f"Piste SimBrief « {simbrief_runway} » inconnue à {icao}.")

        best = scores[0]
        margin = margin_between_best_two(scores)
        if wind.direction_deg is None and not best.preferred:
            confidence = Confidence.LOW
            reason = "vent indisponible : piste la plus longue retenue"
        elif margin >= 3.0:
            confidence = Confidence.HIGH
            reason = (
                f"meilleure composante de vent de face "
                f"({best.headwind_kt:+.0f} kt, traversier {best.crosswind_kt:.0f} kt)"
            )
        else:
            confidence = Confidence.MEDIUM
            reason = f"choix serré entre {scores[0].runway.name} et {scores[1].runway.name}"

        if best.preferred:
            note = self.preferences.note(icao)
            reason += f" ; configuration préférentielle{f' ({note})' if note else ''}"

        choice = Choice(
            best.runway.name, confidence, "moteur", reason,
            alternatives=[
                {
                    "value": s.runway.name,
                    "headwind_kt": round(s.headwind_kt, 1),
                    "crosswind_kt": round(s.crosswind_kt, 1),
                    "disqualified": s.disqualified,
                }
                for s in scores[1:4]
            ],
        )
        return build(best, choice)

    def _rank_by_fix(
        self,
        procedures: Sequence[Procedure],
        target_fix: str | None,
        use_exit_fix: bool,
    ) -> list[_Candidate]:
        """Classe des procédures par lien avec un point de la route.

        `use_exit_fix` : True pour une SID (on compare son point de sortie),
        False pour une STAR (on compare son point d'entrée).
        """
        if not target_fix:
            return []

        target_position = self.provider.fix_position(target_fix)
        candidates: list[_Candidate] = []

        for procedure in procedures:
            link = procedure.exit_fix if use_exit_fix else procedure.entry_fix

            if link == target_fix:
                candidates.append(
                    _Candidate(
                        procedure, 0.0,
                        f"{'sortie' if use_exit_fix else 'entrée'} sur {target_fix}",
                        Confidence.HIGH, link,
                    )
                )
                continue

            if target_fix in procedure.transition_idents():
                candidates.append(
                    _Candidate(
                        procedure, 0.5,
                        f"transition publiée vers {target_fix}",
                        Confidence.HIGH, link, target_fix,
                    )
                )
                continue

            if target_position and link:
                position = self.provider.fix_position(link)
                if position:
                    gap = distance_nm(*target_position, *position)
                    if gap <= 80:
                        candidates.append(
                            _Candidate(
                                procedure, 10.0 + gap,
                                f"{link} à {gap:.0f} NM de {target_fix}",
                                Confidence.MEDIUM if gap <= 30 else Confidence.LOW,
                                link,
                            )
                        )

        candidates.sort(key=lambda c: (c.score, c.procedure.ident))
        return candidates

    def _nearest_transition(
        self, procedure: Procedure, target_fix: str | None
    ) -> str | None:
        idents = procedure.transition_idents()
        if not idents or not target_fix:
            return None
        target_position = self.provider.fix_position(target_fix)
        if not target_position:
            return None

        best_ident: str | None = None
        best_gap = float("inf")
        for ident in idents:
            position = self.provider.fix_position(ident)
            if not position:
                continue
            gap = distance_nm(*target_position, *position)
            if gap < best_gap:
                best_ident, best_gap = ident, gap
        return best_ident if best_gap <= 150 else None

    def _wind_for(
        self, icao: str, forced_metar: str | None, ofp_metar: str | None
    ) -> WindInfo:
        if forced_metar:
            return parse_wind(forced_metar)

        source = self.settings.metar_source
        if source == "none":
            return WindInfo()
        if source == "awc":
            live = fetch_metar(icao)
            if live:
                return parse_wind(live)
            self._warn(f"METAR indisponible pour {icao} ; repli sur l'OFP SimBrief.")

        wind = parse_wind(ofp_metar)
        if wind.raw_metar is None and source != "awc":
            live = fetch_metar(icao)
            if live:
                return parse_wind(live)
            self._warn(f"Aucun METAR pour {icao} : sélection de piste dégradée.")
        return wind

    def _check_airac_alignment(self, ofp: OfpSummary) -> None:
        ofp_cycle = (ofp.airac or "").strip()
        db_cycle = (self.provider.airac_cycle or "").strip()
        if ofp_cycle and db_cycle and ofp_cycle.isdigit() and db_cycle.isdigit():
            if ofp_cycle != db_cycle:
                self._warn(
                    f"Cycles AIRAC différents : SimBrief {ofp_cycle} contre "
                    f"navdata locale {db_cycle}. Une procédure peut avoir changé "
                    "de nom ou disparu."
                )

    def _warn(self, message: str) -> None:
        if message not in self._warnings:
            self._warnings.append(message)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _find_by_ident(procedures: Sequence[Procedure], name: str) -> Procedure | None:
    target = name.strip().upper()
    for procedure in procedures:
        if procedure.ident.upper() == target:
            return procedure
    return None


def _find_approach_by_name(
    procedures: Sequence[Procedure], name: str
) -> Procedure | None:
    target = " ".join(name.strip().upper().split())
    for procedure in procedures:
        if procedure.display_name.upper() == target:
            return procedure
    for procedure in procedures:
        if (procedure.arinc_name or "").upper() == target.replace(" ", ""):
            return procedure
    return None


def _approach_alternative(
    procedure: Procedure, star_exit_fix: str | None
) -> dict:
    """Décrit une approche écartée, et pourquoi elle existe."""
    if procedure.is_vectors_entry:
        role = "variante guidage radar"
    elif procedure.has_published_transitions:
        role = "variante à arrivée publiée"
    else:
        role = "entrée unique publiée"
    return {
        "value": procedure.display_name,
        "role": role,
        "transitions": list(procedure.transition_idents()),
        "requires_rnp": procedure.requires_rnp,
        "connects_to_star": bool(
            star_exit_fix and star_exit_fix in procedure.transition_idents()
        ),
    }


def _alternatives(candidates: Sequence[_Candidate]) -> list[dict]:
    return [
        {
            "value": c.procedure.ident,
            "runways": list(c.procedure.runways),
            "reason": c.reason,
            "confidence": c.confidence.value,
        }
        for c in candidates
    ]

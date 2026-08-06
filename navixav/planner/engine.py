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

import logging
from dataclasses import dataclass, field
from math import isfinite
from typing import Sequence

from navixav.config import Settings
from navixav.constraints import format_altitude, procedure_constraints, procedure_path
from navixav.geo import TERMINAL_FIX_RADIUS_NM, distance_nm, near_direct_route
from navixav.models import (
    ArrivalBlock,
    Choice,
    Confidence,
    DepartureBlock,
    EnrouteBlock,
    FlightPlan,
    RunwayChoice,
    WeatherBriefing,
    WindInfo,
)
from navixav.navdata.base import (
    Airport,
    NavdataProvider,
    Procedure,
    ProcedureKind,
    Runway,
    normalise_runway,
)
from navixav.planner.runway import RunwayScore, margin_between_best_two, score_runways
from navixav.preferences import AirportPreferences
from navixav.simbrief.parser import OfpSummary
from navixav.weather.briefing import build_briefing
from navixav.weather.metar import fetch_metar, parse_wind

LOGGER = logging.getLogger(__name__)

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
        self._planned_nm: float | None = None

    # ------------------------------------------------------------------ #
    # Entrée principale
    # ------------------------------------------------------------------ #

    def complete(
        self, ofp: OfpSummary, overrides: PlannerOverrides | None = None
    ) -> FlightPlan:
        overrides = overrides or PlannerOverrides()
        self._warnings = []
        # Un aller-retour ramène la route directe à zéro : c'est la distance
        # annoncée par le plan qui dit alors jusqu'où le vol s'éloigne.
        self._planned_nm = ofp.dispatch.route_distance_nm

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
        destination = self.provider.airport(ofp.destination_icao)
        if origin is not None:
            route_path.append({
                "ident": origin.ident, "lat": origin.lat, "lon": origin.lon, "via": "",
            })
        elif ofp.origin_lat is not None and ofp.origin_lon is not None:
            route_path.append({
                "ident": ofp.origin_icao,
                "lat": ofp.origin_lat,
                "lon": ofp.origin_lon,
                "via": "",
            })
        # Les repères se résolvent de proche en proche : le précédent sert
        # d'ancrage au suivant, et la route directe arbitre les cas restants.
        # Sans cela, un homonyme d'un autre continent suffit à faire faire un
        # aller-retour au tracé.
        previous = (
            (origin.lat, origin.lon)
            if origin is not None
            else (
                (ofp.origin_lat, ofp.origin_lon)
                if ofp.origin_lat is not None and ofp.origin_lon is not None
                else None
            )
        )
        for leg in route_legs:
            position = (
                (float(leg["lat"]), float(leg["lon"]))
                if _positioned(leg)
                else self._enroute_position(leg["to"], previous)
            )
            if position is None:
                continue
            if not self._on_direct_corridor(position, origin, destination):
                self._warn(
                    f"Point « {leg['to']} » écarté du tracé : sa position en "
                    "base s'écarte trop de la route."
                )
                continue
            leg["lat"], leg["lon"] = position
            route_path.append({
                "ident": leg["to"],
                "lat": position[0],
                "lon": position[1],
                "via": leg["via"],
            })
            previous = position
        if destination is not None:
            route_path.append({
                "ident": destination.ident,
                "lat": destination.lat,
                "lon": destination.lon,
                "via": "",
            })
        elif ofp.destination_lat is not None and ofp.destination_lon is not None:
            route_path.append({
                "ident": ofp.destination_icao,
                "lat": ofp.destination_lat,
                "lon": ofp.destination_lon,
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
        self._anchor_route_on_runways(plan)
        self._drop_stray_points(plan, origin, destination)
        plan.weather = self._build_weather(ofp, plan)
        plan.warnings = self._warnings
        return plan

    def _build_weather(self, ofp: OfpSummary, plan: FlightPlan) -> WeatherBriefing:
        """Briefing météo, construit sur les METAR déjà retenus pour les pistes."""
        try:
            briefing = build_briefing(
                ofp,
                metar_source=self.settings.metar_source,
                departure_metar=plan.departure.wind.raw_metar if plan.departure else None,
                arrival_metar=plan.arrival.wind.raw_metar if plan.arrival else None,
            )
        except Exception:  # noqa: BLE001 - la météo ne doit jamais bloquer un plan
            LOGGER.exception("Échec de construction du briefing météo")
            self._warn("Briefing météo indisponible : le plan reste exploitable.")
            return WeatherBriefing()

        for message in briefing.warnings:
            self._warn(message)
        return briefing

    def _drop_stray_points(
        self, plan: FlightPlan, origin: Airport | None, destination: Airport | None
    ) -> None:
        """Dernier filet : écarte du tracé tout point hors de sa zone.

        Le contrôle porte sur le plan assemblé, une fois toutes les positions
        résolues — à l'import de l'OFP comme au recalcul d'une route. Peu
        importe d'où vient la position fautive : homonyme d'un autre continent,
        repère d'axe attrapé sur le terrain voisin, coordonnée héritée d'une
        base constituée par une version antérieure, ou position fournie
        directement par le simulateur.

        Chaque point est jugé sur un ancrage **stable** — son aérodrome pour
        une procédure, la route directe pour la croisière — jamais sur son
        voisin. Deux points fautifs côte à côte, comme le « CF02 » et le
        « FF02 » d'Orly tombés ensemble en Corse, se couvriraient l'un
        l'autre dans une comparaison de proche en proche.

        Le critère ne mesure aucune longueur de branche : une étape océanique
        de 800 NM en ligne droite est parfaitement licite. Il vaut donc pour
        toutes les routes du monde.
        """
        anchors: list[tuple[list[dict], Airport | None]] = []
        if plan.departure is not None:
            anchors.append((plan.departure.sid_path, origin))
        if plan.arrival is not None:
            anchors.append((plan.arrival.star_path, destination))
            anchors.append((plan.arrival.approach_path, destination))

        for path, airport in anchors:
            if airport is None or not path:
                continue
            self._keep(
                path,
                lambda point, airport=airport: distance_nm(
                    airport.lat, airport.lon, point["lat"], point["lon"]
                ) <= TERMINAL_FIX_RADIUS_NM,
                f"hors de la zone terminale de {airport.ident}",
            )

        # La croisière : ses extrémités sont les aérodromes, jamais en cause.
        route = plan.enroute.route_path if plan.enroute else []
        if len(route) > 2 and origin is not None and destination is not None:
            middle = route[1:-1]
            self._keep(
                middle,
                lambda point: self._on_direct_corridor(
                    (point["lat"], point["lon"]), origin, destination
                ),
                "trop éloigné de la route directe",
            )
            route[1:-1] = middle

    def _keep(self, path: list[dict], accepts, reason: str) -> None:
        """Ne conserve du tracé que les points acceptés, en signalant les autres."""
        kept = []
        for point in path:
            if not _positioned(point):
                continue
            if accepts(point):
                kept.append(point)
                continue
            self._warn(
                f"Point « {point.get('ident') or '?'} » retiré du tracé : {reason}."
            )
        path[:] = kept

    def _anchor_route_on_runways(self, plan: FlightPlan) -> None:
        """Ancre les extrémités du tracé sur les seuils de piste retenus.

        Le tracé part du point de référence de l'aérodrome tant que la piste
        n'est pas choisie ; une fois départ et arrivée résolus, le premier et
        le dernier point sont ramenés sur le seuil réellement utilisé.
        """
        path = plan.enroute.route_path if plan.enroute else []
        if not path:
            return

        departure = plan.departure
        if departure is not None and path[0].get("ident") == departure.icao:
            threshold = self._runway_threshold(departure.icao, departure.runway)
            if threshold is not None:
                path[0]["lat"], path[0]["lon"] = threshold
                path[0]["runway"] = departure.runway.choice.value

        arrival = plan.arrival
        if arrival is not None and path[-1].get("ident") == arrival.icao:
            threshold = self._runway_threshold(arrival.icao, arrival.runway)
            if threshold is not None:
                path[-1]["lat"], path[-1]["lon"] = threshold
                path[-1]["runway"] = arrival.runway.choice.value

    def _runway_threshold(
        self, icao: str, choice: RunwayChoice | None
    ) -> tuple[float, float] | None:
        """Position du seuil de la piste retenue, ou None si indéterminable."""
        name = choice.choice.value if choice is not None else None
        if not name:
            return None
        wanted = normalise_runway(name)
        for runway in self.provider.runways(icao):
            if normalise_runway(runway.name) == wanted:
                return (runway.lat, runway.lon)
        return None

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
                position_lookup=self._airport_lookup(icao),
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
            if picked not in compatible:
                self._warn(
                    f"La SID « {picked.ident} » n'est pas publiée pour la piste "
                    f"{runway_name} : elle part d'un autre seuil."
                )
            choice, transition = self._departure_choice_from(
                picked, target_fix, forced_transition, "utilisateur",
                Confidence.HIGH, "SID imposée",
            )
            choice.alternatives = _procedure_alternatives(compatible, picked)
            return choice, transition

        # Symétrique de la STAR : une SID publiée pour une autre piste part d'un
        # autre seuil, avec ses propres caps et ses propres altitudes minimales.
        # Elle n'est pas un départ dégradé, elle est involable. Sans SID pour la
        # piste retenue, le départ réel est un cap piste puis un guidage radar
        # vers la route : c'est cela qu'il faut annoncer.
        if not compatible:
            self._warn(
                f"Aucune SID n'est publiée pour la piste {runway_name} ; "
                "départ en guidage radar."
            )
            return (
                Choice(
                    None,
                    Confidence.NONE,
                    "moteur",
                    f"aucune SID publiée pour la piste {runway_name}",
                    alternatives=_other_runway_alternatives(sids),
                ),
                Choice(None, Confidence.NONE, "moteur", "aucune SID retenue"),
            )

        if simbrief_name:
            picked = _find_by_ident(compatible, simbrief_name)
            if picked is not None:
                choice, transition = self._departure_choice_from(
                    picked, target_fix, forced_transition, "simbrief",
                    Confidence.HIGH, "SID donnée par SimBrief et validée en base",
                )
                choice.alternatives = _procedure_alternatives(compatible, picked)
                return choice, transition
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
            choice, transition = self._departure_choice_from(
                best, target_fix, forced_transition, "moteur",
                Confidence.LOW, "aucun lien avec le premier point en route",
            )
            choice.alternatives = _procedure_alternatives(compatible, best)
            return choice, transition

        best = candidates[0]
        choice, transition = self._departure_choice_from(
            best.procedure, target_fix, forced_transition, "moteur",
            best.confidence, best.reason,
        )
        choice.alternatives = _procedure_alternatives(
            compatible, best.procedure, candidates[1:]
        )
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
                forced_transition, Confidence.HIGH, "utilisateur", "transition imposée",
                _transition_alternatives(procedure, forced_transition),
            )

        # Cas 1 : la SID publie des transitions explicites.
        if procedure.transitions:
            idents = procedure.transition_idents()
            if target_fix and target_fix in idents:
                return sid_choice, Choice(
                    target_fix, Confidence.HIGH, "moteur",
                    "transition rejoignant le premier point en route",
                    _transition_alternatives(procedure, target_fix),
                )
            picked = self._nearest_transition(procedure, target_fix)
            if picked:
                return sid_choice, Choice(
                    picked, Confidence.MEDIUM, "moteur",
                    "transition la plus proche du premier point en route",
                    _transition_alternatives(procedure, picked),
                )
            return sid_choice, Choice(
                idents[0], Confidence.LOW, "moteur", "première transition publiée",
                _transition_alternatives(procedure, idents[0]),
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
                    position_lookup=self._airport_lookup(icao),
                )
        else:
            self._warn(f"Aucune STAR publiée pour {icao} dans la base.")
            block.star = Choice(None, Confidence.NONE, reason="aucune STAR en base")

        if approaches:
            # Le maillon que l'approche doit reprendre : la sortie de la STAR
            # quand il y en a une, sinon le dernier point de la route. C'est de
            # là que vient l'avion dans les deux cas, et beaucoup de terrains
            # sans STAR pour la piste retenue publient justement une transition
            # d'approche sur ce point-là.
            link_fix = star_exit_fix or ofp.last_enroute_fix
            block.approach, block.approach_transition = self._choose_approach(
                approaches=approaches,
                runway_name=runway_name,
                link_fix=link_fix,
                via_star=star_exit_fix is not None,
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
                    position_lookup=self._airport_lookup(icao),
                )
                block.missed_approach_altitude_ft = (
                    selected_approach.missed_approach_altitude_ft
                )
                self._fill_final_approach_guidance(block, selected_approach)
            self._check_arrival_chain(block, selected_approach, star_exit_fix)
        else:
            self._warn(f"Aucune procédure d'approche publiée pour {icao}.")
            block.approach = Choice(None, Confidence.NONE, reason="aucune approche en base")

        return block

    def _check_arrival_chain(
        self,
        block: ArrivalBlock,
        approach: Procedure | None,
        star_exit_fix: str | None,
    ) -> None:
        """Vérifie la chaîne d'arrivée une fois tous les maillons posés.

        Chaque maillon est choisi pour lui-même ; rien ne garantit que la
        succession tienne. Une STAR peut très bien être publiée pour la piste
        retenue et se terminer sur un repère qu'aucune approche de cette piste
        ne reprend : le pilote sera alors vectoré, ce qu'il vaut mieux annoncer
        que laisser deviner d'un point d'interrogation en fin de STAR.
        """
        if approach is None or not star_exit_fix:
            return
        transition = block.approach_transition.value if block.approach_transition else None
        if transition in {star_exit_fix, VECTORS}:
            return
        if approach.is_vectors_entry:
            # Variante prévue pour le guidage radar : la rupture est normale.
            return
        self._warn(
            f"La STAR {block.star.value} se termine sur {star_exit_fix}, "
            f"qui n'ouvre aucune approche de la piste "
            f"{block.runway.choice.value} : prévoir un guidage radar vers l'axe."
        )

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
            if picked not in compatible:
                self._warn(
                    f"La STAR « {picked.ident} » n'est pas publiée pour la piste "
                    f"{runway_name} : elle mène à l'IAF d'une autre piste."
                )
            confidence, source, reason = Confidence.HIGH, "utilisateur", "STAR imposée"

        # Une STAR publiée pour une autre piste n'est pas une arrivée dégradée,
        # elle est involable : elle dépose l'avion sur l'IAF du côté opposé du
        # terrain, et aucune approche de la piste retenue n'en reprend le point
        # de sortie. Annoncer une arrivée directe — que le pilote sait voler —
        # vaut mieux que produire une chaîne que personne ne peut enchaîner.
        if picked is None and not compatible:
            self._warn(
                f"Aucune STAR n'est publiée pour la piste {runway_name} ; "
                "arrivée directe vers l'approche."
            )
            return (
                Choice(
                    None,
                    Confidence.NONE,
                    "moteur",
                    f"aucune STAR publiée pour la piste {runway_name}",
                    alternatives=_other_runway_alternatives(stars),
                ),
                Choice(None, Confidence.NONE, "moteur", "aucune STAR retenue"),
                None,
            )

        if picked is None and simbrief_name:
            match = _find_by_ident(compatible, simbrief_name)
            if match is not None:
                picked = match
                confidence = Confidence.HIGH
                source = "simbrief"
                reason = "STAR donnée par SimBrief et validée en base"
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
                alternatives = _procedure_alternatives(
                    compatible, picked, candidates[1:]
                )

        if not alternatives:
            alternatives = _procedure_alternatives(compatible, picked)
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
                forced_transition, Confidence.HIGH, "utilisateur", "transition imposée",
                _transition_alternatives(procedure, forced_transition),
            )

        if procedure.transitions:
            idents = procedure.transition_idents()
            if target_fix and target_fix in idents:
                return Choice(
                    target_fix, Confidence.HIGH, "moteur",
                    "transition partant du dernier point en route",
                    _transition_alternatives(procedure, target_fix),
                )
            picked = self._nearest_transition(procedure, target_fix)
            if picked:
                return Choice(
                    picked, Confidence.MEDIUM, "moteur",
                    "transition la plus proche du dernier point en route",
                    _transition_alternatives(procedure, picked),
                )
            return Choice(
                idents[0], Confidence.LOW, "moteur", "première transition publiée",
                _transition_alternatives(procedure, idents[0]),
            )

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
        link_fix: str | None,
        via_star: bool,
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
                Choice(
                    picked.display_name,
                    Confidence.HIGH,
                    "utilisateur",
                    "approche imposée",
                    [
                        _approach_alternative(p, link_fix, rnp_capable)
                        for p in compatible
                        if p is not picked
                    ][:3],
                ),
                self._approach_transition(
                    picked, link_fix, via_star, forced_transition
                ),
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

            # 2. Raccord direct depuis le point d'où l'avion arrive : fin de la
            #    STAR, ou dernier point de la route quand aucune STAR ne dessert
            #    la piste.
            connects = (
                0 if link_fix and link_fix in procedure.transition_idents() else 1
            )

            # 3. Cohérence du mode d'arrivée. Un raccord publié tranche à lui
            #    seul : il n'y a rien de mieux qu'une transition qui part
            #    exactement d'où l'on vient. Sinon, avec une STAR on veut une
            #    entrée publiée ; sans STAR on sera vectoré vers l'axe.
            if connects == 0:
                entry = 0
            elif via_star:
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
        connects = bool(link_fix and link_fix in best.transition_idents())
        blocked_by_rnp = [
            p for p in compatible if p.requires_rnp and not rnp_capable
        ]

        reasons: list[str] = [f"type {best.proc_type} selon la préférence"]
        if connects:
            reasons.insert(0, f"transition publiée depuis {link_fix}")
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
        if not via_star and best.is_vectors_entry:
            # Aucune STAR à raccorder, mais la structure choisie est la bonne.
            confidence = Confidence.HIGH

        approach_choice = Choice(
            best.display_name,
            confidence,
            "moteur",
            " ; ".join(reasons),
            alternatives=[
                _approach_alternative(p, link_fix, rnp_capable)
                for p in ordered[1:]
            ],
        )
        return approach_choice, self._approach_transition(
            best, link_fix, via_star, forced_transition
        )

    def _approach_transition(
        self,
        procedure: Procedure,
        link_fix: str | None,
        via_star: bool,
        forced_transition: str | None,
    ) -> Choice:
        if forced_transition:
            return Choice(
                forced_transition, Confidence.HIGH, "utilisateur", "transition imposée",
                _transition_alternatives(procedure, forced_transition),
            )

        idents = procedure.transition_idents()
        if not idents:
            return Choice(
                VECTORS, Confidence.MEDIUM, "moteur",
                "aucune transition publiée : guidage radar attendu",
            )

        if link_fix and link_fix in idents:
            return Choice(
                link_fix, Confidence.HIGH, "moteur",
                "transition partant du point de sortie de la STAR"
                if via_star
                else "transition partant du dernier point en route",
                _transition_alternatives(procedure, link_fix),
            )

        picked = self._nearest_transition(procedure, link_fix)
        if picked:
            return Choice(
                picked, Confidence.MEDIUM, "moteur",
                "transition la plus proche de la fin de la STAR"
                if via_star
                else "transition la plus proche du dernier point en route",
                _transition_alternatives(procedure, picked),
            )
        return Choice(
            idents[0], Confidence.LOW, "moteur",
            "première transition publiée, aucun lien avec la STAR"
            if via_star
            else "première transition publiée, aucun lien avec la route",
            _transition_alternatives(procedure, idents[0]),
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

        def alternatives_for(selected_name: str) -> list[dict]:
            return [
                {
                    "value": score.runway.name,
                    "headwind_kt": round(score.headwind_kt, 1),
                    "crosswind_kt": round(score.crosswind_kt, 1),
                    "disqualified": score.disqualified,
                }
                for score in scores
                if score.runway.name != selected_name
            ][:3]

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
            return build(
                entry,
                Choice(
                    name,
                    Confidence.HIGH,
                    "utilisateur",
                    "piste imposée",
                    alternatives_for(name),
                ),
            )

        if simbrief_runway:
            name = normalise_runway(simbrief_runway)
            entry = by_name.get(name)
            if entry is not None:
                # Le classement du moteur ne sert plus qu'à nuancer la confiance.
                # Il n'alerte plus quand il diverge de SimBrief : par vent faible,
                # calme ou variable, il est départagé par la configuration
                # préférentielle et l'ILS, pas par le vent.
                agrees = scores[0].runway.name == name
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
                        alternatives_for(name),
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
            alternatives=alternatives_for(best.runway.name),
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

        # Le raccord nominal est le cas courant. Une position n'est utile que
        # pour le repli géométrique ; la demander avant peut déclencher plusieurs
        # tentatives SimConnect pour un repère absent du cache.
        if candidates:
            candidates.sort(key=lambda c: (c.score, c.procedure.ident))
            return candidates

        target_position = self.provider.fix_position(target_fix)
        for procedure in procedures:
            link = procedure.exit_fix if use_exit_fix else procedure.entry_fix
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

    def _airport_lookup(self, icao: str):
        """Recherche de position rattachée à un aérodrome.

        Les repères de seuil de piste (« RW18L ») portent le même nom sur des
        terrains différents : sans ce rattachement, le tracé d'une procédure de
        Madrid pourrait emprunter le seuil homonyme de Toulouse.
        """
        def lookup(ident: str) -> tuple[float, float] | None:
            try:
                return self.provider.fix_position(ident, icao)
            except TypeError:
                # Fournisseur ne connaissant pas le rattachement par aérodrome.
                return self.provider.fix_position(ident)

        return lookup

    def _enroute_position(
        self, ident: str, near: tuple[float, float] | None
    ) -> tuple[float, float] | None:
        """Position d'un repère en route, ancrée sur le point précédent."""
        try:
            return self.provider.fix_position(ident, near=near)
        except TypeError:
            # Fournisseur ne connaissant pas l'ancrage en route.
            return self.provider.fix_position(ident)

    def _on_direct_corridor(
        self,
        position: tuple[float, float],
        origin: Airport | None,
        destination: Airport | None,
    ) -> bool:
        """Le point tient-il dans le couloir plausible de la route ?

        Un repère absent de la base peut avoir un homonyme à l'autre bout du
        monde. Faute de pouvoir choisir, mieux vaut ne pas le tracer que de
        dessiner une branche qui traverse un continent et revient.
        """
        if origin is None or destination is None:
            return True
        return near_direct_route(
            (origin.lat, origin.lon),
            (destination.lat, destination.lon),
            position,
            self._planned_nm,
        )

    def _warn(self, message: str) -> None:
        if message not in self._warnings:
            self._warnings.append(message)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _positioned(point: dict | None) -> bool:
    """Le point porte-t-il une position exploitable ?"""
    if not isinstance(point, dict):
        return False
    try:
        return isfinite(float(point["lat"])) and isfinite(float(point["lon"]))
    except (KeyError, TypeError, ValueError):
        return False


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


def _other_runway_alternatives(procedures: Sequence[Procedure]) -> list[dict]:
    """Procédures écartées parce qu'elles desservent une autre piste.

    Elles restent proposées : le moteur ne les enchaîne pas de lui-même, mais
    un pilote qui sait pourquoi il les veut doit pouvoir les imposer.
    """
    return [
        {
            "value": procedure.ident,
            "runways": list(procedure.runways),
            "reason": "publiée pour une autre piste",
        }
        for procedure in procedures
    ]


def _approach_alternative(
    procedure: Procedure, link_fix: str | None, rnp_capable: bool = True
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
        "disqualified": procedure.requires_rnp and not rnp_capable,
        "connects_to_star": bool(
            link_fix and link_fix in procedure.transition_idents()
        ),
    }


def _procedure_alternatives(
    procedures: Sequence[Procedure],
    selected: Procedure,
    ranked: Sequence[_Candidate] = (),
) -> list[dict]:
    """Toutes les autres procédures publiées pour la piste retenue.

    Celles que le moteur a su classer viennent en tête avec leur justification ;
    les suivantes restent proposées telles quelles. Le pilote doit voir tout ce
    qui est volable depuis la piste, pas seulement ce que le moteur a préféré.
    """
    seen = {selected.ident}
    items: list[dict] = []
    for candidate in ranked:
        if candidate.procedure.ident in seen:
            continue
        seen.add(candidate.procedure.ident)
        items.append(
            {
                "value": candidate.procedure.ident,
                "runways": list(candidate.procedure.runways),
                "reason": candidate.reason,
                "confidence": candidate.confidence.value,
            }
        )
    for procedure in procedures:
        if procedure.ident in seen:
            continue
        seen.add(procedure.ident)
        items.append(
            {
                "value": procedure.ident,
                "runways": list(procedure.runways),
                "reason": "procédure publiée compatible avec la piste",
            }
        )
    return items


def _transition_alternatives(
    procedure: Procedure, selected: str | None
) -> list[dict]:
    return [
        {"value": ident, "reason": "transition publiée"}
        for ident in procedure.transition_idents()
        if ident != selected
    ]

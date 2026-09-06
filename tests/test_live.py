"""Sources de position : unités demandées et dégradation propre."""

from __future__ import annotations

import ctypes

import pytest

from navixav.msfs import client as msfs_client
from navixav.live.base import AircraftState, PositionUnavailable
from navixav.live.registry import LiveTracker
from navixav.live.simconnect import (
    _CAPABILITY_VARIABLES,
    _CONFIGURATION_VARIABLES,
    _FENIX_CONTROL_VARIABLES,
    _FENIX_BARO_VARIABLES,
    _FENIX_ILS_VARIABLES,
    _NAV_SELECTION_VARIABLES,
    _AIRCRAFT_TITLE_VARIABLES,
    _LIGHT_STATE_VARIABLES,
    _MODERN_CONFIGURATION_VARIABLES,
    _PAUSE_VARIABLES,
    _VARIABLES,
    SimConnectSource,
)
from navixav.msfs.client import SimConnectClient, SimConnectError


# --------------------------------------------------------------------------- #
# Unités
#
# NaviXav ne convertit plus rien : il demande l'unité au simulateur, qui la
# fournit. C'est ce qui protège du piège de « PLANE HEADING DEGREES TRUE »,
# dont le nom annonce des degrés alors que l'unité native est le radian.
# --------------------------------------------------------------------------- #


def test_every_variable_declares_its_unit():
    assert _VARIABLES
    for name, unit in _VARIABLES:
        assert name and unit, f"unité manquante pour {name}"


def test_headings_are_requested_in_degrees():
    """Le nom de la variable ment sur son unité : on impose la nôtre."""
    units = dict(_VARIABLES)
    assert units["PLANE HEADING DEGREES TRUE"] == "Degrees"
    assert units["PLANE HEADING DEGREES MAGNETIC"] == "Degrees"


def test_position_and_speed_units():
    units = dict(_VARIABLES)
    assert units["PLANE LATITUDE"] == "Degrees"
    assert units["PLANE LONGITUDE"] == "Degrees"
    assert units["PLANE ALTITUDE"] == "Feet"
    assert units["GROUND VELOCITY"] == "Knots"
    assert units["AIRSPEED INDICATED"] == "Knots"
    assert units["VERTICAL SPEED"] == "Feet per minute"


def test_configuration_variables_declare_their_units():
    for name, unit in (
        _CONFIGURATION_VARIABLES
        + _MODERN_CONFIGURATION_VARIABLES
        + _LIGHT_STATE_VARIABLES
        + _CAPABILITY_VARIABLES
        + _FENIX_CONTROL_VARIABLES
        + _FENIX_BARO_VARIABLES
        + _FENIX_ILS_VARIABLES
        + _NAV_SELECTION_VARIABLES
    ):
        assert name and unit, f"unité manquante pour {name}"


def test_configuration_units_avoid_local_conversions():
    """Les unités affichées sont demandées au simulateur, jamais recalculées."""
    units = dict(_CONFIGURATION_VARIABLES)
    assert units["KOHLSMAN SETTING MB"] == "Millibars"
    assert units["FUEL TOTAL QUANTITY WEIGHT"] == "Kilograms"
    assert units["TOTAL WEIGHT"] == "Kilograms"
    assert units["NAV ACTIVE FREQUENCY:1"] == "MHz"
    assert units["TOTAL AIR TEMPERATURE"] == "Celsius"
    assert units["AMBIENT WIND VELOCITY"] == "Knots"


def test_position_block_stays_independent_of_configuration():
    """La position ne doit pas dépendre de variables qu'un avion peut ignorer."""
    position = {name for name, _unit in _VARIABLES}
    optional = {name for name, _unit in _CONFIGURATION_VARIABLES}
    assert not position & optional


# --------------------------------------------------------------------------- #
# Client SimConnect unique
# --------------------------------------------------------------------------- #


_POSITION_VALUES = {
    "PLANE LATITUDE": 48.723,
    "PLANE LONGITUDE": 2.379,
    "PLANE ALTITUDE": 5100.0,
    "PLANE ALT ABOVE GROUND": 4300.0,
    "PLANE HEADING DEGREES TRUE": 371.5,
    "PLANE HEADING DEGREES MAGNETIC": -2.0,
    "GROUND VELOCITY": 185.0,
    "AIRSPEED INDICATED": 172.0,
    "VERTICAL SPEED": -700.0,
    "SIM ON GROUND": 0.0,
}


class FakeClient:
    """Client SimConnect factice, un bloc de variables à la fois.

    `failing` liste les blocs qui doivent lever, pour vérifier que l'échec d'un
    bloc secondaire ne fait pas tomber la position.
    """

    def __init__(self, failing: tuple[str, ...] = ()) -> None:
        self.failing = failing
        self.calls: list[int] = []

    def read_simvars(self, variables, timeout_s: float = 3.0):
        self.calls.append(len(variables))
        if variables == _VARIABLES:
            if "position" in self.failing:
                raise SimConnectError("bloc position refusé")
            return dict(_POSITION_VALUES)
        if variables == _CONFIGURATION_VARIABLES:
            if "configuration" in self.failing:
                raise SimConnectError("variable inconnue de cet avion")
            values = {name: 0.0 for name, _unit in _CONFIGURATION_VARIABLES}
            values.update({
                "GEAR HANDLE POSITION": 1.0,
                "GEAR TOTAL PCT EXTENDED": 100.0,
                "GEAR CENTER POSITION": 100.0,
                "GEAR LEFT POSITION": 100.0,
                "GEAR RIGHT POSITION": 100.0,
                "FLAPS HANDLE INDEX": 2.0,
                "TRAILING EDGE FLAPS LEFT ANGLE": 15.0,
                "SPOILERS ARMED": 1.0,
                "LIGHT LANDING": 1.0,
                "LIGHT STROBE": 1.0,
                "KOHLSMAN SETTING MB": 1013.25,
                # Trois altitudes distinctes : vraie 5100, indiquée 5000,
                # standard 4800. Les confondre passerait inaperçu autrement.
                "INDICATED ALTITUDE": 5000.0,
                "PRESSURE ALTITUDE": 4800.0,
                "AUTOPILOT MASTER": 1.0,
                "AUTOPILOT ALTITUDE LOCK VAR": 6000.0,
                "AUTOPILOT HEADING LOCK DIR": 361.0,
                "COM ACTIVE FREQUENCY:1": 121.855,
                "NAV ACTIVE FREQUENCY:1": 110.30,
                "NAV LOCALIZER:1": -107.0,
                "FUEL TOTAL QUANTITY WEIGHT": 4200.0,
                "AMBIENT WIND DIRECTION": 400.0,
                "SIMULATION RATE": 1.0,
            })
            return values
        if variables == _PAUSE_VARIABLES:
            if "pause" in self.failing:
                raise SimConnectError("état de pause indisponible")
            return {"MOTION SIMULATION": 1.0}
        if variables == _MODERN_CONFIGURATION_VARIABLES:
            if "modern_configuration" in self.failing:
                raise SimConnectError("SimVars récentes indisponibles")
            return {
                "KOHLSMAN SETTING STD:1": 1.0,
                "KOHLSMAN SETTING MB EX1:1": 1008.0,
                "IS ANY OPEN INTERACTIVE POINTS RISKING TO CAUSE CRASH": 1.0,
            }
        if variables == _LIGHT_STATE_VARIABLES:
            if "light_states" in self.failing:
                raise SimConnectError("masque des feux indisponible")
            return {"LIGHT STATES": 0.0}
        if variables == _CAPABILITY_VARIABLES:
            if "capabilities" in self.failing:
                raise SimConnectError("capacités indisponibles")
            return {
                "IS GEAR RETRACTABLE": 1.0,
                "FLAPS AVAILABLE": 1.0,
                "SPOILER AVAILABLE": 0.0,
                "FLAPS NUM HANDLE POSITIONS": 5.0,
            }
        if variables == _FENIX_BARO_VARIABLES:
            return {"L:B_FCU_EFIS1_BARO_STD": 1.0}
        if variables == _FENIX_ILS_VARIABLES:
            return {"NAV ACTIVE FREQUENCY:3": 108.15}
        if variables == _NAV_SELECTION_VARIABLES:
            return {"AUTOPILOT NAV SELECTED": 1.0}
        raise AssertionError(f"bloc de variables inattendu : {variables}")

    def close(self):
        pass


def test_simconnect_source_maps_direct_values(monkeypatch):
    """La source temps réel passe par le client ctypes commun, sans conversion."""
    source = SimConnectSource()
    fake = FakeClient()
    monkeypatch.setattr(source, "_connect", lambda: fake)

    state = source.read()

    assert state.latitude == 48.723
    assert state.longitude == 2.379
    assert state.altitude_ft == 5100.0
    assert state.height_above_ground_ft == 4300.0
    assert state.heading_true_deg == 11.5
    assert state.heading_magnetic_deg == 358.0
    assert state.ground_speed_kt == 185.0
    assert state.indicated_airspeed_kt == 172.0
    assert state.vertical_speed_fpm == -700.0
    assert not state.on_ground
    assert state.paused is False
    assert state.source == "SimConnect"


def test_simconnect_source_reports_normal_and_active_pause(monkeypatch):
    source = SimConnectSource()
    fake = FakeClient()
    original = fake.read_simvars

    def read_paused(variables, timeout_s=3.0):
        if variables == _PAUSE_VARIABLES:
            return {"MOTION SIMULATION": 0.0}
        return original(variables, timeout_s)

    fake.read_simvars = read_paused
    monkeypatch.setattr(source, "_connect", lambda: fake)

    assert source.read().paused is True


def test_pause_state_is_optional(monkeypatch):
    source = SimConnectSource()
    monkeypatch.setattr(source, "_connect", lambda: FakeClient(("pause",)))

    state = source.read()

    assert state.paused is None
    assert state.latitude == 48.723


# --------------------------------------------------------------------------- #
# Configuration avion
# --------------------------------------------------------------------------- #


def test_configuration_is_read_and_normalised(monkeypatch):
    source = SimConnectSource()
    monkeypatch.setattr(source, "_connect", lambda: FakeClient())

    configuration = source.read().configuration

    assert configuration is not None
    assert configuration.gear_handle_down is True
    assert configuration.gear_extended_pct == 100.0
    assert configuration.flaps_handle_index == 2
    # Le braquage réel accompagne le rang de manette : sur un avion dont le
    # marquage des crans est inconnu, c'est lui qui les rend lisibles.
    assert configuration.flaps_angle_deg == 15.0
    assert configuration.spoilers_armed is True
    assert configuration.lights["landing"] is True
    assert configuration.lights["taxi"] is False
    assert configuration.altimeter_hpa == 1008.0
    assert configuration.altimeter_std is True
    assert configuration.interactive_points_crash_risk is True
    assert configuration.selected_altitude_ft == 6000.0
    # La fréquence composée est rapportée telle quelle : NaviXav constate
    # le réglage de la radio, il ne le commande pas.
    assert configuration.com1_frequency_mhz == pytest.approx(121.855)
    assert configuration.nav1_frequency_mhz == pytest.approx(110.30)
    assert configuration.ils_frequency_mhz == pytest.approx(110.30)
    assert configuration.fuel_total_kg == 4200.0
    # Les caps sont ramenés dans [0, 360[ comme ceux de la position.
    assert configuration.selected_heading_deg == 1.0
    assert configuration.nav1_course_deg == 253.0
    assert configuration.wind_direction_deg == 40.0


def test_recent_simvars_can_fail_without_hiding_historical_configuration(monkeypatch):
    source = SimConnectSource()
    monkeypatch.setattr(
        source, "_connect", lambda: FakeClient(failing=("modern_configuration",))
    )

    configuration = source.read().configuration

    assert configuration is not None
    assert configuration.altimeter_hpa == 1013.25
    assert configuration.altimeter_std is None
    assert configuration.interactive_points_crash_risk is None


def test_light_mask_restores_states_missing_from_individual_simvars(monkeypatch):
    """Les avions complexes peuvent ne renseigner que le masque officiel."""

    class AggregateLightsClient(FakeClient):
        def read_simvars(self, variables, timeout_s: float = 3.0):
            if variables == _LIGHT_STATE_VARIABLES:
                # NAV + BCN + WING + LOGO, comme le panneau de la capture.
                return {"LIGHT STATES": 0x0001 | 0x0002 | 0x0080 | 0x0100}
            values = super().read_simvars(variables, timeout_s)
            if variables == _CONFIGURATION_VARIABLES:
                for name in (
                    "LIGHT LANDING",
                    "LIGHT TAXI",
                    "LIGHT STROBE",
                    "LIGHT NAV",
                    "LIGHT BEACON",
                    "LIGHT LOGO",
                    "LIGHT WING",
                ):
                    values[name] = 0.0
            return values

    source = SimConnectSource()
    monkeypatch.setattr(source, "_connect", lambda: AggregateLightsClient())

    lights = source.read().configuration.lights

    assert lights == {
        "landing": False,
        "taxi": False,
        "strobe": False,
        "nav": True,
        "beacon": True,
        "logo": True,
        "wing": True,
    }


def test_light_mask_failure_keeps_individual_light_states(monkeypatch):
    source = SimConnectSource()
    monkeypatch.setattr(
        source, "_connect", lambda: FakeClient(failing=("light_states",))
    )

    configuration = source.read().configuration

    assert configuration is not None
    assert configuration.lights["landing"] is True
    assert configuration.lights["strobe"] is True
    assert configuration.lights["nav"] is False


def test_stale_control_simvars_fall_back_to_the_values_that_move(monkeypatch):
    """Les avions tiers ne mettent pas tous à jour la même SimVar standard."""

    class MovingControlsClient(FakeClient):
        def __init__(self):
            super().__init__()
            self.configuration_reads = 0

        def read_simvars(self, variables, timeout_s: float = 3.0):
            values = super().read_simvars(variables, timeout_s)
            if variables != _CONFIGURATION_VARIABLES:
                return values
            self.configuration_reads += 1
            if self.configuration_reads == 1:
                values.update({
                    "FLAPS HANDLE INDEX": 4.0,
                    "FLAPS EFFECTIVE HANDLE INDEX": 4.0,
                    "TRAILING EDGE FLAPS LEFT INDEX": 4.0,
                    "SPOILERS HANDLE POSITION": 0.0,
                    "SPOILERS LEFT POSITION": 0.0,
                    "SPOILERS RIGHT POSITION": 0.0,
                    "BRAKE PARKING POSITION": 1.0,
                    "BRAKE PARKING INDICATOR": 1.0,
                })
            else:
                # Poignée volets et frein POSITION restent figés ; les index
                # effectif/surface, spoilers et indicateur continuent de vivre.
                values.update({
                    "FLAPS HANDLE INDEX": 4.0,
                    "FLAPS EFFECTIVE HANDLE INDEX": 2.0,
                    "TRAILING EDGE FLAPS LEFT INDEX": 2.0,
                    "SPOILERS HANDLE POSITION": 0.0,
                    "SPOILERS LEFT POSITION": 42.0,
                    "SPOILERS RIGHT POSITION": 40.0,
                    "BRAKE PARKING POSITION": 1.0,
                    "BRAKE PARKING INDICATOR": 0.0,
                })
            return values

    source = SimConnectSource()
    fake = MovingControlsClient()
    monkeypatch.setattr(source, "_connect", lambda: fake)

    first = source.read().configuration
    second = source.read().configuration

    assert first is not None and second is not None
    assert first.flaps_handle_index == 4
    assert second.flaps_handle_index == 2
    assert first.spoilers_handle_pct == 0.0
    assert second.spoilers_handle_pct == 42.0
    assert first.parking_brake is True
    assert second.parking_brake is False


@pytest.mark.parametrize("model", ("FENIX A319", "FENIX A320", "FENIX A321"))
def test_fenix_family_reads_its_cockpit_levers_with_engines_off(monkeypatch, model):
    class FenixClient(FakeClient):
        def read_simvars(self, variables, timeout_s: float = 3.0):
            if variables == _FENIX_CONTROL_VARIABLES:
                return {
                    "L:S_FC_FLAPS": 2.0,
                    "L:A_FC_SPEEDBRAKE": 3.0,
                    "L:S_MIP_PARKING_BRAKE": 1.0,
                    "L:S_OH_PNEUMATIC_ENG1_ANTI_ICE": 1.0,
                    "L:S_OH_PNEUMATIC_ENG2_ANTI_ICE": 1.0,
                }
            return super().read_simvars(variables, timeout_s)

    source = SimConnectSource()
    source.set_aircraft_hint(model)
    monkeypatch.setattr(source, "_connect", lambda: FenixClient())

    configuration = source.read().configuration

    assert configuration is not None
    assert configuration.flaps_handle_index == 2
    assert configuration.spoilers_handle_pct == 100.0
    assert configuration.spoilers_armed is False
    assert configuration.parking_brake is True
    # La SimVar standard du faux client vaut zéro : seule la commande Fenix
    # prouve ici que l'antigivrage est réellement sélectionné.
    assert configuration.engine_anti_ice is True


def test_fenix_speedbrake_zero_means_armed(monkeypatch):
    class ArmedFenixClient(FakeClient):
        def read_simvars(self, variables, timeout_s: float = 3.0):
            if variables == _FENIX_CONTROL_VARIABLES:
                return {
                    "L:S_FC_FLAPS": 0.0,
                    "L:A_FC_SPEEDBRAKE": 0.0,
                    "L:S_MIP_PARKING_BRAKE": 0.0,
                    "L:S_OH_PNEUMATIC_ENG1_ANTI_ICE": 0.0,
                    "L:S_OH_PNEUMATIC_ENG2_ANTI_ICE": 0.0,
                }
            values = super().read_simvars(variables, timeout_s)
            if variables == _CONFIGURATION_VARIABLES:
                # La SimVar standard figée dit explicitement DISARMED : seul
                # l'adaptateur sélectionné par TITLE peut corriger le résultat.
                values["SPOILERS ARMED"] = 0.0
            return values

    source = SimConnectSource()
    source.set_aircraft_hint("Fenix A320")
    monkeypatch.setattr(source, "_connect", lambda: ArmedFenixClient())

    configuration = source.read().configuration

    assert configuration is not None
    assert configuration.flaps_handle_index == 0
    assert configuration.spoilers_handle_pct == 0.0
    assert configuration.spoilers_armed is True
    assert configuration.parking_brake is False


def test_loaded_msfs_title_selects_fenix_when_simbrief_name_is_generic(monkeypatch):
    """L'OFP décrit souvent un Airbus générique, pas l'addon réellement chargé."""

    class LoadedFenixClient(FakeClient):
        def read_string_simvar(self, name: str, timeout_s: float = 3.0):
            assert name == "TITLE"
            return "Fenix A320 CFM Air France"

        def read_simvars(self, variables, timeout_s: float = 3.0):
            if variables == _FENIX_CONTROL_VARIABLES:
                return {
                    "L:S_FC_FLAPS": 0.0,
                    "L:A_FC_SPEEDBRAKE": 0.0,
                    "L:S_MIP_PARKING_BRAKE": 0.0,
                    "L:S_OH_PNEUMATIC_ENG1_ANTI_ICE": 0.0,
                    "L:S_OH_PNEUMATIC_ENG2_ANTI_ICE": 0.0,
                }
            return super().read_simvars(variables, timeout_s)

    source = SimConnectSource()
    source.set_aircraft_hint("Airbus A320neo")
    monkeypatch.setattr(source, "_connect", lambda: LoadedFenixClient())

    state = source.read()

    assert state.title == "Fenix A320 CFM Air France"
    assert state.configuration is not None
    assert state.configuration.spoilers_armed is True


@pytest.mark.parametrize("model", ["A319", "A320", "A321"])
@pytest.mark.parametrize("frequency", [108.15, 110.30, None, 0, float("nan"), float("inf")])
def test_fenix_ils_uses_nav3_without_replacing_nav1(monkeypatch, model, frequency):
    class IlsClient(FakeClient):
        def read_simvars(self, variables, timeout_s=3.0):
            if variables == _FENIX_CONTROL_VARIABLES:
                raise SimConnectError("controls unavailable")
            if variables == _FENIX_ILS_VARIABLES:
                if frequency is None:
                    raise SimConnectError("ILS unavailable")
                return {"NAV ACTIVE FREQUENCY:3": frequency}
            return super().read_simvars(variables, timeout_s)

    source = SimConnectSource()
    source.set_aircraft_hint(f"Fenix {model}")
    monkeypatch.setattr(source, "_connect", lambda: IlsClient())
    configuration = source.read().configuration
    assert configuration.nav1_frequency_mhz == pytest.approx(110.30)
    if frequency in (108.15, 110.30):
        assert configuration.ils_frequency_mhz == pytest.approx(frequency)
    else:
        assert configuration.ils_frequency_mhz is None


@pytest.mark.parametrize("selected", [1, 2, 3, 4, 0, 1.5, None])
def test_generic_ils_follows_selected_receiver_and_rejects_unknown(selected):
    class Radios:
        def read_simvars(self, variables, timeout_s):
            if variables == _NAV_SELECTION_VARIABLES:
                if selected is None:
                    raise SimConnectError("selection unavailable")
                return {"AUTOPILOT NAV SELECTED": selected}
            return {variables[0][0]: 108.15}

    result = SimConnectSource()._read_ils_receiver(Radios(), {"NAV ACTIVE FREQUENCY:1": 113.6})
    if selected in (1, 2, 3, 4):
        assert result == (selected, 113.6 if selected == 1 else 108.15)
    else:
        assert result == (None, None)


@pytest.mark.parametrize("title", ["FlyByWire A320 Neo", "A32NX Air France", "Fenix A319", "Fenix A320", "Fenix A321"])
def test_dedicated_ils_mapping_ignores_generic_nav_selection(title):
    class Radios:
        def read_simvars(self, variables, timeout_s):
            assert variables == _FENIX_ILS_VARIABLES
            return {"NAV ACTIVE FREQUENCY:3": 108.15}

    source = SimConnectSource()
    source._aircraft_title = title
    assert source._read_ils_receiver(Radios(), {}) == (3, 108.15)


def test_loaded_aircraft_overrides_planned_fenix_for_ils():
    source = SimConnectSource()
    source._aircraft_title = "Cessna 172"
    source.set_aircraft_hint("Fenix A320")
    assert source._read_ils_receiver(FakeClient(), {"NAV ACTIVE FREQUENCY:1": 110.30}) == (1, 110.30)


def test_fenix_reports_anti_ice_off_if_either_engine_is_unprotected(monkeypatch):
    class OneEngineUnprotectedClient(FakeClient):
        def read_simvars(self, variables, timeout_s: float = 3.0):
            if variables == _FENIX_CONTROL_VARIABLES:
                return {
                    "L:S_FC_FLAPS": 0.0,
                    "L:A_FC_SPEEDBRAKE": 0.0,
                    "L:S_MIP_PARKING_BRAKE": 0.0,
                    "L:S_OH_PNEUMATIC_ENG1_ANTI_ICE": 1.0,
                    "L:S_OH_PNEUMATIC_ENG2_ANTI_ICE": 0.0,
                }
            return super().read_simvars(variables, timeout_s)

    source = SimConnectSource()
    source.set_aircraft_hint("Fenix A320")
    monkeypatch.setattr(source, "_connect", lambda: OneEngineUnprotectedClient())

    assert source.read().configuration.engine_anti_ice is False


def test_fenix_does_not_turn_a_lvar_read_failure_into_a_false_anti_ice_alarm(
    monkeypatch,
):
    class UnavailableFenixControlsClient(FakeClient):
        def read_simvars(self, variables, timeout_s: float = 3.0):
            if variables == _FENIX_CONTROL_VARIABLES:
                raise SimConnectError("bloc Fenix momentanément indisponible")
            return super().read_simvars(variables, timeout_s)

    source = SimConnectSource()
    source.set_aircraft_hint("Fenix A320")
    monkeypatch.setattr(source, "_connect", lambda: UnavailableFenixControlsClient())

    assert source.read().configuration.engine_anti_ice is None


def test_atc_model_identifies_an_aircraft_whose_title_is_empty(monkeypatch):
    class ModelOnlyClient(FakeClient):
        def read_string_simvar(self, name: str, timeout_s: float = 3.0):
            assert name in _AIRCRAFT_TITLE_VARIABLES
            return "" if name == "TITLE" else "A320"

    source = SimConnectSource()
    monkeypatch.setattr(source, "_connect", lambda: ModelOnlyClient())

    state = source.read()

    assert state.title == "A320"


def test_the_three_altitudes_stay_distinct(monkeypatch):
    """Le niveau de vol se lit dans l'atmosphère standard, pas en altitude vraie.

    En air chaud l'altitude vraie dépasse la pression de plus de mille pieds :
    les confondre affichait FL342 pour un avion stabilisé au FL330.
    """
    source = SimConnectSource()
    monkeypatch.setattr(source, "_connect", lambda: FakeClient())

    state = source.read()

    assert state.altitude_ft == 5100.0
    assert state.configuration is not None
    assert state.configuration.indicated_altitude_ft == 5000.0
    assert state.configuration.pressure_altitude_ft == 4800.0
    # La pression est demandée en pieds, sans conversion locale.
    assert dict(_CONFIGURATION_VARIABLES)["PRESSURE ALTITUDE"] == "Feet"


def test_configuration_uses_individual_gear_positions_when_total_is_stale(monkeypatch):
    """Les positions des jambes restent fiables si l'agrégat ne bouge plus."""

    class GearInTransitClient(FakeClient):
        def read_simvars(self, variables, timeout_s: float = 3.0):
            values = super().read_simvars(variables, timeout_s)
            if variables == _CONFIGURATION_VARIABLES:
                values.update({
                    "GEAR TOTAL PCT EXTENDED": 100.0,
                    "GEAR CENTER POSITION": 62.0,
                    "GEAR LEFT POSITION": 58.0,
                    "GEAR RIGHT POSITION": 60.0,
                })
            return values

    source = SimConnectSource()
    monkeypatch.setattr(source, "_connect", lambda: GearInTransitClient())

    configuration = source.read().configuration

    assert configuration is not None
    assert configuration.gear_extended_pct == 58.0


def test_capabilities_describe_the_airframe(monkeypatch):
    source = SimConnectSource()
    monkeypatch.setattr(source, "_connect", lambda: FakeClient())

    capabilities = source.read().configuration.capabilities

    assert capabilities is not None
    assert capabilities.retractable_gear is True
    assert capabilities.flaps is True
    assert capabilities.spoilers is False
    assert capabilities.flap_positions == 5


def test_capabilities_are_read_once_per_connection(monkeypatch):
    """Inutile de redemander à chaque sondage ce qui ne change pas en vol."""
    source = SimConnectSource()
    fake = FakeClient()
    monkeypatch.setattr(source, "_connect", lambda: fake)

    source.read()
    first = list(fake.calls)
    source.read()

    capability_calls = fake.calls.count(len(_CAPABILITY_VARIABLES))
    assert capability_calls == 1
    assert len(fake.calls) > len(first)


def test_position_survives_a_refused_configuration_block(monkeypatch):
    """Un avion qui n'expose pas tout ne doit pas couper le suivi de position."""
    source = SimConnectSource()
    monkeypatch.setattr(source, "_connect", lambda: FakeClient(failing=("configuration",)))

    state = source.read()

    assert state.latitude == 48.723
    assert state.configuration is None


def test_refused_configuration_block_is_put_to_sleep(monkeypatch):
    """Le retenter à chaque sondage coûterait un délai d'attente complet."""
    source = SimConnectSource()
    fake = FakeClient(failing=("configuration",))
    monkeypatch.setattr(source, "_connect", lambda: fake)

    source.read()
    attempts_after_first = fake.calls.count(len(_CONFIGURATION_VARIABLES))
    source.read()

    assert fake.calls.count(len(_CONFIGURATION_VARIABLES)) == attempts_after_first == 1


def test_configuration_survives_missing_capabilities(monkeypatch):
    """Sans capacités, la configuration reste lisible : l'interface se taira."""
    source = SimConnectSource()
    monkeypatch.setattr(source, "_connect", lambda: FakeClient(failing=("capabilities",)))

    configuration = source.read().configuration

    assert configuration is not None
    assert configuration.capabilities is None


# --------------------------------------------------------------------------- #
# Définitions SimConnect
#
# Le suivi appelle read_simvars plusieurs fois par seconde pendant des heures :
# déclarer une définition à chaque lecture les accumulerait côté simulateur.
# --------------------------------------------------------------------------- #


class FakeDll:
    def __init__(self) -> None:
        self.added: list[tuple[int, bytes, bytes | None]] = []
        self.cleared: list[int] = []

    def SimConnect_AddToDataDefinition(
        self, _handle, definition_id, name, unit, *_rest
    ):
        self.added.append((definition_id, name, unit))
        return 0

    def SimConnect_ClearDataDefinition(self, _handle, definition_id):
        self.cleared.append(definition_id)
        return 0


def _client_with_fake_dll() -> tuple[SimConnectClient, FakeDll]:
    """Un client sans simulateur : seule la gestion des définitions est testée."""
    client = object.__new__(SimConnectClient)
    dll = FakeDll()
    client._dll = dll
    client._handle = None
    client._next_id = 1
    client._simvar_definitions = {}
    client._string_simvar_definitions = {}
    return client, dll


def test_definition_is_declared_once_and_reused():
    client, dll = _client_with_fake_dll()

    first = client._definition_for(_VARIABLES)
    second = client._definition_for(_VARIABLES)

    assert first == second
    assert len(dll.added) == len(_VARIABLES)


def test_distinct_blocks_get_distinct_definitions():
    client, _dll = _client_with_fake_dll()

    position = client._definition_for(_VARIABLES)
    configuration = client._definition_for(_CONFIGURATION_VARIABLES)

    assert position != configuration


def test_aircraft_title_uses_a_reused_string_definition():
    client, dll = _client_with_fake_dll()

    first = client._string_definition_for("TITLE")
    second = client._string_definition_for("TITLE")

    assert first == second
    assert [(name, unit) for _definition, name, unit in dll.added] == [
        (b"TITLE", None)
    ]


def test_forgetting_a_definition_releases_it():
    """Une variable refusée rend la définition inutilisable : il faut la rendre."""
    client, dll = _client_with_fake_dll()
    definition = client._definition_for(_VARIABLES)

    client._forget_definition(_VARIABLES)

    assert dll.cleared == [definition]
    assert client._definition_for(_VARIABLES) != definition


def test_msfs2024_ai_creation_uses_ex1_with_legacy_fsltl_title():
    class AiDll:
        def __init__(self):
            self.args = None

        def SimConnect_AICreateNonATCAircraft_EX1(self, *args):
            self.args = args
            return 1

    client = object.__new__(SimConnectClient)
    client._dll = AiDll()
    client._handle = None
    client._next_id = 1

    with pytest.raises(SimConnectError, match="Impossible de créer"):
        client.create_ai_aircraft(
            "FSLTL A320 Air France", "AFR123",
            latitude=48.0, longitude=2.0, altitude_ft=5000,
            heading_deg=90, airspeed_kt=180, on_ground=False,
        )

    assert client._dll.args[1:4] == (
        b"FSLTL A320 Air France", b"", b"AFR123"
    )


def test_created_ai_aircraft_is_frozen_before_client_position_updates():
    class AiDll:
        def __init__(self):
            self.assigned = msfs_client._RECV_ASSIGNED_OBJECT_ID()
            self.assigned.dwSize = ctypes.sizeof(self.assigned)
            self.assigned.dwID = msfs_client.RECV_ID_ASSIGNED_OBJECT_ID
            self.assigned.dwRequestID = 2
            self.assigned.dwObjectID = 42
            self._view = ctypes.cast(
                ctypes.byref(self.assigned), ctypes.POINTER(msfs_client._RECV)
            )
            self.mapped = []
            self.transmitted = []

        def SimConnect_AICreateNonATCAircraft_EX1(self, *_args):
            return 0

        def SimConnect_GetNextDispatch(self, _handle, pointer_ref, size_ref):
            pointer_ref._obj.contents = self._view.contents
            size_ref._obj.value = ctypes.sizeof(msfs_client._RECV_ASSIGNED_OBJECT_ID)
            return 0

        def SimConnect_AIReleaseControl(self, *_args):
            return 0

        def SimConnect_MapClientEventToSimEvent(self, _handle, event_id, name):
            self.mapped.append((event_id, name))
            return 0

        def SimConnect_TransmitClientEvent(self, *args):
            self.transmitted.append(args)
            return 0

        def SimConnect_AIRemoveObject(self, *_args):
            return 0

    client = object.__new__(SimConnectClient)
    client._dll = AiDll()
    client._handle = None
    client._next_id = 1
    client._client_events = {}

    assert client.create_ai_aircraft(
        "FSLTL A320 Air France", "AFR123",
        latitude=48.0, longitude=2.0, altitude_ft=5000,
        heading_deg=90, airspeed_kt=180, on_ground=False,
    ) == (2, 42)

    assert [name for _event_id, name in client._dll.mapped] == [
        event.encode("ascii") for event in msfs_client.AI_POSITION_FREEZE_EVENTS
    ]
    assert len(client._dll.transmitted) == 3
    assert all(call[1] == 42 and call[3] == 1 for call in client._dll.transmitted)


def test_old_simconnect_dll_is_rejected_for_msfs2024(monkeypatch, tmp_path):
    old_dll = tmp_path / "SimConnect.dll"
    old_dll.touch()
    monkeypatch.setattr(msfs_client.ct, "WinDLL", lambda _path: object())

    with pytest.raises(SimConnectError, match="API EX1 absente"):
        SimConnectClient(old_dll)


def test_msfs2024_local_connection_ignores_legacy_client_configuration():
    assert msfs_client.SIMCONNECT_OPEN_CONFIGINDEX_LOCAL == 0xFFFFFFFF


# --------------------------------------------------------------------------- #
# Dégradation propre
# --------------------------------------------------------------------------- #


def test_state_serialises():
    state = AircraftState(
        latitude=48.72, longitude=2.36, paused=True, source="Test"
    )
    payload = state.to_dict()
    assert payload["latitude"] == 48.72
    assert payload["source"] == "Test"
    assert "on_ground" in payload
    assert payload["paused"] is True


# --------------------------------------------------------------------------- #
# Trafic voisin
#
# C'est la source du plan de roulage. Elle vient du simulateur parce qu'elle
# doit être exacte au mètre : un relevé réseau, vieux de quinze secondes,
# poserait un appareil sur la voie d'à côté.
# --------------------------------------------------------------------------- #


class _TrafficClient:
    """Client factice qui énumère des objets, avion du joueur compris."""

    def __init__(self, rows, failing: bool = False) -> None:
        self.rows = rows
        self.failing = failing
        self.user_object_id = 1
        self.calls = 0

    def read_objects(self, variables, radius_m, text_variable=None, **_kwargs):
        self.calls += 1
        self.radius_m = radius_m
        self.text_variable = text_variable
        if self.failing:
            raise SimConnectError("énumération refusée")
        return self.rows


def _object(object_id: int, latitude: float, callsign: str, **extra) -> dict:
    row = {
        "object_id": object_id,
        "PLANE LATITUDE": latitude,
        "PLANE LONGITUDE": 2.379,
        "PLANE ALTITUDE": 380.0,
        "PLANE ALT ABOVE GROUND": 0.0,
        "PLANE HEADING DEGREES TRUE": 361.0,
        "GROUND VELOCITY": 12.0,
        "SIM ON GROUND": 1.0,
        "ATC ID": callsign,
    }
    row.update(extra)
    return row


def test_the_traffic_leaves_out_the_player(monkeypatch):
    """Le simulateur inclut le joueur dans sa propre énumération.

    Le garder dessinerait un second avion exactement sur le sien, et le
    pilote croirait à un appareil arrêté sur sa position.
    """
    source = SimConnectSource()
    fake = _TrafficClient([
        _object(1, 48.723, "F-HNAV"),
        _object(7, 48.730, "AFR23TZ"),
    ])
    monkeypatch.setattr(source, "_connect", lambda: fake)

    reports = source.traffic()

    assert [report.callsign for report in reports] == ["AFR23TZ"]
    assert reports[0].object_id == 7
    assert reports[0].on_ground is True
    # Le cap est ramené dans le tour, comme celui de l'avion suivi.
    assert reports[0].heading_true_deg == 1.0
    assert fake.text_variable == "ATC ID"


def test_a_refused_enumeration_is_put_to_sleep(monkeypatch):
    """Le trafic est un confort : son refus ne pèse pas sur le simulateur.

    Réessayer à chaque relevé ferait payer deux fois par seconde une demande
    dont on sait déjà qu'elle échoue.
    """
    source = SimConnectSource()
    fake = _TrafficClient([], failing=True)
    monkeypatch.setattr(source, "_connect", lambda: fake)

    assert source.traffic() == []
    assert source.traffic() == []
    assert fake.calls == 1


def test_the_tracker_says_nothing_without_an_established_source():
    """Le trafic accompagne un suivi : il n'en déclenche jamais la découverte."""
    tracker = LiveTracker()

    assert tracker.traffic() == []


def test_strict_traffic_reports_failure_including_retry_cooldown(monkeypatch):
    source = SimConnectSource()
    fake = _TrafficClient([], failing=True)
    monkeypatch.setattr(source, "_connect", lambda: fake)
    tracker = LiveTracker()
    tracker._active = source
    for _ in range(2):
        with pytest.raises(PositionUnavailable):
            tracker.traffic(strict=True)
    assert fake.calls == 1
    assert tracker.traffic() == []


@pytest.mark.parametrize("aircraft", ["Fenix A319", "Fenix A320", "Fenix A321"])
@pytest.mark.parametrize("mode", [0, 1, None, 2])
def test_fenix_captain_std_overrides_generic_mode_and_missing_data_stays_unknown(monkeypatch, aircraft, mode):
    class BaroClient(FakeClient):
        def read_simvars(self, variables, timeout_s=3.0):
            if variables == _FENIX_CONTROL_VARIABLES:
                return {name: 0 for name, unit in variables}
            if variables == _FENIX_BARO_VARIABLES:
                if mode is None:
                    raise SimConnectError("EFIS unavailable")
                # Actual session: the input remains zero with the displayed STD on.
                return {"L:B_FCU_EFIS1_BARO_STD": mode, "L:S_FCU_EFIS1_BARO_STD": 0}
            result = super().read_simvars(variables, timeout_s)
            if variables == _MODERN_CONFIGURATION_VARIABLES:
                result["KOHLSMAN SETTING STD:1"] = 1 if mode == 0 else 0
                result["KOHLSMAN SETTING MB EX1:1"] = 1008
            return result

    source = SimConnectSource()
    source.set_aircraft_hint(aircraft)
    monkeypatch.setattr(source, "_connect", lambda: BaroClient())
    configuration = source.read().configuration
    if mode in (0, 1):
        assert configuration.altimeter_std is bool(mode)
        assert configuration.altimeter_hpa == (1013.25 if mode == 1 else 1008)
    else:
        assert configuration.altimeter_std is None
        assert configuration.altimeter_hpa is None

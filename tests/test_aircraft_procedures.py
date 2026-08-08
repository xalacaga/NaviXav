"""Moteur de checklist propre à l'appareil chargé."""

from pathlib import Path

from navixav.aircraft import AircraftMatcher
from navixav.aircraft.procedures import evaluate_condition, procedure_payload
from navixav.config import Settings
from navixav.live.base import AircraftConfiguration, AircraftState
from navixav.web import app as web_app
from navixav.web.app import create_app


def _state(**configuration):
    return AircraftState(
        latitude=48.0,
        longitude=2.0,
        on_ground=True,
        title="Cessna 172 Skyhawk G1000",
        configuration=AircraftConfiguration(**configuration),
    )


def test_a_real_aircraft_loads_its_authored_normal_procedures():
    match = AircraftMatcher().match("Cessna 172 Skyhawk G1000")

    payload = procedure_payload(match)

    assert payload["available"] is True
    assert payload["aircraft"]["id"] == "cessna/c172"
    assert payload["aircraft"]["maturity"] == "authored"
    assert [phase["phase"] for phase in payload["phases"]][:6] == [
        "before_start", "start", "after_start", "taxi", "before_takeoff", "takeoff"
    ]


def test_simconnect_values_confirm_only_the_matching_automatic_steps():
    match = AircraftMatcher().match("Cessna 172 Skyhawk G1000")
    state = _state(
        parking_brake=True,
        flaps_handle_index=0,
        autopilot_master=False,
        lights={"landing": False, "strobe": False, "beacon": True},
    )

    payload = procedure_payload(match, state)
    before_takeoff = next(
        phase for phase in payload["phases"] if phase["phase"] == "before_takeoff"
    )
    status = {step["id"]: step["status"] for step in before_takeoff["steps"]}

    assert status["parking_brake_set"] == "complete"
    assert status["flaps_up"] == "complete"
    assert status["autopilot_off"] == "complete"
    assert status["landing_light"] == "pending"
    assert status["strobe_lights"] == "pending"


def test_an_unknown_simulator_value_never_becomes_false():
    condition = {"property": "configuration.lights.landing", "is": True}

    assert evaluate_condition(condition, _state(lights={})) is None
    assert evaluate_condition({"not": condition}, _state(lights={})) is None
    assert evaluate_condition(
        {"all_of": [condition, {"property": "state.on_ground", "is": True}]},
        _state(lights={}),
    ) is None


def test_absent_aircraft_systems_remove_irrelevant_steps():
    match = AircraftMatcher().match("Cessna 172 Skyhawk G1000")

    payload = procedure_payload(match, _state())

    steps = [step for phase in payload["phases"] for step in phase["steps"]]
    assert not any(step.get("requires_system") == "retractable_gear" for step in steps)
    assert not any("GEAR" in step["title"] for step in steps)


def test_an_uncovered_aircraft_gets_no_generic_checklist():
    payload = procedure_payload(AircraftMatcher().match("Imaginary Rocket 9000"))

    assert payload == {
        "available": False,
        "reason": "aircraft_not_covered",
        "phases": [],
    }


def test_live_api_evaluates_the_loaded_aircraft_procedure(monkeypatch):
    state = _state(parking_brake=True, lights={"beacon": True})

    class Tracker:
        def set_aircraft_hint(self, aircraft):
            self.hint = aircraft

        def read(self, allow_demo=False):
            return state

        def close(self):
            pass

    monkeypatch.setattr(web_app, "LiveTracker", Tracker)
    app = create_app(Settings(metar_source="simbrief"))
    endpoint = next(route.endpoint for route in app.routes if route.path == "/api/live")

    payload = endpoint(aircraft="Cessna 172 Skyhawk G1000")

    assert payload["connected"] is True
    assert payload["procedures"]["aircraft"]["id"] == "cessna/c172"
    before_start = payload["procedures"]["phases"][0]
    brakes = next(step for step in before_start["steps"] if step["id"] == "brakes")
    assert brakes["status"] == "complete"
    app.state.close_resources()


def test_interface_exposes_a_modern_procedure_module_in_all_languages():
    static = Path(web_app.__file__).parent / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    assert 'data-tab="procedures"' in html
    assert 'id="panel-procedures"' in html
    assert "function renderProcedurePanel" in javascript
    assert "procedureStepComplete" in javascript
    assert "data.procedures" in javascript
    assert ".procedure-flow" in css
    assert ".procedure-step.complete" in css
    for key in (
        "tab_procedures",
        "procedure_phase_before_takeoff",
        "procedure_confirmed_auto",
        "procedure_source_family",
        "procedure_source_manual",
    ):
        assert translations.count(f"{key}:") == 8
    assert "function procedureSourceText" in javascript
    assert "procedureSourceText(data.source)" in javascript
    assert "function procedurePhaseMark" in javascript
    assert "PROCEDURE_PHASE_ICON_PATHS" in javascript
    assert '"aria-current"' in javascript
    for selector in (
        ".procedure-aircraft-mark",
        ".procedure-aircraft-copy .card-kicker",
        ".procedure-phase-mark",
        ".procedure-workspace-mark",
        ".procedure-leader",
    ):
        assert selector in css
    procedure_kicker = css[css.index(".procedure-aircraft-copy .card-kicker") :]
    procedure_kicker = procedure_kicker[: procedure_kicker.index("}")]
    assert "font-size: 0.8rem" in procedure_kicker
    assert "font-weight: 700" in procedure_kicker


def test_a_confirmed_procedure_item_is_never_taken_back():
    """`status` dit ce que le simulateur voit, pas ce qui a été fait.

    La balise éteinte après l'arrêt, les volets rentrés après le décollage ou
    le frein de parking relâché faisaient reculer le compteur d'une phase
    depuis longtemps terminée.
    """
    static = Path(web_app.__file__).parent / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    latch = javascript[javascript.index("function latchProcedureProgress"):]
    latch = latch[: latch.index("\n}\n")]
    assert 'step.mode !== "auto" || step.status !== "complete"' in latch
    assert "saveProcedureManualProgress(progress, data)" in latch
    # Seule l'arrivée d'un état frais peut ajouter une confirmation.
    assert "latchProcedureProgress(currentProcedures);" in javascript

    complete = javascript[javascript.index("function procedureStepComplete"):]
    complete = complete[: complete.index("\n}\n")]
    assert "if (progress[procedureStepKey(phase, step)] === true) return true;" in complete

    # La réinitialisation du vol reste la seule sortie.
    reset = javascript[javascript.index('t("procedure_reset")'):]
    reset = reset[: reset.index("actions.append(reset);")]
    assert "sessionStorage.removeItem(procedureProgressKey())" in reset


def test_a_latched_item_says_where_its_confirmation_comes_from():
    """Annoncer « Confirmé · SimConnect » sur un point démenti serait faux."""
    static = Path(web_app.__file__).parent / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    assert 'complete ? "procedure_confirmed_earlier"' in javascript
    # Une ligne cochée ne porte plus la mise en forme de l'attente.
    assert 'row.classList.toggle("pending", step.status === "pending" && !complete);' in javascript
    assert translations.count("procedure_confirmed_earlier:") == 8

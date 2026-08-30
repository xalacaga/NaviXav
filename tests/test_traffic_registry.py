import requests

from navixav.traffic.base import (
    generic_callsign,
    is_own_position,
    TrafficAircraft,
)
from navixav.traffic.registry import AircraftRegistry, UNKNOWN_RETRY_S


class _Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("pas de corps JSON")
        return self._payload


class _Session:
    """Répond par source, chaque registre ayant sa couverture propre."""

    def __init__(self, responses):
        self.responses = dict(responses)
        self.calls = []
        self.closed = False

    def get(self, url, *, timeout, headers):
        source = "hexdb" if "hexdb.io" in url else "adsbdb"
        icao24 = url.rsplit("/", 1)[-1]
        self.calls.append((source, icao24))
        return self.responses.get((source, icao24), _Response(404))

    def close(self):
        self.closed = True


def _hexdb(icao_type, operator=""):
    return _Response(200, {"ICAOTypeCode": icao_type, "OperatorFlagCode": operator})


def _adsbdb(icao_type, operator=""):
    return _Response(200, {"response": {"aircraft": {
        "icao_type": icao_type, "registered_owner_operator_flag_code": operator,
    }}})


def _registry(tmp_path, responses=()):
    return AircraftRegistry(
        path=tmp_path / "registry.sqlite",
        session=_Session(dict(responses)),
        min_interval_s=0.0,
    )


def _resolve(registry, icao24):
    """Résout sans le fil de fond, pour un test déterministe."""
    identity = registry._fetch(icao24)
    if identity is not None:
        registry._store(identity)
    return identity


def test_identity_survives_from_one_flight_to_the_next(tmp_path):
    """L'adresse est gravée dans le transpondeur : la réponse est définitive."""
    responses = {("hexdb", "39abcd"): _hexdb("a320", "afr")}
    registry = _registry(tmp_path, responses)
    try:
        assert registry.lookup("39abcd") is None
        _resolve(registry, "39abcd")
        identity = registry.lookup("39abcd")
        assert identity is not None
        assert (identity.aircraft_type, identity.airline_icao) == ("A320", "AFR")
        assert identity.known
    finally:
        registry.close()

    # Un autre vol relit le même disque sans redemander quoi que ce soit.
    again = _registry(tmp_path, responses)
    try:
        identity = again.lookup("39abcd")
        assert identity is not None and identity.aircraft_type == "A320"
        assert again._session.calls == []
    finally:
        again.close()


def test_address_absent_from_the_registry_is_not_asked_again(tmp_path):
    registry = _registry(tmp_path, {})
    try:
        assert _resolve(registry, "000000") is not None
        # Retenue vide : elle ne repart pas à chaque relevé.
        stored = registry.lookup("000000")
        assert stored is not None and not stored.known
    finally:
        registry.close()


def test_an_unresolved_address_is_eventually_retried(tmp_path):
    """Le registre s'enrichit : une absence ne doit pas être définitive."""
    registry = _registry(tmp_path, {})
    try:
        _resolve(registry, "000000")
        registry._connection.execute(
            "UPDATE aircraft SET resolved_at = resolved_at - ? WHERE icao24 = ?",
            (UNKNOWN_RETRY_S + 60.0, "000000"),
        )
        registry._connection.commit()
        assert registry.lookup("000000") is None
    finally:
        registry.close()


def test_a_refused_answer_is_never_stored_as_a_truth(tmp_path):
    registry = _registry(tmp_path, {
        ("hexdb", "39abcd"): _Response(429),
        ("adsbdb", "39abcd"): _Response(429),
    })
    try:
        assert _resolve(registry, "39abcd") is None
        assert registry.lookup("39abcd") is None
    finally:
        registry.close()


def test_the_same_address_is_queued_once(tmp_path):
    """Une adresse déjà en attente ne repart pas une seconde fois.

    Le fil de fond est neutralisé plutôt que stoppé : `request` le relance de
    lui-même — c'est voulu, une demande après `close()` doit repartir — et il
    viderait la file avant la vérification.
    """
    registry = _registry(tmp_path, {})
    registry._ensure_worker = lambda: None
    try:
        registry.request("39abcd")
        registry.request("39abcd")
        assert registry._pending.qsize() == 1
    finally:
        registry.close()


def _aircraft(latitude, longitude, altitude_ft=500.0):
    return TrafficAircraft(
        "x", "X", "A320", "AFR", latitude, longitude, altitude_ft=altitude_ft,
        ground_speed_kt=0, heading_deg=0, on_ground=True,
    )


def test_an_aircraft_on_the_player_is_the_player():
    centre = (43.6304, 1.3725)
    assert is_own_position(_aircraft(43.6304, 1.3725), centre, 500.0)
    # Le stationnement voisin doit rester visible.
    assert not is_own_position(_aircraft(43.6354, 1.3725), centre, 500.0)
    # Le survol n'est pas une superposition.
    assert not is_own_position(_aircraft(43.6304, 1.3725, 5000.0), centre, 500.0)
    # Sans position du joueur, rien n'est escamoté.
    assert not is_own_position(_aircraft(43.6304, 1.3725), None, None)


def test_a_generic_callsign_is_stable_and_readable():
    assert generic_callsign("39abcd") == generic_callsign("39abcd")
    assert generic_callsign("39abcd").startswith("TFC")
    assert generic_callsign("") == "TFC0000"
    assert len(generic_callsign("a0b1c2d3")) <= 12


def test_the_second_registry_covers_what_the_first_ignores(tmp_path):
    """Les couvertures ne se recouvrent pas : l'une rattrape l'autre."""
    registry = _registry(tmp_path, {("adsbdb", "406b1a"): _adsbdb("ULAC", "")})
    try:
        identity = _resolve(registry, "406b1a")
        assert identity is not None and identity.aircraft_type == "ULAC"
        assert [source for source, _ in registry._session.calls] == ["hexdb", "adsbdb"]
    finally:
        registry.close()


def test_a_network_failure_is_never_stored_as_an_unknown_aircraft(tmp_path):
    """Une panne retenue un mois priverait l'appareil de son type pour rien."""
    class _Failing:
        def get(self, *_args, **_kwargs):
            raise requests.ConnectionError("hors ligne")

        def close(self):
            return None

    registry = AircraftRegistry(
        path=tmp_path / "registry.sqlite", session=_Failing(), min_interval_s=0.0,
    )
    try:
        assert _resolve(registry, "39abcd") is None
        assert registry.lookup("39abcd") is None
    finally:
        registry.close()

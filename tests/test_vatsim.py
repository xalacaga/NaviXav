"""Postes de contrôle en ligne sur VATSIM.

Le flux est celui que le réseau publie lui-même. Ces tests portent sur la
lecture qu'en fait NaviXav : ce qu'il retient, ce qu'il écarte, et le fait
qu'un réseau muet n'invente jamais un contrôle qui n'existe pas.
"""

from __future__ import annotations

import pytest
import requests

from navixav.vatsim import TRAFFIC_TTL_S, VatsimClient, VatsimError


class _FakeResponse:
    def __init__(self, payload, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _FakeSession:
    """Session qui compte ses appels, pour vérifier le cache."""

    def __init__(self, payload, status: int = 200) -> None:
        self.payload = payload
        self.status = status
        self.calls = 0

    def get(self, url, timeout=None, headers=None):
        self.calls += 1
        if isinstance(self.payload, Exception):
            raise self.payload
        return _FakeResponse(self.payload, self.status)


def _feed(*controllers, atis=()) -> dict:
    return {
        "general": {"update_timestamp": "2026-08-29T12:00:00.0000000Z"},
        "controllers": list(controllers),
        "atis": list(atis),
    }


def _controller(callsign: str, frequency: str, facility: int = 4) -> dict:
    return {
        "callsign": callsign,
        "frequency": frequency,
        "facility": facility,
        "name": "Contrôleur",
    }


def test_the_positions_of_an_airport_are_gathered_by_role():
    session = _FakeSession(_feed(
        _controller("CYYZ_TWR", "118.700"),
        _controller("CYYZ_GND", "121.900"),
        _controller("LFPG_APP", "121.155"),
    ))
    client = VatsimClient(session=session)

    found = client.positions(["CYYZ"])

    assert [position.code for position in found["CYYZ"]] == ["GND", "TWR"]
    assert found["CYYZ"][1].callsign == "CYYZ_TWR"
    assert found["CYYZ"][1].frequency_mhz == pytest.approx(118.700)


def test_an_airport_without_a_controller_is_answered_not_omitted():
    """« Personne en ligne » et « la question n'a pas été posée » diffèrent."""
    session = _FakeSession(_feed(_controller("LFPG_TWR", "118.655")))
    client = VatsimClient(session=session)

    assert client.positions(["CYYZ", "LFPG"]) == {
        "CYYZ": [],
        "LFPG": client.positions(["LFPG"])["LFPG"],
    }


def test_a_north_american_short_callsign_serves_its_airport():
    """« YYZ_GND » tient CYYZ, « JFK_TWR » tient KJFK.

    Sans cette équivalence, la moitié d'un terrain nord-américain passerait
    pour non contrôlée alors qu'un contrôleur y est assis.
    """
    session = _FakeSession(_feed(
        _controller("YYZ_GND", "121.900"),
        _controller("JFK_TWR", "119.100"),
    ))
    client = VatsimClient(session=session)

    found = client.positions(["CYYZ", "KJFK"])
    assert [position.code for position in found["CYYZ"]] == ["GND"]
    assert [position.code for position in found["KJFK"]] == ["TWR"]


def test_an_observer_is_not_a_controller():
    """Un observateur connecté n'assure aucun service.

    Le marquer ferait croire à un contrôle qui n'existe pas, et le pilote
    appellerait dans le vide.
    """
    session = _FakeSession(_feed(
        _controller("CYYZ_TWR", "199.998", facility=0),
        _controller("CYYZ_GND", "121.900"),
    ))
    client = VatsimClient(session=session)

    assert [p.code for p in client.positions(["CYYZ"])["CYYZ"]] == ["GND"]


def test_the_atis_is_a_position_like_any_other():
    """Le réseau le publie à part ; pour un pilote c'est une fréquence."""
    session = _FakeSession(_feed(
        _controller("CYYZ_TWR", "118.700"),
        atis=[_controller("CYYZ_ATIS", "120.825", facility=0)],
    ))
    client = VatsimClient(session=session)

    assert [p.code for p in client.positions(["CYYZ"])["CYYZ"]] == ["ATIS", "TWR"]


def test_an_unknown_suffix_is_ignored():
    """Un indicatif que le réseau n'assied sur aucun poste connu."""
    session = _FakeSession(_feed(
        _controller("CYYZ_XYZ", "121.000"),
        _controller("CYYZ", "121.000"),
    ))
    client = VatsimClient(session=session)

    assert client.positions(["CYYZ"])["CYYZ"] == []


def test_the_feed_is_read_once_within_its_lifetime():
    """Le réseau demande de l'espacer ; deux terrains ne font qu'un appel."""
    session = _FakeSession(_feed(_controller("CYYZ_TWR", "118.700")))
    client = VatsimClient(session=session)

    client.positions(["CYYZ"])
    client.positions(["LFPG"])
    client.updated_at()

    assert session.calls == 1


def test_an_expired_cache_is_read_again():
    session = _FakeSession(_feed(_controller("CYYZ_TWR", "118.700")))
    client = VatsimClient(session=session, ttl_s=0)

    client.positions(["CYYZ"])
    client.positions(["CYYZ"])

    assert session.calls == 2


def test_a_silent_network_raises_rather_than_inventing_a_controller():
    session = _FakeSession(requests.ConnectionError("réseau coupé"))
    client = VatsimClient(session=session)

    with pytest.raises(VatsimError):
        client.positions(["CYYZ"])


# --------------------------------------------------------------------------- #
# Endpoint
#
# Le réglage est le garde-fou : tant qu'il est fermé, aucun appel ne part.
# --------------------------------------------------------------------------- #


def _endpoint(app, path: str):
    return next(route.endpoint for route in app.routes if route.path == path)


def _app(enabled: bool, client: VatsimClient, traffic: bool = False):
    from dataclasses import replace

    from navixav.config import Settings
    from navixav.web.app import create_app

    settings = replace(
        Settings.load(), vatsim_enabled=enabled, traffic_enabled=traffic
    )
    return create_app(settings=settings, vatsim_client=client)


def test_the_network_is_not_called_while_the_setting_is_off():
    """Un appel réseau n'apprend rien à qui ne vole pas sur le réseau."""
    session = _FakeSession(_feed(_controller("CYYZ_TWR", "118.700")))
    app = _app(False, VatsimClient(session=session))

    answer = _endpoint(app, "/api/vatsim")(icao="CYYZ")

    assert answer["enabled"] is False
    assert answer["positions"] == {}
    assert session.calls == 0


def test_the_endpoint_reports_the_positions_of_both_airports():
    session = _FakeSession(_feed(
        _controller("CYYZ_GND", "121.900"),
        _controller("LFPG_TWR", "118.655"),
    ))
    app = _app(True, VatsimClient(session=session))

    answer = _endpoint(app, "/api/vatsim")(icao="CYYZ,LFPG")

    assert answer["available"] is True
    assert [p["code"] for p in answer["positions"]["CYYZ"]] == ["GND"]
    assert answer["positions"]["LFPG"][0]["callsign"] == "LFPG_TWR"
    assert answer["updated_at"].startswith("2026-08-29")


def test_a_network_failure_marks_nothing_online():
    """Sans réponse, aucun poste n'est armé — et surtout pas figé.

    Renvoyer le dernier état connu laisserait un contrôleur déconnecté marqué
    en ligne, ce qui est pire que de ne rien marquer.
    """
    session = _FakeSession(requests.ConnectionError("réseau coupé"))
    app = _app(True, VatsimClient(session=session))

    answer = _endpoint(app, "/api/vatsim")(icao="CYYZ")

    assert answer["available"] is False
    assert answer["positions"] == {}
    assert "reason" in answer


# --------------------------------------------------------------------------- #
# Trafic
#
# Le même flux, lu pour une autre question. Ce qui change est la fraîcheur
# exigée : un poste tenu se démode en une minute, une position en quinze
# secondes.
# --------------------------------------------------------------------------- #


def _pilot(callsign: str, latitude: float, longitude: float, **extra) -> dict:
    pilot = {
        "callsign": callsign,
        "latitude": latitude,
        "longitude": longitude,
        "altitude": 35000,
        "heading": 271,
        "groundspeed": 452,
    }
    pilot.update(extra)
    return pilot


def _traffic_feed(*pilots) -> dict:
    feed = _feed()
    feed["pilots"] = list(pilots)
    return feed


def test_a_connected_aircraft_is_read_with_its_flight_plan():
    session = _FakeSession(_traffic_feed(_pilot(
        "AFR23TZ", 48.85, 2.35,
        flight_plan={
            "aircraft_short": "A359",
            "departure": "LFPG",
            "arrival": "KJFK",
        },
    )))
    client = VatsimClient(session=session)

    [entry] = client.traffic()

    assert entry.callsign == "AFR23TZ"
    assert entry.latitude == pytest.approx(48.85)
    assert entry.altitude_ft == 35000
    assert entry.heading_deg == 271
    assert entry.ground_speed_kt == 452
    assert (entry.aircraft, entry.departure, entry.arrival) == (
        "A359", "LFPG", "KJFK"
    )


def test_a_client_that_has_not_loaded_its_flight_is_not_an_aircraft():
    """Un client fraîchement connecté se déclare à 0°N 0°E.

    Le laisser passer poserait un avion en plein golfe de Guinée, et le
    pilote y verrait un trafic là où il n'y a que de l'eau.
    """
    session = _FakeSession(_traffic_feed(
        _pilot("BAW117", 0.0, 0.0),
        _pilot("KLM43V", 52.30, 4.76),
    ))
    client = VatsimClient(session=session)

    assert [entry.callsign for entry in client.traffic()] == ["KLM43V"]


def test_an_unreadable_position_is_dropped_rather_than_guessed():
    session = _FakeSession(_traffic_feed(
        _pilot("EZY84DP", "nord", 4.76),
        {"callsign": "DLH2AB"},
        _pilot("", 52.30, 4.76),
        _pilot("RYR19PA", 52.30, 4.76, heading=None, altitude=None),
    ))
    client = VatsimClient(session=session)

    [entry] = client.traffic()
    assert entry.callsign == "RYR19PA"
    # Une donnée absente reste absente : zéro serait une position inventée.
    assert (entry.heading_deg, entry.altitude_ft) == (None, None)


def test_the_traffic_is_capped():
    session = _FakeSession(_traffic_feed(*(
        _pilot(f"TST{index:03d}", 40.0 + index / 100, 2.0) for index in range(10)
    )))
    client = VatsimClient(session=session)

    assert len(client.traffic(limit=4)) == 4


def test_the_traffic_refuses_a_feed_kept_for_the_controllers():
    """Une minute suffit pour un poste tenu, jamais pour une position.

    Le cache est partagé : sans exigence propre, le trafic hériterait de la
    fraîcheur des contrôleurs et traînerait une minute de retard, soit dix
    kilomètres en croisière.
    """
    session = _FakeSession(_traffic_feed(_pilot("AFR23TZ", 48.85, 2.35)))
    client = VatsimClient(session=session, ttl_s=600.0)

    client.positions(["LFPG"])
    # Le flux vieillit d'une demi-minute : encore neuf pour les postes, périmé
    # pour une position.
    client._fetched_at -= 30.0

    client.positions(["LFPG"])
    assert session.calls == 1

    client.traffic()
    assert session.calls == 2
    assert TRAFFIC_TTL_S <= 15.0


def test_a_fresh_traffic_reading_serves_the_controllers_too():
    """L'exigence du trafic ne relance pas un téléchargement de plus."""
    session = _FakeSession(_traffic_feed(_pilot("AFR23TZ", 48.85, 2.35)))
    client = VatsimClient(session=session)

    client.traffic()
    client.positions(["LFPG"])

    assert session.calls == 1


def test_the_network_traffic_is_not_fetched_while_the_setting_is_off():
    session = _FakeSession(_traffic_feed(_pilot("AFR23TZ", 48.85, 2.35)))
    app = _app(False, VatsimClient(session=session), traffic=False)

    answer = _endpoint(app, "/api/vatsim/traffic")()

    assert answer["enabled"] is False
    assert answer["traffic"] == []
    assert session.calls == 0


def test_the_traffic_endpoint_reports_every_aircraft():
    session = _FakeSession(_traffic_feed(
        _pilot("AFR23TZ", 48.85, 2.35),
        _pilot("KLM43V", 52.30, 4.76),
    ))
    app = _app(False, VatsimClient(session=session), traffic=True)

    answer = _endpoint(app, "/api/vatsim/traffic")()

    assert answer["available"] is True
    assert [entry["callsign"] for entry in answer["traffic"]] == [
        "AFR23TZ", "KLM43V"
    ]


def test_a_silent_network_empties_the_traffic_rather_than_freezing_it():
    session = _FakeSession(requests.ConnectionError("réseau coupé"))
    app = _app(False, VatsimClient(session=session), traffic=True)

    answer = _endpoint(app, "/api/vatsim/traffic")()

    assert answer["available"] is False
    assert answer["traffic"] == []
    assert "reason" in answer


# --------------------------------------------------------------------------- #
# Fiche d'un appareil
#
# Le flux principal ne porte pas la fréquence : elle vient du relevé des
# émetteurs, publié à part. Ce second téléchargement ne doit jamais peser sur
# le simple affichage de la carte.
# --------------------------------------------------------------------------- #


class _FakeNetwork:
    """Session qui répond selon l'URL demandée, et retient ce qu'on lui a pris."""

    def __init__(self, feed, transceivers=()) -> None:
        self.feed = feed
        self.transceivers = list(transceivers)
        self.calls: list[str] = []

    def get(self, url, timeout=None, headers=None):
        self.calls.append(url)
        if "transceivers" in url:
            return _FakeResponse(self.transceivers)
        return _FakeResponse(self.feed)


def _transceiver(callsign: str, hertz: int) -> dict:
    return {
        "callsign": callsign,
        "transceivers": [{"id": 0, "frequency": hertz}],
    }


def test_the_card_of_an_aircraft_carries_its_plan_and_its_frequency():
    session = _FakeNetwork(
        _traffic_feed(_pilot(
            "KLM723", 40.0, -70.0,
            name="Enrico Sassetti",
            flight_plan={
                "aircraft_short": "B77W",
                "departure": "EHAM",
                "arrival": "MUHA",
            },
        )),
        [_transceiver("KLM723", 122800000)],
    )
    client = VatsimClient(session=session)

    card = client.detail("klm723")

    assert card.callsign == "KLM723"
    assert card.pilot == "Enrico Sassetti"
    assert card.aircraft == "B77W"
    assert (card.departure, card.arrival) == ("EHAM", "MUHA")
    assert card.frequency_mhz == pytest.approx(122.800)


def test_a_pilot_without_a_transceiver_still_has_a_card():
    """Une radio pas encore réglée n'est pas une raison de taire la route."""
    session = _FakeNetwork(
        _traffic_feed(_pilot("KLM723", 40.0, -70.0)),
        [_transceiver("AFR23TZ", 121500000)],
    )
    client = VatsimClient(session=session)

    card = client.detail("KLM723")

    assert card is not None
    assert card.frequency_mhz is None


def test_an_aircraft_that_left_the_network_has_no_card():
    session = _FakeNetwork(_traffic_feed(_pilot("KLM723", 40.0, -70.0)))
    client = VatsimClient(session=session)

    assert client.detail("AFR23TZ") is None
    assert client.detail("  ") is None


def test_drawing_the_map_never_downloads_the_transceivers():
    """Ce relevé pèse autant que le flux principal pour un seul détail.

    Le payer à chaque rafraîchissement de la carte doublerait le coût du
    trafic pour une fréquence que personne ne regarde tant qu'aucune fiche
    n'est ouverte.
    """
    session = _FakeNetwork(_traffic_feed(_pilot("KLM723", 40.0, -70.0)))
    client = VatsimClient(session=session)

    client.traffic()

    assert not any("transceivers" in url for url in session.calls)


def test_the_card_is_refused_while_the_traffic_is_off():
    from fastapi import HTTPException

    session = _FakeNetwork(_traffic_feed(_pilot("KLM723", 40.0, -70.0)))
    app = _app(False, VatsimClient(session=session), traffic=False)

    with pytest.raises(HTTPException):
        _endpoint(app, "/api/vatsim/aircraft/{callsign}")(callsign="KLM723")
    assert session.calls == []


def test_the_card_endpoint_answers_with_the_airport_fields():
    session = _FakeNetwork(
        _traffic_feed(_pilot(
            "KLM723", 40.0, -70.0,
            flight_plan={"departure": "EHAM", "arrival": "MUHA"},
        )),
    )
    app = _app(False, VatsimClient(session=session), traffic=True)

    card = _endpoint(app, "/api/vatsim/aircraft/{callsign}")(callsign="KLM723")

    assert card["callsign"] == "KLM723"
    # Les noms sont présents même vides : l'interface distingue « inconnu de la
    # base » de « le service n'a rien dit ».
    assert "departure_name" in card and "arrival_name" in card

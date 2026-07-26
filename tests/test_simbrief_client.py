"""Le corps JSON d'une erreur SimBrief doit primer sur le code HTTP 400."""

from __future__ import annotations

import json

import pytest
import requests

from navixav.simbrief.client import SimBriefClient, SimBriefError


class _FakeResponse:
    def __init__(self, payload: dict | str, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = payload if isinstance(payload, str) else json.dumps(payload)

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def json(self):
        if isinstance(self._payload, str):
            raise ValueError("pas du JSON")
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"{self.status_code}")


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.params: dict | None = None

    def get(self, _url, params=None, timeout=None):
        self.params = params
        return self.response


def _client(response: _FakeResponse, **kwargs) -> SimBriefClient:
    return SimBriefClient(
        pilot_id=kwargs.pop("pilot_id", "602151"),
        session=_FakeSession(response),
        **kwargs,
    )


def test_requires_an_identifier():
    with pytest.raises(SimBriefError, match="SIMBRIEF_PILOT_ID"):
        SimBriefClient()


def test_no_flight_plan_on_file_is_explained():
    response = _FakeResponse(
        {
            "fetch": {
                "userid": "602151",
                "status": "Error: No flight plan on file for the specified user",
            }
        },
        status_code=400,
    )
    with pytest.raises(SimBriefError) as excinfo:
        _client(response).fetch_latest()
    message = str(excinfo.value)
    assert "aucun plan de vol n'a été généré" in message
    assert "Generate OFP" in message


def test_unknown_userid_is_explained():
    response = _FakeResponse(
        {"fetch": {"userid": "", "status": "Error: Unknown UserID"}}, status_code=400
    )
    with pytest.raises(SimBriefError, match="Pilot ID inconnu"):
        _client(response).fetch_latest()


def test_successful_fetch_returns_payload():
    payload = {"fetch": {"status": "Success"}, "origin": {"icao_code": "LFST"}}
    assert _client(_FakeResponse(payload)).fetch_latest() == payload


def test_pilot_id_is_sent_as_userid():
    session = _FakeSession(_FakeResponse({"fetch": {"status": "Success"}}))
    SimBriefClient(pilot_id="602151", session=session).fetch_latest()
    assert session.params["userid"] == "602151"
    assert "username" not in session.params


def test_username_is_used_when_no_pilot_id():
    session = _FakeSession(_FakeResponse({"fetch": {"status": "Success"}}))
    SimBriefClient(username="xavier", session=session).fetch_latest()
    assert session.params["username"] == "xavier"
    assert "userid" not in session.params


def test_non_json_response_is_reported():
    with pytest.raises(SimBriefError, match="illisible"):
        _client(_FakeResponse("<html>maintenance</html>")).fetch_latest()

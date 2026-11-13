import pytest

from game_api import config, create_app
from game_api.errors import InvalidCurrencyError, UpstreamError
from game_api.routes import search as search_route


@pytest.fixture
def client():
    return create_app().test_client()


def test_search_returns_service_result(client, monkeypatch):
    calls = []

    def fake(query, currency):
        calls.append((query, currency))
        return [{"name": "Portal"}]

    monkeypatch.setattr(search_route, "search_prices", fake)
    res = client.get("/api/search?query=%20portal%20&currency=thb")

    assert res.status_code == 200
    assert res.get_json() == [{"name": "Portal"}]
    assert calls == [("portal", "THB")]  # trimmed + upper-cased


@pytest.mark.parametrize("qs", ["", "?query=", "?query=%20%20"])
def test_search_requires_query(client, qs):
    assert client.get(f"/api/search{qs}").status_code == 400


@pytest.mark.parametrize(
    "error, status",
    [(InvalidCurrencyError("XYZ"), 400), (UpstreamError("down"), 502)],
)
def test_search_maps_errors(client, monkeypatch, error, status):
    def fail(query, currency):
        raise error

    monkeypatch.setattr(search_route, "search_prices", fail)
    res = client.get("/api/search?query=portal")

    assert res.status_code == status
    assert "error" in res.get_json()


@pytest.mark.parametrize(
    "client_id, secret, igdb",
    [("id", "secret", "configured"), ("id", None, "missing"), (None, None, "missing")],
)
def test_health(client, monkeypatch, client_id, secret, igdb):
    monkeypatch.setattr(config, "TWITCH_CLIENT_ID", client_id)
    monkeypatch.setattr(config, "TWITCH_CLIENT_SECRET", secret)

    body = client.get("/api/health").get_json()

    assert body == {"status": "ok", "igdb": igdb}
    assert "secret" not in str(body)  # never leaks the values

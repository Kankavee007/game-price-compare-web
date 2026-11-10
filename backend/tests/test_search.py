import pytest

from game_api import cheapshark, create_app, exchange
from game_api.http import UpstreamError

SEARCH_RESULT = [
    {
        "gameID": "82",
        "cheapest": "9.99",
        "cheapestDealID": "deal-82",
        "external": "Portal",
        "thumb": "https://example.com/portal.jpg",
    }
]


@pytest.fixture
def client(monkeypatch):
    # reset in-memory caches so tests don't leak into each other
    monkeypatch.setattr(exchange, "_rates", {})
    monkeypatch.setattr(cheapshark, "_store_cache", {})
    monkeypatch.setattr(exchange, "get_rates", lambda: {"USD": 1, "THB": 35.0})
    monkeypatch.setattr(cheapshark, "search_games", lambda title: SEARCH_RESULT)
    monkeypatch.setattr(cheapshark, "get_deal_stores", lambda ids: {"deal-82": "1"})
    monkeypatch.setattr(cheapshark, "get_store_names", lambda: {"1": "Steam"})
    return create_app().test_client()


def test_search_converts_price_and_names_store(client):
    res = client.get("/api/search?query=portal&currency=thb")

    assert res.status_code == 200
    assert res.get_json() == [
        {
            "name": "Portal",
            "price": 349.65,
            "currency": "THB",
            "thumb": "https://example.com/portal.jpg",
            "storeID": "1",
            "storeName": "Steam",
            "dealUrl": "https://www.cheapshark.com/redirect?dealID=deal-82",
        }
    ]


@pytest.mark.parametrize("qs", ["", "?query=", "?query=%20%20"])
def test_search_requires_query(client, qs):
    res = client.get(f"/api/search{qs}")
    assert res.status_code == 400


def test_search_rejects_unknown_currency(client):
    res = client.get("/api/search?query=portal&currency=XYZ")
    assert res.status_code == 400


def test_search_returns_502_when_upstream_fails(client, monkeypatch):
    def boom(title):
        raise UpstreamError("down")

    monkeypatch.setattr(cheapshark, "search_games", boom)
    res = client.get("/api/search?query=portal")

    assert res.status_code == 502
    assert "error" in res.get_json()


def test_unknown_store_gives_null_name(client, monkeypatch):
    monkeypatch.setattr(cheapshark, "get_deal_stores", lambda ids: {})
    game = client.get("/api/search?query=portal").get_json()[0]

    assert game["storeID"] is None
    assert game["storeName"] is None


def test_exchange_uses_stale_cache_when_api_down(monkeypatch):
    monkeypatch.setattr(exchange, "_rates", {"THB": 30.0})
    monkeypatch.setattr(exchange, "_fetched_at", 0.0)  # expired

    def down(url, params=None):
        raise UpstreamError("down")

    monkeypatch.setattr(exchange, "get_json", down)
    assert exchange.get_rates() == {"THB": 30.0}


def test_exchange_raises_without_cache(monkeypatch):
    monkeypatch.setattr(exchange, "_rates", {})

    def down(url, params=None):
        raise UpstreamError("down")

    monkeypatch.setattr(exchange, "get_json", down)
    with pytest.raises(UpstreamError):
        exchange.get_rates()


def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}

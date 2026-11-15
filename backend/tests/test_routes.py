import pytest

from game_api import config, create_app
from game_api.errors import InvalidCurrencyError, InvalidParamError, UpstreamError
from game_api.routes import deals as deals_route
from game_api.routes import prices as prices_route
from game_api.routes import search as search_route
from game_api.routes import stores as stores_route


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


def test_deals_passes_query_currency_and_args(client, monkeypatch):
    calls = []

    def fake(query, currency, args):
        calls.append((query, currency, args.get("maxPrice")))
        return {"results": [], "page": 0, "totalPages": 1, "currency": currency}

    monkeypatch.setattr(deals_route, "find_deals", fake)
    res = client.get("/api/deals?q=%20portal%20&currency=thb&maxPrice=300")

    assert res.status_code == 200
    assert res.get_json()["currency"] == "THB"
    assert calls == [("portal", "THB", "300")]


@pytest.mark.parametrize(
    "error, status, message",
    [
        (InvalidParamError("sort must be one of: x"), 400, "sort must be one of: x"),
        (InvalidCurrencyError("XYZ"), 400, "unsupported currency: USD"),
        (UpstreamError("down"), 502, "price service unavailable, try again later"),
    ],
)
def test_deals_maps_errors(client, monkeypatch, error, status, message):
    def fail(query, currency, args):
        raise error

    monkeypatch.setattr(deals_route, "find_deals", fail)
    res = client.get("/api/deals")

    assert res.status_code == status
    assert res.get_json() == {"error": message}


def test_deals_bad_param_end_to_end(client):
    # Validation happens before any API call, so this needs no mocks
    res = client.get("/api/deals?minPrice=abc")

    assert res.status_code == 400
    assert "minPrice" in res.get_json()["error"]


def test_stores_returns_service_result(client, monkeypatch):
    stores = [{"storeID": "1", "storeName": "Steam", "logo": None}]
    monkeypatch.setattr(stores_route, "list_active_stores", lambda: stores)
    res = client.get("/api/stores")

    assert res.status_code == 200
    assert res.get_json() == stores


def test_stores_upstream_error_is_502(client, monkeypatch):
    def fail():
        raise UpstreamError("down")

    monkeypatch.setattr(stores_route, "list_active_stores", fail)
    res = client.get("/api/stores")

    assert res.status_code == 502
    assert res.get_json() == {"error": "store list unavailable, try again later"}


@pytest.mark.parametrize(
    "url, route_module, name, value",
    [
        ("/api/deals", "deals", "find_deals", {"results": [], "page": 0, "totalPages": 1}),
        ("/api/stores", "stores", "list_active_stores", []),
    ],
)
def test_shared_responses_are_cacheable(client, monkeypatch, url, route_module, name, value):
    module = {"deals": deals_route, "stores": stores_route}[route_module]
    monkeypatch.setattr(module, name, lambda *args: value)
    res = client.get(url)

    assert res.status_code == 200
    assert res.headers["Cache-Control"] == "public, s-maxage=900, stale-while-revalidate=300"


@pytest.mark.parametrize(
    "url, route_module, name",
    [("/api/deals", "deals", "find_deals"), ("/api/stores", "stores", "list_active_stores")],
)
def test_errors_are_not_cacheable(client, monkeypatch, url, route_module, name):
    def fail(*args):
        raise UpstreamError("down")

    module = {"deals": deals_route, "stores": stores_route}[route_module]
    monkeypatch.setattr(module, name, fail)
    res = client.get(url)

    assert res.status_code == 502
    assert "s-maxage" not in res.headers.get("Cache-Control", "")


def test_prices_passes_ids_and_currency(client, monkeypatch):
    calls = []

    def fake(ids, currency):
        calls.append((ids, currency))
        return [{"gameID": "82"}]

    monkeypatch.setattr(prices_route, "get_prices", fake)
    res = client.get("/api/prices?ids=82,99&currency=thb")

    assert res.status_code == 200
    assert res.get_json() == [{"gameID": "82"}]
    assert calls == [("82,99", "THB")]


@pytest.mark.parametrize(
    "error, status",
    [(InvalidParamError("ids is required"), 400), (InvalidCurrencyError("X"), 400), (UpstreamError("down"), 502)],
)
def test_prices_maps_errors(client, monkeypatch, error, status):
    def fail(ids, currency):
        raise error

    monkeypatch.setattr(prices_route, "get_prices", fail)
    res = client.get("/api/prices?ids=1")

    assert res.status_code == status
    assert "error" in res.get_json()


def test_prices_without_ids_end_to_end(client):
    res = client.get("/api/prices")
    assert res.status_code == 400
    assert "ids" in res.get_json()["error"]

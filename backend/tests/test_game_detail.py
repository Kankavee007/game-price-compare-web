import pytest

from game_api import create_app
from game_api.errors import ConfigError, UpstreamError, UpstreamNotFoundError
from game_api.services import cheapshark, exchange, igdb

CHEAPSHARK_GAME = {
    "info": {"title": "LEGO Batman", "steamAppID": "21000", "thumb": "https://example.com/thumb.jpg"},
    "cheapestPriceEver": {"price": "2.28", "date": 1759177295},
    "deals": [
        {"storeID": "2", "dealID": "deal-b", "price": "10.00", "retailPrice": "20.00", "savings": "50.000000"},
        {"storeID": "1", "dealID": "deal-a", "price": "20.00", "retailPrice": "20.00", "savings": "0.000000"},
        # same price as deal-b: the tie is broken by store name (Fanatical < GOG)
        {"storeID": "3", "dealID": "deal-c", "price": "10.00", "retailPrice": "19.99", "savings": "49.974987"},
    ],
}

IGDB_GAME = {
    "name": "LEGO Batman: The Videogame",
    "genres": [{"id": 31, "name": "Adventure"}, {"id": 8, "name": "Platform"}],
    "rating": 72.4,
    "rating_count": 150,
    "aggregated_rating": 79.6,
    "cover": {"image_id": "co1abc"},
    "summary": "Bricks.",
    "first_release_date": 1222128000,  # 2008-09-23 UTC
}


@pytest.fixture
def client():
    return create_app().test_client()


@pytest.fixture(autouse=True)
def fake_apis(monkeypatch):
    monkeypatch.setattr(exchange, "get_rates", lambda: {"USD": 1, "THB": 35.0})
    monkeypatch.setattr(cheapshark, "get_game", lambda game_id: CHEAPSHARK_GAME)
    monkeypatch.setattr(cheapshark, "get_store_names", lambda: {"1": "Steam", "2": "GOG", "3": "Fanatical"})
    monkeypatch.setattr(igdb, "find_game", lambda steam_app_id, title: IGDB_GAME)


def test_returns_igdb_info_and_deals_sorted_by_price(client):
    res = client.get("/api/games/612")

    assert res.status_code == 200
    body = res.get_json()
    assert body["id"] == "612"
    assert body["name"] == "LEGO Batman: The Videogame"
    assert body["thumb"] == "https://example.com/thumb.jpg"
    assert body["cover"] == "https://images.igdb.com/igdb/image/upload/t_cover_big/co1abc.jpg"
    assert body["genres"] == ["Adventure", "Platform"]
    assert body["rating"] == 72
    assert body["ratingCount"] == 150
    assert body["criticRating"] == 80
    assert body["summary"] == "Bricks."
    assert body["releaseDate"] == "2008-09-23"
    assert body["currency"] == "USD"
    assert [d["storeName"] for d in body["deals"]] == ["Fanatical", "GOG", "Steam"]
    assert body["deals"][1] == {
        "storeID": "2",
        "storeName": "GOG",
        "price": 10.0,
        "retailPrice": 20.0,
        "savings": 50,
        "dealUrl": "https://www.cheapshark.com/redirect?dealID=deal-b",
    }


def test_converts_prices_to_currency(client):
    body = client.get("/api/games/612?currency=thb").get_json()

    assert body["currency"] == "THB"
    cheapest = body["deals"][0]
    assert cheapest["price"] == 350.0
    assert cheapest["retailPrice"] == 699.65  # 19.99 * 35


def test_passes_steam_id_and_title_to_igdb(client, monkeypatch):
    calls = []
    monkeypatch.setattr(igdb, "find_game", lambda steam_app_id, title: calls.append((steam_app_id, title)))

    client.get("/api/games/612")

    assert calls == [("21000", "LEGO Batman")]


@pytest.mark.parametrize("error", [UpstreamError("igdb down"), ConfigError("no env"), None])
def test_igdb_failure_or_no_match_still_shows_prices(client, monkeypatch, error):
    def find_game(steam_app_id, title):
        if error:
            raise error
        return None

    monkeypatch.setattr(igdb, "find_game", find_game)
    res = client.get("/api/games/612")

    assert res.status_code == 200
    body = res.get_json()
    assert body["name"] == "LEGO Batman"  # CheapShark title
    assert body["cover"] is None
    assert body["genres"] == []
    assert body["rating"] is None
    assert body["criticRating"] is None
    assert body["summary"] is None
    assert body["releaseDate"] is None
    assert len(body["deals"]) == 3


def test_unknown_id_is_404(client, monkeypatch):
    monkeypatch.setattr(cheapshark, "get_game", lambda game_id: None)
    res = client.get("/api/games/999999999")

    assert res.status_code == 404
    assert "error" in res.get_json()


@pytest.mark.parametrize("game_id", ["abc", "12a", "²"])
def test_non_numeric_id_is_404_without_calling_cheapshark(client, monkeypatch, game_id):
    def fail(game_id):
        raise AssertionError("should not call CheapShark")

    monkeypatch.setattr(cheapshark, "get_game", fail)
    assert client.get(f"/api/games/{game_id}").status_code == 404


def test_bad_currency_is_400(client):
    res = client.get("/api/games/612?currency=XYZ")

    assert res.status_code == 400
    assert res.get_json() == {"error": "unsupported currency: XYZ"}


def test_cheapshark_down_is_502(client, monkeypatch):
    def down(game_id):
        raise UpstreamError("down")

    monkeypatch.setattr(cheapshark, "get_game", down)
    res = client.get("/api/games/612")

    assert res.status_code == 502
    assert res.get_json() == {"error": "price service unavailable, try again later"}


def test_get_game_returns_none_on_cheapshark_404(monkeypatch):
    def not_found(url, params=None, headers=None):
        raise UpstreamNotFoundError("404")

    monkeypatch.undo()  # use the real get_game, not the fixture's fake
    monkeypatch.setattr(cheapshark, "get_json", not_found)

    assert cheapshark.get_game("999999999") is None


def test_lowest_price_ever_compares_the_cheapest_deal(client):
    body = client.get("/api/games/612?currency=THB").get_json()

    assert body["lowestPriceEver"] == 79.8  # 2.28 USD * 35
    assert body["lowestPriceEverDate"] == "2025-09-29"
    assert body["isHistoricalLow"] is False  # cheapest deal is 10.00 USD


def test_cheapest_deal_at_lowest_ever_is_historical_low(client, monkeypatch):
    game = {**CHEAPSHARK_GAME, "cheapestPriceEver": {"price": "10.00", "date": 1759177295}}
    monkeypatch.setattr(cheapshark, "get_game", lambda game_id: game)

    assert client.get("/api/games/612").get_json()["isHistoricalLow"] is True


def test_no_lowest_price_data(client, monkeypatch):
    game = {key: value for key, value in CHEAPSHARK_GAME.items() if key != "cheapestPriceEver"}
    monkeypatch.setattr(cheapshark, "get_game", lambda game_id: game)
    body = client.get("/api/games/612").get_json()

    assert body["lowestPriceEver"] is None
    assert body["isHistoricalLow"] is False

import pytest

from game_api.errors import InvalidCurrencyError
from game_api.services import cheapshark, exchange
from game_api.services.search import search_prices

SEARCH_RESULT = [
    {
        "gameID": "82",
        "cheapest": "9.99",
        "cheapestDealID": "deal-82",
        "external": "Portal",
        "steamAppID": "400",
        "thumb": "https://example.com/portal.jpg",
    }
]


GAMES = {
    "82": {
        "cheapestPriceEver": {"price": "0.99", "date": 1498153168},  # 2017-06-22
        "deals": [{"dealID": "deal-82", "storeID": "1"}],
    }
}


@pytest.fixture(autouse=True)
def fake_apis(monkeypatch):
    monkeypatch.setattr(exchange, "get_rates", lambda: {"USD": 1, "THB": 35.0})
    monkeypatch.setattr(cheapshark, "search_games", lambda title: SEARCH_RESULT)
    monkeypatch.setattr(cheapshark, "get_games", lambda ids: GAMES)
    monkeypatch.setattr(cheapshark, "get_store_names", lambda: {"1": "Steam"})


def test_converts_price_and_names_store():
    assert search_prices("portal", "THB") == [
        {
            "gameID": "82",
            "name": "Portal",
            "price": 349.65,
            "currency": "THB",
            "thumb": "https://example.com/portal.jpg",
            "cover": "https://shared.steamstatic.com/store_item_assets/steam/apps/400/library_600x900.jpg",
            "storeID": "1",
            "storeName": "Steam",
            "dealUrl": "https://www.cheapshark.com/redirect?dealID=deal-82",
            "lowestPriceEver": 34.65,
            "lowestPriceEverDate": "2017-06-22",
            "isHistoricalLow": False,
        }
    ]


def test_unknown_currency_raises():
    with pytest.raises(InvalidCurrencyError):
        search_prices("portal", "XYZ")


def test_unknown_store_gives_null_name(monkeypatch):
    monkeypatch.setattr(cheapshark, "get_games", lambda ids: {})
    game = search_prices("portal", "USD")[0]

    assert game["storeID"] is None
    assert game["storeName"] is None


def test_unknown_game_in_lookup_gives_null_lowest_price(monkeypatch):
    monkeypatch.setattr(cheapshark, "get_games", lambda ids: {})
    game = search_prices("portal", "USD")[0]

    assert game["lowestPriceEver"] is None
    assert game["lowestPriceEverDate"] is None
    assert game["isHistoricalLow"] is False


def test_price_at_lowest_ever_is_historical_low(monkeypatch):
    monkeypatch.setattr(cheapshark, "get_games", lambda ids: {
        "82": {**GAMES["82"], "cheapestPriceEver": {"price": "9.99", "date": 1498153168}}
    })
    assert search_prices("portal", "THB")[0]["isHistoricalLow"] is True

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
        "thumb": "https://example.com/portal.jpg",
    }
]


@pytest.fixture(autouse=True)
def fake_apis(monkeypatch):
    monkeypatch.setattr(exchange, "get_rates", lambda: {"USD": 1, "THB": 35.0})
    monkeypatch.setattr(cheapshark, "search_games", lambda title: SEARCH_RESULT)
    monkeypatch.setattr(cheapshark, "get_deal_stores", lambda ids: {"deal-82": "1"})
    monkeypatch.setattr(cheapshark, "get_store_names", lambda: {"1": "Steam"})


def test_converts_price_and_names_store():
    assert search_prices("portal", "THB") == [
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


def test_unknown_currency_raises():
    with pytest.raises(InvalidCurrencyError):
        search_prices("portal", "XYZ")


def test_unknown_store_gives_null_name(monkeypatch):
    monkeypatch.setattr(cheapshark, "get_deal_stores", lambda ids: {})
    game = search_prices("portal", "USD")[0]

    assert game["storeID"] is None
    assert game["storeName"] is None

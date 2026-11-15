import pytest

from game_api.errors import InvalidCurrencyError, InvalidParamError
from game_api.services import cheapshark, exchange
from game_api.services.prices import get_prices

GAMES = {
    "82": {
        "info": {"title": "Portal", "thumb": "p.jpg"},
        "cheapestPriceEver": {"price": "0.99", "date": 1498153168},
        "deals": [
            {"storeID": "1", "dealID": "a", "price": "9.99", "retailPrice": "9.99", "savings": "0"},
            {"storeID": "7", "dealID": "b", "price": "4.99", "retailPrice": "9.99", "savings": "50.05"},
        ],
    },
    "99": {
        "info": {"title": "Portal 2", "thumb": "p2.jpg"},
        "cheapestPriceEver": {"price": "2.00", "date": 1498153168},
        "deals": [{"storeID": "1", "dealID": "c", "price": "2.00", "retailPrice": "20.00", "savings": "90"}],
    },
    "50": {"info": {"title": "No deals"}, "deals": []},
}


@pytest.fixture
def lookups(monkeypatch):
    calls = []

    def fake_get_games(ids):
        calls.append(list(ids))
        return {i: GAMES[i] for i in ids if i in GAMES}

    monkeypatch.setattr(exchange, "get_rates", lambda: {"USD": 1, "THB": 35.0})
    monkeypatch.setattr(cheapshark, "get_games", fake_get_games)
    monkeypatch.setattr(cheapshark, "get_store_names", lambda: {"1": "Steam", "7": "GOG"})
    return calls


def test_cheapest_deal_per_game_converted(lookups):
    assert get_prices("82", "THB") == [
        {
            "gameID": "82",
            "name": "Portal",
            "thumb": "p.jpg",
            "price": 174.65,
            "retailPrice": 349.65,
            "savings": 50,
            "currency": "THB",
            "storeID": "7",
            "storeName": "GOG",
            "dealUrl": "https://www.cheapshark.com/redirect?dealID=b",
            "lowestPriceEver": 34.65,
            "lowestPriceEverDate": "2017-06-22",
            "isHistoricalLow": False,
        }
    ]


def test_keeps_id_order_and_marks_historical_low(lookups):
    result = get_prices("99, 82", "USD")
    assert [(r["gameID"], r["isHistoricalLow"]) for r in result] == [("99", True), ("82", False)]


def test_unknown_ids_and_games_without_deals_are_left_out(lookups):
    assert [r["gameID"] for r in get_prices("1,82,50", "USD")] == ["82"]


def test_repeated_ids_are_looked_up_once(lookups):
    get_prices("82,82,99", "USD")
    assert lookups == [["82", "99"]]


@pytest.mark.parametrize("ids", ["", " , ", "1,abc", "1;2", "-1", "1.5"])
def test_bad_ids_raise(lookups, ids):
    with pytest.raises(InvalidParamError, match="ids"):
        get_prices(ids, "USD")
    assert lookups == []


def test_more_than_50_ids_raise(lookups):
    with pytest.raises(InvalidParamError, match="at most 50"):
        get_prices(",".join(str(i) for i in range(51)), "USD")


def test_exactly_50_ids_are_fine(lookups):
    get_prices(",".join(str(i) for i in range(50)), "USD")
    assert len(lookups[0]) == 50  # get_games splits it into calls of 25 (see test_cheapshark)


def test_unknown_currency_raises(lookups):
    with pytest.raises(InvalidCurrencyError):
        get_prices("82", "XYZ")

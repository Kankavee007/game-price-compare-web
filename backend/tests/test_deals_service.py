import pytest

from game_api.errors import InvalidCurrencyError, InvalidParamError, UpstreamError
from game_api.services import cheapshark, exchange
from game_api.services.deals import find_deals


def row(game_id, price, store="1", **extra):
    """One /deals row the way CheapShark sends it (numbers as strings)."""
    return {
        "gameID": game_id,
        "title": f"Game {game_id}",
        "dealID": f"deal-{game_id}-{store}",
        "storeID": store,
        "salePrice": price,
        "normalPrice": "20.00",
        "savings": "50.000000",
        "thumb": f"https://example.com/{game_id}.jpg",
        "steamRatingPercent": "90",
        "steamRatingCount": "1000",
        "metacriticScore": "85",
        "releaseDate": 1700000000,
        **extra,
    }


class CallLog(list):
    pass


@pytest.fixture
def deals_api(monkeypatch):
    log = CallLog()
    log.rows = [row("1", "10.00")]

    def fake_list_deals(params):
        log.append(params)
        return log.rows, 3

    monkeypatch.setattr(exchange, "get_rates", lambda: {"USD": 1, "THB": 35.0})
    monkeypatch.setattr(cheapshark, "list_deals", fake_list_deals)
    monkeypatch.setattr(cheapshark, "get_store_names", lambda: {"1": "Steam", "7": "GOG"})
    # Lowest price lookup: no data unless a test sets log.lowest
    log.lowest = {}
    log.lookups = []

    def fake_get_games(ids):
        log.lookups.append(list(ids))
        return {i: {"cheapestPriceEver": log.lowest[i]} for i in ids if i in log.lowest}

    monkeypatch.setattr(cheapshark, "get_games", fake_get_games)
    return log


@pytest.mark.parametrize(
    "sort, sort_by",
    [
        ("deal", "Deal Rating"),
        ("price", "Price"),
        ("savings", "Savings"),
        ("rating", "Metacritic"),
        ("reviews", "Reviews"),
        ("newest", "Release"),
    ],
)
def test_sort_maps_to_cheapshark(deals_api, sort, sort_by):
    find_deals("portal", "USD", {"sort": sort})
    assert deals_api[0]["sortBy"] == sort_by
    assert deals_api[0]["title"] == "portal"


def test_no_query_defaults_to_deal_rating_and_sends_no_title(deals_api):
    find_deals("", "USD", {})
    assert deals_api[0]["sortBy"] == "Deal Rating"
    assert "title" not in deals_api[0]


def test_relevance_without_query_falls_back_to_deal_rating(deals_api):
    find_deals("", "USD", {"sort": "relevance"})
    assert deals_api[0]["sortBy"] == "Deal Rating"


def test_result_shape_and_conversion(deals_api):
    body = find_deals("", "THB", {"page": "2"})

    assert body["page"] == 2
    assert body["totalPages"] == 3
    assert body["currency"] == "THB"
    assert deals_api[0]["pageNumber"] == 2
    assert body["results"] == [
        {
            "gameID": "1",
            "name": "Game 1",
            "price": 350.0,
            "retailPrice": 700.0,
            "savings": 50,
            "currency": "THB",
            "thumb": "https://example.com/1.jpg",
            "cover": None,
            "storeID": "1",
            "storeName": "Steam",
            "dealUrl": "https://www.cheapshark.com/redirect?dealID=deal-1-1",
            "steamRating": 90,
            "metacriticScore": 85,
            "releaseDate": "2023-11-14",
            "lowestPriceEver": None,
            "lowestPriceEverDate": None,
            "isHistoricalLow": False,
        }
    ]


def test_deal_row_with_steam_app_id_gets_portrait_cover(deals_api):
    deals_api.rows = [row("1", "10.00", steamAppID="220")]
    result = find_deals("", "USD", {})["results"][0]

    assert result["cover"] == "https://shared.steamstatic.com/store_item_assets/steam/apps/220/library_600x900.jpg"
    assert result["thumb"] == "https://example.com/1.jpg"


def test_missing_ratings_and_date_become_null(deals_api):
    deals_api.rows = [row("1", "10.00", steamRatingCount="0", metacriticScore="0", releaseDate=0)]
    result = find_deals("", "USD", {})["results"][0]

    assert result["steamRating"] is None
    assert result["metacriticScore"] is None
    assert result["releaseDate"] is None


def test_price_bounds_are_converted_to_usd_rounding_outward(deals_api):
    find_deals("", "THB", {"minPrice": "100", "maxPrice": "300"})

    # 100 / 35 = 2.857..., 300 / 35 = 8.571...
    assert deals_api[0]["lowerPrice"] == 2.85
    assert deals_api[0]["upperPrice"] == 8.58


def test_results_outside_range_after_conversion_are_dropped(deals_api):
    # 2.85 USD * 35 = 99.75 THB: CheapShark returns it (bound rounded down) but it is under 100
    deals_api.rows = [row("1", "2.85"), row("2", "5.00")]
    results = find_deals("", "THB", {"minPrice": "100"})["results"]

    assert [r["gameID"] for r in results] == ["2"]


def test_max_price_zero_means_free(deals_api):
    deals_api.rows = [row("1", "0.00"), row("2", "0.01")]
    results = find_deals("", "USD", {"maxPrice": "0"})["results"]

    assert deals_api[0]["upperPrice"] == 0
    assert [r["gameID"] for r in results] == ["1"]


def test_one_row_per_game_keeps_order_and_cheapest_store(deals_api):
    deals_api.rows = [row("1", "9.00", store="1"), row("2", "5.00"), row("1", "7.00", store="7")]
    results = find_deals("", "USD", {"sort": "savings"})["results"]

    assert [(r["gameID"], r["price"], r["storeName"]) for r in results] == [
        ("1", 7.0, "GOG"),
        ("2", 5.0, "Steam"),
    ]


def test_optional_filters_are_sent(deals_api):
    find_deals("", "USD", {"stores": "1, 7", "onSale": "1", "minRating": "80"})

    assert deals_api[0]["storeID"] == "1,7"
    assert deals_api[0]["onSale"] == 1
    assert deals_api[0]["steamRating"] == 80


def test_empty_values_count_as_unset(deals_api):
    find_deals("", "USD", {"minPrice": "", "maxPrice": " ", "stores": "", "onSale": "", "page": ""})

    assert set(deals_api[0]) == {"pageSize", "pageNumber", "sortBy"}


@pytest.mark.parametrize(
    "args, names",
    [
        ({"minPrice": "abc"}, "minPrice"),
        ({"maxPrice": "-1"}, "maxPrice"),
        ({"maxPrice": "inf"}, "maxPrice"),
        ({"minPrice": "10", "maxPrice": "5"}, "minPrice"),
        ({"sort": "foo"}, "sort"),
        ({"page": "-1"}, "page"),
        ({"page": "1.5"}, "page"),
        ({"stores": "1,steam"}, "stores"),
        ({"onSale": "yes"}, "onSale"),
        ({"minRating": "101"}, "minRating"),
    ],
)
def test_invalid_params_raise_with_the_param_name(deals_api, args, names):
    with pytest.raises(InvalidParamError, match=names):
        find_deals("", "USD", args)
    assert deals_api == []  # nothing sent upstream


def test_unknown_currency_raises(deals_api):
    with pytest.raises(InvalidCurrencyError):
        find_deals("", "XYZ", {})


def test_lowest_price_ever_is_converted_and_compared_in_usd(deals_api):
    deals_api.rows = [row("1", "10.00"), row("2", "5.00")]
    deals_api.lowest = {
        "1": {"price": "4.99", "date": 1534118400},  # 2018-08-13, cheaper than today
        "2": {"price": "5.00", "date": 1534118400},  # today's price is the lowest
    }
    results = find_deals("", "THB", {})["results"]

    assert deals_api.lookups == [["1", "2"]]
    assert [(r["lowestPriceEver"], r["lowestPriceEverDate"], r["isHistoricalLow"]) for r in results] == [
        (174.65, "2018-08-13", False),
        (175.0, "2018-08-13", True),
    ]


def test_lowest_price_lookup_only_for_games_in_range(deals_api):
    deals_api.rows = [row("1", "1.00"), row("2", "50.00")]
    find_deals("", "USD", {"maxPrice": "10"})
    assert deals_api.lookups == [["1"]]


def test_lowest_price_lookup_failure_still_returns_deals(deals_api, monkeypatch, caplog):
    def down(ids):
        raise UpstreamError("down")

    monkeypatch.setattr(cheapshark, "get_games", down)
    results = find_deals("", "USD", {})["results"]

    assert results[0]["gameID"] == "1"
    assert results[0]["lowestPriceEver"] is None
    assert results[0]["isHistoricalLow"] is False
    assert "lowest price lookup failed" in caplog.text


# --- sort=relevance (title search) ---------------------------------------------------------

SEARCH = [
    {"gameID": "82", "external": "Portal", "steamAppID": "400", "thumb": "p.jpg"},
    {"gameID": "99", "external": "Portal 2", "thumb": "p2.jpg"},
]
GAMES = {
    "82": {"deals": [
        {"storeID": "1", "dealID": "a", "price": "9.99", "retailPrice": "9.99", "savings": "0"},
        {"storeID": "7", "dealID": "b", "price": "4.99", "retailPrice": "9.99", "savings": "50"},
    ]},
    "99": {"deals": [
        {"storeID": "1", "dealID": "c", "price": "2.00", "retailPrice": "20.00", "savings": "90"},
    ]},
}


@pytest.fixture
def title_search(deals_api, monkeypatch):
    monkeypatch.setattr(cheapshark, "search_games", lambda title: SEARCH)
    monkeypatch.setattr(cheapshark, "get_games", lambda ids: {i: GAMES[i] for i in ids})
    return deals_api


def test_relevance_is_default_with_query_and_keeps_search_order(title_search):
    body = find_deals("portal", "USD", {})

    assert title_search == []  # /deals is not called
    assert body["totalPages"] == 1
    assert [(r["name"], r["price"], r["storeName"]) for r in body["results"]] == [
        ("Portal", 4.99, "GOG"),
        ("Portal 2", 2.0, "Steam"),
    ]
    first = body["results"][0]
    assert first["retailPrice"] == 9.99
    assert first["savings"] == 50
    assert first["steamRating"] is None
    assert first["cover"] == "https://shared.steamstatic.com/store_item_assets/steam/apps/400/library_600x900.jpg"
    assert body["results"][1]["cover"] is None


def test_relevance_store_filter_picks_cheapest_allowed_store(title_search):
    results = find_deals("portal", "USD", {"stores": "1"})["results"]
    assert [(r["name"], r["price"]) for r in results] == [("Portal", 9.99), ("Portal 2", 2.0)]


def test_relevance_on_sale_and_price_range(title_search):
    results = find_deals("portal", "USD", {"onSale": "1", "minPrice": "3"})["results"]
    assert [(r["name"], r["price"]) for r in results] == [("Portal", 4.99)]


def test_relevance_min_rating_keeps_only_rated_games(title_search):
    title_search.rows = [row("99", "2.00", steamRatingPercent="95")]
    results = find_deals("portal", "USD", {"minRating": "90"})["results"]

    assert title_search[0] == {"title": "portal", "steamRating": 90, "pageSize": 60}
    assert [(r["name"], r["steamRating"]) for r in results] == [("Portal 2", 95)]


def test_relevance_lowest_price_uses_the_chosen_store(title_search, monkeypatch):
    games = {
        "82": {**GAMES["82"], "cheapestPriceEver": {"price": "4.99", "date": 1534118400}},
        "99": GAMES["99"],
    }
    monkeypatch.setattr(cheapshark, "get_games", lambda ids: {i: games[i] for i in ids})

    all_stores = find_deals("portal", "USD", {})["results"]
    steam_only = find_deals("portal", "USD", {"stores": "1"})["results"]

    assert (all_stores[0]["lowestPriceEver"], all_stores[0]["isHistoricalLow"]) == (4.99, True)
    assert (steam_only[0]["price"], steam_only[0]["isHistoricalLow"]) == (9.99, False)
    assert all_stores[1]["lowestPriceEver"] is None  # no cheapestPriceEver for game 99


def test_relevance_has_one_page_only(title_search):
    assert find_deals("portal", "USD", {"page": "1"})["results"] == []

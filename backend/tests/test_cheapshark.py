import pytest

from game_api import config
from game_api.errors import UpstreamError
from game_api.services import cheapshark


@pytest.fixture(autouse=True)
def empty_cache(monkeypatch):
    monkeypatch.setattr(cheapshark, "_deals_cache", {})
    monkeypatch.setattr(cheapshark, "_games_cache", {})


class Calls(list):
    pass


@pytest.fixture
def http(monkeypatch):
    calls = Calls()
    calls.data = [{"gameID": "1"}]
    calls.headers = {"X-Total-Page-Count": "7"}

    def fake(url, params=None, headers=None):
        calls.append(params)
        return calls.data, calls.headers

    monkeypatch.setattr(cheapshark, "get_json_with_headers", fake)
    return calls


def test_list_deals_returns_rows_and_page_count(http):
    assert cheapshark.list_deals({"pageNumber": 0}) == ([{"gameID": "1"}], 7)


@pytest.mark.parametrize("header", [{}, {"X-Total-Page-Count": "abc"}, {"X-Total-Page-Count": "0"}])
def test_list_deals_page_count_defaults_to_one(http, header):
    http.headers = header
    assert cheapshark.list_deals({})[1] == 1


def test_list_deals_cache_hit_skips_the_api(http):
    cheapshark.list_deals({"a": 1, "b": 2})
    cheapshark.list_deals({"b": 2, "a": 1})  # same params, other order

    assert len(http) == 1


def test_list_deals_cache_expires(http, monkeypatch):
    now = {"t": 1000.0}
    monkeypatch.setattr(cheapshark.time, "time", lambda: now["t"])
    cheapshark.list_deals({})
    now["t"] += config.DEALS_CACHE_SECONDS + 1
    cheapshark.list_deals({})

    assert len(http) == 2


def test_list_deals_cache_drops_oldest_above_max(http, monkeypatch):
    monkeypatch.setattr(config, "DEALS_CACHE_MAX_ENTRIES", 2)
    for page in range(3):
        cheapshark.list_deals({"pageNumber": page})
    cheapshark.list_deals({"pageNumber": 0})  # was dropped, fetched again

    assert len(http) == 4
    assert len(cheapshark._deals_cache) == 2


def test_list_deals_unexpected_response(http):
    http.data = {"error": "nope"}
    with pytest.raises(UpstreamError):
        cheapshark.list_deals({})


def test_get_games_splits_ids_into_calls_of_25(monkeypatch):
    calls = []

    def fake(url, params=None, headers=None):
        ids = params["ids"].split(",")
        calls.append(ids)
        return {i: {"deals": []} for i in ids}

    monkeypatch.setattr(cheapshark, "get_json", fake)
    games = cheapshark.get_games([str(i) for i in range(30)])

    assert [len(c) for c in calls] == [25, 5]
    assert len(games) == 30


def test_get_games_empty_makes_no_call(monkeypatch):
    monkeypatch.setattr(cheapshark, "get_json", lambda *a, **k: pytest.fail("called"))
    assert cheapshark.get_games([]) == {}


@pytest.fixture
def games_http(monkeypatch):
    """Fake /games?ids: records the ids of each call; ids in `calls.unknown` are left out."""
    calls = Calls()
    calls.unknown = set()

    def fake(url, params=None, headers=None):
        ids = params["ids"].split(",")
        calls.append(ids)
        return {i: {"info": {"title": f"Game {i}"}} for i in ids if i not in calls.unknown}

    monkeypatch.setattr(cheapshark, "get_json", fake)
    return calls


def test_get_games_cache_hit_skips_the_api(games_http):
    first = cheapshark.get_games(["1", "2"], cached=True)
    second = cheapshark.get_games(["1", "2"], cached=True)

    assert games_http == [["1", "2"]]
    assert second == first == {"1": {"info": {"title": "Game 1"}}, "2": {"info": {"title": "Game 2"}}}


def test_get_games_fetches_only_ids_not_cached(games_http):
    cheapshark.get_games(["1", "2"], cached=True)
    games = cheapshark.get_games(["1", "2", "3"], cached=True)

    assert games_http == [["1", "2"], ["3"]]
    assert set(games) == {"1", "2", "3"}


def test_get_games_cache_expires(games_http, monkeypatch):
    now = {"t": 1000.0}
    monkeypatch.setattr(cheapshark.time, "time", lambda: now["t"])
    cheapshark.get_games(["1"], cached=True)
    now["t"] += config.GAMES_CACHE_SECONDS + 1
    cheapshark.get_games(["1"], cached=True)

    assert games_http == [["1"], ["1"]]


def test_get_games_unknown_id_is_not_cached(games_http):
    games_http.unknown = {"9"}
    assert cheapshark.get_games(["1", "9"], cached=True) == {"1": {"info": {"title": "Game 1"}}}
    cheapshark.get_games(["1", "9"], cached=True)

    assert games_http == [["1", "9"], ["9"]]  # 1 from the cache, 9 asked again


def test_get_games_cache_drops_oldest_above_max(games_http, monkeypatch):
    monkeypatch.setattr(config, "GAMES_CACHE_MAX_ENTRIES", 2)
    cheapshark.get_games(["1", "2", "3"], cached=True)
    cheapshark.get_games(["1"], cached=True)  # was dropped, fetched again

    assert games_http == [["1", "2", "3"], ["1"]]
    assert len(cheapshark._games_cache) == 2


def test_get_games_without_cached_always_calls_the_api(games_http):
    """Search and the wishlist need live deals: the default never reads the cache."""
    cheapshark.get_games(["1"])
    cheapshark.get_games(["1"])

    assert games_http == [["1"], ["1"]]


def test_get_games_live_call_refreshes_the_cache(games_http):
    cheapshark.get_games(["1"])  # live, still saved
    cheapshark.get_games(["1"], cached=True)

    assert games_http == [["1"]]


def test_get_games_unexpected_response_is_not_cached(monkeypatch):
    monkeypatch.setattr(cheapshark, "get_json", lambda *a, **k: ["not", "a", "dict"])
    with pytest.raises(UpstreamError):
        cheapshark.get_games(["1"])

    assert cheapshark._games_cache == {}


# --- stores ---------------------------------------------------------------------------------

STORES = [
    {"storeID": "1", "storeName": "Steam", "isActive": 1, "images": {"logo": "/img/stores/logos/0.png"}},
    {"storeID": "4", "storeName": "Amazon", "isActive": 0, "images": {}},
]


@pytest.fixture
def stores_http(monkeypatch):
    monkeypatch.setattr(cheapshark, "_stores", [])
    monkeypatch.setattr(cheapshark, "_store_fetched_at", 0.0)
    calls = Calls()
    calls.fail = False

    def fake(url, params=None, headers=None):
        calls.append(url)
        if calls.fail:
            raise UpstreamError("down")
        return STORES

    monkeypatch.setattr(cheapshark, "get_json", fake)
    return calls


def test_get_stores_shape_and_logo_url(stores_http):
    assert cheapshark.get_stores() == [
        {"storeID": "1", "storeName": "Steam", "isActive": True,
         "logo": "https://www.cheapshark.com/img/stores/logos/0.png"},
        {"storeID": "4", "storeName": "Amazon", "isActive": False, "logo": None},
    ]


def test_get_stores_is_cached(stores_http):
    cheapshark.get_stores()
    cheapshark.get_stores()
    assert len(stores_http) == 1


def test_get_stores_uses_old_cache_when_api_fails(stores_http, monkeypatch):
    now = {"t": 1000.0}
    monkeypatch.setattr(cheapshark.time, "time", lambda: now["t"])
    first = cheapshark.get_stores()
    now["t"] += config.STORE_CACHE_SECONDS + 1
    stores_http.fail = True

    assert cheapshark.get_stores() == first
    assert len(stores_http) == 2  # it did try again


def test_get_stores_raises_without_cache(stores_http):
    stores_http.fail = True
    with pytest.raises(UpstreamError):
        cheapshark.get_stores()


def test_get_store_names_includes_inactive_stores(stores_http):
    assert cheapshark.get_store_names() == {"1": "Steam", "4": "Amazon"}


def test_get_store_names_is_empty_when_api_fails(stores_http):
    stores_http.fail = True
    assert cheapshark.get_store_names() == {}

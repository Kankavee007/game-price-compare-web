import pytest

from game_api import config
from game_api.errors import UpstreamError
from game_api.services import cheapshark


@pytest.fixture(autouse=True)
def empty_cache(monkeypatch):
    monkeypatch.setattr(cheapshark, "_deals_cache", {})


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

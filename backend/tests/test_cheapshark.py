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

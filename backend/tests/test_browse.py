import pytest

from game_api import create_app
from game_api.errors import ConfigError, UpstreamError
from game_api.services import browse, cheapshark, exchange, igdb

GENRES = [{"id": 31, "name": "Adventure"}, {"id": 12, "name": "Role-playing (RPG)"}]


def igdb_game(gid, name, steam_ids, rating=90.4, cover="co1"):
    return {
        "id": gid,
        "name": name,
        "total_rating": rating,
        "cover": {"image_id": cover} if cover else None,
        "external_games": [{"uid": s, "external_game_source": 1} for s in steam_ids]
        + [{"uid": "gog-1", "external_game_source": 5}],
    }


POPULAR = [
    igdb_game(1, "Witcher", ["292030"]),
    igdb_game(2, "Not on CheapShark", ["999"]),
    igdb_game(3, "No Steam", [], rating=None, cover=None),
    igdb_game(4, "Second id", ["111", "222"]),
]

CHEAPSHARK = {
    "292030": [
        {"gameID": "10", "cheapest": "9.99"},
        {"gameID": "11", "cheapest": "4.00"},  # cheapest of the two listings
    ],
    "999": [],
    "111": [],
    "222": [{"gameID": "40", "cheapest": "2.00"}],
}


@pytest.fixture(autouse=True)
def fresh_cache():
    browse._genres.clear()
    browse._browse_cache.clear()
    yield
    browse._genres.clear()
    browse._browse_cache.clear()


@pytest.fixture
def calls(monkeypatch):
    seen = {"genres": 0, "popular": [], "steam": []}

    def list_genres():
        seen["genres"] += 1
        return list(GENRES)

    def popular_games(genre_id, limit):
        seen["popular"].append((genre_id, limit))
        return POPULAR

    def find(app_id):
        seen["steam"].append(app_id)
        return CHEAPSHARK[app_id]

    monkeypatch.setattr(igdb, "list_genres", list_genres)
    monkeypatch.setattr(igdb, "popular_games", popular_games)
    monkeypatch.setattr(cheapshark, "find_by_steam_app_id", find)
    monkeypatch.setattr(exchange, "get_rates", lambda: {"USD": 1, "THB": 35.0})
    return seen


@pytest.fixture
def client():
    return create_app().test_client()


def test_genres_sorted_and_cached(client, calls):
    res = client.get("/api/genres")
    assert res.status_code == 200
    assert res.get_json() == [{"id": 31, "name": "Adventure"}, {"id": 12, "name": "Role-playing (RPG)"}]
    assert "s-maxage" in res.headers["Cache-Control"]
    client.get("/api/genres")
    assert calls["genres"] == 1


def test_browse_games_with_prices(client, calls):
    res = client.get("/api/browse?genre=12&currency=THB")
    assert res.status_code == 200
    body = res.get_json()
    assert body["genre"] == {"id": 12, "name": "Role-playing (RPG)"}
    assert body["currency"] == "THB"
    assert body["games"] == [
        {"name": "Witcher", "cover": "https://images.igdb.com/igdb/image/upload/t_cover_big/co1.jpg",
         "rating": 90, "gameID": "11", "price": 140.0},
        {"name": "Not on CheapShark", "cover": "https://images.igdb.com/igdb/image/upload/t_cover_big/co1.jpg",
         "rating": 90, "gameID": None, "price": None},
        {"name": "No Steam", "cover": None, "rating": None, "gameID": None, "price": None},
        {"name": "Second id", "cover": "https://images.igdb.com/igdb/image/upload/t_cover_big/co1.jpg",
         "rating": 90, "gameID": "40", "price": 70.0},
    ]
    assert calls["popular"] == [(12, 12)]
    assert sorted(calls["steam"]) == ["111", "222", "292030", "999"]  # no lookup without a Steam id


def test_browse_cached_per_genre_and_currency_converted_each_time(client, calls):
    client.get("/api/browse?genre=12")
    usd = client.get("/api/browse?genre=12&currency=USD").get_json()
    assert usd["games"][0]["price"] == 4.0
    assert len(calls["popular"]) == 1


def test_browse_cache_expires(client, calls, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(browse.time, "time", lambda: now[0])
    client.get("/api/browse?genre=12")
    now[0] += 6 * 3600 + 1
    client.get("/api/browse?genre=12")
    assert len(calls["popular"]) == 2


def test_failed_lookup_gets_null_price_and_is_not_cached(client, calls, monkeypatch):
    def find(app_id):
        if app_id == "292030":
            raise UpstreamError("down")
        return CHEAPSHARK[app_id]

    monkeypatch.setattr(cheapshark, "find_by_steam_app_id", find)
    games = client.get("/api/browse?genre=12").get_json()["games"]
    assert games[0]["price"] is None and games[0]["gameID"] is None
    assert games[3]["price"] == 2.0  # the rest still return
    client.get("/api/browse?genre=12")
    assert len(calls["popular"]) == 2  # not cached, tried again


@pytest.mark.parametrize("qs, message", [
    ("", "genre is required"),
    ("?genre=", "genre is required"),
    ("?genre=abc", "genre must be a genre id"),
    ("?genre=12)%20%7C%20(1", "genre must be a genre id"),
    ("?genre=777", "unknown genre"),
])
def test_bad_genre_is_400(client, calls, qs, message):
    res = client.get(f"/api/browse{qs}")
    assert res.status_code == 400
    assert res.get_json() == {"error": message}
    assert calls["popular"] == []


def test_bad_currency_is_400(client, calls):
    assert client.get("/api/browse?genre=12&currency=XYZ").status_code == 400


@pytest.mark.parametrize("path", ["/api/genres", "/api/browse?genre=12"])
def test_igdb_down_is_502(client, monkeypatch, path):
    def down():
        raise UpstreamError("igdb down")

    monkeypatch.setattr(igdb, "list_genres", down)
    res = client.get(path)
    assert res.status_code == 502
    assert "Cache-Control" not in res.headers


def test_popular_games_down_is_502(client, calls, monkeypatch):
    def down(genre_id, limit):
        raise UpstreamError("igdb down")

    monkeypatch.setattr(igdb, "popular_games", down)
    assert client.get("/api/browse?genre=12").status_code == 502


@pytest.mark.parametrize("path", ["/api/genres", "/api/browse?genre=12"])
def test_missing_twitch_env_is_500(client, monkeypatch, path):
    def no_env():
        raise ConfigError("no env")

    monkeypatch.setattr(igdb, "list_genres", no_env)
    res = client.get(path)
    assert res.status_code == 500
    assert res.get_json() == {"error": "server is not configured for game info"}


def test_stale_genres_served_when_igdb_down(calls, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(browse.time, "time", lambda: now[0])
    browse.get_genres()
    now[0] += 2 * 86400

    def down():
        raise UpstreamError("igdb down")

    monkeypatch.setattr(igdb, "list_genres", down)
    assert browse.get_genres()[0]["name"] == "Adventure"


def test_igdb_popular_query(monkeypatch):
    sent = []
    monkeypatch.setattr(igdb, "_get_token", lambda: "t")
    monkeypatch.setattr(igdb, "post_json", lambda url, body, headers: sent.append((url, body)) or [])
    igdb.popular_games(12, 12)
    url, body = sent[0]
    assert url.endswith("/games")
    assert "where genres = (12) & platforms = (6) & game_type = 0;" in body
    assert "sort total_rating_count desc; limit 12;" in body


def test_steam_app_ids_only_steam():
    assert igdb.steam_app_ids(POPULAR[3]) == ["111", "222"]
    assert igdb.steam_app_ids({"name": "x"}) == []

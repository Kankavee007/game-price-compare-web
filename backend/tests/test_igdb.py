import pytest

from game_api.errors import UpstreamError
from game_api.services import igdb

# setup fake IGDB API responses and set autouse to True so that it applies to all tests in this file
@pytest.fixture(autouse=True)
def reset_token(monkeypatch):
    # Set Config values for Twitch client ID and secret
    monkeypatch.setattr(igdb.config, "TWITCH_CLIENT_ID", "fake_client_id")
    monkeypatch.setattr(igdb.config, "TWITCH_CLIENT_SECRET", "fake_client_secret")

    # Reset the token and expiration time before each test
    monkeypatch.setattr(igdb, "_token", None)
    monkeypatch.setattr(igdb, "_token_expired_at", 0.0)

def test_id_or_secret_not_set(monkeypatch):
    # [AAA] Arrange: unset env vars
    monkeypatch.setattr(igdb.config, "TWITCH_CLIENT_ID", None)
    monkeypatch.setattr(igdb.config, "TWITCH_CLIENT_SECRET", None)

    # [AAA] Act & Assert: calling _get_token raises ConfigError
    with pytest.raises(igdb.ConfigError):
        igdb._get_token()

def test_token_is_cached(monkeypatch):
    # [AAA] Arrange: fake post_json
    calls = []

    def fake_post_json(url, body, headers):
        calls.append((url, body, headers))
        return {"access_token": "fake_token", "expires_in": 3600}

    monkeypatch.setattr(igdb, "post_json", fake_post_json)
    monkeypatch.setattr(igdb.time, "time", lambda: 1000.0) # time stop

    # [AAA] Act: call _get_token twice
    token1 = igdb._get_token()
    token2 = igdb._get_token()

    # [AAA] Assert: token is cached
    assert token1 == token2
    assert len(calls) == 1

def test_token_refreshes_when_expired(monkeypatch):
    # [AAA] Arrange: fake post_json
    calls = []

    def fake_post_json(url, body, headers):
        calls.append((url, body, headers))
        return {"access_token": "fake_token", "expires_in": 3600}

    monkeypatch.setattr(igdb, "post_json", fake_post_json)
    monkeypatch.setattr(igdb.time, "time", lambda: 1000.0) # time stop

    # [AAA] Act: call _get_token twice with time advancing
    token1 = igdb._get_token()
    monkeypatch.setattr(igdb.time, "time", lambda: 5000.0) # time advanced
    token2 = igdb._get_token()

    # [AAA] Assert: token is refreshed
    assert token1 == token2
    assert len(calls) == 2

# FIX: the find_game tests used to fake post_json with a lambda that returned the same game
# for every body, so they passed even if the code sent the wrong query (or skipped the Steam
# lookup). fake_igdb is a spy: it records every query body, and answers based on what the
# query looks like, so tests can check both the result and what was sent to IGDB.
def fake_igdb(monkeypatch, by_steam, by_title):
    """Fake IGDB: Steam lookups (queries with "where") get by_steam, title searches get by_title.

    Returns the list that collects every query body sent, in order.
    """
    bodies = []

    def fake_post_json(url, body, headers):
        bodies.append(body)
        return by_steam if "where" in body else by_title

    monkeypatch.setattr(igdb, "_get_token", lambda: "fake_token")
    monkeypatch.setattr(igdb, "post_json", fake_post_json)
    return bodies


def test_find_game_by_steam_app_id(monkeypatch):
    # [AAA] Arrange
    bodies = fake_igdb(monkeypatch, by_steam=[{"id": 123, "name": "Test Game"}], by_title=[])

    # [AAA] Act
    result = igdb.find_game("12345", "Test Game")

    # [AAA] Assert: found by Steam id in one query, and the query really used that id
    # FIX: now also checks the query sent, not only the result
    assert result["id"] == 123
    assert len(bodies) == 1
    assert 'external_games.uid = "12345"' in bodies[0]
    assert "external_games.external_game_source = 1" in bodies[0]


def test_falls_back_to_title_when_steam_finds_nothing(monkeypatch):
    # FIX: new test, the spec asks for the title fallback but nothing tested it.
    # [AAA] Arrange: Steam lookup finds nothing, title search finds the game
    bodies = fake_igdb(monkeypatch, by_steam=[], by_title=[{"id": 456, "name": "Another Game"}])

    # [AAA] Act
    result = igdb.find_game("12345", "Another Game")

    # [AAA] Assert: two queries, Steam first, then title
    assert result["id"] == 456
    assert len(bodies) == 2
    assert "where" in bodies[0]
    assert bodies[1].startswith('search "Another Game";')


def test_find_game_by_title(monkeypatch):
    # [AAA] Arrange
    bodies = fake_igdb(monkeypatch, by_steam=[], by_title=[{"id": 456, "name": "Another Game"}])

    # [AAA] Act: no Steam id (CheapShark sends null for games not on Steam)
    result = igdb.find_game(None, "Another Game")

    # [AAA] Assert: only the title search ran
    # FIX: now checks that no Steam lookup was sent
    assert result["id"] == 456
    assert len(bodies) == 1
    assert bodies[0].startswith('search "Another Game";')


def test_title_search_prefers_exact_name(monkeypatch):
    # FIX: new test for _pick_best. Real IGDB results for "Portal 2" put
    # "Portal Maze 2" first and Portal 2 third (checked on 2026-11-13).
    fake_igdb(monkeypatch, by_steam=[], by_title=[
        {"id": 1, "name": "Portal Maze 2", "game_type": 0},
        {"id": 2, "name": "Portal 2: In Motion", "game_type": 1},
        {"id": 3, "name": "Portal 2", "game_type": 0},
    ])

    assert igdb.find_game(None, "portal 2")["id"] == 3  # case does not matter


def test_title_search_prefers_main_game_over_same_name_dlc(monkeypatch):
    # FIX: new test, a bundle/DLC can have exactly the same name as the main game
    fake_igdb(monkeypatch, by_steam=[], by_title=[
        {"id": 1, "name": "Some Game", "game_type": 3},  # bundle
        {"id": 2, "name": "Some Game", "game_type": 0},  # main game
    ])

    assert igdb.find_game(None, "Some Game")["id"] == 2


def test_title_search_without_exact_name_takes_first(monkeypatch):
    # FIX: new test, no exact name still returns something instead of None
    fake_igdb(monkeypatch, by_steam=[], by_title=[
        {"id": 1, "name": "Portal 2: Community Edition", "game_type": 5},
        {"id": 2, "name": "Portal Maze 2", "game_type": 0},
    ])

    assert igdb.find_game(None, "Portal 2")["id"] == 1


def test_title_is_escaped(monkeypatch):
    # FIX: new test for _escape, a " in the name must not end the quoted search string
    bodies = fake_igdb(monkeypatch, by_steam=[], by_title=[])

    igdb.find_game(None, 'The "Best" Game')

    assert bodies[0].startswith('search "The \\"Best\\" Game";')


def test_find_game_not_found(monkeypatch):
    # [AAA] Arrange: both lookups return nothing
    bodies = fake_igdb(monkeypatch, by_steam=[], by_title=[])

    # [AAA] Act
    result = igdb.find_game("99999", "Nonexistent Game")

    # [AAA] Assert: tried both, found nothing
    assert result is None
    assert len(bodies) == 2


def test_find_game_invalid_steam_app_id(monkeypatch):
    # [AAA] Arrange
    bodies = fake_igdb(monkeypatch, by_steam=[{"id": 1, "name": "Wrong"}], by_title=[{"id": 789, "name": "Valid Game"}])

    # [AAA] Act: Steam id is not a number, could be an injection attempt
    result = igdb.find_game('620"; fields *', "Valid Game")

    # [AAA] Assert: Steam lookup skipped, the bad id never reached IGDB
    # FIX: before, this passed even if the bad id was sent, because the fake ignored the body
    assert result["id"] == 789
    assert len(bodies) == 1
    assert "where" not in bodies[0]
    assert "fields *" not in bodies[0]


def test_igdb_error_raises(monkeypatch):
    # [AAA] Arrange: IGDB is down
    # FIX: a named function instead of (_ for _ in ()).throw(...), easier to read
    def fail(url, body, headers):
        raise UpstreamError("IGDB API error")

    monkeypatch.setattr(igdb, "_get_token", lambda: "fake_token")
    monkeypatch.setattr(igdb, "post_json", fail)

    # [AAA] Act & Assert
    with pytest.raises(UpstreamError):
        igdb.find_game("12345", "Test Game")

from .. import config
from ..errors import ConfigError, UpstreamError

from ..http import post_json
import time

_token = None
_token_expired_at = 0.0

def _get_token():
    """ดึง token จาก Twitch API แล้ว cache ไว้"""
    global _token, _token_expired_at

    if not config.TWITCH_CLIENT_ID or not config.TWITCH_CLIENT_SECRET:
        # ConfigError, not UpstreamError: a missing env var is our mistake (500), not Twitch being down (502)
        raise ConfigError("TWITCH_CLIENT_ID or TWITCH_CLIENT_SECRET is not set")

    now = time.time()
    if _token and _token_expired_at - now > 60:  # more than 1 minute left
        return _token
    
    body = {
        "client_id": config.TWITCH_CLIENT_ID,
        "client_secret": config.TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    data = post_json("https://id.twitch.tv/oauth2/token", body, headers={})
    if not isinstance(data, dict) or "access_token" not in data:
        raise UpstreamError("Twitch token: unexpected response")
    _token = data["access_token"]
    _token_expired_at = data.get("expires_in", 3600) + now
    return _token


def _headers():
    """IGDB auth headers (Twitch app token). Raises ConfigError when env vars are missing."""
    return {
        "Client-ID": config.TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {_get_token()}",
    }


def list_genres():
    """All IGDB genres as [{id, name}] (about 23)."""
    data = post_json(
        config.IGDB_BASE_URL + "/genres", body="fields name; limit 100;", headers=_headers()
    )
    if not isinstance(data, list):
        raise UpstreamError("IGDB genres: unexpected response")
    return [{"id": g["id"], "name": g["name"]} for g in data if "id" in g and g.get("name")]


def popular_games(genre_id: int, limit: int):
    """Most rated PC main games in a genre, with cover, rating and Steam app ids.

    genre_id must be an int (checked by the caller), so nothing from outside is injected.
    Sorted by total_rating_count: how many people rated it, a stand-in for "popular".
    """
    query = (
        "fields name, cover.image_id, total_rating, "
        "external_games.uid, external_games.external_game_source; "
        f"where genres = ({int(genre_id)}) & platforms = ({PC_PLATFORM}) & game_type = {MAIN_GAME}; "
        f"sort total_rating_count desc; limit {int(limit)};"
    )
    data = post_json(config.IGDB_BASE_URL + "/games", body=query, headers=_headers())
    if not isinstance(data, list):
        raise UpstreamError("IGDB popular games: unexpected response")
    return data


def steam_app_ids(game):
    """Steam app ids of an IGDB game (external_game_source 1 = Steam), as strings."""
    return [
        str(e["uid"])
        for e in game.get("external_games") or []
        if isinstance(e, dict) and e.get("external_game_source") == STEAM_SOURCE and e.get("uid")
    ]


def find_game(steam_app_id: str | None, title: str | None):
    """search game by steam_app_id or title, return the best match or None"""
    # FIX: type hints now allow None; CheapShark gives steamAppID = null for games not on Steam.
    headers = _headers()

    url = config.IGDB_BASE_URL + "/games"

    fields = (
        "name, genres.name, rating, rating_count, first_release_date, "
        "aggregated_rating, cover.image_id, summary, game_type, "
        "similar_games.name, similar_games.cover.image_id"
    )

    # search by steam_app_id first
    steam_id = _to_int(steam_app_id)
    if steam_id is not None:
        # FIX: the body was a dict ({"fields": ..., "where": ...}). IGDB does not read JSON;
        # it reads an Apicalypse query string where every clause ends with ";".
        # FIX: external_games.category is deprecated; external_game_source = 1 means Steam.
        # Checked against the live API on 2026-11-13: Steam app 620 returns Portal 2.
        # FIX: steam_id is an int (see _to_int), so nothing from outside can be injected into the query.
        query = (
            f"fields {fields}; "
            f'where external_games.external_game_source = 1 & external_games.uid = "{steam_id}"; '
            "limit 1;"
        )
        data = post_json(url, body=query, headers=headers)

        if isinstance(data, list) and data:
            return data[0]

    # fallback to search by title
    if title:
        # FIX: same as above, build a query string instead of a dict.
        # The title is escaped so a game name with " or \ cannot break out of search "...".
        # FIX: was "limit 1" and took the first result. IGDB search does not rank the exact
        # name first: "Portal 2" returned "Portal Maze 2" first and Portal 2 third, and
        # "The Witcher 3: Wild Hunt" returned a bundle first. Fetch a few and pick with _pick_best.
        # FIX: only PC games (CheapShark only sells PC games). Without it, "LEGO Batman" matched
        # an unlicensed Sega Mega Drive game with exactly the same name.
        query = (
            f'search "{_escape(title)}"; fields {fields}; '
            f"where platforms = ({PC_PLATFORM}); limit {TITLE_SEARCH_LIMIT};"
        )
        data = post_json(url, body=query, headers=headers)

        if isinstance(data, list) and data:
            return _pick_best(data, title)

    return None


TITLE_SEARCH_LIMIT = 10  # enough to reach the real game in the searches we tried (it was 2nd or 3rd)
MAIN_GAME = 0  # IGDB game_type 0 = main game (1 = DLC, 3 = bundle, 5 = mod, ...)
PC_PLATFORM = 6  # IGDB platform 6 = PC (Microsoft Windows)
STEAM_SOURCE = 1  # IGDB external_game_source 1 = Steam


def _pick_best(games :list[dict], title :str):
    """Pick the game whose name matches the title exactly (ignoring case), else None.

    FIX: added for the title search (see find_game). Order of preference:
    1. exact name that is a main game, not a DLC/bundle/mod with the same name
    2. exact name of any type
    FIX: no longer falls back to IGDB's first result. With no exact name that was often a
    different game ("LEGO Batman" gave "LEGO Batman: Legacy of the Dark Knight", a 2025 game),
    and showing another game's cover and rating is worse than showing none.
    """
    wanted = title.casefold()
    exact = [g for g in games if g.get("name", "").casefold() == wanted]
    for game in exact:
        if game.get("game_type") == MAIN_GAME:
            return game
    return exact[0] if exact else None


def _to_int(value):
    """Return value as an int, or None if it is missing or not a number.

    FIX: steam_app_id used to go into the query unchecked. CheapShark sends it as a
    string (or null), so anything that is not a plain number is skipped and we fall
    back to the title search instead of sending a broken or injected query.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _escape(text):
    """Escape a string for use inside double quotes in an Apicalypse query.

    FIX: added so titles like 'The "Best" Game' do not end the quoted string early.
    Backslash first, otherwise the backslashes added for quotes would be escaped again.
    """
    return text.replace("\\", "\\\\").replace('"', '\\"')

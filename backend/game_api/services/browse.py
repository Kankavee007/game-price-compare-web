import logging
import time
from concurrent.futures import ThreadPoolExecutor

from .. import config
from ..errors import InvalidCurrencyError, InvalidParamError, UpstreamError
from . import cheapshark, exchange, igdb

log = logging.getLogger(__name__)

IGDB_COVER_URL = "https://images.igdb.com/igdb/image/upload/t_cover_big/{}.jpg"

_genres = []  # see get_genres
_genres_fetched_at = 0.0
_browse_cache = {}  # {genre id: (fetched_at, games with USD prices)}


def get_genres():
    """IGDB genres as [{id, name}] sorted by name, cached GENRES_CACHE_SECONDS.

    Raises:
        ConfigError: Twitch env vars missing
        UpstreamError: IGDB down and nothing cached
    """
    global _genres, _genres_fetched_at

    now = time.time()
    if _genres and now - _genres_fetched_at < config.GENRES_CACHE_SECONDS:
        return _genres
    try:
        genres = sorted(igdb.list_genres(), key=lambda g: g["name"])
    except UpstreamError:
        if _genres:
            return _genres  # stale is fine: genres hardly change
        raise
    _genres, _genres_fetched_at = genres, now
    return _genres


def browse(genre_param, currency):
    """Popular PC games in a genre with the cheapest CheapShark price in `currency`.

    Returns {genre: {id, name}, currency, games: [{name, cover, rating, gameID, price}]};
    gameID and price are None when CheapShark does not sell the game (or its lookup failed).

    Raises:
        InvalidParamError: genre missing, not a number, or not an IGDB genre
        InvalidCurrencyError: ไม่รู้จักสกุลเงินนี้
        ConfigError: Twitch env vars missing
        UpstreamError: IGDB or er-api down
    """
    genre_id = _parse_genre(genre_param)
    genre = next((g for g in get_genres() if g["id"] == genre_id), None)
    if genre is None:
        raise InvalidParamError("unknown genre")

    rates = exchange.get_rates()
    if currency not in rates:
        raise InvalidCurrencyError(currency)
    rate = rates[currency]

    games = [
        {**g, "price": None if g["priceUSD"] is None else round(g["priceUSD"] * rate, 2)}
        for g in _games_usd(genre_id)
    ]
    for g in games:
        del g["priceUSD"]
    return {"genre": genre, "currency": currency, "games": games}


def _parse_genre(value):
    text = (value or "").strip()
    if not text:
        raise InvalidParamError("genre is required")
    if not (text.isascii() and text.isdigit()):
        raise InvalidParamError("genre must be a genre id")
    return int(text)


def _games_usd(genre_id):
    """Games of a genre with USD prices; cached BROWSE_CACHE_SECONDS when every lookup worked."""
    now = time.time()
    cached = _browse_cache.get(genre_id)
    if cached and now - cached[0] < config.BROWSE_CACHE_SECONDS:
        return cached[1]

    found = igdb.popular_games(genre_id, config.BROWSE_LIMIT)
    with ThreadPoolExecutor(max_workers=config.BROWSE_LOOKUP_WORKERS) as pool:
        lookups = list(pool.map(_cheapest_on_cheapshark, found))

    games = [_to_game(g, deal) for g, (deal, _) in zip(found, lookups)]
    # A failed lookup shows "no price"; do not keep that for 6 hours, try again next time
    if all(ok for _, ok in lookups):
        _browse_cache[genre_id] = (now, games)
    return games


def _cheapest_on_cheapshark(game):
    """(cheapest CheapShark row or None, lookup worked?) for an IGDB game.

    Tries each Steam app id until one is on CheapShark. Games without a Steam id are not
    looked up (CheapShark's title search is too loose to trust for this).
    """
    try:
        for app_id in igdb.steam_app_ids(game):
            rows = [r for r in cheapshark.find_by_steam_app_id(app_id) if _price(r) is not None]
            if rows:
                return min(rows, key=_price), True
        return None, True
    except UpstreamError:
        log.warning("CheapShark lookup failed for IGDB game %s", game.get("id"))
        return None, False


def _price(row):
    try:
        return float(row["cheapest"])
    except (KeyError, TypeError, ValueError):
        return None


def _to_game(game, deal):
    cover_id = (game.get("cover") or {}).get("image_id")
    rating = game.get("total_rating")
    return {
        "name": game.get("name"),
        "cover": IGDB_COVER_URL.format(cover_id) if cover_id else None,
        "rating": round(rating) if isinstance(rating, (int, float)) else None,
        "gameID": deal["gameID"] if deal else None,
        "priceUSD": _price(deal) if deal else None,
    }

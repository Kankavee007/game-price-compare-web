import time

from .. import config
from ..errors import UpstreamError, UpstreamNotFoundError
from ..http import get_json, get_json_with_headers

_store_cache = {}
_store_fetched_at = 0.0

# {cache key: (fetched_at, rows, total_pages)}; dicts keep insertion order, so the first key is the oldest
_deals_cache = {}

GAME_IDS_PER_CALL = 25  # CheapShark /games?ids accepts at most 25 ids


def search_games(title):
    """ค้นเกมตามชื่อ แต่ละเกมมีราคาถูกสุด (USD) และ dealID ของร้านที่ถูกสุด"""
    data = get_json(
        f"{config.CHEAPSHARK_BASE_URL}/games",
        {"title": title, "limit": config.SEARCH_LIMIT},
    )
    if not isinstance(data, list):
        raise UpstreamError("CheapShark search: unexpected response")
    return data


def get_games(game_ids):
    """{gameID: {info, cheapestPriceEver, deals}} for many games, one call per 25 ids.

    Ids CheapShark does not know are missing from the result.
    """
    games = {}
    for start in range(0, len(game_ids), GAME_IDS_PER_CALL):
        chunk = game_ids[start:start + GAME_IDS_PER_CALL]
        data = get_json(f"{config.CHEAPSHARK_BASE_URL}/games", {"ids": ",".join(chunk)})
        if not isinstance(data, dict):
            raise UpstreamError("CheapShark game lookup: unexpected response")
        games.update({gid: game for gid, game in data.items() if isinstance(game, dict)})
    return games


def get_deal_stores(game_ids):
    """คืน {dealID: storeID} ของทุก deal ในเกมที่ระบุ"""
    return {
        deal["dealID"]: deal["storeID"]
        for game in get_games(game_ids).values()
        for deal in game.get("deals", [])
    }


def list_deals(params):
    """GET /deals with the given CheapShark params; returns (rows, total_pages).

    Cached in memory for DEALS_CACHE_SECONDS per set of params: the landing page asks for the
    same lists for every visitor. Prices in the rows are USD.
    """
    key = tuple(sorted((k, str(v)) for k, v in params.items()))
    now = time.time()
    cached = _deals_cache.get(key)
    if cached and now - cached[0] < config.DEALS_CACHE_SECONDS:
        return cached[1], cached[2]

    data, headers = get_json_with_headers(f"{config.CHEAPSHARK_BASE_URL}/deals", params)
    if not isinstance(data, list):
        raise UpstreamError("CheapShark deals: unexpected response")
    total_pages = _to_page_count(headers.get("X-Total-Page-Count"))

    _deals_cache.pop(key, None)  # re-insert at the end so it counts as the newest
    _deals_cache[key] = (now, data, total_pages)
    while len(_deals_cache) > config.DEALS_CACHE_MAX_ENTRIES:
        _deals_cache.pop(next(iter(_deals_cache)))
    return data, total_pages


def _to_page_count(value):
    """X-Total-Page-Count as an int >= 1; 1 when the header is missing or not a number."""
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return 1


def get_game(game_id):
    """ข้อมูลเกมหนึ่งเกมจาก CheapShark: info (title, steamAppID, thumb), cheapestPriceEver, deals

    Returns None when CheapShark does not know the id (it answers 404 with an empty list).
    """
    try:
        data = get_json(f"{config.CHEAPSHARK_BASE_URL}/games", {"id": game_id})
    except UpstreamNotFoundError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("info"), dict):
        raise UpstreamError("CheapShark game: unexpected response")
    return data


def get_store_names():
    """คืน {storeID: storeName} cache ไว้ 1 วัน เพราะรายชื่อร้านแทบไม่เปลี่ยน"""
    global _store_cache, _store_fetched_at

    now = time.time()
    if _store_cache and now - _store_fetched_at < config.STORE_CACHE_SECONDS:
        return _store_cache

    try:
        data = get_json(f"{config.CHEAPSHARK_BASE_URL}/stores")
        _store_cache = {s["storeID"]: s["storeName"] for s in data}
        _store_fetched_at = now
    except (UpstreamError, KeyError, TypeError):
        # ชื่อร้านไม่ใช่ข้อมูลหลัก ถ้าดึงไม่ได้ใช้ cache เก่า (หรือว่าง) ไปก่อน
        pass
    return _store_cache

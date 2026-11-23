import time

from .. import config
from ..errors import UpstreamError, UpstreamNotFoundError
from ..http import get_json, get_json_with_headers, get_text

_stores = []  # see get_stores
_store_fetched_at = 0.0

# {cache key: (fetched_at, rows, total_pages)}; dicts keep insertion order, so the first key is the oldest
_deals_cache = {}
# {gameID: (fetched_at, game)}; same oldest-first order as _deals_cache
_games_cache = {}

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


def get_games(game_ids, cached=False):
    """{gameID: {info, cheapestPriceEver, deals}} for many games, one call per 25 ids.

    Ids CheapShark does not know are missing from the result.

    cached=True reuses answers up to GAMES_CACHE_SECONDS old and fetches only the other ids.
    Use it only where slightly old data is fine (lowest price ever on deal lists). Search and
    the wishlist leave it False: they match live prices to these deals, which must be current.
    Every fetched game is saved to the cache either way, so live calls keep it fresh.
    """
    games = {}

    now = time.time()
    if cached:
        for gid in game_ids:
            in_cache = _games_cache.get(gid)
            if not in_cache or now - in_cache[0] >= config.GAMES_CACHE_SECONDS:
                _games_cache.pop(gid, None)
                continue

            games.update({gid: in_cache[1]})

    left_over = [gid for gid in game_ids if gid not in games]

    for start in range(0, len(left_over), GAME_IDS_PER_CALL):
        chunk = left_over[start:start + GAME_IDS_PER_CALL]
        data = get_json(f"{config.CHEAPSHARK_BASE_URL}/games", {"ids": ",".join(chunk)})
        if not isinstance(data, dict):
            raise UpstreamError("CheapShark game lookup: unexpected response")

        for gid, game in data.items():
            if not isinstance(game, dict):
                continue

            games.update({gid: game})
            _games_cache.pop(gid, None)  # re-insert at the end so it counts as the newest
            _games_cache[gid] = (now, game)

    while len(_games_cache) > config.GAMES_CACHE_MAX_ENTRIES:
        _games_cache.pop(next(iter(_games_cache)))

    return games


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


def find_by_steam_app_id(steam_app_id):
    """CheapShark games for a Steam app id: [{gameID, cheapest (USD), thumb, ...}], often 1.

    One Steam app can map to several CheapShark games (an old and a remastered listing).
    """
    data = get_json(f"{config.CHEAPSHARK_BASE_URL}/games", {"steamAppID": steam_app_id})
    if not isinstance(data, list):
        raise UpstreamError("CheapShark Steam lookup: unexpected response")
    return data


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


def get_stores():
    """All CheapShark stores as [{storeID, storeName, isActive, logo}], cached 1 day.

    The store list hardly ever changes. If CheapShark fails and an old list is cached, the old
    list is returned.

    Raises:
        UpstreamError: CheapShark failed and nothing is cached yet
    """
    global _stores, _store_fetched_at

    now = time.time()
    if _stores and now - _store_fetched_at < config.STORE_CACHE_SECONDS:
        return _stores

    try:
        data = get_json(f"{config.CHEAPSHARK_BASE_URL}/stores")
        stores = [_to_store(s) for s in data]
    except (UpstreamError, KeyError, TypeError, AttributeError) as err:
        if _stores:
            return _stores
        raise UpstreamError(f"CheapShark stores: {err}") from err

    _stores = stores
    _store_fetched_at = now
    return _stores


def _to_store(store):
    logo = (store.get("images") or {}).get("logo")
    return {
        "storeID": store["storeID"],
        "storeName": store["storeName"],
        "isActive": bool(store.get("isActive")),
        "logo": f"https://www.cheapshark.com{logo}" if logo else None,
    }


def get_store_names():
    """คืน {storeID: storeName} ของทุกร้าน (รวมร้านที่ปิดแล้ว เพราะ deal เก่าอาจยังอ้างถึง)

    ชื่อร้านไม่ใช่ข้อมูลหลัก ถ้าดึงไม่ได้และไม่มี cache คืน {} แทนการ raise
    """
    try:
        return {s["storeID"]: s["storeName"] for s in get_stores()}
    except UpstreamError:
        return {}


def set_alert(email, game_id, price_usd):
    """Create or update a CheapShark email alert: CheapShark emails `email` when the game's
    price drops below `price_usd`. Calling it again for the same email and game updates the price.

    Returns True when CheapShark accepted it (it answers a bare true / false).

    The email is in the request URL (CheapShark only takes GET params), and requests puts that
    URL in its error messages. So errors are re-raised with a fixed message and no cause
    (`from None`): a logged traceback must never contain the email.

    Raises:
        UpstreamError: CheapShark is down or answered something that is not JSON
    """
    try:
        data = get_json(
            f"{config.CHEAPSHARK_BASE_URL}/alerts",
            {"action": "set", "email": email, "gameID": game_id, "price": f"{price_usd:.2f}"},
        )
    except UpstreamError:
        raise UpstreamError(f"CheapShark alert for game {game_id}: request failed") from None
    return data is True


def manage_alerts(email):
    """Ask CheapShark to email `email` a link to view, change or delete its price alerts.

    CheapShark answers in plain text, not JSON (checked live 2026-11-16):
    - 200: the email is sent
    - 400 "No alerts found for email": the address has no alerts
    - 400 "Link was already sent recently": a link was sent a short while ago; CheapShark
      will not send another yet, the earlier one is still valid
    Returns "sent", "alreadySent" or "noAlerts".

    The email is in the request URL, so errors never carry it: network errors get a fixed
    message, and CheapShark's reply has the address removed before it goes in the message.

    Raises:
        UpstreamError: CheapShark is down or answered something else
    """
    try:
        status, text = get_text(
            f"{config.CHEAPSHARK_BASE_URL}/alerts", {"action": "manage", "email": email}
        )
    except UpstreamError:
        raise UpstreamError("CheapShark manage alerts: request failed") from None
    if status == 200:
        return "sent"
    if status == 400 and "already sent" in text.lower():
        return "alreadySent"
    if status == 400 and "no alerts" in text.lower():
        return "noAlerts"
    reply = text.replace(email, "<email>")[:100].strip()
    raise UpstreamError(f"CheapShark manage alerts: HTTP {status}: {reply!r}")

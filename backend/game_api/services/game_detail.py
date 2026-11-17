import logging
from datetime import datetime, timezone

from ..errors import ConfigError, InvalidCurrencyError, UpstreamError
from . import cheapshark, exchange, igdb
from .lowest import lowest_price_fields

log = logging.getLogger(__name__)

IGDB_COVER_URL = "https://images.igdb.com/igdb/image/upload/t_cover_big/{}.jpg"
SIMILAR_LIMIT = 6
# Screenshots: 889x500 for the strip, 1920x1080 (or smaller if IGDB has no bigger) for the full view
IGDB_SCREENSHOT_URL = "https://images.igdb.com/igdb/image/upload/{size}/{image_id}.jpg"
SCREENSHOT_LIMIT = 12


def get_game_detail(game_id, currency):
    """ข้อมูลเกม (IGDB) + ราคาทุกร้าน (CheapShark) แปลงเป็นสกุล `currency` เรียงจากถูกไปแพง

    Returns None when CheapShark does not know the id.

    Raises:
        InvalidCurrencyError: ไม่รู้จักสกุลเงินนี้
        UpstreamError: CheapShark หรือ er-api ล่มหรือตอบผิดรูปแบบ (IGDB ล่มไม่ raise ดู _find_igdb)
    """
    rates = exchange.get_rates()
    if currency not in rates:
        raise InvalidCurrencyError(currency)
    rate = rates[currency]

    game = cheapshark.get_game(game_id)
    if game is None:
        return None
    info = game["info"]
    store_names = cheapshark.get_store_names()

    deals = [_to_deal(d, rate, store_names) for d in game.get("deals", [])]
    # Cheapest first; same price sorted by store name so the order does not jump between requests.
    deals.sort(key=lambda d: (d["price"], d["storeName"] or ""))

    found = _find_igdb(info.get("steamAppID"), info.get("title"))
    cover_id = (found.get("cover") or {}).get("image_id")

    return {
        "id": game_id,
        # CheapShark's title is the fallback so the page always has a name.
        "name": found.get("name") or info.get("title"),
        "thumb": info.get("thumb"),
        "cover": IGDB_COVER_URL.format(cover_id) if cover_id else None,
        "genres": [g["name"] for g in found.get("genres", []) if g.get("name")],
        # Same genres with their IGDB id, so the page can link to /browse?genre=<id>
        "genreTags": [
            {"id": g["id"], "name": g["name"]}
            for g in found.get("genres", [])
            if g.get("name") and isinstance(g.get("id"), int)
        ],
        "rating": _round(found.get("rating")),
        "ratingCount": found.get("rating_count"),
        "criticRating": _round(found.get("aggregated_rating")),
        "summary": found.get("summary"),
        "releaseDate": _to_date(found.get("first_release_date")),
        "similarGames": _similar_games(found.get("similar_games")),
        "screenshots": _screenshots(found.get("screenshots")),
        "currency": currency,
        "deals": deals,
        **lowest_price_fields(
            game.get("cheapestPriceEver"),
            min((float(d["price"]) for d in game.get("deals", [])), default=None),
            rate,
        ),
    }


def _to_deal(deal, rate, store_names):
    store_id = deal["storeID"]
    return {
        "storeID": store_id,
        "storeName": store_names.get(store_id),
        "price": round(float(deal["price"]) * rate, 2),
        "retailPrice": round(float(deal["retailPrice"]) * rate, 2),
        "savings": round(float(deal["savings"])),
        "dealUrl": f"https://www.cheapshark.com/redirect?dealID={deal['dealID']}",
    }


def _find_igdb(steam_app_id, title):
    """IGDB game as a dict, or {} when there is no match or IGDB cannot be used.

    IGDB only adds extra info; prices come from CheapShark. So an IGDB failure is logged
    and the page still gets its prices instead of a 502. That includes ConfigError (no
    Twitch env vars): it is logged as an error so it gets noticed, but does not hide prices.
    """
    try:
        return igdb.find_game(steam_app_id, title) or {}
    except ConfigError as err:
        log.error("IGDB disabled, server misconfigured: %s", err)
    except (UpstreamError, KeyError, TypeError, ValueError):
        log.exception("IGDB lookup failed for steam_app_id=%r title=%r", steam_app_id, title)
    return {}


def _similar_games(games):
    """IGDB similar_games as [{name, cover}], at most SIMILAR_LIMIT; [] when there are none.

    Only the name is used to link (to the search page): IGDB ids are not CheapShark ids.
    """
    if not isinstance(games, list):
        return []
    result = []
    for game in games:
        if not isinstance(game, dict) or not game.get("name"):
            continue
        cover_id = (game.get("cover") or {}).get("image_id")
        result.append({
            "name": game["name"],
            "cover": IGDB_COVER_URL.format(cover_id) if cover_id else None,
        })
        if len(result) == SIMILAR_LIMIT:
            break
    return result


def _screenshots(shots):
    """IGDB screenshots as [{thumb, full}], at most SCREENSHOT_LIMIT; [] when there are none.

    image_id goes into the URL path, so only plain letters and digits are used.
    """
    if not isinstance(shots, list):
        return []
    result = []
    for shot in shots:
        image_id = shot.get("image_id") if isinstance(shot, dict) else None
        if not (isinstance(image_id, str) and image_id.isascii() and image_id.isalnum()):
            continue
        result.append({
            "thumb": IGDB_SCREENSHOT_URL.format(size="t_screenshot_big", image_id=image_id),
            "full": IGDB_SCREENSHOT_URL.format(size="t_1080p", image_id=image_id),
        })
        if len(result) == SCREENSHOT_LIMIT:
            break
    return result


def _round(value):
    """IGDB ratings are floats like 87.4321; the page shows whole numbers out of 100."""
    return round(value) if isinstance(value, (int, float)) else None


def _to_date(timestamp):
    """IGDB first_release_date is a Unix timestamp (UTC); return "YYYY-MM-DD" or None."""
    if not isinstance(timestamp, (int, float)):
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()

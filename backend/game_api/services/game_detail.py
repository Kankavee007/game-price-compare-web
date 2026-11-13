import logging
from datetime import datetime, timezone

from ..errors import ConfigError, InvalidCurrencyError, UpstreamError
from . import cheapshark, exchange, igdb

log = logging.getLogger(__name__)

IGDB_COVER_URL = "https://images.igdb.com/igdb/image/upload/t_cover_big/{}.jpg"


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
        "rating": _round(found.get("rating")),
        "ratingCount": found.get("rating_count"),
        "criticRating": _round(found.get("aggregated_rating")),
        "summary": found.get("summary"),
        "releaseDate": _to_date(found.get("first_release_date")),
        "currency": currency,
        "deals": deals,
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


def _round(value):
    """IGDB ratings are floats like 87.4321; the page shows whole numbers out of 100."""
    return round(value) if isinstance(value, (int, float)) else None


def _to_date(timestamp):
    """IGDB first_release_date is a Unix timestamp (UTC); return "YYYY-MM-DD" or None."""
    if not isinstance(timestamp, (int, float)):
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()

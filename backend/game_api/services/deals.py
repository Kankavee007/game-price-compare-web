import logging
import math
from datetime import datetime, timezone

from .. import config
from ..errors import InvalidCurrencyError, InvalidParamError, UpstreamError
from . import cheapshark, exchange
from .lowest import lowest_price_fields
from .steam import steam_cover_url

log = logging.getLogger(__name__)

# Our sort names -> CheapShark sortBy. CheapShark's default direction is already the one users
# expect (checked live 2026-11-15): Price cheapest first; Savings, Metacritic, Reviews highest
# first; Release newest first. So no "desc" param is sent.
SORTS = {
    "relevance": None,  # title search order, see _relevance
    "deal": "Deal Rating",
    "price": "Price",
    "savings": "Savings",
    "rating": "Metacritic",
    "reviews": "Reviews",
    "newest": "Release",
}

RATING_LOOKUP_PAGE_SIZE = 60  # CheapShark's max page size, used to find ratings for a title search


def find_deals(query, currency, args):
    """Deals filtered and sorted, one row per game (its cheapest store), prices in `currency`.

    `args` is a mapping of raw strings (e.g. request.args): minPrice, maxPrice, sort, page,
    stores, onSale, minRating. Empty values count as unset.

    Returns { results, page, totalPages, currency }.

    Raises:
        InvalidParamError: a parameter is invalid; the message names it
        InvalidCurrencyError: ไม่รู้จักสกุลเงินนี้
        UpstreamError: API ภายนอกล่มหรือตอบผิดรูปแบบ
    """
    f = _parse(query, args)

    rates = exchange.get_rates()
    if currency not in rates:
        raise InvalidCurrencyError(currency)
    rate = rates[currency]

    if f["sort"] == "relevance":
        results, total_pages = _relevance(query, f, rate, currency), 1
    else:
        results, total_pages = _from_deals(query, f, rate, currency)

    return {"results": results, "page": f["page"], "totalPages": total_pages, "currency": currency}


def _from_deals(query, f, rate, currency):
    params = {
        "pageSize": config.DEALS_PAGE_SIZE,
        "pageNumber": f["page"],
        "sortBy": SORTS[f["sort"]],
    }
    if query:
        params["title"] = query
    # Bounds are in the user's currency; CheapShark wants USD. Round outward so a price at the
    # edge is not lost to rounding; the exact range is checked again after conversion.
    if f["min_price"] is not None:
        params["lowerPrice"] = math.floor(f["min_price"] / rate * 100) / 100
    if f["max_price"] is not None:
        params["upperPrice"] = math.ceil(f["max_price"] / rate * 100) / 100
    if f["stores"]:
        params["storeID"] = ",".join(f["stores"])
    if f["on_sale"]:
        params["onSale"] = 1
    if f["min_rating"] is not None:
        params["steamRating"] = f["min_rating"]

    rows, total_pages = cheapshark.list_deals(params)
    store_names = cheapshark.get_store_names()

    # /deals has one row per store. Keep each game where it first appears (that is the sort
    # order) but with the data of its cheapest row.
    cheapest = {}
    for row in rows:
        gid = row["gameID"]
        if gid not in cheapest or float(row["salePrice"]) < float(cheapest[gid]["salePrice"]):
            cheapest[gid] = row

    rows = [row for row in cheapest.values() if _in_range(round(float(row["salePrice"]) * rate, 2), f)]
    lowest = _lowest_prices([row["gameID"] for row in rows])
    results = [
        {
            **_from_deal_row(row, rate, currency, store_names),
            **lowest_price_fields(lowest.get(row["gameID"]), float(row["salePrice"]), rate),
        }
        for row in rows
    ]
    return results, total_pages


def _lowest_prices(game_ids):
    """{gameID: cheapestPriceEver} from /games?ids (one call per 25 games).

    The lowest price ever is extra info: if the lookup fails, the deals are still returned
    (with null lowest-price fields) and the error is logged.
    """
    try:
        games = cheapshark.get_games(game_ids)
    except (UpstreamError, KeyError, TypeError, ValueError):
        log.exception("lowest price lookup failed for %d games", len(game_ids))
        return {}
    return {gid: game.get("cheapestPriceEver") for gid, game in games.items()}


def _relevance(query, f, rate, currency):
    """Title search in CheapShark's relevance order, with the filters applied to its results.

    /games?title ranks the closest names first; /deals?title is a plain substring match
    ('portal' also returns 'SPORTAL'), so it is only used here to look up Steam ratings
    when minRating is set. A game with no rating found is then left out.
    """
    if f["page"] > 0:
        return []  # a title search has one page only

    games = cheapshark.search_games(query)
    details = cheapshark.get_games([g["gameID"] for g in games])
    store_names = cheapshark.get_store_names()

    rated = None
    if f["min_rating"] is not None:
        rows, _ = cheapshark.list_deals({
            "title": query,
            "steamRating": f["min_rating"],
            "pageSize": RATING_LOOKUP_PAGE_SIZE,
        })
        rated = {row["gameID"]: row for row in rows}

    results = []
    for game in games:
        gid = game["gameID"]
        if rated is not None and gid not in rated:
            continue
        detail = details.get(gid, {})
        # (USD price, converted deal) so the historical-low check can compare in USD
        deals = [
            (float(d["price"]), _from_game_deal(d, rate, store_names))
            for d in detail.get("deals", [])
            if (not f["stores"] or d["storeID"] in f["stores"])
            and (not f["on_sale"] or float(d["savings"]) > 0)
        ]
        deals = [d for d in deals if _in_range(d[1]["price"], f)]
        if not deals:
            continue
        best_usd, best = min(deals, key=lambda d: (d[1]["price"], d[1]["storeName"] or ""))
        rating_row = (rated or {}).get(gid, {})
        results.append({
            "gameID": gid,
            "name": game["external"],
            **best,
            **lowest_price_fields(detail.get("cheapestPriceEver"), best_usd, rate),
            "currency": currency,
            "thumb": game["thumb"],
            "cover": steam_cover_url(game.get("steamAppID")),
            "steamRating": _steam_rating(rating_row),
            "metacriticScore": _positive_int(rating_row.get("metacriticScore")),
            "releaseDate": _to_date(rating_row.get("releaseDate")),
        })
    return results


def _from_deal_row(row, rate, currency, store_names):
    store_id = row["storeID"]
    return {
        "gameID": row["gameID"],
        "name": row["title"],
        "price": round(float(row["salePrice"]) * rate, 2),
        "retailPrice": round(float(row["normalPrice"]) * rate, 2),
        "savings": round(float(row["savings"])),
        "currency": currency,
        "thumb": row.get("thumb"),
        "cover": steam_cover_url(row.get("steamAppID")),
        "storeID": store_id,
        "storeName": store_names.get(store_id),
        "dealUrl": f"https://www.cheapshark.com/redirect?dealID={row['dealID']}",
        "steamRating": _steam_rating(row),
        "metacriticScore": _positive_int(row.get("metacriticScore")),
        "releaseDate": _to_date(row.get("releaseDate")),
    }


def _from_game_deal(deal, rate, store_names):
    """A deal from /games?ids (keys price/retailPrice, not salePrice/normalPrice)."""
    store_id = deal["storeID"]
    return {
        "price": round(float(deal["price"]) * rate, 2),
        "retailPrice": round(float(deal["retailPrice"]) * rate, 2),
        "savings": round(float(deal["savings"])),
        "storeID": store_id,
        "storeName": store_names.get(store_id),
        "dealUrl": f"https://www.cheapshark.com/redirect?dealID={deal['dealID']}",
    }


def _in_range(price, f):
    return (f["min_price"] is None or price >= f["min_price"]) and (
        f["max_price"] is None or price <= f["max_price"]
    )


def _steam_rating(row):
    """Steam rating percent, or None when the game has no Steam reviews (CheapShark sends "0")."""
    if not _positive_int(row.get("steamRatingCount")):
        return None
    return _positive_int(row.get("steamRatingPercent"))


def _positive_int(value):
    """CheapShark sends numbers as strings and "0" for "no data"."""
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _to_date(timestamp):
    """Unix timestamp -> "YYYY-MM-DD"; None for missing or 0 (CheapShark's "unknown")."""
    if not isinstance(timestamp, (int, float)) or timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()


# --- parameter parsing -------------------------------------------------------------------


def _parse(query, args):
    def raw(name):
        value = args.get(name)
        return value.strip() if isinstance(value, str) and value.strip() else None

    f = {
        "min_price": _price(raw("minPrice"), "minPrice"),
        "max_price": _price(raw("maxPrice"), "maxPrice"),
        "page": _int(raw("page"), "page", 0, 1000) or 0,
        "stores": _stores(raw("stores")),
        "on_sale": _flag(raw("onSale"), "onSale"),
        "min_rating": _int(raw("minRating"), "minRating", 0, 100),
    }
    if f["min_price"] is not None and f["max_price"] is not None and f["min_price"] > f["max_price"]:
        raise InvalidParamError("minPrice must not be higher than maxPrice")

    sort = raw("sort")
    if sort is not None and sort not in SORTS:
        raise InvalidParamError(f"sort must be one of: {', '.join(SORTS)}")
    if sort is None:
        sort = "relevance" if query else "deal"
    elif sort == "relevance" and not query:
        sort = "deal"  # relevance needs a title; with no title fall back to the default
    f["sort"] = sort
    return f


def _price(value, name):
    if value is None:
        return None
    try:
        number = float(value)
    except ValueError:
        raise InvalidParamError(f"{name} must be a number") from None
    if not math.isfinite(number) or number < 0:
        raise InvalidParamError(f"{name} must be 0 or more")
    return number


def _int(value, name, low, high):
    if value is None:
        return None
    if not (value.isascii() and value.isdigit()) or not low <= int(value) <= high:
        raise InvalidParamError(f"{name} must be a whole number from {low} to {high}")
    return int(value)


def _stores(value):
    if value is None:
        return []
    ids = [s.strip() for s in value.split(",") if s.strip()]
    if not all(s.isascii() and s.isdigit() for s in ids):
        raise InvalidParamError("stores must be a comma-separated list of store ids")
    return ids


def _flag(value, name):
    if value is None or value in ("0", "false"):
        return False
    if value in ("1", "true"):
        return True
    raise InvalidParamError(f"{name} must be 1 or 0")

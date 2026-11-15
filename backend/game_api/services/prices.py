from ..errors import InvalidCurrencyError, InvalidParamError
from . import cheapshark, exchange
from .lowest import lowest_price_fields

MAX_IDS = 50  # same as the wishlist limit; CheapShark is called once per 25 ids


def get_prices(ids_param, currency):
    """Current cheapest deal of many games (e.g. the wishlist), prices in `currency`.

    `ids_param` is the raw "1,2,3" string. Games CheapShark no longer knows, or with no
    deal, are left out, so the caller can show them as "no longer listed". The result keeps
    the order of the ids.

    Raises:
        InvalidParamError: no ids, more than MAX_IDS, or an id that is not a number
        InvalidCurrencyError: ไม่รู้จักสกุลเงินนี้
        UpstreamError: CheapShark หรือ er-api ล่ม
    """
    ids = _parse_ids(ids_param)

    rates = exchange.get_rates()
    if currency not in rates:
        raise InvalidCurrencyError(currency)
    rate = rates[currency]

    games = cheapshark.get_games(ids)
    store_names = cheapshark.get_store_names()

    results = []
    for gid in ids:
        game = games.get(gid)
        deals = (game or {}).get("deals") or []
        if not deals:
            continue
        # Cheapest first; same price sorted by store name so the choice does not jump
        best = min(deals, key=lambda d: (float(d["price"]), store_names.get(d["storeID"]) or ""))
        info = game.get("info") or {}
        results.append({
            "gameID": gid,
            "name": info.get("title"),
            "thumb": info.get("thumb"),
            "price": round(float(best["price"]) * rate, 2),
            "retailPrice": round(float(best["retailPrice"]) * rate, 2),
            "savings": round(float(best["savings"])),
            "currency": currency,
            "storeID": best["storeID"],
            "storeName": store_names.get(best["storeID"]),
            "dealUrl": f"https://www.cheapshark.com/redirect?dealID={best['dealID']}",
            **lowest_price_fields(game.get("cheapestPriceEver"), float(best["price"]), rate),
        })
    return results


def _parse_ids(value):
    ids = [part.strip() for part in (value or "").split(",") if part.strip()]
    if not ids:
        raise InvalidParamError("ids is required (comma-separated game ids)")
    if not all(i.isascii() and i.isdigit() for i in ids):
        raise InvalidParamError("ids must be a comma-separated list of game ids")
    ids = list(dict.fromkeys(ids))  # drop repeats, keep order
    if len(ids) > MAX_IDS:
        raise InvalidParamError(f"ids accepts at most {MAX_IDS} games")
    return ids

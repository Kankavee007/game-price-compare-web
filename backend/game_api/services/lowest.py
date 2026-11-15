from datetime import datetime, timezone


def lowest_price_fields(cheapest_ever, current_usd, rate):
    """lowestPriceEver / lowestPriceEverDate / isHistoricalLow for one game.

    `cheapest_ever` is CheapShark's {"price": "0.99", "date": 1498153168} (USD, Unix time) or
    None. `current_usd` is today's cheapest price in USD. isHistoricalLow compares the USD
    prices before conversion, so rounding in another currency cannot flip it. A current price
    below the recorded lowest (CheapShark has not updated it yet) also counts as a low.
    """
    lowest_usd = _to_float((cheapest_ever or {}).get("price"))
    if lowest_usd is None:
        return {"lowestPriceEver": None, "lowestPriceEverDate": None, "isHistoricalLow": False}
    return {
        "lowestPriceEver": round(lowest_usd * rate, 2),
        "lowestPriceEverDate": _to_date((cheapest_ever or {}).get("date")),
        "isHistoricalLow": current_usd is not None and current_usd <= lowest_usd,
    }


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_date(timestamp):
    if not isinstance(timestamp, (int, float)) or timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()

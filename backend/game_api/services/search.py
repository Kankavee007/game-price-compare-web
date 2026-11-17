from ..errors import InvalidCurrencyError
from . import cheapshark, exchange
from .lowest import lowest_price_fields
from .steam import steam_cover_url


def search_prices(query, currency):
    """ค้นเกมแล้วคืนราคาถูกสุดของแต่ละเกม แปลงเป็นสกุล `currency` พร้อมชื่อร้าน

    Raises:
        InvalidCurrencyError: ไม่รู้จักสกุลเงินนี้
        UpstreamError: API ภายนอกล่มหรือตอบผิดรูปแบบ
    """
    rates = exchange.get_rates()
    if currency not in rates:
        raise InvalidCurrencyError(currency)
    rate = rates[currency]

    games = cheapshark.search_games(query)
    # One /games?ids call gives every deal's store and each game's lowest price ever
    details = cheapshark.get_games([g["gameID"] for g in games])
    deal_stores = {
        deal["dealID"]: deal["storeID"]
        for game in details.values()
        for deal in game.get("deals", [])
    }
    store_names = cheapshark.get_store_names()

    results = []
    for game in games:
        deal_id = game["cheapestDealID"]
        store_id = deal_stores.get(deal_id)
        results.append({
            "gameID": game["gameID"],
            "name": game["external"],
            "price": round(float(game["cheapest"]) * rate, 2),
            "currency": currency,
            "thumb": game["thumb"],
            "cover": steam_cover_url(game.get("steamAppID")),
            "storeID": store_id,
            "storeName": store_names.get(store_id) if store_id else None,
            "dealUrl": f"https://www.cheapshark.com/redirect?dealID={deal_id}",
            **lowest_price_fields(
                details.get(game["gameID"], {}).get("cheapestPriceEver"),
                float(game["cheapest"]),
                rate,
            ),
        })
    return results

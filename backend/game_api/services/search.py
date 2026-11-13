from ..errors import InvalidCurrencyError
from . import cheapshark, exchange


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
    deal_stores = cheapshark.get_deal_stores([g["gameID"] for g in games])
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
            "storeID": store_id,
            "storeName": store_names.get(store_id) if store_id else None,
            "dealUrl": f"https://www.cheapshark.com/redirect?dealID={deal_id}",
        })
    return results

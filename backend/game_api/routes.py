import logging

from flask import Blueprint, jsonify, request

from . import cheapshark, exchange
from .http import UpstreamError

bp = Blueprint("api", __name__, url_prefix="/api")
log = logging.getLogger(__name__)


@bp.get("/search")
def search():
    query = request.args.get("query", "").strip()
    currency = request.args.get("currency", "USD").strip().upper()

    if not query:
        return jsonify({"error": "query is required"}), 400

    try:
        rates = exchange.get_rates()
        if currency not in rates:
            return jsonify({"error": f"unsupported currency: {currency}"}), 400

        games = cheapshark.search_games(query)
        deal_stores = cheapshark.get_deal_stores([g["gameID"] for g in games])
        store_names = cheapshark.get_store_names()

        result = []
        for game in games:
            deal_id = game["cheapestDealID"]
            store_id = deal_stores.get(deal_id)
            result.append({
                "name": game["external"],
                "price": round(float(game["cheapest"]) * rates[currency], 2),
                "currency": currency,
                "thumb": game["thumb"],
                "storeID": store_id,
                "storeName": store_names.get(store_id) if store_id else None,
                "dealUrl": f"https://www.cheapshark.com/redirect?dealID={deal_id}",
            })
    except (UpstreamError, KeyError, TypeError, ValueError):
        log.exception("search failed for query=%r", query)
        return jsonify({"error": "price service unavailable, try again later"}), 502

    return jsonify(result)


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})

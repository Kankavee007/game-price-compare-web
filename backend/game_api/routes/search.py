import logging

from flask import Blueprint, jsonify, request

from ..errors import InvalidCurrencyError, UpstreamError
from ..services.search import search_prices

bp = Blueprint("search", __name__, url_prefix="/api")
log = logging.getLogger(__name__)


@bp.get("/search")
def search():
    query = request.args.get("query", "").strip()
    currency = request.args.get("currency", "USD").strip().upper()

    if not query:
        return jsonify({"error": "query is required"}), 400

    try:
        return jsonify(search_prices(query, currency))
    except InvalidCurrencyError:
        return jsonify({"error": f"unsupported currency: {currency}"}), 400
    except (UpstreamError, KeyError, TypeError, ValueError):
        log.exception("search failed for query=%r", query)
        return jsonify({"error": "price service unavailable, try again later"}), 502

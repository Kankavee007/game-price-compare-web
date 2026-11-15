import logging

from flask import Blueprint, jsonify, request

from ..errors import InvalidCurrencyError, InvalidParamError, UpstreamError
from ..services.deals import find_deals

bp = Blueprint("deals", __name__, url_prefix="/api")
log = logging.getLogger(__name__)


@bp.get("/deals")
def deals():
    query = request.args.get("q", "").strip()
    currency = request.args.get("currency", "USD").strip().upper()

    try:
        return jsonify(find_deals(query, currency, request.args))
    except InvalidCurrencyError:
        return jsonify({"error": f"unsupported currency: {currency}"}), 400
    except InvalidParamError as err:
        return jsonify({"error": str(err)}), 400
    except (UpstreamError, KeyError, TypeError, ValueError):
        log.exception("deals failed for query=%r", query)
        return jsonify({"error": "price service unavailable, try again later"}), 502

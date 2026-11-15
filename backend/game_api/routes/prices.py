import logging

from flask import Blueprint, jsonify, request

from ..errors import InvalidCurrencyError, InvalidParamError, UpstreamError
from ..services.prices import get_prices

bp = Blueprint("prices", __name__, url_prefix="/api")
log = logging.getLogger(__name__)


@bp.get("/prices")
def prices():
    currency = request.args.get("currency", "USD").strip().upper()

    try:
        return jsonify(get_prices(request.args.get("ids", ""), currency))
    except InvalidCurrencyError:
        return jsonify({"error": f"unsupported currency: {currency}"}), 400
    except InvalidParamError as err:
        return jsonify({"error": str(err)}), 400
    except (UpstreamError, KeyError, TypeError, ValueError):
        log.exception("prices failed")
        return jsonify({"error": "price service unavailable, try again later"}), 502

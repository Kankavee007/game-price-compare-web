import logging

from flask import Blueprint, jsonify, request

from ..errors import InvalidCurrencyError, UpstreamError
from ..services.game_detail import get_game_detail

bp = Blueprint("games", __name__, url_prefix="/api")
log = logging.getLogger(__name__)


@bp.get("/games/<game_id>")
def game_detail(game_id):
    currency = request.args.get("currency", "USD").strip().upper()

    # CheapShark game ids are numbers; anything else cannot exist, so skip the API call.
    # isascii: str.isdigit() alone also accepts digits like "²".
    if not (game_id.isascii() and game_id.isdigit()):
        return jsonify({"error": "game not found"}), 404

    try:
        detail = get_game_detail(game_id, currency)
    except InvalidCurrencyError:
        return jsonify({"error": f"unsupported currency: {currency}"}), 400
    except (UpstreamError, KeyError, TypeError, ValueError):
        log.exception("game detail failed for id=%r", game_id)
        return jsonify({"error": "price service unavailable, try again later"}), 502

    if detail is None:
        return jsonify({"error": "game not found"}), 404
    return jsonify(detail)

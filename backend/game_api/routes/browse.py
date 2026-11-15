import logging

from flask import Blueprint, jsonify, request

from .. import config
from ..errors import ConfigError, InvalidCurrencyError, InvalidParamError, UpstreamError
from ..services.browse import browse, get_genres

bp = Blueprint("browse", __name__, url_prefix="/api")
log = logging.getLogger(__name__)


@bp.get("/genres")
def genres():
    try:
        res = jsonify(get_genres())
        res.headers["Cache-Control"] = config.SHARED_CACHE_CONTROL
        return res
    except ConfigError as err:
        log.error("IGDB disabled, server misconfigured: %s", err)
        return jsonify({"error": "server is not configured for game info"}), 500
    except (UpstreamError, KeyError, TypeError, ValueError):
        log.exception("genre list failed")
        return jsonify({"error": "genre list unavailable, try again later"}), 502


@bp.get("/browse")
def browse_genre():
    currency = request.args.get("currency", "USD").strip().upper()
    try:
        res = jsonify(browse(request.args.get("genre"), currency))
        res.headers["Cache-Control"] = config.SHARED_CACHE_CONTROL
        return res
    except InvalidCurrencyError:
        return jsonify({"error": f"unsupported currency: {currency}"}), 400
    except InvalidParamError as err:
        return jsonify({"error": str(err)}), 400
    except ConfigError as err:
        log.error("IGDB disabled, server misconfigured: %s", err)
        return jsonify({"error": "server is not configured for game info"}), 500
    except (UpstreamError, KeyError, TypeError, ValueError):
        log.exception("browse failed")
        return jsonify({"error": "browse unavailable, try again later"}), 502

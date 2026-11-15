import logging

from flask import Blueprint, jsonify, request

from ..errors import InvalidCurrencyError, InvalidParamError, UpstreamError
from ..services.alerts import AlertRejectedError, RateLimitedError, manage_alerts, set_alert

bp = Blueprint("alerts", __name__, url_prefix="/api")
log = logging.getLogger(__name__)

# POST, not GET: the email stays in the body, out of our URLs and access logs.
# Never log the body or the email; log lines use the gameID only.


@bp.post("/alerts")
def alerts():
    body = request.get_json(silent=True)
    game_id = body.get("gameID") if isinstance(body, dict) else None

    try:
        return jsonify(set_alert(body, _client_ip()))
    except InvalidCurrencyError:
        return jsonify({"error": "currency is not supported"}), 400
    except InvalidParamError as err:
        return jsonify({"error": str(err)}), 400
    except RateLimitedError:
        return jsonify({"error": "Too many alerts, try later"}), 429
    except AlertRejectedError:
        log.warning("CheapShark rejected an alert for game %s", game_id)
        return jsonify({"error": "Could not create alert, try again later"}), 502
    except UpstreamError as err:
        # The message has the gameID only (see cheapshark.set_alert); no traceback, so no URL
        log.error("alert failed: %s", err)
        return jsonify({"error": "Could not create alert, try again later"}), 502


@bp.post("/alerts/manage")
def manage():
    try:
        return jsonify(manage_alerts(request.get_json(silent=True), _client_ip()))
    except InvalidParamError as err:
        return jsonify({"error": str(err)}), 400
    except RateLimitedError:
        return jsonify({"error": "Too many requests, try later"}), 429
    except UpstreamError as err:
        log.error("manage alerts failed: %s", err)  # message has no email, see cheapshark.manage_alerts
        return jsonify({"error": "Could not send the email, try again later"}), 502


def _client_ip():
    """The visitor's IP. On Vercel the first X-Forwarded-For entry is the client (Vercel sets
    the header itself); locally it is missing and remote_addr is used."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() or request.remote_addr

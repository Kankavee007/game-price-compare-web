import logging

from flask import Blueprint, jsonify

from ..errors import UpstreamError
from ..services.stores import list_active_stores

bp = Blueprint("stores", __name__, url_prefix="/api")
log = logging.getLogger(__name__)


@bp.get("/stores")
def stores():
    try:
        return jsonify(list_active_stores())
    except UpstreamError:
        log.exception("store list failed")
        return jsonify({"error": "store list unavailable, try again later"}), 502

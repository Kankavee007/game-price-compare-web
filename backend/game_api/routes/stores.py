import logging

from flask import Blueprint, jsonify

from .. import config
from ..errors import UpstreamError
from ..services.stores import list_active_stores

bp = Blueprint("stores", __name__, url_prefix="/api")
log = logging.getLogger(__name__)


@bp.get("/stores")
def stores():
    try:
        res = jsonify(list_active_stores())
        res.headers["Cache-Control"] = config.SHARED_CACHE_CONTROL
        return res
    except UpstreamError:
        log.exception("store list failed")
        return jsonify({"error": "store list unavailable, try again later"}), 502

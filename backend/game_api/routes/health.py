from flask import Blueprint, jsonify

from .. import config

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    # igdb: whether the Twitch env vars are set (never their values). Without them the game
    # detail page still shows prices, only the IGDB info is empty, so this makes that visible.
    # It does not call Twitch: "configured" can still mean a wrong secret (check the logs then).
    igdb_ready = bool(config.TWITCH_CLIENT_ID and config.TWITCH_CLIENT_SECRET)
    return jsonify({"status": "ok", "igdb": "configured" if igdb_ready else "missing"})

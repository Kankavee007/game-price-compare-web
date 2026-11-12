import logging

from flask import Flask, jsonify

from .errors import ConfigError
from .routes import register_routes

log = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    register_routes(app)

    @app.errorhandler(ConfigError)
    def config_error(err):
        # Log the real reason for us; tell the client only that the server is at fault.
        log.error("server misconfigured: %s", err)
        return jsonify({"error": "server misconfigured"}), 500

    return app

from . import games, health, search


def register_routes(app):
    app.register_blueprint(search.bp)
    app.register_blueprint(games.bp)
    app.register_blueprint(health.bp)

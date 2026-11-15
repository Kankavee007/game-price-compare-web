from . import alerts, browse, deals, games, health, prices, search, stores


def register_routes(app):
    app.register_blueprint(search.bp)
    app.register_blueprint(games.bp)
    app.register_blueprint(deals.bp)
    app.register_blueprint(stores.bp)
    app.register_blueprint(prices.bp)
    app.register_blueprint(alerts.bp)
    app.register_blueprint(browse.bp)
    app.register_blueprint(health.bp)

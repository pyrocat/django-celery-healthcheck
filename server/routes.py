from server.views import healthcheck


def setup_routes(app):
    app.router.add_get("/healthcheck", healthcheck, name="healthcheck")



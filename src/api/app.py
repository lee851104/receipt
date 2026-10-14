"""Build the FastAPI app: settings, database, models and the /api routes."""
import json

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from .backends import load_backends
from .db import ROOT, init_db, make_engine
from .errors import ApiError, api_error_handler, validation_error_handler
from .routes import auth, health, items


def create_app(settings, backends=None):
    """The app for these settings; backends defaults to the models settings ask for, and tests pass their own."""
    app = FastAPI(title="消費配對系統 API", version="2.0.0")
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url)
    init_db(app.state.engine)
    app.state.backends = backends or load_backends(settings)
    report = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))
    app.state.categories = [category["name"] for category in report["categories"]]
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(auth.router)
    app.include_router(items.router)
    app.include_router(health.router)
    return app

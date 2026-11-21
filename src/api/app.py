"""Build the FastAPI app: settings, database, models, the /api routes, and the web pages under /web/."""
import json
from functools import partial

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from ..receipt import places
from ..receipt.traits import load_context
from . import dating
from .backends import load_backends
from .cache import Judging
from .dating_demo import ensure_demo_profiles
from .db import ROOT, init_db, make_engine
from .errors import ApiError, api_error_handler, internal_error_handler, validation_error_handler
from .jobs import Worker, fail_unfinished, recompute_profiles, run_job
from .limits import UploadLimit
from .routes import account, auth, health, invoices, items, matches, me
from .routes import dating as dating_routes


def create_app(settings, backends=None):
    """The app for these settings; backends defaults to the models settings ask for, and tests pass their own."""
    app = FastAPI(title="消費配對系統 API", version="2.0.0")
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url)
    init_db(app.state.engine)
    fail_unfinished(app.state.engine)
    app.state.backends = backends or load_backends(settings)
    app.state.context = load_context(ROOT)  # what the taste pipeline reads, loaded once
    app.state.regions = places.load_regions(ROOT)  # city or county → region, for the match list's distances
    # Upload jobs run here, one at a time in upload order, never on the threads that answer requests.
    app.state.worker = Worker(partial(run_job, app.state.engine, app.state.backends, settings, app.state.context))
    recompute_profiles(app.state.engine, app.state.worker, app.state.backends, app.state.context)
    app.state.judging = Judging()  # the names the classify box has being judged in the background
    report = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))
    app.state.categories = [category["name"] for category in report["categories"]]
    # The dating app: its word lists, the regions in their configured order for the city picker, the message limit,
    # and the demo users' dating profiles (made again for any demo user the seed added since).
    app.state.dating = dating.load_config(ROOT)
    regions = json.loads((ROOT / "configs" / "regions.json").read_text(encoding="utf-8"))
    app.state.region_list = [{"region": region, "cities": cities} for region, cities in regions.items()]
    app.state.throttle = dating_routes.Throttle(app.state.dating["messages_per_minute"])
    ensure_demo_profiles(app.state.engine, app.state.dating, app.state.regions)
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)
    # Before any body is read, so an oversized upload is refused without the server writing it to disk.
    app.add_middleware(UploadLimit, path="/api/invoices", limit=invoices.MAX_BODY)
    app.add_middleware(UploadLimit, path=dating_routes.PHOTO_PATH, limit=app.state.dating["photo_max_bytes"] + 64 * 1024)
    app.include_router(auth.router)
    # Without DEMO_MODE the demo endpoints do not exist at all, so they answer 404 and stay out of /docs.
    if settings.demo_mode:
        app.include_router(auth.demo_router)
    app.include_router(items.router)
    app.include_router(invoices.router)
    app.include_router(me.router)
    app.include_router(account.router)
    app.include_router(matches.router)
    app.include_router(dating_routes.public)
    app.include_router(dating_routes.router)
    app.include_router(health.router)

    @app.get("/", include_in_schema=False)
    def home():
        return RedirectResponse("/app/")

    # The dating app under /app/, the v2 analysis pages under /web/; neither at /, so an unknown /api path is a plain
    # 404 instead of a static-file 405. src/web/ is the frozen v1 report's build input and is never served.
    app.mount("/app", StaticFiles(directory=ROOT / "src" / "web_app", html=True), name="app")
    app.mount("/web", StaticFiles(directory=ROOT / "src" / "web_v2", html=True), name="web")
    return app

"""What the Docker container runs (design D14): the secret, the category model when one is to be downloaded from the
protected Space (the only place the container downloads from; a public model repo is refused, see
ensure_category_model), the jobs a stop left unfinished (failed, so the seed does not refuse over them), the 300 demo
users with their purchases and profiles (the seed runs on every start and writes nothing once they are complete), then
the server on all of the container's interfaces (docker-compose.yml publishes the port on the host's 127.0.0.1 only).

    python -m src.api.container
"""
import logging
import os
import secrets
import sys
from pathlib import Path

from .backends import model_dir
from .db import ROOT, init_db, make_engine
from .jobs import fail_unfinished
from .settings import Settings

DATA = Path("/data")  # the database volume
log = logging.getLogger(__name__)


def jwt_secret(env, data_dir=None):
    """JWT_SECRET from the environment, or the one kept in the data volume (DATA unless data_dir says otherwise),
    made on the first start, so tokens keep working when the container is rebuilt."""
    given = env.get("JWT_SECRET", "").strip()
    if given:
        return given
    data_dir = DATA if data_dir is None else data_dir  # looked up now, not when the module loaded
    kept = data_dir / "jwt-secret"
    if not kept.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        kept.write_text(secrets.token_urlsafe(32), encoding="utf-8")
    return kept.read_text(encoding="utf-8").strip()


def ensure_category_model(settings):
    """Get the category model into place before the server starts, and return what happened:

    - "skipped": CATEGORY_MODEL is not bert, so no model folder is read.
    - CATEGORY_MODEL_REPO_TYPE=space: the protected Space is the source. src/ml/category_remote.py downloads only the
      files its manifest lists, checks each against the pinned SHA-256 and puts them in place whole or not at all; its
      answer ("downloaded" or "present") is returned. A failure is one log line and "failed": the server starts anyway
      and reports the model unavailable.
    - "refused": a repo is set with CATEGORY_MODEL_REPO_TYPE=model. Settings.from_env already stops that at start-up,
      so this is only a second line of defence for a Settings built without it; nothing is downloaded.
    - "local": anything else. bert reads whatever verified bundle CATEGORY_MODEL_DIR holds, and
      backends.category_backend decides between bert and unavailable when the app loads.

    The container downloads only from the protected Space. The flow that took a whole public model repo was dropped
    on 2026-10-18 because Settings refuses it, so nothing here can reach a public repo."""
    if settings.category_model != "bert":
        return "skipped"
    if settings.category_model_repo_type == "space":
        try:
            from ..ml.category_remote import download_space_model
            return download_space_model(repo_id=settings.category_model_repo,
                                        revision=settings.category_model_revision,
                                        destination=model_dir(settings),
                                        expected_sha256=settings.category_model_sha256)
        except Exception:
            log.warning("protected category download failed; model availability will be checked at startup")
            return "failed"
    if settings.category_model_repo:
        # The repo, revision and anything else a public source carries stay out of the line.
        log.warning("CATEGORY_MODEL_REPO is set without CATEGORY_MODEL_REPO_TYPE=space: "
                    "nothing is downloaded and only a verified local model can be used")
        return "refused"
    return "local"


def seed_demo(engine, demo_mode):
    """Role 3's demo population (300 fictional users with their purchases, the reviewed attribute answers and the
    profiles) in demo mode only; the seed's summary, or None when demo mode is off or the seed refused.

    It runs on every start, not only into an empty database: the seed writes nothing when the population is already
    complete and repairs a stale one (a new MODEL_VERSION, an older image's 40 bare demo users). A refusal (a username
    held by someone else, a cached answer that differs, a demo job that never finished) must not keep the server from
    starting, as in launch.main: it is one log line, and the server starts with the demo users it has."""
    if not demo_mode:
        return None
    # The first start is silent for as long as the seed takes and the server is not up yet: say what is going on.
    log.info("demo users: checking them; the first start puts them in, about 20 seconds when timed outside Docker")
    try:
        from ..receipt.personas import build_personas
        from ..receipt.traits import load_context
        from .seed import seed_demo_population
        context = load_context(ROOT)
        return seed_demo_population(engine, build_personas(context["calendar"], total=300), context)
    except Exception as error:  # a clash, a differing cache, an unfinished job, a full disk: start anyway
        from .launch import reason_for  # one short line: the seed's clash list has one entry per demo user
        log.warning("demo users not updated: %s", reason_for(error))
        return None


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    os.environ["JWT_SECRET"] = jwt_secret(os.environ)
    try:
        settings = Settings.from_env(os.environ)
    except ValueError as error:  # a weak secret or a bad setting: one line, not a traceback, as src/api/main.py
        sys.exit(f"error: {error}")
    ensure_category_model(settings)
    engine = make_engine(settings.database_url)
    init_db(engine)
    # The container is the only process on its volume, and create_app fails the same jobs a few seconds later. It is
    # done here first because the seed refuses to run over a demo job left queued or running: a stop during the first
    # (long, silent) seed would make the next start's seed refuse, and the demo would stay half filled until a third.
    fail_unfinished(engine)
    summary = seed_demo(engine, settings.demo_mode)
    if isinstance(summary, dict):
        # "0 added" alone reads as no write: a repair (a new MODEL_VERSION, an interrupted seed) adds no account.
        log.info("demo users: %d in all, %d added%s", summary["users"], summary["added_users"],
                 " (already complete)" if summary["skipped"] else ", purchases and profiles rewritten")
    engine.dispose()
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

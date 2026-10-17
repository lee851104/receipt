"""What the Docker container runs (design D14): the secret, the category model when one is to be downloaded, the
demo users on an empty database, then the server on all of the container's interfaces (docker-compose.yml publishes
the port on the host's 127.0.0.1 only).

    python -m src.api.container
"""
import logging
import os
import secrets
import shutil
import sys
from pathlib import Path

from sqlmodel import Session, select

from .backends import model_dir
from .db import ROOT, init_db, make_engine
from .settings import Settings
from .tables import User

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


def hub_download(repo_id, revision, local_dir):
    from huggingface_hub import snapshot_download  # only the image installs it
    snapshot_download(repo_id=repo_id, revision=revision, local_dir=local_dir)


def put_in_place(partial, folder):
    """Move everything the download made into folder, replacing the entries of the same name and touching nothing
    else. config.json goes last: it is what makes the folder a model, so a move that stops half way leaves none."""
    for entry in sorted(partial.iterdir(), key=lambda path: path.name == "config.json"):
        target = folder / entry.name
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        elif target.exists() or target.is_symlink():
            target.unlink()
        shutil.move(str(entry), str(target))


def ensure_category_model(settings, download=hub_download):
    """Download the category model when CATEGORY_MODEL=bert and its folder holds none. It goes to a .partial folder
    inside the model folder (so it is on the same filesystem even when a volume is mounted there) and is moved into
    place with config.json last, so a failure leaves no half model and the next start tries again. Nothing else in
    the model folder is ever deleted. A failure is one line in the log: the server starts anyway and reports the
    model unavailable."""
    if settings.category_model != "bert":
        return "skipped"
    folder = model_dir(settings)
    if (folder / "config.json").exists():
        return "present"
    if not settings.category_model_repo:
        log.warning("CATEGORY_MODEL=bert, no model in %s and no CATEGORY_MODEL_REPO to download it from", folder)
        return "no_repo"
    existed = folder.exists()
    partial = folder / ".partial"
    try:
        shutil.rmtree(partial, ignore_errors=True)  # what an earlier crash left
        partial.mkdir(parents=True)
        download(settings.category_model_repo, settings.category_model_revision, str(partial))
        if not (partial / "config.json").is_file():
            raise ValueError("the repo holds no model: it has no config.json")
        put_in_place(partial, folder)
    except Exception as error:  # no network, a wrong repo or revision, a full disk: start without the model
        shutil.rmtree(partial, ignore_errors=True)
        if not existed:
            try:
                folder.rmdir()  # only when it is empty again
            except OSError:
                pass
        log.warning("could not get the category model %s@%s: %s", settings.category_model_repo,
                    settings.category_model_revision, " ".join(str(error).split()))
        return "failed"
    shutil.rmtree(partial, ignore_errors=True)  # empty now
    return "downloaded"


def seed_if_empty(engine, demo_mode):
    """The demo users, only in demo mode and only into a database nobody is in yet; how many were added."""
    if not demo_mode:
        return 0
    with Session(engine) as session:
        if session.exec(select(User.id).limit(1)).first() is not None:
            return 0
    from ..receipt.personas import build_personas
    from ..receipt.traits import load_context
    from .seed import seed_demo_users
    return seed_demo_users(engine, build_personas(load_context(ROOT)["calendar"]))


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
    added = seed_if_empty(engine, settings.demo_mode)
    if added:
        log.info("added %d demo users", added)
    engine.dispose()
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

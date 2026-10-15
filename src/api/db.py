"""The SQLite engine, and one session per request."""
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from . import tables  # noqa: F401  registers every table on SQLModel.metadata

ROOT = Path(__file__).resolve().parents[2]
MEMORY = "sqlite://"


def file_url(url):
    """A SQLite file URL whose relative path starts at the repository root rather than wherever the server was
    started, so data/app.db always lands in the git-ignored data/ folder. Absolute paths stay as they are."""
    return "sqlite:///" + (ROOT / url.removeprefix("sqlite:///")).as_posix()


def write_ahead(connection, record):
    """Readers no longer wait for a background upload's writes, and a busy database is waited on for 5 seconds
    instead of failing at once."""
    cursor = connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def make_engine(url):
    """An engine for url. An in-memory database (for tests only) keeps one shared connection, or each request
    would see an empty one; that single connection cannot serve requests running at the same time."""
    if url in (MEMORY, "sqlite:///:memory:"):
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    if url.startswith("sqlite:///"):
        url = file_url(url)
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", write_ahead)
    return engine


def init_db(engine):
    """Create the tables that do not exist yet. It never changes a table that exists, so after a column is added
    to tables.py, delete data/app.db and run the seed again."""
    SQLModel.metadata.create_all(engine)


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

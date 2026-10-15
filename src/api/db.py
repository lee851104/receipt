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


def pragmas(write_ahead):
    """What each new connection turns on. Foreign keys, so a row for a missing user fails at once instead of waiting
    for the next account that gets the same id; and for a file, write-ahead logging, so readers do not wait for a
    background upload's writes. (Python's sqlite3 already waits up to 5 seconds for a busy database.)"""
    def run(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        if write_ahead:
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    return run


def make_engine(url):
    """An engine for url. An in-memory database (for tests only) keeps one shared connection, or each request
    would see an empty one; that single connection cannot serve requests running at the same time."""
    # hide_parameters: a database error may reach the log, and the log must never hold real product names
    # (overview section 10); SQLAlchemy otherwise prints the statement's parameters in the message.
    if url in (MEMORY, "sqlite:///:memory:"):
        engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool,
                               hide_parameters=True)
        event.listen(engine, "connect", pragmas(write_ahead=False))
        return engine
    if url.startswith("sqlite:///"):
        url = file_url(url)
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, connect_args={"check_same_thread": False}, hide_parameters=True)
        event.listen(engine, "connect", pragmas(write_ahead=True))
        return engine
    raise ValueError("DATABASE_URL must be a SQLite URL such as sqlite:///data/app.db")


def init_db(engine):
    """Create the tables that do not exist yet, so a database from before new tables were added (week 1's, which
    has only users) simply gains them. It never changes a table that exists: only after a column or an index of an
    existing table changes in tables.py (as in databases made from earlier commits of role-1/uploads), delete
    data/app.db* (the database and its -wal and -shm files) and run the seed again."""
    SQLModel.metadata.create_all(engine)


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session


# scope="function": the session closes when the route returns, not after the response and its background task (the
# classify box's judgement), which would keep a connection checked out through a model call.
SessionDep = Annotated[Session, Depends(get_session, scope="function")]

"""The SQLite engine, and one session per request."""
from pathlib import Path

from fastapi import Request
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from . import tables  # noqa: F401  registers every table on SQLModel.metadata

MEMORY = "sqlite://"


def make_engine(url):
    """An engine for url. An in-memory database keeps one shared connection, or each request would see an empty one."""
    if url == MEMORY:
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, connect_args={"check_same_thread": False})


def init_db(engine):
    """Create the tables that do not exist yet."""
    SQLModel.metadata.create_all(engine)


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session

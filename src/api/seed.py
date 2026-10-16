"""Put the fictional population in the database as demo users. Run from the repository root:

    .venv/Scripts/python.exe -m src.api.seed

The list of fictional people may only grow at the end. After reordering or renaming people, delete the database
files (data/app.db*: the database and its -wal and -shm files) and run the seed again.
"""
import os
import sys

from dotenv import load_dotenv
from sqlmodel import Session, col, select

from ..receipt.personas import build_personas
from ..receipt.traits import load_context
from .db import ROOT, init_db, make_engine
from .settings import Settings
from .tables import User


def clash(username, user, person):
    """Why the database user at username is not the fictional person meant to be there, or None when it is."""
    if user.is_demo and user.display_name == person["name"]:
        return None
    holder = repr(user.display_name) + ("" if user.is_demo else " (a real account)")
    return f"{username} is {holder} in the database but {person['name']!r} in the list"


def seed_demo_users(engine, people):
    """One demo user per fictional person, demo_001 onwards by position, adding only the ones not there yet.
    A username held by anyone else stops the seed. The list may only grow at the end: a shorter list leaves the
    extra demo users in place."""
    wanted = {f"demo_{index:03}": person for index, person in enumerate(people, start=1)}
    with Session(engine) as session:
        existing = {user.username: user
                    for user in session.exec(select(User).where(col(User.username).in_(list(wanted)))).all()}
        wrong = [clash(username, existing[username], person) for username, person in wanted.items()
                 if username in existing]
        wrong = [message for message in wrong if message]
        if wrong:
            raise ValueError("; ".join(wrong) + ". Delete the database file and run the seed again.")
        for username, person in wanted.items():
            if username not in existing:
                session.add(User(username=username, display_name=person["name"], is_demo=True,
                                 persona=person["type"]))
        session.commit()
    return len(wanted) - len(existing)


def main():
    load_dotenv(ROOT / ".env")
    try:
        engine = make_engine(Settings.from_env(os.environ).database_url)
        init_db(engine)
        people = build_personas(load_context(ROOT)["calendar"], total=300)
        added = seed_demo_users(engine, people)
    except ValueError as error:  # a bad setting, or a database that no longer matches the list
        sys.exit(f"error: {error}")
    print(f"added {added} demo users; {len(people)} fictional people in all; database: {engine.url.database}")


if __name__ == "__main__":
    main()

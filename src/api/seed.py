"""Put the fictional population in the database as demo users. Run from the repository root:

    .venv/Scripts/python.exe -m src.api.seed
"""
import os

from dotenv import load_dotenv
from sqlmodel import Session, select

from ..receipt.personas import build_personas
from ..receipt.traits import load_context
from .app import ROOT
from .db import init_db, make_engine
from .settings import Settings
from .tables import User


def seed_demo_users(engine, people):
    """One demo user per fictional person, demo_001 onwards; usernames already taken are left alone."""
    with Session(engine) as session:
        taken = set(session.exec(select(User.username)).all())
        added = 0
        for index, person in enumerate(people, start=1):
            username = f"demo_{index:03}"
            if username not in taken:
                session.add(User(username=username, display_name=person["name"], is_demo=True,
                                 persona=person["type"]))
                added += 1
        session.commit()
    return added


def main():
    load_dotenv(ROOT / ".env")
    engine = make_engine(Settings.from_env(os.environ).database_url)
    init_db(engine)
    people = build_personas(load_context(ROOT)["calendar"])
    print("added", seed_demo_users(engine, people), "demo users;", len(people), "fictional people in all")


if __name__ == "__main__":
    main()

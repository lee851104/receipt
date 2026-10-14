"""The fictional population becomes demo users once, however often the seed runs."""
import unittest
from pathlib import Path

from sqlmodel import Session, select

from src.api.db import MEMORY, init_db, make_engine
from src.api.seed import seed_demo_users
from src.api.tables import User
from src.receipt.personas import build_personas
from src.receipt.traits import load_context

ROOT = Path(__file__).resolve().parents[1]
PEOPLE = [{"name": "咖啡上班族 A", "type": "咖啡上班族"}, {"name": "健身族 A", "type": "健身族"}]


class SeedTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine(MEMORY)
        init_db(self.engine)

    def users(self):
        with Session(self.engine) as session:
            return session.exec(select(User).order_by(User.id)).all()

    def test_each_person_becomes_a_demo_user_without_a_password(self):
        self.assertEqual(seed_demo_users(self.engine, PEOPLE), 2)
        self.assertEqual([(user.username, user.display_name, user.persona, user.is_demo, user.password_hash)
                          for user in self.users()],
                         [("demo_001", "咖啡上班族 A", "咖啡上班族", True, None),
                          ("demo_002", "健身族 A", "健身族", True, None)])

    def test_running_the_seed_again_adds_nobody(self):
        seed_demo_users(self.engine, PEOPLE)
        self.assertEqual(seed_demo_users(self.engine, PEOPLE), 0)
        self.assertEqual(len(self.users()), 2)

    def test_the_whole_fictional_population_fits(self):
        people = build_personas(load_context(ROOT)["calendar"])
        self.assertEqual(seed_demo_users(self.engine, people), len(people))
        self.assertEqual(len({user.display_name for user in self.users()}), len(people))


if __name__ == "__main__":
    unittest.main()

"""Database URLs: tests share one in-memory connection, and a file always lives under the repository root."""
import tempfile
import threading
import unittest
from pathlib import Path

from sqlmodel import Session, select

from src.api.db import ROOT, file_url, init_db, make_engine
from src.api.tables import User


def add_amy(engine):
    with Session(engine) as session:
        session.add(User(username="amy", display_name="Amy"))
        session.commit()


def usernames(engine):
    with Session(engine) as session:
        return session.exec(select(User.username)).all()


class DatabaseTests(unittest.TestCase):
    def test_a_relative_file_is_kept_under_the_repository_root(self):
        self.assertEqual(file_url("sqlite:///data/app.db"), "sqlite:///" + (ROOT / "data" / "app.db").as_posix())

    def test_an_absolute_file_stays_where_it_is_and_its_folder_is_made(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "nested" / "app.db"
            engine = make_engine("sqlite:///" + path.as_posix())
            try:
                init_db(engine)
                add_amy(engine)
                self.assertEqual(usernames(engine), ["amy"])
            finally:
                engine.dispose()  # Windows cannot delete a file that is still open, even after a failed check
            self.assertTrue(path.is_file())

    def test_both_in_memory_spellings_share_one_database_across_threads(self):
        for url in ("sqlite://", "sqlite:///:memory:"):
            with self.subTest(url=url):
                engine = make_engine(url)
                init_db(engine)
                # FastAPI runs plain def routes in worker threads, so another thread must see the same tables.
                thread = threading.Thread(target=add_amy, args=(engine,))
                thread.start()
                thread.join()
                self.assertEqual(usernames(engine), ["amy"])


if __name__ == "__main__":
    unittest.main()

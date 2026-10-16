"""Database URLs: tests share one in-memory connection, and a file always lives under the repository root."""
import tempfile
import threading
import unittest
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.api.db import MEMORY, ROOT, file_url, init_db, make_engine
from src.api.tables import ItemCache, Job, User


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

    def test_a_file_database_writes_ahead_and_enforces_foreign_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            engine = make_engine("sqlite:///" + (Path(folder) / "app.db").as_posix())
            try:
                with engine.connect() as connection:
                    mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar()
                    keys = connection.exec_driver_sql("PRAGMA foreign_keys").scalar()
            finally:
                engine.dispose()  # Windows cannot delete a file that is still open, even after a failed check
        self.assertEqual((mode, keys), ("wal", 1))

    def test_every_connection_overwrites_what_it_deletes(self):
        """D13: deleting really deletes, so a deleted row's bytes do not stay behind in the file."""
        with tempfile.TemporaryDirectory() as folder:
            for url in (MEMORY, "sqlite:///" + (Path(folder) / "app.db").as_posix()):
                engine = make_engine(url)
                try:
                    with self.subTest(url=url.rpartition("/")[2]), engine.connect() as connection:
                        self.assertEqual(connection.exec_driver_sql("PRAGMA secure_delete").scalar(), 1)
                finally:
                    engine.dispose()  # Windows cannot delete a file that is still open

    def test_every_engine_hides_statement_parameters(self):
        with tempfile.TemporaryDirectory() as folder:
            for url in (MEMORY, "sqlite:///:memory:", "sqlite:///" + (Path(folder) / "app.db").as_posix()):
                engine = make_engine(url)
                try:
                    with self.subTest(url=url.rpartition("/")[2]):
                        self.assertTrue(engine.hide_parameters)
                finally:
                    engine.dispose()  # Windows cannot delete a file that is still open

    def test_an_error_never_holds_a_product_name(self):
        engine = make_engine(MEMORY)
        init_db(engine)
        with Session(engine) as session:
            session.add_all([ItemCache(name="鮮奶茶", model="fake", fields="{}") for _ in range(2)])
            with self.assertRaises(IntegrityError) as caught:
                session.commit()
        self.assertNotIn("鮮奶茶", str(caught.exception))

    def test_a_url_that_is_not_sqlite_is_refused_without_echoing_it(self):
        for url in ("postgresql://amy:secret@localhost/app", "sqlite://foo"):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "DATABASE_URL must be a SQLite URL") as caught:
                make_engine(url)
            self.assertNotIn(url, str(caught.exception))

    def test_items_have_one_index_for_a_users_month(self):
        engine = make_engine(MEMORY)
        init_db(engine)
        with engine.connect() as connection:
            indexes = [row[1] for row in connection.exec_driver_sql("PRAGMA index_list(items)").all()]
        self.assertEqual(indexes, ["ix_items_user_month"])

    def test_a_row_for_a_missing_user_is_refused(self):
        engine = make_engine(MEMORY)
        init_db(engine)
        with Session(engine) as session:
            session.add(Job(user_id=99, month="2026-05"))
            with self.assertRaises(IntegrityError):
                session.commit()

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

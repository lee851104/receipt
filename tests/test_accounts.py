"""What deleting a month or an account removes, and the attribute answers that go with it."""
import unittest

from sqlmodel import Session, select

from src.api import accounts
from src.api.db import MEMORY, init_db, make_engine
from src.api.tables import Item, ItemCache, Job, Profile, User


def item(user_id, month, name):
    return Item(user_id=user_id, month=month, day=1, invoice=f"{month}-R01", merchant="測試店", district="臺北市大安區",
                name=name, quantity=1, amount=50, category=1)


class AccountsTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine(MEMORY)
        init_db(self.engine)
        with Session(self.engine) as session:
            session.add_all([User(username="amy", display_name="Amy", password_hash="x"),
                             User(username="ben", display_name="Ben", password_hash="x")])
            session.commit()
            session.add_all([item(1, "2026-05", "測試五月茶"), item(1, "2026-05", "測試共用茶"), item(1, "2026-06", "測試六月茶"),
                             item(1, "2026-06", "測試兩月茶"), item(1, "2026-05", "測試兩月茶"), item(2, "2026-05", "測試共用茶"),
                             Job(user_id=1, month="2026-05", status="done"), Job(user_id=1, month="2026-07", status="failed"),
                             Job(user_id=2, month="2026-05", status="done"), Profile(user_id=1), Profile(user_id=2)])
            for name in ("測試五月茶", "測試共用茶", "測試六月茶", "測試兩月茶", "測試只查過的茶"):
                for model in ("fake", "qwen"):
                    session.add(ItemCache(name=name, model=model, fields="{}"))
            session.commit()

    def rows(self, table, **where):
        with Session(self.engine) as session:
            query = select(table)
            for key, value in where.items():
                query = query.where(getattr(table, key) == value)
            return session.exec(query).all()

    def cached_names(self):
        return {row.name for row in self.rows(ItemCache)}

    def test_the_months_are_those_with_items_or_a_job_oldest_first(self):
        with Session(self.engine) as session:
            self.assertEqual(accounts.months_of(session, 1), ["2026-05", "2026-06", "2026-07"])
            self.assertEqual(accounts.months_of(session, 2), ["2026-05"])
            self.assertEqual(accounts.months_of(session, 3), [])

    def test_busy_means_a_queued_or_running_job_of_the_month_when_one_is_given(self):
        with Session(self.engine) as session:
            self.assertFalse(accounts.busy(session, 1))
            for status in ("queued", "running"):
                job = Job(user_id=1, month="2026-08", status=status)
                session.add(job)
                session.commit()
                self.assertTrue(accounts.busy(session, 1))
                self.assertTrue(accounts.busy(session, 1, "2026-08"))
                self.assertFalse(accounts.busy(session, 1, "2026-05"))
                self.assertFalse(accounts.busy(session, 2))
                session.delete(job)
                session.commit()

    def test_deleting_a_month_removes_its_items_and_jobs_only(self):
        with Session(self.engine) as session:
            accounts.delete_month(session, 1, "2026-05")
            session.commit()
        self.assertEqual({row.name for row in self.rows(Item, user_id=1)}, {"測試六月茶", "測試兩月茶"})
        self.assertEqual([row.month for row in self.rows(Job, user_id=1)], ["2026-07"])
        self.assertEqual(len(self.rows(Item, user_id=2)), 1)
        self.assertEqual(len(self.rows(Profile)), 2)

    def test_deleting_a_month_drops_only_the_answers_nothing_uses_any_more(self):
        with Session(self.engine) as session:
            accounts.delete_month(session, 1, "2026-05")
            session.commit()
        # 五月茶 was only in May; 共用茶 Ben still has; 兩月茶 June still has; 只查過的茶 was never uploaded.
        self.assertEqual(self.cached_names(), {"測試六月茶", "測試共用茶", "測試兩月茶", "測試只查過的茶"})

    def test_deleting_an_account_removes_everything_of_theirs_and_nothing_of_anyone_else(self):
        with Session(self.engine) as session:
            accounts.delete_account(session, 1)
            session.commit()
        self.assertEqual([self.rows(table, user_id=1) for table in (Item, Job, Profile)], [[], [], []])
        self.assertEqual([user.username for user in self.rows(User)], ["ben"])
        self.assertEqual((len(self.rows(Item, user_id=2)), len(self.rows(Job, user_id=2)), len(self.rows(Profile, user_id=2))),
                         (1, 1, 1))

    def test_deleting_an_account_drops_the_answers_only_its_items_used_for_every_model(self):
        with Session(self.engine) as session:
            accounts.delete_account(session, 1)
            session.commit()
        self.assertEqual(self.cached_names(), {"測試共用茶", "測試只查過的茶"})
        self.assertEqual(sorted(row.model for row in self.rows(ItemCache, name="測試共用茶")), ["fake", "qwen"])

    def test_forgetting_no_names_does_nothing(self):
        with Session(self.engine) as session:
            accounts.forget_unused(session, [])
            session.commit()
        self.assertEqual(len(self.rows(ItemCache)), 10)


if __name__ == "__main__":
    unittest.main()

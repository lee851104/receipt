"""DELETE /api/me/months/{month}: one month's items and jobs go, and the taste profile is worked out again."""
import threading
import unittest

from sqlmodel import Session, select

from src.api.tables import Item, ItemCache, Job, Profile, User
from tests.api_support import drain, invoice_csv, login, make_client, register, upload


def teas(month, count, prefix="測試茶"):
    """A fictional month of count valid items, one 50-dollar tea per bill."""
    return [[f"2026{month:02}{number % 28 + 1:02}", "開立已確認", f"TEST-{month:02}-{number}", "測試飲料店",
             "臺北市大安區測試路1號", f"{prefix}{number}", 1, 50] for number in range(count)]


class DeleteMonthTests(unittest.TestCase):
    def setUp(self):
        self.client = make_client()
        register(self.client, display_name="Amy")  # user 1
        self.headers = login(self.client)
        self.engine = self.client.app.state.engine

    def delete(self, month, headers=None):
        return self.client.delete(f"/api/me/months/{month}", headers=headers or self.headers)

    def profile(self):
        return self.client.get("/api/me/profile", headers=self.headers).json()

    def rows(self, table, **where):
        with Session(self.engine) as session:
            query = select(table)
            for key, value in where.items():
                query = query.where(getattr(table, key) == value)
            return session.exec(query).all()

    def hold_worker(self):
        """Keep the worker busy until the returned event is set, so whatever is queued after waits."""
        release = threading.Event()
        self.addCleanup(release.set)
        self.client.app.state.worker.call("held by the test", lambda: release.wait(timeout=5))
        return release

    def test_deleting_a_month_removes_it_and_works_the_profile_out_again(self):
        upload(self.client, self.headers, invoice_csv(teas(5, 15)))
        upload(self.client, self.headers, invoice_csv(teas(6, 15, "測試六月茶")))
        self.assertEqual((self.profile()["ready"], self.profile()["item_count"]), (True, 30))
        response = self.delete("2026-06")
        self.assertEqual((response.status_code, response.content), (204, b""))
        drain(self.client)
        body = self.profile()
        self.assertEqual((body["ready"], body["item_count"], list(body["months"])), (False, 15, ["2026-05"]))
        self.assertEqual(self.client.get("/api/me", headers=self.headers).json()["months"], ["2026-05"])
        self.assertEqual(self.client.get("/api/jobs/2", headers=self.headers).status_code, 404)

    def test_the_recompute_waits_on_the_worker_instead_of_the_request(self):
        upload(self.client, self.headers, invoice_csv(teas(5, 15)))
        upload(self.client, self.headers, invoice_csv(teas(6, 15, "測試六月茶")))
        release = self.hold_worker()
        self.assertEqual(self.delete("2026-06").status_code, 204)
        self.assertEqual(self.profile()["item_count"], 30)  # not worked out yet
        release.set()
        drain(self.client)
        self.assertEqual(self.profile()["item_count"], 15)

    def test_deleting_the_last_month_leaves_an_empty_profile(self):
        upload(self.client, self.headers, invoice_csv(teas(5, 25)))
        self.delete("2026-05")
        drain(self.client)
        body = self.profile()
        self.assertEqual((body["ready"], body["item_count"], body["areas"], body["months"]), (False, 0, [], {}))

    def test_an_unknown_month_is_404_and_a_badly_written_one_422(self):
        upload(self.client, self.headers, invoice_csv(teas(5, 3)))
        self.assertEqual((self.delete("2026-09").status_code, self.delete("2026-09").json()), (404, {"detail": "month_not_found"}))
        for month in ("2026-13", "2026-00", "202605", "2026-5", "abcd-ef", "2026-05-01"):
            with self.subTest(month=month):
                self.assertEqual(self.delete(month).status_code, 422)
        self.assertEqual(len(self.rows(Item, user_id=1)), 3)

    def test_a_queued_or_running_job_of_that_month_is_409_but_another_months_job_is_not(self):
        upload(self.client, self.headers, invoice_csv(teas(5, 3)))
        upload(self.client, self.headers, invoice_csv(teas(6, 3, "測試六月茶")))
        for status in ("queued", "running"):
            with self.subTest(status=status):
                with Session(self.engine) as session:
                    job = session.exec(select(Job).where(Job.month == "2026-05")).one()
                    job.status = status
                    session.add(job)
                    session.add(Job(user_id=1, month="2026-07", status=status))
                    session.commit()
                response = self.delete("2026-05")
                self.assertEqual((response.status_code, response.json()), (409, {"detail": "job_in_progress"}))
                self.assertEqual(len(self.rows(Item, user_id=1, month="2026-05")), 3)
                with Session(self.engine) as session:
                    for job in session.exec(select(Job).where(Job.month == "2026-07")).all():
                        session.delete(job)
                    job = session.exec(select(Job).where(Job.month == "2026-05")).one()
                    job.status = "done"
                    session.add(job)
                    session.commit()
        with Session(self.engine) as session:
            session.add(Job(user_id=1, month="2026-07", status="running"))
            session.commit()
        self.assertEqual(self.delete("2026-06").status_code, 204)

    def test_only_the_answers_nothing_else_uses_are_dropped_and_other_users_keep_their_month(self):
        register(self.client, username="ben", display_name="Ben")
        upload(self.client, self.headers, invoice_csv(teas(5, 2, "測試五月茶") + teas(5, 1, "測試共用茶")[0:1]))
        upload(self.client, self.headers, invoice_csv(teas(6, 1, "測試共用茶")))
        upload(self.client, login(self.client, username="ben"), invoice_csv(teas(5, 1, "測試班的茶")))
        self.delete("2026-05")
        drain(self.client)
        self.assertEqual({row.name for row in self.rows(ItemCache)}, {"測試共用茶0", "測試班的茶0"})
        self.assertEqual([row.name for row in self.rows(Item, user_id=2)], ["測試班的茶0"])

    def test_an_account_deleted_before_its_recompute_runs_is_no_error(self):
        upload(self.client, self.headers, invoice_csv(teas(5, 3)))
        upload(self.client, self.headers, invoice_csv(teas(6, 3, "測試六月茶")))
        release = self.hold_worker()
        self.assertEqual(self.delete("2026-06").status_code, 204)
        self.assertEqual(self.client.request("DELETE", "/api/me", json={"password": "password123"},
                                             headers=self.headers).status_code, 204)
        with self.assertNoLogs("src.api.jobs", level="ERROR"):
            release.set()
            drain(self.client)
        self.assertEqual((self.rows(User), self.rows(Profile)), ([], []))

    def test_explain_draws_what_the_items_give_now_while_the_cells_wait_for_the_recompute(self):
        register(self.client, username="ben", display_name="Ben")
        upload(self.client, self.headers, invoice_csv(teas(5, 20) + teas(5, 10, "測試五月奶茶")))
        upload(self.client, self.headers, invoice_csv(teas(6, 25, "測試六月茶")))
        upload(self.client, login(self.client, username="ben"), invoice_csv(teas(5, 30)))
        release = self.hold_worker()
        self.assertEqual(self.delete("2026-06").status_code, 204)
        body = self.client.get("/api/matches/2/explain", headers=self.headers).json()
        stored = [cell["mine"] for cell in body["cells"]]
        drawn = body["network"]["mine"]
        self.assertTrue(body["comparable"])
        self.assertNotEqual(drawn["vector"], stored)  # the graph already shows May alone; the cells wait
        for trait, (value, pushes) in enumerate(zip(drawn["vector"], drawn["pushes"], strict=True)):
            if value is not None:  # trait-network.js validate: the pushes add up to the value
                self.assertAlmostEqual(sum(push or 0 for push in pushes), value, delta=0.001, msg=trait)
        release.set()
        drain(self.client)
        body = self.client.get("/api/matches/2/explain", headers=self.headers).json()
        self.assertEqual(body["network"]["mine"]["vector"], [cell["mine"] for cell in body["cells"]])

    def test_explain_draws_nothing_for_me_once_my_last_month_is_gone(self):
        register(self.client, username="ben", display_name="Ben")
        upload(self.client, self.headers, invoice_csv(teas(5, 25)))
        upload(self.client, login(self.client, username="ben"), invoice_csv(teas(5, 25)))
        release = self.hold_worker()
        self.delete("2026-05")
        body = self.client.get("/api/matches/2/explain", headers=self.headers).json()
        self.assertTrue(body["comparable"])  # the stored vector is still there
        self.assertEqual(body["network"]["mine"], {"vector": None, "pushes": None, "signals": None, "items": None})
        release.set()
        drain(self.client)
        body = self.client.get("/api/matches/2/explain", headers=self.headers).json()
        self.assertEqual((body["comparable"], body["reason"]), (False, "not_enough_items"))

    def test_demo_users_cannot_delete_a_month(self):
        client = make_client(demo_mode=True)
        with Session(client.app.state.engine) as session:
            session.add(User(username="demo_001", display_name="Mia", is_demo=True, persona="咖啡上班族"))
            session.commit()
        demo = {"Authorization": "Bearer " + client.post("/api/auth/demo-login", json={"user_id": 1}).json()["access_token"]}
        response = client.delete("/api/me/months/2026-05", headers=demo)
        self.assertEqual((response.status_code, response.json()), (403, {"detail": "demo_user_read_only"}))

    def test_it_needs_a_valid_token(self):
        response = self.client.delete("/api/me/months/2026-05")
        self.assertEqual((response.status_code, response.json()), (401, {"detail": "not_authenticated"}))


if __name__ == "__main__":
    unittest.main()

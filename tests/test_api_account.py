"""Account management (overview 5.11): see and rename the account, change the password, log out, delete it."""
import json
import unittest
from unittest import mock

from sqlmodel import Session, select

from src.api import accounts
from src.api.tables import Item, ItemCache, Job, Profile, User
from tests.api_support import commit_a_job, file_client, invoice_csv, login, make_client, register, upload
from tests.test_matching import ME, scoring

ACCOUNT_KEYS = {"user_id", "username", "display_name", "is_demo", "months"}


def month_of(month, names):
    """A fictional month with one 50-dollar bill per name."""
    return [[f"2026{month:02}{number % 28 + 1:02}", "開立已確認", f"TEST-{month:02}-{number}", "測試飲料店",
             "臺北市大安區測試路1號", name, 1, 50] for number, name in enumerate(names)]


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.client = make_client()
        register(self.client, display_name="Amy")  # user 1
        self.headers = login(self.client)
        self.engine = self.client.app.state.engine

    def rows(self, table, **where):
        with Session(self.engine) as session:
            query = select(table)
            for key, value in where.items():
                query = query.where(getattr(table, key) == value)
            return session.exec(query).all()

    def set_profile(self, user_id, vector):
        with Session(self.engine) as session:
            session.merge(Profile(user_id=user_id, vector=json.dumps(vector), areas="[]", item_count=30))
            session.commit()

    def me(self, headers=None):
        return self.client.get("/api/me", headers=headers or self.headers)

    def test_every_account_endpoint_needs_a_valid_token(self):
        calls = [("GET", "/api/me", None), ("PATCH", "/api/me", {"display_name": "X"}),
                 ("POST", "/api/me/password", {"current_password": "password123", "new_password": "password456"}),
                 ("DELETE", "/api/me", {"password": "password123"}), ("POST", "/api/auth/logout", None)]
        for method, path, body in calls:
            with self.subTest(method=method, path=path):
                response = self.client.request(method, path, json=body)
                self.assertEqual((response.status_code, response.json()), (401, {"detail": "not_authenticated"}))

    def test_the_account_shows_its_names_and_months_oldest_first_and_no_password(self):
        upload(self.client, self.headers, invoice_csv(month_of(8, ["測試茶"])))
        upload(self.client, self.headers, invoice_csv(month_of(7, ["測試茶"])))
        response = self.me()
        self.assertEqual(response.json(), {"user_id": 1, "username": "amy", "display_name": "Amy", "is_demo": False,
                                           "months": ["2026-07", "2026-08"]})
        self.assertNotIn("password", response.text)
        self.assertNotIn("argon2", response.text)

    def test_a_new_display_name_is_what_others_see_in_their_match_list(self):
        register(self.client, username="ben", display_name="Ben")
        self.set_profile(1, scoring(0.6))
        self.set_profile(2, ME)
        response = self.client.patch("/api/me", json={"display_name": "  愛喝咖啡的人 "}, headers=self.headers)
        self.assertEqual((response.status_code, response.json()["display_name"]), (200, "愛喝咖啡的人"))
        self.assertEqual(set(response.json()), ACCOUNT_KEYS)
        [person] = self.client.get("/api/matches", headers=login(self.client, username="ben")).json()["people"]
        self.assertEqual(person["display_name"], "愛喝咖啡的人")

    def test_a_bad_display_name_is_422_and_the_name_stays(self):
        for name in ("茶" * 21, "", "   ", chr(0x200B), "a" + chr(10) + "b", 7):
            with self.subTest(name=name):
                response = self.client.patch("/api/me", json={"display_name": name}, headers=self.headers)
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.me().json()["display_name"], "Amy")
        self.assertEqual(self.client.patch("/api/me", json={"display_name": "茶" * 20}, headers=self.headers).status_code, 200)

    def test_the_username_cannot_be_changed(self):
        response = self.client.patch("/api/me", json={"display_name": "Amy2", "username": "bob"}, headers=self.headers)
        self.assertEqual((response.status_code, response.json()["username"]), (200, "amy"))

    def test_a_new_password_gives_a_working_token_and_ends_every_old_one(self):
        other_device = login(self.client)
        response = self.client.post("/api/me/password", json={"current_password": "password123",
                                                                "new_password": "0123456789"}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"access_token", "token_type", "expires_in"})
        fresh = {"Authorization": "Bearer " + response.json()["access_token"]}
        for old in (self.headers, other_device):
            self.assertEqual(self.client.get("/api/matches", headers=old).status_code, 401)
        self.assertEqual(self.client.get("/api/matches", headers=fresh).status_code, 200)
        self.assertEqual(self.client.post("/api/auth/login", data={"username": "amy", "password": "password123"}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", data={"username": "amy", "password": "0123456789"}).status_code, 200)

    def test_a_wrong_current_password_is_403_and_changes_nothing(self):
        response = self.client.post("/api/me/password", json={"current_password": "wrong-password",
                                                                "new_password": "0123456789"}, headers=self.headers)
        self.assertEqual((response.status_code, response.json()), (403, {"detail": "wrong_password"}))
        self.assertEqual(self.me().status_code, 200)  # the old token still works
        self.assertEqual(self.client.post("/api/auth/login", data={"username": "amy", "password": "password123"}).status_code, 200)

    def test_a_new_password_of_7_or_129_characters_is_422_without_echoing_it(self):
        for password in ("short77", "x" * 129):
            with self.subTest(length=len(password)):
                response = self.client.post("/api/me/password", json={"current_password": "password123",
                                                                        "new_password": password}, headers=self.headers)
                self.assertEqual(response.status_code, 422)
                self.assertNotIn(password, response.text)

    def test_logging_out_ends_every_device_and_a_new_login_works(self):
        phone, computer = login(self.client), login(self.client)
        response = self.client.post("/api/auth/logout", headers=computer)
        self.assertEqual((response.status_code, response.content), (204, b""))
        for old in (phone, computer, self.headers):
            self.assertEqual(self.client.get("/api/matches", headers=old).status_code, 401)
        again = login(self.client)
        self.assertEqual(self.client.get("/api/matches", headers=again).status_code, 200)
        self.assertEqual(self.client.get("/api/matches", headers=phone).status_code, 401)

    def test_deleting_the_account_removes_everything_and_its_tokens(self):
        register(self.client, username="ben", display_name="Ben")
        ben = login(self.client, username="ben")
        upload(self.client, self.headers, invoice_csv(month_of(5, ["測試茶"])))
        self.set_profile(1, scoring(0.6))
        self.set_profile(2, ME)
        self.assertEqual([person["user_id"] for person in self.client.get("/api/matches", headers=ben).json()["people"]], [1])
        response = self.client.request("DELETE", "/api/me", json={"password": "password123"}, headers=self.headers)
        self.assertEqual((response.status_code, response.content), (204, b""))
        self.assertEqual([self.rows(table, user_id=1) for table in (Item, Job, Profile)], [[], [], []])
        self.assertEqual([user.username for user in self.rows(User)], ["ben"])
        self.assertEqual(self.me().status_code, 401)
        self.assertEqual(self.client.get("/api/matches", headers=ben).json()["people"], [])

    def test_a_wrong_password_deletes_nothing(self):
        response = self.client.request("DELETE", "/api/me", json={"password": "wrong-password"}, headers=self.headers)
        self.assertEqual((response.status_code, response.json()), (403, {"detail": "wrong_password"}))
        self.assertEqual(self.me().status_code, 200)

    def test_a_refused_delete_keeps_every_token_working(self):
        other_device = login(self.client)
        with Session(self.engine) as session:
            session.add(Job(user_id=1, month="2026-09", status="queued"))
            session.commit()
        response = self.client.request("DELETE", "/api/me", json={"password": "password123"}, headers=self.headers)
        self.assertEqual((response.status_code, response.json()), (409, {"detail": "job_in_progress"}))
        for headers in (self.headers, other_device):
            self.assertEqual(self.me(headers).status_code, 200)

    def test_an_upload_cannot_commit_its_job_between_the_check_and_the_delete(self):
        client, path = file_client(self)
        register(client)
        headers = login(client)
        busy, gap = accounts.busy, []

        def upload_in_the_gap(session, user_id, month=None):
            answer = busy(session, user_id, month)
            gap.append(commit_a_job(path, user_id, "2026-05"))
            return answer
        with mock.patch.object(accounts, "busy", side_effect=upload_in_the_gap):
            response = client.request("DELETE", "/api/me", json={"password": "password123"}, headers=headers)
        # The delete holds SQLite's write lock from before the check, so the upload waits for it to be done.
        self.assertEqual((response.status_code, gap), (204, ["locked"]))

    def test_an_upload_job_still_queued_or_running_is_409_and_deletes_nothing(self):
        for status in ("queued", "running"):
            with self.subTest(status=status):
                with Session(self.engine) as session:
                    session.add(Job(user_id=1, month="2026-09", status=status))
                    session.commit()
                response = self.client.request("DELETE", "/api/me", json={"password": "password123"}, headers=self.headers)
                self.assertEqual((response.status_code, response.json()), (409, {"detail": "job_in_progress"}))
                self.assertEqual(self.me().status_code, 200)
                with Session(self.engine) as session:
                    for job in session.exec(select(Job)).all():
                        session.delete(job)
                    session.commit()

    def test_deleting_the_account_keeps_the_answers_someone_else_still_needs(self):
        register(self.client, username="ben", display_name="Ben")
        upload(self.client, self.headers, invoice_csv(month_of(5, ["測試只有我買", "測試大家都買"])))
        upload(self.client, login(self.client, username="ben"), invoice_csv(month_of(5, ["測試大家都買"])))
        with Session(self.engine) as session:
            session.add(ItemCache(name="測試只查過", model="fake", fields="{}"))
            session.commit()
        self.client.request("DELETE", "/api/me", json={"password": "password123"}, headers=self.headers)
        self.assertEqual({row.name for row in self.rows(ItemCache)}, {"測試只查過", "測試大家都買"})

    def test_demo_users_cannot_change_or_delete_anything_but_can_log_out(self):
        client = make_client(demo_mode=True)
        with Session(client.app.state.engine) as session:
            session.add(User(username="demo_001", display_name="Mia", is_demo=True, persona="咖啡上班族"))
            session.commit()
        demo = {"Authorization": "Bearer " + client.post("/api/auth/demo-login", json={"user_id": 1}).json()["access_token"]}
        calls = [("PATCH", "/api/me", {"display_name": "X"}),
                 ("POST", "/api/me/password", {"current_password": "whatever1", "new_password": "password456"}),
                 ("DELETE", "/api/me", {"password": "whatever1"})]
        for method, path, body in calls:
            with self.subTest(method=method, path=path):
                response = client.request(method, path, json=body, headers=demo)
                self.assertEqual((response.status_code, response.json()), (403, {"detail": "demo_user_read_only"}))
        self.assertEqual(client.get("/api/me", headers=demo).json()["display_name"], "Mia")
        self.assertEqual(client.post("/api/auth/logout", headers=demo).status_code, 204)

    def test_a_demo_logout_leaves_the_personas_other_visitors_logged_in(self):
        """A demo persona is shared, so its logout only ends this browser's session: the page drops its token."""
        client = make_client(demo_mode=True)
        with Session(client.app.state.engine) as session:
            session.add(User(username="demo_001", display_name="Mia", is_demo=True, persona="咖啡上班族"))
            session.commit()
        def demo_login():
            token = client.post("/api/auth/demo-login", json={"user_id": 1}).json()["access_token"]
            return {"Authorization": "Bearer " + token}
        mine, theirs = demo_login(), demo_login()
        response = client.post("/api/auth/logout", headers=mine)
        self.assertEqual((response.status_code, response.content), (204, b""))
        self.assertEqual(client.get("/api/me", headers=theirs).status_code, 200)


if __name__ == "__main__":
    unittest.main()

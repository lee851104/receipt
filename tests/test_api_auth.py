"""Register, log in, and the demo quick switch that only fictional people can use."""
import unittest

from src.api.security import read_token
from src.api.seed import seed_demo_users
from tests.api_support import login, make_client, register

PEOPLE = [{"name": "咖啡上班族 A", "type": "咖啡上班族"}, {"name": "健身族 A", "type": "健身族"}]


class RegisterTests(unittest.TestCase):
    def test_register_answers_201_with_the_new_user(self):
        response = register(make_client(), display_name="Amy")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"user_id": 1, "username": "amy", "display_name": "Amy"})

    def test_the_display_name_defaults_to_the_username(self):
        self.assertEqual(register(make_client()).json()["display_name"], "amy")

    def test_a_taken_username_is_409(self):
        client = make_client()
        register(client)
        response = register(client, password="different-password")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"detail": "username_taken"})

    def test_bad_fields_are_422(self):
        for fields in ({"username": "am"}, {"username": "a" * 33}, {"username": "amy!"}, {"password": "short"},
                       {"password": "p" * 129}, {"display_name": "   "}, {"display_name": "名" * 21},
                       {"display_name": "\u200b"}, {"display_name": "\u202eymA"}, {"display_name": "a\nb"},
                       {"display_name": "a" + chr(0x2028) + "b"}, {"display_name": chr(0xE000)}):
            with self.subTest(fields=fields):
                self.assertEqual(register(make_client(), **fields).status_code, 422)

    def test_a_rejected_password_is_not_sent_back(self):
        response = register(make_client(), password="hunter2")
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("hunter2", response.text)
        self.assertEqual(response.json()["detail"][0]["loc"], ["body", "password"])

    def test_the_longest_and_shortest_allowed_values_are_accepted(self):
        for fields in ({"username": "abc"}, {"username": "a" * 32}, {"password": "p" * 8}, {"password": "p" * 128},
                       {"display_name": "名" * 20}):
            with self.subTest(fields=fields):
                self.assertEqual(register(make_client(), **fields).status_code, 201)

    def test_usernames_ignore_case(self):
        client = make_client()
        self.assertEqual(register(client, username="Amy").json()["username"], "amy")
        self.assertEqual(register(client, username="amy").status_code, 409)
        response = client.post("/api/auth/login", data={"username": "AMY", "password": "password123"})
        self.assertEqual(response.status_code, 200)


class LoginTests(unittest.TestCase):
    def test_login_answers_a_bearer_token_for_the_user(self):
        client = make_client()
        user_id = register(client).json()["user_id"]
        body = client.post("/api/auth/login", data={"username": "amy", "password": "password123"}).json()
        self.assertEqual((body["token_type"], body["expires_in"]), ("bearer", 86400))
        self.assertEqual(read_token(body["access_token"], client.app.state.settings)[0], user_id)

    def test_a_wrong_password_and_an_unknown_user_get_the_same_401(self):
        client = make_client()
        register(client)
        for form in ({"username": "amy", "password": "wrong-password"}, {"username": "bob", "password": "password123"}):
            with self.subTest(form=form):
                response = client.post("/api/auth/login", data=form)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "bad_credentials"})
                self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_a_password_matches_however_its_letters_were_composed(self):
        client = make_client()
        register(client, password="caf\u00e9-1234")  # é as one character
        response = client.post("/api/auth/login", data={"username": "amy", "password": "cafe\u0301-1234"})  # e + accent
        self.assertEqual(response.status_code, 200)

    def test_the_longest_allowed_password_logs_in(self):
        client = make_client()
        register(client, password="p" * 128)
        response = client.post("/api/auth/login", data={"username": "amy", "password": "p" * 128})
        self.assertEqual(response.status_code, 200)

    def test_the_helper_headers_work(self):
        client = make_client()
        register(client)
        self.assertTrue(login(client)["Authorization"].startswith("Bearer "))


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.client = make_client(demo_mode=True)
        seed_demo_users(self.client.app.state.engine, PEOPLE)
        self.real_id = register(self.client).json()["user_id"]

    def test_without_demo_mode_the_demo_endpoints_do_not_exist(self):
        client = make_client()
        self.assertEqual(client.get("/api/auth/demo-users").status_code, 404)
        self.assertEqual(client.post("/api/auth/demo-login", json={"user_id": 1}).status_code, 404)
        paths = client.get("/openapi.json").json()["paths"]
        self.assertNotIn("/api/auth/demo-users", paths)
        self.assertNotIn("/api/auth/demo-login", paths)

    def test_demo_users_lists_only_the_fictional_people(self):
        self.assertEqual(self.client.get("/api/auth/demo-users").json(), [
            {"user_id": 1, "display_name": "咖啡上班族 A", "persona": "咖啡上班族"},
            {"user_id": 2, "display_name": "健身族 A", "persona": "健身族"}])

    def test_demo_login_gives_a_fictional_person_a_working_token(self):
        body = self.client.post("/api/auth/demo-login", json={"user_id": 2}).json()
        self.assertEqual(read_token(body["access_token"], self.client.app.state.settings)[0], 2)
        self.assertEqual((body["token_type"], body["expires_in"]), ("bearer", 86400))
        response = self.client.post("/api/items/classify", json={"name": "鮮奶茶"},
                                    headers={"Authorization": "Bearer " + body["access_token"]})
        self.assertEqual(response.status_code, 200)

    def test_demo_login_refuses_ids_that_are_not_plain_database_ids(self):
        for user_id in (0, -1, 2**63, True, "2", 2.0):
            with self.subTest(user_id=user_id):
                response = self.client.post("/api/auth/demo-login", json={"user_id": user_id})
                self.assertEqual(response.status_code, 422)

    def test_demo_login_refuses_real_accounts_and_unknown_ids(self):
        real = self.client.post("/api/auth/demo-login", json={"user_id": self.real_id})
        self.assertEqual((real.status_code, real.json()), (403, {"detail": "not_demo_user"}))
        unknown = self.client.post("/api/auth/demo-login", json={"user_id": 99})
        self.assertEqual((unknown.status_code, unknown.json()), (404, {"detail": "not_found"}))

    def test_registering_cannot_make_a_demo_user(self):
        user_id = register(self.client, username="sneaky", is_demo=True, persona="咖啡上班族").json()["user_id"]
        response = self.client.post("/api/auth/demo-login", json={"user_id": user_id})
        self.assertEqual((response.status_code, response.json()), (403, {"detail": "not_demo_user"}))
        self.assertEqual(len(self.client.get("/api/auth/demo-users").json()), len(PEOPLE))

    def test_a_fictional_person_cannot_log_in_with_a_password(self):
        response = self.client.post("/api/auth/login", data={"username": "demo_001", "password": "password123"})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

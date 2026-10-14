"""Register, log in, and the demo quick switch that only fictional people can use."""
import unittest

from src.api.security import read_token
from tests.api_support import login, make_client, register


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
                       {"password": "p" * 129}, {"display_name": "   "}, {"display_name": "名" * 21}):
            with self.subTest(fields=fields):
                self.assertEqual(register(make_client(), **fields).status_code, 422)


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

    def test_the_helper_headers_work(self):
        client = make_client()
        register(client)
        self.assertTrue(login(client)["Authorization"].startswith("Bearer "))


if __name__ == "__main__":
    unittest.main()

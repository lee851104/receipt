"""POST /api/items/classify needs a login and answers the category and attributes of one name."""
import json
import unittest

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.api.security import create_token
from src.api.tables import User
from src.ml.fields import FIELDS
from tests.api_support import login, make_client, register


class ClassifyTests(unittest.TestCase):
    def client_and_headers(self, **backend_changes):
        client = make_client(**backend_changes)
        register(client)
        return client, login(client)

    def test_classify_needs_a_valid_token(self):
        client = make_client()
        ghost = create_token(User(id=99, username="ghost", display_name="Ghost"), client.app.state.settings)
        for headers in ({}, {"Authorization": "Bearer not.a.token"}, {"Authorization": "Bearer " + ghost}):
            with self.subTest(headers=headers):
                response = client.post("/api/items/classify", json={"name": "鮮奶茶"}, headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "not_authenticated"})
                self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_a_deleted_accounts_token_does_not_work_for_the_next_account_with_its_id(self):
        client, old = self.client_and_headers()
        with Session(client.app.state.engine) as session:
            session.delete(session.exec(select(User).where(User.username == "amy")).one())
            session.commit()
        self.assertEqual(register(client, username="bob").json()["user_id"], 1)  # SQLite gave amy's id to bob
        self.assertEqual(client.post("/api/items/classify", json={"name": "鮮奶茶"}, headers=old).status_code, 401)
        bob = login(client, username="bob")
        self.assertEqual(client.post("/api/items/classify", json={"name": "鮮奶茶"}, headers=bob).status_code, 200)

    def test_classify_answers_the_category_probabilities_and_attributes(self):
        client, headers = self.client_and_headers()
        body = client.post("/api/items/classify", json={"name": "  鮮奶茶 微糖 "}, headers=headers).json()
        self.assertEqual(body["name"], "鮮奶茶 微糖")
        self.assertEqual(body["category"], {"id": 1, "name": "飲品", "prob": 0.9})
        self.assertEqual(len(body["probs"]), 10)
        self.assertEqual(body["attributes"], dict.fromkeys(FIELDS))
        self.assertEqual(body["attributes_status"], "ready")

    def test_a_hundred_characters_fit_and_ids_follow_the_report_categories(self):
        client, headers = self.client_and_headers()
        long_name = client.post("/api/items/classify", json={"name": " " + "茶" * 100 + " "}, headers=headers)
        self.assertEqual(long_name.status_code, 200)
        body = client.post("/api/items/classify", json={"name": "衛生紙"}, headers=headers).json()
        self.assertEqual(body["category"], {"id": 8, "name": "日用品", "prob": 0.9})

    def test_a_name_the_attribute_model_has_not_seen_is_pending(self):
        client, headers = self.client_and_headers(describe_items=lambda names, ask_model=True: [None for _ in names])
        body = client.post("/api/items/classify", json={"name": "鮮奶茶"}, headers=headers).json()
        self.assertEqual((body["attributes"], body["attributes_status"]), (None, "pending"))

    def test_the_classify_box_only_reads_the_cache(self):
        asked = []
        client, headers = self.client_and_headers(
            describe_items=lambda names, ask_model=True: asked.append(ask_model) or [None for _ in names])
        client.post("/api/items/classify", json={"name": "鮮奶茶"}, headers=headers)
        self.assertEqual(asked, [False])

    def test_a_crashing_model_still_answers_json(self):
        app = make_client(classify=lambda names: 1 / 0).app
        client = TestClient(app, raise_server_exceptions=False)
        register(client)
        response = client.post("/api/items/classify", json={"name": "鮮奶茶"}, headers=login(client))
        self.assertEqual((response.status_code, response.json()), (500, {"detail": "internal_error"}))

    def test_an_empty_too_long_or_unreadable_name_is_422(self):
        client, headers = self.client_and_headers()
        for name in ("", "   ", "茶" * 101, "a" + chr(10) + "b", chr(0x200B), chr(0), chr(0xD800)):
            with self.subTest(code_points=[hex(ord(char)) for char in name[:3]], length=len(name)):
                # json.dumps writes every character as an ASCII escape, so even a lone surrogate can be sent.
                response = client.post("/api/items/classify", content=json.dumps({"name": name}),
                                       headers={**headers, "Content-Type": "application/json"})
                self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

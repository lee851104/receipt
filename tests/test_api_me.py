"""GET /api/me/profile: the logged-in user's taste profile and uploaded months, as the last upload job stored them."""
import json
import unittest

from sqlmodel import Session

from src.api.db import ROOT
from src.api.tables import ItemCache, Profile, User
from src.ml.fields import FIELDS
from src.receipt.build import trait_words
from src.receipt.traits import load_context
from tests.api_support import invoice_csv, login, make_client, register, upload

CONTEXT = load_context(ROOT)
TRAIT_IDS = [trait["id"] for trait in CONTEXT["traits"]["traits"]]
# A stand-in Qwen with no GPU: it cannot judge any name now, so every name stays pending.
NO_GPU = {"attributes": "qwen", "describe_items": lambda names, ask_model=True: [None] * len(names)}


def month_of(month, names):
    """A fictional month with one 50-dollar bill per name, each on its own day."""
    return [[f"2026{month:02}{number % 28 + 1:02}", "開立已確認", f"TEST-{month:02}-{number}", "測試飲料店",
             "臺北市大安區測試路1號", name, 1, 50] for number, name in enumerate(names)]


def many_teas(count):
    """Names the fake classifier is sure about (a 茶), so every line of the month is a valid item."""
    return [f"測試茶{number}" for number in range(count)]


class MyProfileTests(unittest.TestCase):
    def setUp(self):
        self.client = make_client()
        register(self.client, display_name="Amy")
        self.headers = login(self.client)

    def profile(self, headers=None):
        response = self.client.get("/api/me/profile", headers=headers or self.headers)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_it_needs_a_valid_token(self):
        for headers in ({}, {"Authorization": "Bearer not.a.token"}):
            with self.subTest(headers=headers):
                response = self.client.get("/api/me/profile", headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "not_authenticated"})
                self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_someone_who_has_not_uploaded_yet_is_not_ready(self):
        body = self.profile()
        self.assertEqual({key: body[key] for key in ("user_id", "display_name", "is_demo", "ready", "item_count",
                                                     "min_items", "pending_attributes", "areas", "months",
                                                     "recomputing")},
                         {"user_id": 1, "display_name": "Amy", "is_demo": False, "ready": False, "item_count": 0,
                          "min_items": 20, "pending_attributes": 0, "areas": [], "months": {}, "recomputing": False})
        self.assertEqual([trait["value"] for trait in body["traits"]], [None] * 18)

    def test_the_traits_are_the_18_of_the_match_page_in_order_each_with_a_value(self):
        traits = self.profile()["traits"]
        self.assertEqual([trait["id"] for trait in traits], TRAIT_IDS)
        self.assertEqual(len(traits), 18)
        self.assertEqual(traits, [{**word, "value": None} for word in trait_words(CONTEXT["traits"])])
        by_id = {trait["id"]: trait for trait in traits}
        self.assertEqual(by_id["spend"], {"id": "spend", "name": "省錢 ↔ 享受", "kind": "two_sided",
                                          "ends": ["省錢", "享受"], "value": None})
        self.assertEqual(by_id["sport"], {"id": "sport", "name": "運動投入", "kind": "level", "habit": "運動",
                                          "value": None})
        self.assertEqual(by_id["pets_cat"]["group"], "有養寵物")

    def test_the_categories_are_the_eleven_of_the_report_with_their_colors(self):
        categories = self.profile()["categories"]
        self.assertEqual(len(categories), 11)
        self.assertEqual([categories[0], categories[-1]], [{"name": "正餐", "color": "#df646b"},
                                                           {"name": "待確認", "color": "#b5b5b5"}])
        self.assertTrue(all(set(category) == {"name", "color"} for category in categories))

    def test_a_month_with_too_few_items_shows_the_month_but_no_values(self):
        upload(self.client, self.headers, invoice_csv(month_of(5, ["鮮奶茶", "測試餅乾", "衛生紙"])))
        body = self.profile()
        self.assertEqual((body["ready"], body["item_count"]), (False, 3))  # fewer than the 20 items a vector needs
        self.assertEqual([trait["value"] for trait in body["traits"]], [None] * 18)
        self.assertEqual(body["areas"], ["臺北市大安區"])
        self.assertEqual(list(body["months"]), ["2026-05"])
        month = body["months"]["2026-05"]
        self.assertEqual({key: month[key] for key in ("year", "monthNumber", "month", "days")},
                         {"year": 2026, "monthNumber": 5, "month": "2026 年 5 月", "days": 31})
        self.assertEqual([row["name"] for row in month["rows"]], ["鮮奶茶", "測試餅乾", "衛生紙"])
        self.assertEqual(set(month["rows"][0]), {"day", "invoice", "merchant", "district", "name", "quantity",
                                                 "amount", "category", "provisional"})
        self.assertEqual((month["rows"][0]["day"], month["rows"][0]["district"], month["rows"][0]["amount"]),
                         (1, "臺北市大安區", 50))

    def test_enough_items_give_the_stored_vector_with_every_value_in_its_range(self):
        upload(self.client, self.headers, invoice_csv(month_of(5, many_teas(25))))
        body = self.profile()
        self.assertEqual((body["ready"], body["item_count"], body["min_items"]), (True, 25, 20))
        self.assertEqual(len(body["traits"]), 18)
        with Session(self.client.app.state.engine) as session:
            stored = json.loads(session.get(Profile, 1).vector)
        # Read as stored: the request never works the vector out again.
        self.assertEqual([trait["value"] for trait in body["traits"]], stored)
        values = {trait["id"]: trait["value"] for trait in body["traits"]}
        self.assertTrue(any(value is not None for value in values.values()))  # drinks alone say little, not nothing
        for trait in body["traits"]:
            value = trait["value"]  # None stays where the data is thin
            if value is not None:
                low = -1 if trait["kind"] == "two_sided" else 0
                self.assertTrue(low <= value <= 1, f"{trait['id']} is {value}")

    def test_each_value_goes_to_the_trait_at_its_place_in_the_vector(self):
        vector = [round(number / 20, 2) for number in range(18)]
        with Session(self.client.app.state.engine) as session:
            session.add(Profile(user_id=1, vector=json.dumps(vector), areas=json.dumps(["臺北市大安區", "新北市板橋區"]),
                                item_count=57))
            session.commit()
        body = self.profile()
        self.assertEqual((body["ready"], body["item_count"], body["areas"]), (True, 57, ["臺北市大安區", "新北市板橋區"]))
        self.assertEqual({trait["id"]: trait["value"] for trait in body["traits"]}, dict(zip(TRAIT_IDS, vector)))

    def test_a_profile_without_a_vector_is_not_ready_whatever_its_count(self):
        with Session(self.client.app.state.engine) as session:
            session.add(Profile(user_id=1, vector=None, areas="[]", item_count=19))
            session.commit()
        body = self.profile()
        self.assertEqual((body["ready"], body["item_count"]), (False, 19))
        self.assertEqual([trait["value"] for trait in body["traits"]], [None] * 18)

    def test_months_come_from_the_stored_items_by_date(self):
        upload(self.client, self.headers, invoice_csv(month_of(6, ["鮮奶茶", "衛生紙"])))
        upload(self.client, self.headers, invoice_csv(month_of(5, ["測試餅乾"])))
        months = self.profile()["months"]
        self.assertEqual(list(months), ["2026-05", "2026-06"])
        self.assertEqual((months["2026-06"]["monthNumber"], months["2026-06"]["days"]), (6, 30))
        self.assertEqual([row["name"] for row in months["2026-06"]["rows"]], ["鮮奶茶", "衛生紙"])

    def test_uploading_a_month_again_replaces_its_rows_in_the_answer(self):
        upload(self.client, self.headers, invoice_csv(month_of(5, ["鮮奶茶", "衛生紙"])))
        upload(self.client, self.headers, invoice_csv(month_of(5, ["測試餅乾"])))
        body = self.profile()
        self.assertEqual([row["name"] for row in body["months"]["2026-05"]["rows"]], ["測試餅乾"])
        self.assertEqual(body["item_count"], 1)

    def test_nothing_of_another_user_appears(self):
        register(self.client, username="ben", display_name="Ben")
        ben = login(self.client, username="ben")
        upload(self.client, self.headers, invoice_csv(month_of(5, ["鮮奶茶", "衛生紙"])))
        upload(self.client, ben, invoice_csv(month_of(5, many_teas(25))))
        upload(self.client, ben, invoice_csv(month_of(6, ["測試餅乾"])))
        amy, other = self.profile(), self.profile(ben)
        self.assertEqual((amy["user_id"], amy["display_name"], amy["item_count"]), (1, "Amy", 2))
        self.assertEqual((other["user_id"], other["display_name"], other["item_count"]), (2, "Ben", 26))
        self.assertEqual((amy["ready"], other["ready"]), (False, True))
        self.assertEqual(list(amy["months"]), ["2026-05"])
        self.assertEqual([row["name"] for row in amy["months"]["2026-05"]["rows"]], ["鮮奶茶", "衛生紙"])
        self.assertEqual(list(other["months"]), ["2026-05", "2026-06"])

    def test_a_demo_user_has_no_profile_until_the_seed_gives_it_one(self):
        client = make_client(demo_mode=True)
        with Session(client.app.state.engine) as session:
            session.add(User(username="demo_001", display_name="Mia", is_demo=True, persona="咖啡上班族"))
            session.commit()
        token = client.post("/api/auth/demo-login", json={"user_id": 1}).json()["access_token"]
        body = client.get("/api/me/profile", headers={"Authorization": "Bearer " + token}).json()
        self.assertEqual((body["user_id"], body["display_name"], body["is_demo"]), (1, "Mia", True))
        self.assertEqual((body["ready"], body["item_count"], body["months"]), (False, 0, {}))


class PendingAttributesTests(unittest.TestCase):
    """pending_attributes: how many distinct product names of the user's the current attribute model has no answer
    for yet, which the page tells the user is still being analysed."""

    def setUp(self):
        self.client = make_client(**NO_GPU)
        register(self.client, display_name="Amy")
        self.headers = login(self.client)

    def pending(self, headers=None):
        return self.client.get("/api/me/profile", headers=headers or self.headers).json()["pending_attributes"]

    def test_without_a_gpu_every_new_name_counts_once(self):
        # 滷肉飯 is a meal the fake classifier is unsure of: it stays out of item_count but still waits for attributes.
        upload(self.client, self.headers, invoice_csv(month_of(5, ["鮮奶茶", "滷肉飯", "鮮奶茶", "衛生紙"])))
        body = self.client.get("/api/me/profile", headers=self.headers).json()
        self.assertEqual((body["pending_attributes"], body["item_count"]), (3, 3))

    def test_a_name_answered_for_the_current_model_stops_counting_but_another_models_answer_does_not(self):
        upload(self.client, self.headers, invoice_csv(month_of(5, ["鮮奶茶", "滷肉飯", "衛生紙"])))
        self.assertEqual(self.pending(), 3)
        fields = json.dumps(dict.fromkeys(FIELDS))
        with Session(self.client.app.state.engine) as session:
            session.add_all([ItemCache(name="鮮奶茶", model="qwen", fields=fields),
                             ItemCache(name="衛生紙", model="fake", fields=fields)])
            session.commit()
        self.assertEqual(self.pending(), 2)

    def test_answers_of_another_version_are_not_used(self):
        client = make_client(attributes="qwen", attributes_version="v2", gpu_probe=lambda: False,
                             describe_items=lambda names, ask_model=True: [None] * len(names))
        register(client)
        headers = login(client)
        fields = json.dumps(dict.fromkeys(FIELDS))
        with Session(client.app.state.engine) as session:
            # One name answered by an older version, one by the current version: only the second counts as judged.
            session.add_all([ItemCache(name="測試奶茶", model="v1", fields=fields),
                             ItemCache(name="測試新品", model="v2", fields=fields)])
            session.commit()
        upload(client, headers, invoice_csv(month_of(5, ["測試奶茶", "測試新品"])))
        self.assertEqual(client.get("/api/me/profile", headers=headers).json()["pending_attributes"], 1)

    def test_the_request_never_asks_the_model_even_when_it_could_answer(self):
        asked, answering = [], []

        def describe_items(names, ask_model=True):
            asked.append(names)
            return [dict.fromkeys(FIELDS) if answering else None for _ in names]
        client = make_client(attributes="qwen", gpu_probe=lambda: True, describe_items=describe_items)
        register(client)
        headers = login(client)
        upload(client, headers, invoice_csv(month_of(5, ["鮮奶茶"])))  # the model could not answer during the job
        asked.clear()
        answering.append(True)  # from now on it would, if it were asked
        for _ in range(2):
            self.assertEqual(client.get("/api/me/profile", headers=headers).json()["pending_attributes"], 1)
        self.assertEqual(asked, [])

    def test_only_the_names_of_the_user_count(self):
        register(self.client, username="ben")
        ben = login(self.client, username="ben")
        upload(self.client, self.headers, invoice_csv(month_of(5, ["鮮奶茶", "衛生紙"])))
        upload(self.client, ben, invoice_csv(month_of(5, ["鮮奶茶", "測試餅乾", "測試新品"])))
        self.assertEqual((self.pending(), self.pending(ben)), (2, 3))

    def test_with_the_fake_model_every_name_is_judged_so_none_is_pending(self):
        client = make_client()
        register(client)
        headers = login(client)
        upload(client, headers, invoice_csv(month_of(5, ["鮮奶茶", "測試新品"])))
        self.assertEqual(client.get("/api/me/profile", headers=headers).json()["pending_attributes"], 0)


if __name__ == "__main__":
    unittest.main()

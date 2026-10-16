"""GET /api/matches/{user_id}/explain: one score taken apart cell by cell, and the network graph of the two people."""
import json
import unittest

from sqlmodel import Session, select

from src.api.db import ROOT
from src.api.tables import ItemCache, Profile, User
from src.ml.fields import FIELDS
from src.receipt.traits import load_context
from tests.api_support import invoice_csv, login, make_client, register, upload
from tests.test_matching import FIVE, ME, scoring

SETTINGS = load_context(ROOT)["traits"]
TRAITS = [(trait["id"], trait["name"], trait["kind"]) for trait in SETTINGS["traits"]]
TOTALS = ("dot", "norm_mine", "norm_theirs", "shrink", "denominator", "score", "percent")
NOTHING = {"vector": None, "pushes": None, "signals": None, "items": None}


def month(names, merchant="測試秘密商行", address="臺北市大安區測試路1號"):
    """A fictional May: 40 bills of 4321 dollars, one name each, cycling through names. A name loses the districts
    of its own buyer only (overview 5.8), so both people here shop in 大安."""
    return [[f"202605{number % 28 + 1:02}", "開立已確認", f"TEST-05-{number}", merchant, address,
             f"{names[number % len(names)]}{number % 3}", 1, 4321] for number in range(40)]


# Names the fake classifier files under drinks, snacks and daily goods; two carry a place name.
SHOPPING = ["大安測試奶茶", "測試便當", "臺中測試餅乾", "測試衛生紙", "測試咖啡", "測試啤酒", "測試貓飼料", "測試青菜"]


class ExplainTests(unittest.TestCase):
    def setUp(self):
        self.client = make_client()
        register(self.client, display_name="Amy")  # user 1, the one asking
        self.headers = login(self.client)
        self.engine = self.client.app.state.engine
        self.added = 0

    def set_profile(self, user_id, vector, areas=()):
        with Session(self.engine) as session:
            session.merge(Profile(user_id=user_id, vector=None if vector is None else json.dumps(vector),
                                  areas=json.dumps(list(areas)), item_count=5 if vector is None else 30))
            session.commit()

    def add_person(self, name, vector=None, is_demo=False):
        """Someone else, with a stored profile unless vector is None; returns their user id."""
        self.added += 1
        with Session(self.engine) as session:
            other = User(username=f"peer{self.added}", display_name=name, is_demo=is_demo)
            session.add(other)
            session.commit()
            user_id = other.id
        if vector is not None:
            self.set_profile(user_id, vector)
        return user_id

    def explain(self, user_id, status=200, headers=None):
        response = self.client.get(f"/api/matches/{user_id}/explain", headers=headers or self.headers)
        self.assertEqual(response.status_code, status, response.text)
        return response.json()

    def test_it_needs_a_valid_token(self):
        ben = self.add_person("Ben", scoring(0.6))
        response = self.client.get(f"/api/matches/{ben}/explain")
        self.assertEqual((response.status_code, response.json()), (401, {"detail": "not_authenticated"}))

    def test_asking_about_myself_is_400_and_about_nobody_is_404(self):
        self.set_profile(1, ME)
        self.assertEqual(self.explain(1, 400), {"detail": "self"})
        self.assertEqual(self.explain(999, 404), {"detail": "not_found"})
        for bad in ("0", "-1", "abc", str(2**63)):
            with self.subTest(user_id=bad):
                self.assertIsInstance(self.explain(bad, 422)["detail"], list)

    def test_the_18_cells_follow_the_traits_with_the_stored_values(self):
        self.set_profile(1, ME)
        ben = self.add_person("Ben", scoring(0.6))
        body = self.explain(ben)
        self.assertEqual((body["user_id"], body["display_name"], body["comparable"], body["reason"]), (ben, "Ben", True, None))
        self.assertEqual([(cell["id"], cell["name"], cell["kind"]) for cell in body["cells"]], TRAITS)
        self.assertEqual([cell["mine"] for cell in body["cells"]], ME)
        self.assertEqual([cell["theirs"] for cell in body["cells"]], scoring(0.6))
        self.assertEqual(set(body["cells"][0]), {"id", "name", "kind", "mine", "theirs", "weight", "shared", "product", "part"})
        self.assertEqual((body["shared_two_sided"], body["min_shared_two_sided"], body["shrink"]), (5, 5, 0.25))

    def test_the_parts_add_up_to_the_score_which_is_the_one_on_the_match_list(self):
        self.set_profile(1, ME, ["臺北市大安區"])
        ben = self.add_person("Ben", scoring(0.6))
        body = self.explain(ben)
        self.assertEqual(sum(cell["part"] for cell in body["cells"] if cell["part"] is not None), body["score"])
        [listed] = self.client.get("/api/matches", headers=self.headers).json()["people"]
        self.assertEqual((listed["score"], listed["percent"]), (body["score"], body["percent"]))
        self.assertAlmostEqual(body["score"], body["dot"] / body["denominator"], places=12)

    def test_anyone_can_be_explained_not_only_the_top_five(self):
        self.set_profile(1, ME)
        people = [self.add_person(f"P{number}", scoring(0.4 + number / 20)) for number in range(7)]
        self.add_person("Opposite", scoring(-0.5))
        listed = [person["user_id"] for person in self.client.get("/api/matches", headers=self.headers).json()["people"]]
        for user_id in [*people, people[0]]:
            self.assertEqual(self.explain(user_id)["comparable"], True)
        self.assertNotIn(people[0], listed)

    def test_too_few_shared_cells_give_a_reason_and_no_numbers(self):
        self.set_profile(1, ME)
        four = scoring(0.6)
        four[FIVE[4]] = None
        ben = self.add_person("Ben", four)
        body = self.explain(ben)
        self.assertEqual((body["comparable"], body["reason"], body["shared_two_sided"]), (False, "too_few_shared", 4))
        self.assertEqual({key: body[key] for key in TOTALS}, dict.fromkeys(TOTALS))
        self.assertTrue(all(cell["product"] is None and cell["part"] is None for cell in body["cells"]))

    def test_too_little_data_on_either_side_is_not_enough_items(self):
        ben = self.add_person("Ben", scoring(0.6))
        nobody = self.add_person("Nobody")  # never uploaded
        for user_id, mine in ((ben, None), (nobody, ME)):
            with self.subTest(user_id=user_id):
                if mine is not None:
                    self.set_profile(1, mine)
                body = self.explain(user_id)
                self.assertEqual((body["comparable"], body["reason"]), (False, "not_enough_items"))
                self.assertEqual({key: body[key] for key in TOTALS}, dict.fromkeys(TOTALS))
                self.assertEqual(len(body["cells"]), 18)
        self.assertEqual(self.explain(nobody)["network"]["theirs"], NOTHING)

    def test_a_demo_session_cannot_see_a_real_user_but_a_real_user_can_see_demo_users(self):
        client = make_client(demo_mode=True)
        register(client, display_name="Amy")  # user 1, real
        with Session(client.app.state.engine) as session:
            session.add(User(username="demo_001", display_name="Mia", is_demo=True, persona="咖啡上班族"))
            session.add(User(username="demo_002", display_name="Leo", is_demo=True, persona="咖啡上班族"))
            session.commit()
        demo = {"Authorization": "Bearer " + client.post("/api/auth/demo-login", json={"user_id": 2}).json()["access_token"]}
        response = client.get("/api/matches/1/explain", headers=demo)
        self.assertEqual((response.status_code, response.json()), (404, {"detail": "not_found"}))
        self.assertEqual(client.get("/api/matches/3/explain", headers=demo).status_code, 200)
        self.assertEqual(client.get("/api/matches/2/explain", headers=login(client)).status_code, 200)

    def test_the_network_draws_both_people_from_their_purchases(self):
        register(self.client, username="ben", display_name="Ben")
        ben = login(self.client, username="ben")
        upload(self.client, self.headers, invoice_csv(month(SHOPPING)))
        upload(self.client, ben, invoice_csv(month(SHOPPING[::-1], merchant="測試另一間", address="臺北市大安區測試路2號")))
        body = self.explain(2)
        self.assertTrue(body["comparable"])
        network = body["network"]
        self.assertEqual(set(network), {"model", "traits", "signals", "readout", "mine", "theirs"})
        for side, cells_key in (("mine", "mine"), ("theirs", "theirs")):
            with self.subTest(side=side):
                drawing = network[side]
                self.assertEqual(set(drawing), {"vector", "pushes", "signals", "items"})
                self.assertEqual(drawing["vector"], [cell[cells_key] for cell in body["cells"]])
                self.assertEqual(len(drawing["signals"]), len(network["signals"]))
        names = [name for lists in network["theirs"]["items"] if lists for name, _ in lists]
        self.assertTrue(names)
        self.assertTrue(any(name.startswith("測試奶茶") for name in names))  # 大安 taken out

    def test_nothing_in_the_answer_tells_where_when_or_how_much(self):
        register(self.client, username="ben", display_name="Ben")
        ben = login(self.client, username="ben")
        upload(self.client, self.headers, invoice_csv(month(SHOPPING)))
        upload(self.client, ben, invoice_csv(month(SHOPPING, merchant="測試另一間", address="臺北市大安區測試路2號")))
        text = self.client.get("/api/matches/2/explain", headers=self.headers).text
        # Amounts cannot be searched for as text: the signals carry averages such as the mean bill. Every purchase
        # entry is [name, number of bills], and the names below are the ones that must not show.
        for secret in ("測試秘密商行", "測試另一間", "測試路", "TEST-05", "2026-05-R", "大安", "臺中", "20260501"):
            self.assertNotIn(secret, text)

    def test_the_location_signals_list_no_purchases(self):
        upload(self.client, self.headers, invoice_csv(month(SHOPPING)))
        register(self.client, username="ben", display_name="Ben")
        upload(self.client, login(self.client, username="ben"), invoice_csv(month(SHOPPING)))
        network = self.explain(2)["network"]
        hidden = [index for index, signal in enumerate(network["signals"]) if signal.get("list_items") is False]
        self.assertTrue(hidden)
        for side in ("mine", "theirs"):
            self.assertEqual([network[side]["items"][index] for index in hidden], [None] * len(hidden))

    def test_explaining_never_asks_the_attribute_model(self):
        asked = []

        def describe_items(names, ask_model=True):
            asked.append(list(names))
            return [dict.fromkeys(FIELDS) for _ in names]
        client = make_client(attributes="qwen", gpu_probe=lambda: True, describe_items=describe_items)
        register(client, display_name="Amy")
        register(client, username="ben", display_name="Ben")
        upload(client, login(client), invoice_csv(month(SHOPPING)))
        upload(client, login(client, username="ben"), invoice_csv(month(SHOPPING)))
        # The uploads have the names judged and cached, which would hide a model asked for what is missing: leave
        # every name uncached, so that an explain which asked the model would have to.
        with Session(client.app.state.engine) as session:
            judged = session.exec(select(ItemCache)).all()
            self.assertTrue(judged)
            for row in judged:
                session.delete(row)
            session.commit()
            self.assertEqual(session.exec(select(ItemCache)).all(), [])
        asked.clear()
        self.assertEqual(client.get("/api/matches/2/explain", headers=login(client)).status_code, 200)
        self.assertEqual(asked, [])


if __name__ == "__main__":
    unittest.main()

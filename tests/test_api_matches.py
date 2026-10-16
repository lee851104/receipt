"""GET /api/matches: the people closest to my taste, or most opposite, scored now from everyone's stored profile."""
import json
import unittest

from fastapi.testclient import TestClient
from sqlmodel import Session

from src.api.tables import Item, Profile, User
from tests.api_support import invoice_csv, login, make_client, register, upload
from tests.test_matching import FIVE, ME, scoring

LIST_KEYS = {"kind", "scope", "ready", "my_areas", "eligible", "within", "people"}
PERSON_KEYS = {"user_id", "display_name", "score", "percent", "area", "distance"}


def ids(body):
    return [person["user_id"] for person in body["people"]]


class MatchListTests(unittest.TestCase):
    def setUp(self):
        self.client = make_client()
        register(self.client, display_name="Amy")  # user 1, the one asking
        self.headers = login(self.client)
        self.engine = self.client.app.state.engine
        self.added = 0

    def set_profile(self, user_id, vector, areas=()):
        """Store a profile as an upload job would: vector None means too few items for one."""
        with Session(self.engine) as session:
            session.merge(Profile(user_id=user_id, vector=None if vector is None else json.dumps(vector),
                                  areas=json.dumps(list(areas)), item_count=5 if vector is None else 30))
            session.commit()

    def add_person(self, name, vector, areas=(), is_demo=False):
        """Someone else with a stored profile; returns their user id."""
        self.added += 1
        with Session(self.engine) as session:
            other = User(username=f"peer{self.added}", display_name=name, is_demo=is_demo)
            session.add(other)
            session.commit()
            user_id = other.id
        self.set_profile(user_id, vector, areas)
        return user_id

    def matches(self, status=200, **params):
        response = self.client.get("/api/matches", params=params, headers=self.headers)
        self.assertEqual(response.status_code, status, response.text)
        return response.json()

    def test_it_needs_a_valid_token(self):
        for headers in ({}, {"Authorization": "Bearer not.a.token"}):
            with self.subTest(headers=headers):
                response = self.client.get("/api/matches", headers=headers)
                self.assertEqual((response.status_code, response.json()), (401, {"detail": "not_authenticated"}))
                self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_someone_who_has_not_uploaded_yet_gets_an_empty_list_whatever_the_scope(self):
        self.add_person("Ben", scoring(0.6), ["臺北市大安區"])
        for scope in ("all", "district", "city", "region"):
            with self.subTest(scope=scope):
                self.assertEqual(self.matches(scope=scope), {
                    "kind": "similar", "scope": scope, "ready": False, "my_areas": [],
                    "eligible": 0, "within": 0, "people": []})

    def test_too_few_items_of_my_own_is_not_ready_but_still_shows_my_home_districts(self):
        self.set_profile(1, None, ["臺北市大安區"])
        self.add_person("Ben", scoring(-0.6), ["臺北市大安區"])
        self.assertEqual(self.matches(kind="opposite", scope="district"), {
            "kind": "opposite", "scope": "district", "ready": False, "my_areas": ["臺北市大安區"],
            "eligible": 0, "within": 0, "people": []})

    def test_the_defaults_are_similar_people_at_any_distance(self):
        self.set_profile(1, ME, ["臺北市大安區"])
        ben = self.add_person("Ben", scoring(0.6), ["臺北市信義區"])
        body = self.matches()
        self.assertEqual({key: body[key] for key in LIST_KEYS - {"people"}}, {
            "kind": "similar", "scope": "all", "ready": True, "my_areas": ["臺北市大安區"], "eligible": 1, "within": 1})
        [person] = body["people"]
        self.assertEqual({key: person[key] for key in PERSON_KEYS - {"score"}}, {
            "user_id": ben, "display_name": "Ben", "percent": 60, "area": "臺北市信義區", "distance": 1})
        self.assertAlmostEqual(person["score"], 0.6)

    def test_an_unknown_kind_or_scope_is_422(self):
        self.set_profile(1, ME, ["臺北市大安區"])
        for params in ({"kind": "close"}, {"kind": "Similar"}, {"scope": "nearby"}, {"scope": "ALL"}):
            with self.subTest(params=params):
                body = self.matches(422, **params)
                self.assertIsInstance(body["detail"], list)

    def test_without_a_home_district_only_any_distance_works(self):
        self.set_profile(1, ME, [])
        ben = self.add_person("Ben", scoring(0.6), ["臺北市信義區"])
        for kind in ("similar", "opposite"):
            for scope in ("district", "city", "region"):
                with self.subTest(kind=kind, scope=scope):
                    self.assertEqual(self.matches(400, kind=kind, scope=scope), {"detail": "no_home_area"})
        [person] = self.matches()["people"]
        self.assertEqual((person["user_id"], person["area"], person["distance"]), (ben, "臺北市信義區", None))

    def test_only_the_top_five_show_but_eligible_and_within_count_all_eight(self):
        self.set_profile(1, ME, ["臺北市大安區"])
        eight = [self.add_person(f"P{number}", scoring(0.31 + number / 100), ["臺北市大安區"]) for number in range(8)]
        self.add_person("Low", scoring(0.2), ["臺北市大安區"])
        body = self.matches()
        self.assertEqual((body["eligible"], body["within"]), (8, 8))
        self.assertEqual(ids(body), eight[::-1][:5])
        scores = [person["score"] for person in body["people"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_equal_scores_go_by_display_name_then_user_id(self):
        self.set_profile(1, ME)
        first_amy = self.add_person("amy", scoring(0.5))
        bob = self.add_person("Bob", scoring(0.5))
        second_amy = self.add_person("amy", scoring(0.5))
        coffee = self.add_person("咖啡", scoring(0.5))
        self.assertEqual(ids(self.matches()), [bob, first_amy, second_amy, coffee])

    def test_four_scopes_narrow_the_list_but_never_change_a_score(self):
        self.set_profile(1, ME, ["臺北市大安區"])
        same = self.add_person("Same", scoring(0.5), ["臺北市大安區"])
        city = self.add_person("City", scoring(0.6), ["臺北市信義區"])
        region = self.add_person("Region", scoring(0.7), ["新北市板橋區"])
        far = self.add_person("Far", scoring(0.8), ["高雄市苓雅區"])
        nowhere = self.add_person("Nowhere", scoring(0.9), [])
        lists = {scope: self.matches(scope=scope) for scope in ("all", "district", "city", "region")}
        expected = {"all": [nowhere, far, region, city, same], "district": [same], "city": [city, same],
                    "region": [region, city, same]}
        for scope, chosen in expected.items():
            with self.subTest(scope=scope):
                self.assertEqual(ids(lists[scope]), chosen)
                self.assertEqual((lists[scope]["eligible"], lists[scope]["within"]), (5, len(chosen)))
        everyone = {person["user_id"]: person for person in lists["all"]["people"]}
        for body in lists.values():
            for person in body["people"]:
                self.assertEqual(person, everyone[person["user_id"]])
        self.assertEqual({user_id: (person["area"], person["distance"]) for user_id, person in everyone.items()}, {
            same: ("臺北市大安區", 0), city: ("臺北市信義區", 1), region: ("新北市板橋區", 2),
            far: ("高雄市苓雅區", 3), nowhere: (None, None)})

    def test_opposite_lists_the_most_opposite_first_and_never_among_the_similar(self):
        self.set_profile(1, ME)
        mild = self.add_person("Mild", scoring(-0.12))
        strong = self.add_person("Strong", scoring(-0.42))
        self.add_person("Faint", scoring(-0.05))
        alike = self.add_person("Alike", scoring(0.6))
        body = self.matches(kind="opposite")
        self.assertEqual((ids(body), body["people"][0]["percent"], body["eligible"]), ([strong, mild], -42, 2))
        self.assertEqual(ids(self.matches()), [alike])

    def test_a_score_just_under_0_3_that_prints_as_30_percent_is_listed(self):
        self.set_profile(1, ME)
        edge = self.add_person("Edge", scoring(0.297))
        self.add_person("Under", scoring(0.294))  # +29%
        [person] = self.matches()["people"]
        self.assertEqual((person["user_id"], person["percent"]), (edge, 30))
        self.assertLess(person["score"], 0.3)

    def test_people_without_a_vector_or_with_too_few_shared_cells_are_left_out_and_never_myself(self):
        self.set_profile(1, ME)
        self.add_person("Thin", None)
        four = scoring(0.6)
        four[FIVE[4]] = None  # only four shared two-sided cells
        self.add_person("Four", four)
        twin = self.add_person("Twin", list(ME))
        body = self.matches()
        self.assertEqual((ids(body), body["eligible"]), ([twin], 1))

    def test_demo_users_are_matched_too(self):
        self.set_profile(1, ME)
        demo = self.add_person("咖啡上班族 C", scoring(0.6), is_demo=True)
        self.assertEqual(ids(self.matches()), [demo])

    def test_the_list_shows_nothing_of_theirs_but_id_name_area_distance_and_score(self):
        self.set_profile(1, ME, ["臺北市大安區"])
        ben = self.add_person("Ben", scoring(0.6), ["臺北市信義區"])
        with Session(self.engine) as session:
            session.add(Item(user_id=ben, month="2026-05", day=7, invoice="2026-05-R07", merchant="測試秘密商行",
                             district="臺北市信義區", name="測試秘密餅乾", quantity=1, amount=4321, category=1))
            session.commit()
        response = self.client.get("/api/matches", headers=self.headers)
        self.assertEqual(set(response.json()), LIST_KEYS)
        self.assertEqual(set(response.json()["people"][0]), PERSON_KEYS)
        for secret in ("測試秘密商行", "2026-05-R07", "測試秘密餅乾", "4321", "2026-05"):
            self.assertNotIn(secret, response.text)

    def test_a_stored_vector_of_another_length_is_a_500_not_a_wrong_score(self):
        self.set_profile(1, ME)
        self.add_person("Old", scoring(0.6)[:-1])  # stored before a trait was added
        client = TestClient(self.client.app, raise_server_exceptions=False)
        response = client.get("/api/matches", headers=self.headers)
        self.assertEqual((response.status_code, response.json()), (500, {"detail": "internal_error"}))

    def test_an_upload_with_enough_items_makes_me_ready(self):
        teas = [[f"202605{number % 28 + 1:02}", "開立已確認", f"TEST-05-{number}", "測試飲料店",
                 "臺北市大安區測試路1號", f"測試茶{number}", 1, 50] for number in range(25)]
        upload(self.client, self.headers, invoice_csv(teas))
        body = self.matches(scope="district")
        self.assertEqual((body["ready"], body["my_areas"], body["eligible"], body["people"]),
                         (True, ["臺北市大安區"], 0, []))


if __name__ == "__main__":
    unittest.main()

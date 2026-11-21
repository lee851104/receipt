"""The dating app's API under /api/dating: profiles, the quiz, photos, cards, likes, matches, chat, blocking and
reporting, and who may see whom."""
import json
import unittest
from datetime import date
from pathlib import Path

from sqlmodel import Session, select

from src.api import dating
from src.api.routes.dating import Throttle
from src.api.tables import Block, DatingProfile, Match, Message, Photo, Profile, Report, Swipe, User
from tests.api_support import login, make_client, register

YEAR = date.today().year
# Two-sided traits sit at indexes 0-5, 8, 9, 12 and 13; the rest are habits from 0 to 1.
TWO_SIDED = (0, 1, 2, 3, 4, 5, 8, 9, 12, 13)


def taste(lean, habits=0.0):
    """A vector leaning `lean` on every two-sided trait, with every habit at `habits`."""
    return [lean if index in TWO_SIDED else habits for index in range(18)]


def jpeg(width=64, height=48, exif=True):
    """A small JPEG put together by hand: its structure is all the server reads, so the picture itself is noise."""
    def segment(marker, payload):
        return bytes((0xFF, marker)) + (len(payload) + 2).to_bytes(2, "big") + payload
    parts = [b"\xff\xd8", segment(0xE0, b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")]
    if exif:
        parts.append(segment(0xE1, b"Exif\x00\x00GPS 25.03N 121.56E secret-camera"))
    parts += [segment(0xDB, b"\x00" + bytes(range(64))),
              segment(0xC0, b"\x08" + height.to_bytes(2, "big") + width.to_bytes(2, "big") + b"\x01\x01\x11\x00"),
              segment(0xC4, b"\x00" + bytes(16) + b"\x00"),
              segment(0xFE, b"a comment"),
              segment(0xDA, b"\x01\x01\x00\x00\x3f\x00"), b"\x12\x34\xff\x00\x56\xff\xd0\x78", b"\xff\xd9"]
    return b"".join(parts)


class DatingTestCase(unittest.TestCase):
    demo_mode = False

    def setUp(self):
        self.client = make_client(demo_mode=self.demo_mode)
        self.engine = self.client.app.state.engine
        register(self.client, display_name="Amy")  # user 1
        self.headers = login(self.client)
        self.count = 0

    def api(self, method, path, status=200, headers=None, **kwargs):
        response = self.client.request(method, "/api/dating" + path, headers=headers or self.headers, **kwargs)
        self.assertEqual(response.status_code, status, response.text)
        return response.json() if response.content else None

    def set_me(self, **changes):
        fields = {"birth_year": YEAR - 28, "gender": "female", "interested_in": ["male"], "city": "臺北市"}
        return self.api("PATCH", "/me", json={**fields, **changes})

    def quiz(self, lean=0.5, headers=None):
        return self.api("PUT", "/me/quiz", json={"answers": taste(lean)}, headers=headers)

    def ready_me(self, lean=0.5, **changes):
        self.set_me(**changes)
        return self.quiz(lean)

    def person(self, vector=None, demo=False, gender="male", wants=("female",), age=30, city="臺北市", discoverable=True,
               quiz=None, name=None, age_range=(18, 99)):
        """Someone else on the dating app, straight into the tables; vector is their invoice taste."""
        self.count += 1
        with Session(self.engine) as session:
            user = User(username=f"{'demo_' if demo else 'peer'}{self.count:03}", display_name=name or f"P{self.count}",
                        is_demo=demo, persona="咖啡上班族" if demo else None)
            session.add(user)
            session.commit()
            session.refresh(user)
            if vector is not None:
                session.add(Profile(user_id=user.id, vector=json.dumps(vector), item_count=40))
            session.add(DatingProfile(user_id=user.id, birth_year=YEAR - age, gender=gender,
                                      interested_in=json.dumps(list(wants)), city=city, discoverable=discoverable,
                                      quiz=None if quiz is None else json.dumps(quiz), age_min=age_range[0],
                                      age_max=age_range[1]))
            session.commit()
            return user.id

    def headers_for(self, user_id):
        """A login for a person made with person(): give them a password first."""
        from src.api.security import hash_password
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            user.password_hash = hash_password("password123")
            session.add(user)
            session.commit()
            username = user.username
        return login(self.client, username)

    def card_ids(self, **params):
        return [card["user_id"] for card in self.api("GET", "/discover", params=params)["cards"]]


class MetaAndProfileTests(DatingTestCase):
    def test_the_word_lists_need_no_login(self):
        response = self.client.get("/api/dating/meta")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([trait["id"] for trait in body["traits"]][:3], ["spend", "meals", "motive"])
        self.assertEqual(len(body["traits"]), 18)
        self.assertEqual(len(body["quiz"]["questions"]) + len(body["quiz"]["habits"]), 18)
        self.assertEqual(body["regions"][0]["region"], "北部")
        self.assertIn("臺北市", body["regions"][0]["cities"])
        self.assertFalse(body["demo_mode"])

    def test_a_new_account_needs_a_birth_year_gender_and_whom_to_meet(self):
        me = self.api("GET", "/me")
        self.assertEqual((me["has_profile"], me["ready"], me["profile"]), (False, False, None))
        self.assertEqual(me["missing"], ["birth_year", "gender", "interested_in"])
        me = self.set_me(bio="喜歡咖啡\n也喜歡貓", intent="chat", emoji="☕", display_name="Amy L")
        self.assertEqual(me["missing"], [])
        self.assertFalse(me["ready"])  # no taste yet
        self.assertEqual(me["profile"]["age"], 28)
        self.assertEqual(me["profile"]["bio"], "喜歡咖啡\n也喜歡貓")
        self.assertEqual((me["name"], me["display_name"]), ("Amy L", "Amy L"))

    def test_fields_left_out_stay_and_null_clears_an_optional_one(self):
        self.set_me(intent="chat", emoji="☕")
        me = self.api("PATCH", "/me", json={"bio": "新的介紹", "intent": None})
        self.assertEqual((me["profile"]["bio"], me["profile"]["intent"], me["profile"]["emoji"]), ("新的介紹", None, "☕"))
        self.assertEqual(me["profile"]["gender"], "female")

    def test_bad_values_are_refused(self):
        cases = [({"birth_year": YEAR - 17}, "birth_year"), ({"gender": "robot"}, "gender"),
                 ({"interested_in": []}, "interested_in"), ({"interested_in": ["male", "male"]}, "interested_in"),
                 ({"city": "東京都"}, "city"), ({"intent": "marry_now"}, "intent"), ({"emoji": "🦄"}, "emoji"),
                 ({"gender": None}, "gender"), ({"age_min": 40, "age_max": 30}, "age_min")]
        for body, field in cases:
            with self.subTest(body=body):
                response = self.client.patch("/api/dating/me", json=body, headers=self.headers)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(response.json()["detail"], "invalid_profile")
                self.assertTrue(response.json()["message"].startswith(field))
        for body in ({"bio": "a​b"}, {"bio": "x" * 301}, {"unknown": 1}, {"birth_year": "1990"}, {"age_min": 17}):
            with self.subTest(body=body):
                self.assertEqual(self.client.patch("/api/dating/me", json=body, headers=self.headers).status_code, 422)

    def test_a_demo_user_cannot_change_a_shared_profile(self):
        client = make_client(demo_mode=True)
        with Session(client.app.state.engine) as session:
            session.add(User(username="demo_001", display_name="Mia", is_demo=True, persona="咖啡上班族"))
            session.commit()
        token = client.post("/api/auth/demo-login", json={"user_id": 1}).json()["access_token"]
        headers = {"Authorization": "Bearer " + token}
        for method, path, kwargs in (("PATCH", "/me", {"json": {"bio": "x"}}),
                                     ("PUT", "/me/quiz", {"json": {"answers": taste(0.5)}}),
                                     ("DELETE", "/me/photo", {})):
            with self.subTest(path=path):
                response = client.request(method, "/api/dating" + path, headers=headers, **kwargs)
                self.assertEqual((response.status_code, response.json()["detail"]), (403, "demo_user_read_only"))

    def test_everything_needs_a_login_but_the_word_lists_and_photos(self):
        for method, path in (("GET", "/me"), ("GET", "/discover"), ("GET", "/likes"), ("GET", "/matches"),
                             ("GET", "/summary"), ("POST", "/swipes"), ("POST", "/blocks")):
            with self.subTest(path=path):
                self.assertEqual(self.client.request(method, "/api/dating" + path).status_code, 401)


class QuizTests(DatingTestCase):
    def test_the_quiz_gives_a_taste_until_invoices_do(self):
        self.set_me()
        me = self.quiz(-0.5)
        self.assertTrue(me["ready"])
        self.assertEqual(me["taste"]["source"], "quiz")
        self.assertEqual(me["taste"]["vector"][0], -0.5)
        self.assertIn("省錢", me["taste"]["keywords"])
        with Session(self.engine) as session:
            session.add(Profile(user_id=1, vector=json.dumps(taste(0.4)), item_count=40))
            session.commit()
        me = self.api("GET", "/me")
        self.assertEqual((me["taste"]["source"], me["taste"]["vector"][0], me["taste"]["invoice_ready"]), ("invoice", 0.4, True))
        self.assertEqual(me["taste"]["quiz"][0], -0.5)  # kept for when invoices are gone again

    def test_answers_must_be_in_range_and_enough(self):
        too_few = [None] * 18
        too_few[0] = too_few[1] = 0.5
        out_of_range = taste(0.5)
        out_of_range[6] = -0.5  # a habit below 0
        for answers in (too_few, out_of_range, taste(0.5)[:17], [*taste(0.5)[:17], 2]):
            with self.subTest(answers=answers):
                response = self.client.put("/api/dating/me/quiz", json={"answers": answers}, headers=self.headers)
                self.assertEqual(response.status_code, 422, response.text)

    def test_quiz_rules(self):
        settings = self.client.app.state.context["traits"]
        config = self.client.app.state.dating
        self.assertEqual(dating.quiz_answers(taste(1), settings, config), taste(1.0))
        with self.assertRaises(ValueError):
            dating.quiz_answers([True] * 18, settings, config)
        with self.assertRaises(ValueError):
            dating.quiz_answers([float("nan")] * 18, settings, config)


class DiscoverTests(DatingTestCase):
    def test_cards_need_a_whole_profile_then_a_taste(self):
        response = self.client.get("/api/dating/discover", headers=self.headers)
        self.assertEqual((response.status_code, response.json()["detail"]), (409, "profile_incomplete"))
        self.set_me()
        response = self.client.get("/api/dating/discover", headers=self.headers)
        self.assertEqual((response.status_code, response.json()["detail"]), (409, "no_taste"))

    def test_only_people_who_fit_both_ways_and_are_not_answered_hidden_or_blocked(self):
        self.ready_me(0.5)
        fits = self.person(taste(0.6))
        self.person(taste(0.6), gender="female")                    # not whom I want
        self.person(taste(0.6), wants=("male",))                     # does not want me
        self.person(taste(0.6), age_range=(35, 50))                  # I am too young for them
        self.person(taste(0.6), discoverable=False)                  # hidden
        self.person(None)                                            # no taste
        self.person(taste(0.6), demo=True)                           # a demo person outside DEMO_MODE
        blocked = self.person(taste(0.6))
        blocker = self.person(taste(0.6))
        passed = self.person(taste(0.6))
        quizzed = self.person(None, quiz=taste(0.3))
        with Session(self.engine) as session:
            session.add(Block(user_id=1, target_id=blocked))
            session.add(Block(user_id=blocker, target_id=1))
            session.add(Swipe(user_id=1, target_id=passed, action="pass"))
            session.commit()
        self.assertEqual(sorted(self.card_ids()), sorted([fits, quizzed]))
        self.api("PATCH", "/me", json={"age_min": 31})
        self.assertEqual(self.card_ids(), [])  # both are 30

    def test_similar_goes_from_the_most_alike_and_opposite_from_the_most_opposite(self):
        self.ready_me(0.5)
        alike, middle, opposite = self.person(taste(0.7)), self.person(taste(0.1)), self.person(taste(-0.7))
        self.assertEqual(self.card_ids(), [alike, middle, opposite])
        self.assertEqual(self.card_ids(mode="opposite"), [opposite, middle, alike])
        cards = self.api("GET", "/discover")["cards"]
        self.assertEqual(cards[0]["band"]["tone"], "similar")
        self.assertEqual(cards[-1]["band"]["tone"], "opposite")
        self.assertGreater(cards[0]["percent"], 30)
        self.assertEqual(cards[0]["source"], "invoice")

    def test_a_card_tells_what_two_people_share_and_where_they_differ(self):
        self.ready_me(0.5)
        mixed = taste(0.6, habits=0.8)
        mixed[4] = -0.6  # sweet: I lean high, they lean low
        other = self.person(mixed)
        card = self.api("GET", "/discover")["cards"][0]
        self.assertEqual(card["user_id"], other)
        self.assertEqual(len(card["alike"]), 3)
        self.assertEqual(card["contrast"][0]["trait"], "sweet")
        self.assertEqual((card["contrast"][0]["mine"], card["contrast"][0]["theirs"]), ("高甜度", "低甜度"))
        self.assertNotIn("traits", card)  # the detail endpoint has the whole comparison
        detail = self.api("GET", f"/people/{other}")
        self.assertEqual(len(detail["traits"]), 18)
        self.assertEqual(detail["traits"][0], {"id": "spend", "mine": 0.5, "theirs": 0.6})
        parts = sum(row["part"] for row in detail["contributions"])
        self.assertAlmostEqual(parts, detail["percent"] / 100, delta=0.01)
        self.assertTrue(detail["icebreakers"])
        self.assertIsNone(detail["match_id"])

    def test_a_city_or_region_narrows_the_cards(self):
        self.ready_me(0.5)
        taipei, keelung, kaohsiung = (self.person(taste(0.6), city=city) for city in ("臺北市", "基隆市", "高雄市"))
        self.assertEqual(sorted(self.card_ids(scope="city")), [taipei])
        self.assertEqual(sorted(self.card_ids(scope="region")), sorted([taipei, keelung]))
        self.assertEqual(sorted(self.card_ids(scope="all")), sorted([taipei, keelung, kaohsiung]))
        self.api("PATCH", "/me", json={"city": None})
        response = self.client.get("/api/dating/discover", params={"scope": "city"}, headers=self.headers)
        self.assertEqual((response.status_code, response.json()["detail"]), (400, "no_city"))


class SwipeAndMatchTests(DatingTestCase):
    def test_two_likes_make_a_match_and_a_pass_does_not(self):
        self.ready_me(0.5)
        ben = self.person(taste(0.6))
        ben_headers = self.headers_for(ben)
        first = self.api("POST", "/swipes", json={"user_id": ben, "action": "like"})
        self.assertIsNone(first["match"])
        likes = self.api("GET", "/likes", headers=ben_headers)
        self.assertEqual([person["user_id"] for person in likes["people"]], [1])
        self.assertTrue(likes["people"][0]["liked_me"])
        second = self.api("POST", "/swipes", json={"user_id": 1, "action": "like"}, headers=ben_headers)
        self.assertEqual(second["match"]["person"]["user_id"], 1)
        match_id = second["match"]["match_id"]
        mine = self.api("GET", "/matches")["matches"]
        self.assertEqual([(match["match_id"], match["opened"]) for match in mine], [(match_id, False)])
        self.assertEqual(self.api("GET", "/summary")["new_matches"], 1)
        self.api("GET", f"/matches/{match_id}")
        self.assertEqual(self.api("GET", "/summary")["new_matches"], 0)
        self.assertEqual(self.api("GET", "/likes", headers=ben_headers)["people"], [])

    def test_a_match_made_by_both_likes_at_once_is_kept_once(self):
        """The two likes arrive together: the second one finds the match already written when it commits."""
        from unittest import mock
        from src.api.routes import dating as routes
        self.ready_me(0.5)
        ben = self.person(taste(0.6))
        with Session(self.engine) as session:
            session.add(Swipe(user_id=ben, target_id=1, action="like"))
            session.add(Match(low_id=1, high_id=ben))
            session.commit()
        real = routes.match_between
        calls = []

        def late(session, a, b):  # the first look sees no match yet, as when Ben's request had not committed
            calls.append(1)
            return None if len(calls) == 1 else real(session, a, b)
        with mock.patch.object(routes, "match_between", late):
            answer = self.api("POST", "/swipes", json={"user_id": ben, "action": "like"})
        self.assertEqual(answer["match"]["person"]["user_id"], ben)
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(Match)).all()), 1)
            self.assertEqual(session.get(Swipe, (1, ben)).action, "like")

    def test_a_like_never_reaches_someone_who_does_not_want_me(self):
        self.ready_me(0.5)
        only_men = self.person(taste(0.6), wants=("male",))
        self.api("POST", "/swipes", 404, json={"user_id": only_men, "action": "like"})
        with Session(self.engine) as session:  # a like left from before their wishes changed
            session.add(Swipe(user_id=only_men, target_id=1, action="like"))
            session.commit()
        self.assertEqual(self.api("GET", "/likes")["people"], [])

    def test_two_likes_committed_together_still_make_the_match(self):
        """Ben's like was written after my look but before my commit: the look after the commit finds it."""
        from unittest import mock
        from src.api.routes import dating as routes
        self.ready_me(0.5)
        ben = self.person(taste(0.6))
        real_get = Session.get
        state = {"hidden": True}

        def get(session, table, key, *args, **kwargs):
            if table is Swipe and key == (ben, 1) and state["hidden"]:
                state["hidden"] = False
                with Session(self.engine) as other:
                    other.add(Swipe(user_id=ben, target_id=1, action="like"))
                    other.commit()
                return None
            return real_get(session, table, key, *args, **kwargs)
        with mock.patch.object(Session, "get", get):
            answer = self.api("POST", "/swipes", json={"user_id": ben, "action": "like"})
        self.assertIsNotNone(answer["match"])
        del routes

    def test_emoji_built_with_joiners_are_fine_in_bios_and_messages(self):
        me = self.set_me(bio="一家人 👨‍👩‍👧 🏳️‍🌈")
        self.assertEqual(me["profile"]["bio"], "一家人 👨‍👩‍👧 🏳️‍🌈")
        self.api("PATCH", "/me", 422, json={"bio": "a​b"})

    def test_a_pass_can_be_taken_back(self):
        self.ready_me(0.5)
        ben = self.person(taste(0.6))
        self.api("POST", "/swipes", json={"user_id": ben, "action": "pass"})
        self.assertEqual(self.card_ids(), [])
        self.assertEqual(self.api("POST", "/swipes/reset"), {"reset": 1})
        self.assertEqual(self.card_ids(), [ben])

    def test_nobody_hidden_can_be_answered_and_nobody_answers_themselves(self):
        self.ready_me(0.5)
        hidden = self.person(taste(0.6), discoverable=False)
        for user_id, status in ((1, 400), (hidden, 404), (999, 404)):
            with self.subTest(user_id=user_id):
                self.api("POST", "/swipes", status, json={"user_id": user_id, "action": "like"})
        self.api("POST", "/swipes", 422, json={"user_id": hidden, "action": "superlike"})

    def test_chat_reads_and_marks_read(self):
        self.ready_me(0.5)
        ben = self.person(taste(0.6))
        ben_headers = self.headers_for(ben)
        self.api("POST", "/swipes", json={"user_id": ben, "action": "like"})
        match_id = self.api("POST", "/swipes", json={"user_id": 1, "action": "like"}, headers=ben_headers)["match"]["match_id"]
        sent = self.api("POST", f"/matches/{match_id}/messages", 201, json={"body": "  嗨！\n你好  "})
        self.assertEqual((sent["message"]["body"], sent["message"]["from_me"], sent["replies"]), ("嗨！\n你好", True, []))
        self.assertTrue(sent["message"]["created_at"].endswith("+00:00"))
        self.assertEqual(self.api("GET", "/summary", headers=ben_headers)["unread"], 1)
        read = self.api("GET", f"/matches/{match_id}/messages", headers=ben_headers)
        self.assertEqual([(m["body"], m["from_me"]) for m in read["messages"]], [("嗨！\n你好", False)])
        self.assertEqual(self.api("GET", "/summary", headers=ben_headers)["unread"], 0)
        self.assertEqual(self.api("GET", f"/matches/{match_id}/messages")["their_read"], sent["message"]["id"])
        later = self.api("POST", f"/matches/{match_id}/messages", 201, json={"body": "在嗎"}, headers=ben_headers)
        after = self.api("GET", f"/matches/{match_id}/messages", params={"after": sent["message"]["id"]})
        self.assertEqual([m["id"] for m in after["messages"]], [later["message"]["id"]])
        self.assertTrue(self.api("GET", "/matches")["matches"][0]["last_message"]["body"] == "在嗎")
        for body in ("", "   ", "x" * 501, "a\u0000b"):
            with self.subTest(body=body):
                self.api("POST", f"/matches/{match_id}/messages", 422, json={"body": body})
        stranger = self.person(taste(0.6))
        self.api("GET", f"/matches/{match_id}/messages", 404, headers=self.headers_for(stranger))

    def test_leaving_a_match_deletes_the_chat_but_keeps_the_answers(self):
        self.ready_me(0.5)
        ben = self.person(taste(0.6))
        ben_headers = self.headers_for(ben)
        self.api("POST", "/swipes", json={"user_id": ben, "action": "like"})
        match_id = self.api("POST", "/swipes", json={"user_id": 1, "action": "like"}, headers=ben_headers)["match"]["match_id"]
        self.api("POST", f"/matches/{match_id}/messages", 201, json={"body": "hi"})
        self.client.delete(f"/api/dating/matches/{match_id}", headers=self.headers)
        self.assertEqual(self.api("GET", "/matches", headers=ben_headers)["matches"], [])
        with Session(self.engine) as session:
            self.assertEqual(session.exec(select(Message)).all(), [])
            self.assertEqual(len(session.exec(select(Swipe)).all()), 2)
        self.assertEqual(self.card_ids(), [])  # still answered, so not shown again

    def test_too_many_messages_a_minute_are_refused(self):
        throttle, moment = Throttle(2, window=60), [0.0]
        clock = lambda: moment[0]
        self.assertEqual([throttle.allow(1, clock), throttle.allow(1, clock), throttle.allow(1, clock)], [True, True, False])
        self.assertTrue(throttle.allow(2, clock))
        moment[0] = 61
        self.assertTrue(throttle.allow(1, clock))


class SafetyTests(DatingTestCase):
    def setUp(self):
        super().setUp()
        self.ready_me(0.5)
        self.ben = self.person(taste(0.6))
        self.ben_headers = self.headers_for(self.ben)
        self.api("POST", "/swipes", json={"user_id": self.ben, "action": "like"})
        self.match_id = self.api("POST", "/swipes", json={"user_id": 1, "action": "like"},
                                 headers=self.ben_headers)["match"]["match_id"]
        self.api("POST", f"/matches/{self.match_id}/messages", 201, json={"body": "hi"})

    def test_blocking_ends_the_match_and_hides_both_ways(self):
        self.client.post("/api/dating/blocks", json={"user_id": self.ben}, headers=self.headers)
        self.assertEqual(self.api("GET", "/matches")["matches"], [])
        self.assertEqual(self.api("GET", "/matches", headers=self.ben_headers)["matches"], [])
        self.api("GET", f"/people/{self.ben}", 404)
        self.api("GET", "/people/1", 404, headers=self.ben_headers)
        self.api("GET", f"/matches/{self.match_id}/messages", 404)
        self.assertEqual(self.client.get(f"/api/matches/{self.ben}/explain", headers=self.headers).status_code, 404)
        self.api("POST", "/blocks", 400, json={"user_id": 1})

    def test_a_report_is_kept_and_blocks(self):
        response = self.client.post("/api/dating/reports", json={"user_id": self.ben, "reason": "scam", "note": "要我匯款"},
                                    headers=self.headers)
        self.assertEqual(response.status_code, 204)
        with Session(self.engine) as session:
            [report] = session.exec(select(Report)).all()
            self.assertEqual((report.reporter_id, report.target_id, report.reason, report.note), (1, self.ben, "scam", "要我匯款"))
            self.assertIsNotNone(session.get(Block, (1, self.ben)))
        self.api("POST", "/reports", 422, json={"user_id": self.ben, "reason": "dislike"})

    def test_deleting_an_account_deletes_its_dating_side(self):
        self.client.post("/api/dating/me/photo", files={"file": ("me.jpg", jpeg(), "image/jpeg")}, headers=self.headers)
        self.client.post("/api/dating/reports", json={"user_id": self.ben, "reason": "other"}, headers=self.headers)
        response = self.client.request("DELETE", "/api/me", json={"password": "password123"}, headers=self.headers)
        self.assertEqual(response.status_code, 204)
        with Session(self.engine) as session:
            for table in (Match, Message, Swipe, Block, Report, Photo):
                self.assertEqual(session.exec(select(table)).all(), [], table.__name__)
            self.assertIsNone(session.get(DatingProfile, 1))

    def test_purchases_stay_private_to_matches_on_the_old_explain_page(self):
        stranger = self.person(taste(0.6))
        with Session(self.engine) as session:
            session.merge(Profile(user_id=1, vector=json.dumps(taste(0.5)), item_count=40))
            session.commit()
        matched = self.client.get(f"/api/matches/{self.ben}/explain", headers=self.headers).json()
        unmatched = self.client.get(f"/api/matches/{stranger}/explain", headers=self.headers).json()
        self.assertFalse(matched["purchases_hidden"])
        self.assertTrue(unmatched["purchases_hidden"])
        paused = self.person(taste(0.6), discoverable=False)
        self.assertEqual(self.client.get(f"/api/matches/{paused}/explain", headers=self.headers).status_code, 404)

    def test_the_old_match_list_leaves_out_hidden_and_blocked_people(self):
        hidden = self.person(taste(0.6), discoverable=False)
        with Session(self.engine) as session:
            session.merge(Profile(user_id=1, vector=json.dumps(taste(0.5)), item_count=40))
            session.commit()
        listed = [person["user_id"] for person in self.client.get("/api/matches", headers=self.headers).json()["people"]]
        self.assertIn(self.ben, listed)
        self.assertNotIn(hidden, listed)
        self.client.post("/api/dating/blocks", json={"user_id": self.ben}, headers=self.headers)
        listed = [person["user_id"] for person in self.client.get("/api/matches", headers=self.headers).json()["people"]]
        self.assertNotIn(self.ben, listed)


class PhotoTests(DatingTestCase):
    def test_a_photo_is_kept_without_its_metadata_and_served_by_a_random_key(self):
        response = self.client.post("/api/dating/me/photo", files={"file": ("me.jpg", jpeg(), "image/jpeg")},
                                    headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        url = response.json()["profile"]["photo"]
        self.assertRegex(url, r"^/api/dating/photos/[0-9a-f]{32}$")
        served = self.client.get(url)
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served.headers["content-type"], "image/jpeg")
        self.assertEqual(served.headers["x-content-type-options"], "nosniff")
        self.assertNotIn(b"GPS", served.content)
        self.assertNotIn(b"a comment", served.content)
        self.assertEqual(served.content, jpeg(exif=False).replace(b"\xff\xfe\x00\x0ba comment", b""))
        again = self.client.post("/api/dating/me/photo", files={"file": ("me.jpg", jpeg(), "image/jpeg")},
                                 headers=self.headers).json()["profile"]["photo"]
        self.assertNotEqual(again, url)
        self.assertEqual(self.client.get(url).status_code, 404)  # the old address is gone
        removed = self.client.delete("/api/dating/me/photo", headers=self.headers).json()
        self.assertIsNone(removed["profile"]["photo"])
        self.assertEqual(self.client.get(again).status_code, 404)

    def test_only_a_whole_jpeg_of_a_sensible_size_is_taken(self):
        for data in (b"GIF89a", b"\xff\xd8\xff", jpeg()[:-2], jpeg(width=4000), b"\x89PNG\r\n\x1a\n" + bytes(40)):
            with self.subTest(data=data[:12]):
                response = self.client.post("/api/dating/me/photo", files={"file": ("x.jpg", data, "image/jpeg")},
                                            headers=self.headers)
                self.assertEqual((response.status_code, response.json()["detail"]), (400, "invalid_photo"))
        big = jpeg() + bytes(700_000)
        response = self.client.post("/api/dating/me/photo", files={"file": ("x.jpg", big, "image/jpeg")}, headers=self.headers)
        self.assertEqual(response.status_code, 413)

    def test_clean_jpeg_reports_the_size(self):
        cleaned, size = dating.clean_jpeg(jpeg(width=320, height=400), 2048)
        self.assertEqual(size, (320, 400))
        self.assertTrue(cleaned.startswith(b"\xff\xd8") and cleaned.endswith(b"\xff\xd9"))


class DemoTests(DatingTestCase):
    demo_mode = True

    def demo_session(self, user_id):
        token = self.client.post("/api/auth/demo-login", json={"user_id": user_id}).json()["access_token"]
        return {"Authorization": "Bearer " + token}

    def test_demo_people_like_back_answer_messages_and_never_meet_real_people(self):
        self.ready_me(0.5)
        mia = self.person(taste(0.6), demo=True)
        leo = self.person(taste(0.4), demo=True, gender="female", wants=("male", "female"))
        real = self.person(taste(0.6))
        self.assertEqual(sorted(self.card_ids()), sorted([mia, real]))
        match = self.api("POST", "/swipes", json={"user_id": mia, "action": "like"})["match"]
        self.assertIsNotNone(match)  # a clearly alike demo person always likes back
        sent = self.api("POST", f"/matches/{match['match_id']}/messages", 201, json={"body": "嗨"})
        self.assertEqual(len(sent["replies"]), 1)
        self.assertFalse(sent["replies"][0]["from_me"])
        self.assertEqual(self.api("GET", f"/matches/{match['match_id']}/messages")["their_read"], sent["replies"][0]["id"])
        # Someone using Mia's demo login sees demo people only: not Amy's match or messages, nor real cards.
        as_mia = self.demo_session(mia)
        self.assertEqual(self.api("GET", "/matches", headers=as_mia)["matches"], [])
        self.api("GET", "/people/1", 404, headers=as_mia)
        with Session(self.engine) as session:
            session.merge(DatingProfile(user_id=mia, birth_year=YEAR - 30, gender="female",
                                        interested_in=json.dumps(["female"]), city="臺北市"))
            session.commit()
        self.assertEqual(self.card_ids_for(as_mia), [leo])
        self.assertNotIn(real, self.card_ids_for(as_mia))

    def card_ids_for(self, headers):
        return [card["user_id"] for card in self.api("GET", "/discover", headers=headers)["cards"]]

    def test_a_new_real_person_gets_a_few_demo_likes_once(self):
        alike = [self.person(taste(0.5 + step / 10), demo=True) for step in range(3)]
        opposite = self.person(taste(-0.6), demo=True)
        self.ready_me(0.5)
        waiting = [person["user_id"] for person in self.api("GET", "/likes")["people"]]
        self.assertEqual(sorted(waiting), sorted([alike[1], alike[2], opposite]))  # the two most alike, the most opposite
        for user_id in waiting:
            self.api("POST", "/swipes", json={"user_id": user_id, "action": "pass"})
        self.assertEqual(self.api("GET", "/likes")["people"], [])
        self.assertEqual(self.api("GET", "/summary")["likes"], 0)

    def test_the_sample_invoices_exist_in_demo_mode_only_and_make_a_verified_taste(self):
        response = self.client.get("/api/dating/sample-invoices", params={"variant": 3})
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["content-disposition"])
        upload = self.client.post("/api/invoices", files={"file": ("sample.csv", response.content, "text/csv")}, headers=self.headers)
        self.assertEqual(upload.status_code, 202, upload.text)
        self.client.app.state.worker.queue.join()
        self.set_me()
        self.assertEqual(self.api("GET", "/me")["taste"]["source"], "invoice")
        self.assertEqual(make_client().get("/api/dating/sample-invoices").status_code, 404)

    def test_demo_users_get_a_dating_profile_of_their_own(self):
        with Session(self.engine) as session:
            session.add(User(username="demo_900", display_name="咖啡上班族 Z", is_demo=True, persona="咖啡上班族"))
            session.commit()
        self.ready_me(0.5)
        self.api("GET", "/discover")
        with Session(self.engine) as session:
            user = session.exec(select(User).where(User.username == "demo_900")).one()
            profile = session.get(DatingProfile, user.id)
            self.assertIsNotNone(profile)
            self.assertEqual(profile.emoji, "☕")
            self.assertIn(profile.gender, ("female", "male", "nonbinary"))
            again = dating.demo_profile(user, None, self.client.app.state.dating, self.client.app.state.regions)
            self.assertEqual((again["nickname"], again["gender"]), (profile.nickname, profile.gender))


class RuleTests(unittest.TestCase):
    def test_bands(self):
        config = {"bands": [{"min": 30, "label": "很合拍", "tone": "similar"}, {"min": -9, "label": "各有特色", "tone": "neutral"},
                            {"min": -100, "label": "互補", "tone": "opposite"}]}
        self.assertEqual([dating.band(value, config)["label"] for value in (80, 30, 29, 0, -9, -10, -100)],
                         ["很合拍", "很合拍", "各有特色", "各有特色", "各有特色", "互補", "互補"])
        self.assertEqual(dating.band(None, config)["tone"], "neutral")

    def test_ages_and_preferences(self):
        me = DatingProfile(user_id=1, gender="female", interested_in='["male"]', age_min=25, age_max=35)
        him = DatingProfile(user_id=2, gender="male", interested_in='["female"]', age_min=18, age_max=30)
        self.assertEqual(dating.age_of(2000, date(2026, 1, 1)), 26)
        self.assertTrue(dating.mutual(me, 28, him, 30))
        self.assertFalse(dating.mutual(me, 31, him, 30))  # I am older than he wants
        self.assertFalse(dating.mutual(me, 28, him, 36))  # he is older than I want
        self.assertEqual(dating.missing(None), ["birth_year", "gender", "interested_in"])

    def test_demo_replies_are_the_same_every_time(self):
        config = dating.load_config(Path(__file__).resolve().parents[1])
        found = {"alike": [{"line": "無糖派，清爽到底。"}], "contrast": []}
        first = dating.demo_reply(config, "嗨", 0, found, "Amy", 42, 7)
        self.assertEqual(first, dating.demo_reply(config, "嗨", 0, found, "Amy", 42, 7))
        self.assertIn(first, [template.format(name="Amy", percent="+42%") for template in config["demo"]["replies"]["opening"]])
        answer = dating.demo_reply(config, "你喜歡什麼？", 2, found, "Amy", 42, 7)
        self.assertIn(answer, config["demo"]["replies"]["question"])
        greeting, reply = dating.demo_reply(config, "嗨！你平常喝什麼？", 0, found, "Amy", 42, 7).split("\n")
        self.assertIn(greeting, [template.format(name="Amy", percent="+42%") for template in config["demo"]["replies"]["opening"]])
        self.assertIn(reply, config["demo"]["replies"]["question"])

    def test_openers_ask_about_the_side_each_person_is_on(self):
        config = dating.load_config(Path(__file__).resolve().parents[1])
        found = {"alike": [{"trait": "travel", "end": 0, "word": "待在生活圈"}, {"trait": "pets_cat", "word": "養貓"}],
                 "contrast": [{"trait": "sweet", "mine": "高甜度", "theirs": "低甜度", "their_end": 0}]}
        lines = dating.icebreakers(found, config)
        self.assertEqual(lines[0], "我們都是「待在生活圈」！" + config["icebreakers"]["travel"][0])
        self.assertEqual(lines[1], "你低甜度、我高甜度，剛好相反 😆 " + config["icebreakers"]["sweet"][0])
        self.assertEqual(lines[2], "我們都是「養貓」！" + config["icebreakers"]["pets_cat"])
        self.assertEqual(dating.icebreakers({"alike": [], "contrast": []}, config), config["default_icebreakers"][:3])


if __name__ == "__main__":
    unittest.main()

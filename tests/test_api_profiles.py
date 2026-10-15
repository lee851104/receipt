"""A finished upload job leaves the user's taste profile: the vector, the home districts and the items they rest on."""
import json
import math
import unittest
from unittest import mock

from sqlmodel import Session, select

from src.api import profiles
from src.api.db import MEMORY, ROOT, init_db, make_engine
from src.api.tables import Item, ItemCache, Job, Profile, User
from src.ml.fields import FIELDS
from src.receipt.traits import load_context
from tests.api_support import fake_backends, invoice_csv, login, make_client, register, upload

CONTEXT = load_context(ROOT)
# Fictional names the fake classifier is sure about (a 茶, a 餅乾 or a 衛生紙), so every line is a valid item.
THREE = [
    ["20260502", "開立已確認", "TEST-INV-1", "測試飲料店", "臺北市大安區測試路1號", "鮮奶茶", 1, 60],
    ["20260503", "開立已確認", "TEST-INV-2", "測試飲料店", "臺北市大安區測試路1號", "測試餅乾", 1, 40],
    ["20260504", "開立已確認", "TEST-INV-3", "測試超市", "臺北市信義區測試路2號", "衛生紙", 2, 120],
]


def tea_month(month, count, label="茶"):
    """A month of count valid items: one 測試{label} per bill, on its own day."""
    return [[f"2026{month:02}{number % 28 + 1:02}", "開立已確認", f"TEST-{month:02}-{number}", "測試飲料店",
             "臺北市大安區測試路1號", f"測試{label}{number}", 1, 50] for number in range(count)]


def stored_profile(engine, user_id=1):
    """The user's profile row as a dict, or None."""
    with Session(engine) as session:
        profile = session.get(Profile, user_id)
        return None if profile is None else profile.model_dump()


def refuse_nan(constant):
    raise AssertionError(f"{constant} in the stored vector")


def cells_of(profile):
    """The stored vector's cells, read as strict JSON: a NaN or an Infinity fails the test."""
    return json.loads(profile["vector"], parse_constant=refuse_nan)


class UploadProfileTests(unittest.TestCase):
    def client(self, **backend_changes):
        client = make_client(**backend_changes)
        register(client)
        return client, login(client)

    def profile(self, client):
        return stored_profile(client.app.state.engine)

    def jobs(self, client):
        with Session(client.app.state.engine) as session:
            return [(job.month, job.status, job.message) for job in session.exec(select(Job).order_by(Job.id)).all()]

    def test_an_upload_leaves_a_profile_with_too_few_items_for_a_vector(self):
        client, headers = self.client()
        upload(client, headers, invoice_csv(THREE))
        profile = self.profile(client)
        self.assertEqual(profile["item_count"], 3)
        self.assertIsNone(profile["vector"])  # fewer than the 20 items a vector needs
        self.assertEqual(json.loads(profile["areas"]), ["臺北市大安區", "臺北市信義區"])  # two bills in 大安, one in 信義

    def test_enough_items_give_all_18_cells_without_a_nan(self):
        client, headers = self.client()
        upload(client, headers, invoice_csv(tea_month(5, 25)))
        profile = self.profile(client)
        self.assertEqual(profile["item_count"], 25)
        cells = cells_of(profile)
        self.assertEqual(len(cells), 18)
        self.assertTrue(all(cell is None or math.isfinite(cell) for cell in cells))

    def test_two_months_are_weighed_together(self):
        client, headers = self.client()
        upload(client, headers, invoice_csv(tea_month(5, 15)))
        self.assertIsNone(self.profile(client)["vector"])  # 15 items are too few
        upload(client, headers, invoice_csv(tea_month(6, 15, label="餅乾")))
        profile = self.profile(client)
        self.assertEqual(profile["item_count"], 30)
        self.assertEqual(len(cells_of(profile)), 18)

    def test_uploading_a_month_again_works_the_profile_out_again(self):
        client, headers = self.client()
        upload(client, headers, invoice_csv(THREE))
        first = self.profile(client)
        upload(client, headers, invoice_csv(THREE + tea_month(5, 2)))
        second = self.profile(client)
        self.assertEqual(second["item_count"], 5)  # the month is replaced, not added to
        self.assertGreater(second["updated_at"], first["updated_at"])
        with Session(client.app.state.engine) as session:
            self.assertEqual(len(session.exec(select(Profile)).all()), 1)

    def test_a_user_gets_only_their_own_profile(self):
        client, headers = self.client()
        register(client, username="ben")
        upload(client, headers, invoice_csv(THREE))
        upload(client, login(client, username="ben"), invoice_csv(tea_month(5, 2)))
        self.assertEqual([stored_profile(client.app.state.engine, user)["item_count"] for user in (1, 2)], [3, 2])

    def test_names_the_model_has_not_judged_yet_do_not_stop_the_profile(self):
        def no_gpu(names, ask_model=True):
            return [None] * len(names)  # a stand-in Qwen that cannot answer now
        client, headers = self.client(attributes="qwen", describe_items=no_gpu)
        upload(client, headers, invoice_csv(tea_month(5, 25)))
        self.assertEqual(self.jobs(client), [("2026-05", "done", "完成")])
        profile = self.profile(client)
        self.assertEqual(profile["item_count"], 25)
        self.assertEqual(len(cells_of(profile)), 18)

    def sweetness(self, **backend_changes):
        """The sweetness cell of the profile that 25 drinks give, with the attribute model of these backends."""
        client, headers = self.client(**backend_changes)
        upload(client, headers, invoice_csv(tea_month(5, 25)))
        return cells_of(self.profile(client))[[trait["id"] for trait in CONTEXT["traits"]["traits"]].index("sweet")]

    def test_the_profile_is_worked_out_with_the_cached_attributes(self):
        def sugar_free(names, ask_model=True):
            return [{**dict.fromkeys(FIELDS), "sugar": 0} for _ in names]
        # A drink the model knows nothing about is as sweet as its name and shop suggest; the model says 0.
        self.assertLess(self.sweetness(describe_items=sugar_free), self.sweetness())

    def test_the_job_is_done_only_once_its_profile_is_written(self):
        client, headers = self.client()
        seen = []
        recompute = profiles.recompute

        def look_then_recompute(*arguments):
            seen.append(client.get("/api/jobs/1", headers=headers).json())
            recompute(*arguments)
        with mock.patch.object(profiles, "recompute", side_effect=look_then_recompute):
            upload(client, headers, invoice_csv(THREE))
        # Asked while it was worked out, the job was still running: a re-upload deletes only jobs that are over.
        self.assertEqual([(job["status"], job["message"]) for job in seen], [("running", "重算品味向量")])
        self.assertEqual(self.jobs(client), [("2026-05", "done", "完成")])
        self.assertEqual(self.profile(client)["item_count"], 3)

    def test_a_failing_recompute_fails_the_job_and_keeps_the_old_profile(self):
        client, headers = self.client()
        upload(client, headers, invoice_csv(THREE))
        before = self.profile(client)
        with mock.patch.object(profiles.places, "areas_of", side_effect=RuntimeError("boom")), \
                self.assertLogs("src.api.jobs", level="ERROR"):
            upload(client, headers, invoice_csv(tea_month(6, 2)))
        self.assertEqual(self.jobs(client), [("2026-05", "done", "完成"), ("2026-06", "failed", "處理失敗，請重新上傳")])
        self.assertEqual(self.profile(client), before)

    def test_a_vector_that_cannot_be_stored_fails_the_job_and_keeps_the_old_profile(self):
        client, headers = self.client()
        upload(client, headers, invoice_csv(THREE))
        before = self.profile(client)
        with mock.patch.object(profiles.traits, "build_vector", return_value=[math.nan] * 18), \
                self.assertLogs("src.api.jobs", level="ERROR"):
            upload(client, headers, invoice_csv(tea_month(6, 2)))
        self.assertEqual([status for _, status, _ in self.jobs(client)], ["done", "failed"])
        self.assertEqual(self.profile(client), before)


class RecomputeTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine(MEMORY)
        init_db(self.engine)
        with Session(self.engine) as session:
            session.add(User(username="amy", display_name="Amy"))
            session.commit()  # foreign keys are enforced, so the user must exist before its rows

    def recompute(self, backends=None):
        with Session(self.engine) as session:
            profiles.recompute(session, backends or fake_backends(), CONTEXT, 1)

    def test_without_any_items_the_profile_is_empty(self):
        self.recompute()
        self.assertEqual(stored_profile(self.engine), {"user_id": 1, "vector": None, "areas": "[]", "item_count": 0,
                                                       "updated_at": mock.ANY})

    def test_a_profile_of_items_that_are_gone_is_emptied(self):
        with Session(self.engine) as session:
            session.add(Profile(user_id=1, vector=json.dumps([0.5] * 18), areas='["臺北市大安區"]', item_count=30))
            session.commit()
        self.recompute()
        profile = stored_profile(self.engine)
        self.assertEqual((profile["vector"], profile["areas"], profile["item_count"]), (None, "[]", 0))

    def test_the_pending_items_are_not_counted(self):
        with Session(self.engine) as session:
            session.add_all([Item(user_id=1, month="2026-05", day=2, invoice="2026-05-R01", merchant="測試飲料店",
                                  name=name, quantity=1, amount=60, category=category)
                             for name, category in (("鮮奶茶", 1), ("測試新品", 10))])
            session.commit()
        self.recompute()
        self.assertEqual(stored_profile(self.engine)["item_count"], 1)


class MonthsOfTests(unittest.TestCase):
    def item(self, month, day, name="鮮奶茶", **changes):
        values = {"user_id": 1, "month": month, "day": day, "invoice": f"{month}-R01", "merchant": "測試飲料店",
                  "district": "臺北市大安區", "name": name, "quantity": 1, "amount": 60, "category": 1}
        return Item(**{**values, **changes})

    def test_items_become_report_months_with_their_rows_by_day(self):
        months = profiles.months_of([self.item("2026-06", 3, name="衛生紙", category=8, quantity=2, amount=120),
                                     self.item("2026-05", 9, name="測試餅乾", category=2),
                                     self.item("2026-05", 2, district=None)])
        self.assertEqual(list(months), ["2026-05", "2026-06"])
        self.assertEqual({key: months["2026-05"][key] for key in ("year", "monthNumber", "month", "days")},
                         {"year": 2026, "monthNumber": 5, "month": "2026 年 5 月", "days": 31})
        self.assertEqual(months["2026-06"]["days"], 30)
        self.assertEqual(months["2026-05"]["rows"], [
            {"day": 2, "invoice": "2026-05-R01", "merchant": "測試飲料店", "district": None, "name": "鮮奶茶",
             "quantity": 1, "amount": 60, "category": 1, "provisional": False},
            {"day": 9, "invoice": "2026-05-R01", "merchant": "測試飲料店", "district": "臺北市大安區",
             "name": "測試餅乾", "quantity": 1, "amount": 60, "category": 2, "provisional": False}])
        self.assertEqual(months["2026-06"]["rows"][0]["category"], 8)

    def test_no_items_are_no_months(self):
        self.assertEqual(profiles.months_of([]), {})


class AttributesOfTests(unittest.TestCase):
    def test_only_the_cache_of_the_current_model_answers_and_the_model_is_never_asked(self):
        engine = make_engine(MEMORY)
        init_db(engine)
        fields = {**dict.fromkeys(FIELDS), "food": True}
        asked = []
        backends = fake_backends(describe_items=lambda names, ask_model=True: asked.append(names) or [])
        with Session(engine) as session:
            session.add_all([ItemCache(name="鮮奶茶", model="fake", fields=json.dumps(fields)),
                             ItemCache(name="衛生紙", model="qwen", fields=json.dumps(fields))])
            session.commit()
            found = profiles.attributes_of(session, backends, {"鮮奶茶", "衛生紙", "測試新品"})
            self.assertEqual(found, {"鮮奶茶": fields, "衛生紙": None, "測試新品": None})
            self.assertEqual(len(session.exec(select(ItemCache)).all()), 2)  # nothing was written
        self.assertEqual(asked, [])


if __name__ == "__main__":
    unittest.main()

"""The upload job classifies, judges attributes through the cache, and never stays running when something fails."""
import unittest

from sqlmodel import Session, select

from src.api import cache
from src.api.db import MEMORY, init_db, make_engine
from src.api.jobs import fail_unfinished
from src.api.tables import Item, ItemCache, Job, User
from src.ml.fields import FIELDS
from tests.api_support import MAY, fake_backends, invoice_csv, login, make_client, register, upload

JUNE = [["20260601", "開立已確認", "TEST-INV-9", "測試飲料店", "臺北市大安區測試路1號", name, 1, 50]
        for name in ("鮮奶茶", "測試新品")]


def judged_only_with_the_model(names, ask_model=True):
    """A stand-in Qwen with no cache of its own: it answers only when it may be asked."""
    return [dict.fromkeys(FIELDS) if ask_model else None for _ in names]


class JobTests(unittest.TestCase):
    def client(self, **backend_changes):
        client = make_client(**backend_changes)
        register(client)
        return client, login(client)

    def rows(self, client, model):
        with Session(client.app.state.engine) as session:
            return session.exec(select(model)).all()

    def test_a_name_judged_once_is_taken_from_the_cache(self):
        asked = []
        client, headers = self.client(
            describe_items=lambda names, ask_model=True: asked.append(set(names)) or judged_only_with_the_model(names))
        upload(client, headers, invoice_csv(MAY))
        upload(client, headers, invoice_csv(JUNE))
        self.assertEqual(asked, [{"鮮奶茶", "滷肉飯", "衛生紙"}, {"測試新品"}])
        self.assertEqual(len(self.rows(client, ItemCache)), 4)

    def test_without_the_gpu_new_names_stay_pending_and_the_job_still_finishes(self):
        client, headers = self.client(attributes="qwen", describe_items=judged_only_with_the_model)
        upload(client, headers, invoice_csv(MAY))
        self.assertEqual([(job.status, job.done, job.total) for job in self.rows(client, Job)], [("done", 3, 3)])
        self.assertEqual(self.rows(client, ItemCache), [])

    def test_with_the_gpu_back_uploading_the_month_again_judges_the_pending_names(self):
        gpu = [False]
        client, headers = self.client(attributes="qwen", describe_items=judged_only_with_the_model,
                                      gpu_probe=lambda: gpu[0])
        upload(client, headers, invoice_csv(MAY))
        gpu[0] = True
        upload(client, headers, invoice_csv(MAY))
        self.assertEqual(sorted(row.name for row in self.rows(client, ItemCache)), ["滷肉飯", "衛生紙", "鮮奶茶"])
        self.assertEqual({row.model for row in self.rows(client, ItemCache)}, {"qwen"})

    def test_an_unavailable_classifier_fails_the_job_and_says_why(self):
        client, headers = self.client(category="unavailable")
        self.assertEqual(upload(client, headers, invoice_csv(MAY)).status_code, 202)
        [job] = self.rows(client, Job)
        self.assertEqual(job.status, "failed")
        self.assertIn("分類模型", job.message)
        self.assertEqual({item.category for item in self.rows(client, Item)}, {10})

    def test_a_crash_fails_the_job_instead_of_leaving_it_running(self):
        client, headers = self.client(classify=lambda names: 1 / 0)
        with self.assertLogs("src.api.jobs", level="ERROR"):
            upload(client, headers, invoice_csv(MAY))
        [job] = self.rows(client, Job)
        self.assertEqual((job.status, job.message), ("failed", "處理失敗，請重新上傳"))


class CacheTests(unittest.TestCase):
    def test_a_name_another_upload_stored_meanwhile_is_no_error(self):
        engine = make_engine(MEMORY)
        init_db(engine)

        def judged_while_another_job_stores_it(names, ask_model=True):
            with Session(engine) as other:
                other.add(ItemCache(name=names[0], model="fake", fields="{}"))
                other.commit()
            return [dict.fromkeys(FIELDS) for _ in names]
        backends = fake_backends(describe_items=judged_while_another_job_stores_it)
        with Session(engine) as session:
            self.assertEqual(cache.describe(session, backends, ["鮮奶茶"], ask_model=True), [dict.fromkeys(FIELDS)])
            # The answer stored first stays; this one is not written over it.
            self.assertEqual([row.fields for row in session.exec(select(ItemCache)).all()], ["{}"])


class StartUpTests(unittest.TestCase):
    def test_jobs_left_unfinished_by_a_stop_are_failed_at_start_up(self):
        engine = make_engine(MEMORY)
        init_db(engine)
        with Session(engine) as session:
            session.add(User(username="amy", display_name="Amy"))
            session.commit()  # foreign keys are enforced, so the user must exist before its jobs
            session.add_all([Job(user_id=1, month="2026-05", status=status) for status in ("queued", "running", "done")])
            session.commit()
        fail_unfinished(engine)
        with Session(engine) as session:
            jobs = session.exec(select(Job).order_by(Job.id)).all()
        self.assertEqual([job.status for job in jobs], ["failed", "failed", "done"])
        self.assertEqual(jobs[0].message, "服務重新啟動，請重新上傳")


if __name__ == "__main__":
    unittest.main()

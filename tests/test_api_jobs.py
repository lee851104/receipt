"""The upload job classifies, judges attributes through the cache, and never stays running when something fails."""
import json
import sqlite3
import tempfile
import threading
import unittest
from functools import partial
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.api import accounts, cache, jobs, profiles
from src.api.app import create_app
from src.api.db import MEMORY, ROOT, init_db, make_engine
from src.api.jobs import classify_items, fail_unfinished, run_job, run_recompute
from src.api.settings import Settings
from src.api.tables import Item, ItemCache, Job, Profile, User
from src.ml import fakes
from src.ml.fields import FIELDS
from src.receipt.traits import load_context
from tests.api_support import (MAY, SECRET, drain, fake_backends, invoice_csv, login, make_client, register,
                               upload)

JUNE = [["20260601", "開立已確認", "TEST-INV-9", "測試飲料店", "臺北市大安區測試路1號", name, 1, 50]
        for name in ("鮮奶茶", "測試新品")]
JULY = [["20260701", "開立已確認", "TEST-INV-10", "測試飲料店", "臺北市大安區測試路1號", "測試七月品", 1, 50]]
SETTINGS = Settings(jwt_secret=SECRET, database_url="sqlite://")
CONTEXT = load_context(ROOT)


def judged_only_with_the_model(names, ask_model=True):
    """A stand-in Qwen with no cache of its own: it answers only when it may be asked."""
    return [dict.fromkeys(FIELDS) if ask_model else None for _ in names]


def add_queued_job(engine, names=("鮮奶茶",)):
    """Amy with one queued job (id 1) over a May item per name, written straight into the database."""
    with Session(engine) as session:
        session.add(User(username="amy", display_name="Amy"))
        session.commit()  # foreign keys are enforced, so the user must exist before its rows
        session.add_all([Item(user_id=1, month="2026-05", day=2, invoice="2026-05-R01", merchant="測試飲料店",
                              name=name, quantity=1, amount=60) for name in names])
        session.add(Job(user_id=1, month="2026-05"))
        session.commit()


def table(engine, model):
    with Session(engine) as session:
        return session.exec(select(model)).all()


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

    def test_a_model_that_raises_fails_the_job(self):
        def broken(names, ask_model=True):
            raise RuntimeError("llama-server went away")
        client, headers = self.client(describe_items=broken)
        with self.assertLogs("src.api.jobs", level="ERROR"):
            upload(client, headers, invoice_csv(MAY))
        [job] = self.rows(client, Job)
        self.assertEqual((job.status, job.message), ("failed", "處理失敗，請重新上傳"))

    def test_a_model_that_answers_for_too_few_names_fails_the_job(self):
        cases = {"classify": dict(classify=lambda names: fakes.classify(names)[:-1]),
                 "describe_items": dict(describe_items=lambda names, ask_model=True: fakes.describe_items(names)[:-1])}
        for model, changes in cases.items():
            with self.subTest(model=model):
                client, headers = self.client(**changes)
                with self.assertLogs("src.api.jobs", level="ERROR"):
                    upload(client, headers, invoice_csv(MAY))
                [job] = self.rows(client, Job)
                self.assertEqual((job.status, job.message), ("failed", "處理失敗，請重新上傳"))

    def test_a_month_of_25_names_counts_all_of_them_across_two_batches(self):
        rows = [["20260502", "開立已確認", "TEST-INV-1", "測試飲料店", "臺北市大安區測試路1號", f"測試品{number}", 1, 50]
                for number in range(25)]
        client, headers = self.client()
        upload(client, headers, invoice_csv(rows))
        [job] = self.rows(client, Job)
        self.assertEqual((job.status, job.done, job.total), ("done", 25, 25))

    def test_a_job_asked_about_midway_is_running_with_its_progress(self):
        seen = []

        def describe_items(names, ask_model=True):
            seen.append(client.get("/api/jobs/1", headers=headers).json())
            return fakes.describe_items(names, ask_model)
        rows = [["20260502", "開立已確認", "TEST-INV-1", "測試飲料店", "臺北市大安區測試路1號", f"測試品{number}", 1, 50]
                for number in range(25)]
        client, headers = self.client(describe_items=describe_items)
        upload(client, headers, invoice_csv(rows))
        # Asked before each batch of 20 names is judged.
        self.assertEqual(seen, [{"job_id": 1, "month": "2026-05", "status": "running", "done": done, "total": 25,
                                 "message": "判斷品項屬性"} for done in (0, 20)])


class ConnectionTests(unittest.TestCase):
    def test_no_connection_is_held_while_the_model_works(self):
        """The request's session closes when its route returns, not when its job on the worker thread ends, and the job
        lets go of its own before asking."""
        held = []

        def describe_items(names, ask_model=True):
            held.append(client.app.state.engine.pool.checkedout())
            return fakes.describe_items(names, ask_model)
        with tempfile.TemporaryDirectory() as folder:
            settings = Settings(jwt_secret=SECRET, database_url="sqlite:///" + (Path(folder) / "app.db").as_posix())
            client = TestClient(create_app(settings, fake_backends(describe_items=describe_items)))
            try:
                register(client)
                self.assertEqual(upload(client, login(client), invoice_csv(MAY)).status_code, 202)
            finally:
                client.app.state.engine.dispose()  # Windows cannot delete a file that is still open
        self.assertEqual(held, [0])


class WorkerTests(unittest.TestCase):
    """Jobs run on the app's one worker thread: one at a time, in upload order, and never on a request's thread."""

    def setUp(self):
        self.started, self.release, self.asked, self.threads = threading.Event(), threading.Event(), [], []
        self.client = make_client(classify=self.held_classify)
        register(self.client)
        self.headers = login(self.client)
        self.addCleanup(self.release.set)  # never leave the worker held, whatever a test does

    def held_classify(self, names):
        """The fake classifier, held on its first call until the test releases it."""
        self.asked.append(set(names))
        self.threads.append(threading.current_thread())
        if len(self.asked) == 1:
            self.started.set()
            self.release.wait(timeout=5)
        return fakes.classify(names)

    def statuses(self, *job_ids):
        return [self.client.get(f"/api/jobs/{job_id}", headers=self.headers).json()["status"] for job_id in job_ids]

    def test_an_upload_answers_while_its_job_runs_on_the_worker_thread(self):
        self.assertEqual(upload(self.client, self.headers, invoice_csv(MAY), wait=False).status_code, 202)
        self.assertTrue(self.started.wait(timeout=5))
        # The job is held inside the model, and requests still answer.
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        self.assertEqual(self.statuses(1), ["running"])
        self.release.set()
        drain(self.client)
        self.assertEqual(self.statuses(1), ["done"])
        self.assertEqual(self.threads, [self.client.app.state.worker.thread])

    def test_jobs_run_one_at_a_time_in_upload_order(self):
        upload(self.client, self.headers, invoice_csv(MAY), wait=False)
        self.assertTrue(self.started.wait(timeout=5))
        for month in (JUNE, JULY):
            self.assertEqual(upload(self.client, self.headers, invoice_csv(month), wait=False).status_code, 202)
        self.assertEqual(self.statuses(1, 2, 3), ["running", "queued", "queued"])
        self.release.set()
        drain(self.client)
        self.assertEqual(self.statuses(1, 2, 3), ["done", "done", "done"])
        self.assertEqual(self.asked, [{"鮮奶茶", "滷肉飯", "衛生紙"}, {"鮮奶茶", "測試新品"}, {"測試七月品"}])


class WorkerLoopTests(unittest.TestCase):
    def test_a_job_that_breaks_the_runner_is_logged_and_the_next_one_still_runs(self):
        ran = []

        def run(job_id):
            if job_id == 1:
                raise RuntimeError("the database went away")
            ran.append(job_id)
        worker = jobs.Worker(run)
        with self.assertLogs("src.api.jobs", level="ERROR") as logs:
            worker.add(1)
            worker.add(2)
            worker.queue.join()
        self.assertEqual(ran, [2])
        self.assertIn("upload job 1 failed", "\n".join(logs.output))
        self.assertTrue(worker.thread.daemon)  # a stop never waits for a running job


class WorkerCallTests(unittest.TestCase):
    def test_other_work_waits_behind_the_uploads_queued_before_it(self):
        ran = []
        worker = jobs.Worker(ran.append)
        worker.add(1)
        worker.call("other work", lambda: ran.append("other"))
        worker.add(2)
        worker.queue.join()
        self.assertEqual(ran, [1, "other", 2])

    def test_failing_work_is_logged_by_its_label_and_the_next_still_runs(self):
        ran = []
        worker = jobs.Worker(ran.append)
        with self.assertLogs("src.api.jobs", level="ERROR") as logs:
            worker.call("recompute for user 7", lambda: 1 / 0)
            worker.add(3)
            worker.queue.join()
        self.assertEqual(ran, [3])
        self.assertIn("recompute for user 7 failed", "\n".join(logs.output))

    def test_a_user_is_recomputing_while_work_of_theirs_is_queued_or_running(self):
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)  # never leave the worker held, whatever the test does

        def held():
            started.set()
            release.wait(timeout=30)
        worker = jobs.Worker(lambda job_id: None)
        self.assertFalse(worker.recomputing(7))
        worker.call("recompute for user 7", held, user_id=7)
        worker.call("recompute for user 7", lambda: 1 / 0, user_id=7)  # fails, and still counts as run
        worker.add(1)  # an upload job keeps its own status, so it is not counted
        self.assertTrue(started.wait(timeout=5))
        self.assertEqual((worker.recomputing(7), worker.recomputing(1)), (True, False))
        with self.assertLogs("src.api.jobs", level="ERROR"):
            release.set()
            worker.queue.join()
        self.assertFalse(worker.recomputing(7))


class RunJobTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine(MEMORY)
        init_db(self.engine)

    def run_job(self, job_id=1, **backend_changes):
        run_job(self.engine, fake_backends(**backend_changes), SETTINGS, CONTEXT, job_id)

    def test_a_job_that_does_not_exist_ends_quietly_and_writes_nothing(self):
        with self.assertNoLogs("src.api.jobs", level="ERROR"):
            self.run_job(job_id=99)
        self.assertEqual([table(self.engine, model) for model in (Job, Item, ItemCache)], [[], [], []])

    def test_a_job_deleted_while_it_fails_is_gone_and_raises_nothing(self):
        add_queued_job(self.engine)

        def delete_the_job_then_crash(names):
            with Session(self.engine) as other:  # the account was deleted meanwhile, and its jobs with it
                other.delete(other.get(Job, 1))
                other.commit()
            raise RuntimeError("model crashed")
        with self.assertLogs("src.api.jobs", level="ERROR") as logs:
            self.run_job(classify=delete_the_job_then_crash)
        self.assertEqual(table(self.engine, Job), [])
        self.assertEqual(len(logs.records), 1)  # the crash only: nothing tried to mark a missing job failed

    def test_a_failure_that_cannot_be_written_is_logged_and_raises_nothing(self):
        add_queued_job(self.engine)
        update = jobs.update

        def refuse_to_write_failure(session, job, **changes):
            if changes.get("status") == "failed":
                raise RuntimeError("database is locked")
            update(session, job, **changes)
        with mock.patch.object(jobs, "update", side_effect=refuse_to_write_failure), \
                self.assertLogs("src.api.jobs", level="ERROR") as logs:
            self.run_job(classify=lambda names: 1 / 0)
        self.assertIn("could not mark upload job 1 failed", "\n".join(logs.output))
        # Still "running": the next start-up fails it, like any job a stop left behind.
        self.assertEqual([job.status for job in table(self.engine, Job)], ["running"])

    def test_only_the_names_that_were_classified_get_a_category(self):
        add_queued_job(self.engine, names=("鮮奶茶", "衛生紙"))
        with Session(self.engine) as session:
            classify_items(session, session.get(Job, 1), fake_backends(), 0.5, ["鮮奶茶"])
        items = table(self.engine, Item)
        self.assertEqual(sorted((item.name, item.category) for item in items), [("衛生紙", 10), ("鮮奶茶", 1)])

    def test_a_month_uploaded_again_while_categories_are_written_gets_them_by_name(self):
        """The new upload's items take the old ones' ids again (SQLite reuses them), so a category written by id
        would land on another name."""
        add_queued_job(self.engine, names=("鮮奶茶", "衛生紙"))  # ids 1 and 2

        def upload_again_first(connection, cursor, statement, parameters, context, executemany):
            if statement.startswith("UPDATE items") and not replaced:
                replaced.append(True)
                cursor.connection.execute("DELETE FROM items")
                for name in ("衛生紙", "測試新品"):  # ids 1 and 2 once more
                    cursor.connection.execute(
                        "INSERT INTO items (user_id, month, day, invoice, merchant, name, quantity, amount, category)"
                        " VALUES (1, '2026-05', 2, '2026-05-R01', '測試飲料店', ?, 1, 60, 10)", (name,))
        replaced = []
        event.listen(self.engine, "before_cursor_execute", upload_again_first)
        with Session(self.engine) as session:
            classify_items(session, session.get(Job, 1), fake_backends(), 0.5, ["衛生紙", "鮮奶茶"])
        self.assertEqual(replaced, [True])
        items = table(self.engine, Item)
        self.assertEqual(sorted((item.name, item.category) for item in items), [("測試新品", 10), ("衛生紙", 8)])


class RunRecomputeTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine(MEMORY)
        init_db(self.engine)

    def add_amy_with_items(self):
        with Session(self.engine) as session:
            session.add(User(username="amy", display_name="Amy", password_hash="x"))
            session.commit()  # foreign keys are enforced, so the user must exist before its rows
            session.add_all([Item(user_id=1, month="2026-05", day=day, invoice=f"2026-05-R{day:02}", merchant="測試飲料店",
                                  district="臺北市大安區", name=f"測試茶{day}", quantity=1, amount=50, category=1)
                             for day in range(1, 4)])
            session.commit()

    def test_it_stores_the_profile_worked_out_from_the_items(self):
        self.add_amy_with_items()
        run_recompute(self.engine, fake_backends(), CONTEXT, 1)
        with Session(self.engine) as session:
            profile = session.get(Profile, 1)
        self.assertEqual((profile.item_count, profile.vector, json.loads(profile.areas)), (3, None, ["臺北市大安區"]))

    def test_an_account_deleted_meanwhile_is_skipped_quietly(self):
        with self.assertNoLogs("src.api.jobs", level="ERROR"):
            run_recompute(self.engine, fake_backends(), CONTEXT, 42)
        with Session(self.engine) as session:
            self.assertEqual(session.exec(select(Profile)).all(), [])

    def test_an_account_deleted_while_it_runs_ends_it_quietly(self):
        self.add_amy_with_items()
        history = profiles.history

        def delete_the_account_meanwhile(session, backends, user_id):
            answer = history(session, backends, user_id)
            with Session(self.engine) as other:
                accounts.delete_account(other, user_id)
                other.commit()
            return answer
        worker = jobs.Worker(lambda job_id: None)
        with mock.patch.object(profiles, "history", side_effect=delete_the_account_meanwhile), \
                self.assertNoLogs("src.api.jobs", level="ERROR"):
            worker.call("recompute for user 1", partial(run_recompute, self.engine, fake_backends(), CONTEXT, 1))
            worker.queue.join()
        self.assertEqual((table(self.engine, User), table(self.engine, Profile)), ([], []))

    def test_a_constraint_that_fails_while_the_account_is_there_is_raised(self):
        self.add_amy_with_items()
        failure = IntegrityError("INSERT INTO profiles", None, sqlite3.IntegrityError("CHECK constraint failed"))
        with mock.patch.object(profiles, "recompute", side_effect=failure), self.assertRaises(IntegrityError):
            run_recompute(self.engine, fake_backends(), CONTEXT, 1)


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

    def test_every_real_users_profile_is_worked_out_again_at_start_up(self):
        """The recompute queued after a month was deleted lived only in the stopped server's queue, so a profile may
        still be the one from before the deletion."""
        def profile_of(client, user_id):
            with Session(client.app.state.engine) as session:
                profile = session.get(Profile, user_id)
                return profile.vector, profile.areas, profile.item_count
        stale = {"vector": json.dumps([0.5] * 18), "areas": json.dumps(["臺北市信義區"]), "item_count": 30}
        with tempfile.TemporaryDirectory() as folder:
            settings = Settings(jwt_secret=SECRET, database_url="sqlite:///" + (Path(folder) / "app.db").as_posix())
            first = TestClient(create_app(settings, fake_backends()))
            try:
                register(first)  # user 1
                upload(first, login(first), invoice_csv(MAY))
                worked_out = profile_of(first, 1)
                with Session(first.app.state.engine) as session:
                    session.add(User(username="demo_001", display_name="Mia", is_demo=True, persona="咖啡上班族"))
                    session.commit()  # user 2, whose profile the seed stored
                    session.merge(Profile(user_id=1, **stale))
                    session.merge(Profile(user_id=2, **stale))
                    session.commit()
            finally:
                first.app.state.engine.dispose()  # Windows cannot delete a file that is still open
            second = TestClient(create_app(settings, fake_backends()))
            try:
                drain(second)
                self.assertEqual(profile_of(second, 1), worked_out)
                self.assertEqual(profile_of(second, 2), (stale["vector"], stale["areas"], stale["item_count"]))
            finally:
                second.app.state.engine.dispose()


if __name__ == "__main__":
    unittest.main()

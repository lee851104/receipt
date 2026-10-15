"""POST /api/invoices checks a month's CSV at once and leaves the rest to a job; GET /api/jobs/{id} follows it."""
import unittest
from pathlib import Path
from unittest import mock

from sqlmodel import Session, select

from src.api.routes import invoices
from src.api.seed import seed_demo_users
from src.api.tables import Item, Job
from tests.api_support import COLUMNS, MAY, invoice_csv, login, make_client, register, upload


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.client = make_client()
        register(self.client)
        self.headers = login(self.client)

    def rows(self, model):
        with Session(self.client.app.state.engine) as session:
            return session.exec(select(model)).all()

    def test_an_upload_answers_202_and_its_job_finishes(self):
        response = upload(self.client, self.headers, invoice_csv(MAY))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"job_id": 1, "month": "2026-05", "rows": 3})
        self.assertEqual(self.client.get("/api/jobs/1", headers=self.headers).json(),
                         {"job_id": 1, "month": "2026-05", "status": "done", "done": 3, "total": 3, "message": "完成"})

    def test_items_keep_only_what_the_analysis_needs_with_the_models_categories(self):
        upload(self.client, self.headers, invoice_csv(MAY))
        items = sorted(self.rows(Item), key=lambda item: item.name)
        # 滷肉飯 is the fake model's weak guess (0.3), below CATEGORY_MIN_PROB, so it waits as 待確認.
        self.assertEqual([(item.name, item.category) for item in items], [("滷肉飯", 10), ("衛生紙", 8), ("鮮奶茶", 1)])
        self.assertEqual({item.invoice for item in items}, {"2026-05-R01", "2026-05-R02"})
        self.assertEqual({item.district for item in items}, {"臺北市大安區", "臺北市信義區"})
        self.assertNotIn("TEST-INV", str(items))
        self.assertNotIn("測試路", str(items))

    def test_uploading_a_month_again_replaces_it(self):
        upload(self.client, self.headers, invoice_csv(MAY))
        upload(self.client, self.headers, invoice_csv([MAY[2]]))
        self.assertEqual([item.name for item in self.rows(Item)], ["衛生紙"])
        self.assertEqual([(job.id, job.status) for job in self.rows(Job)], [(2, "done")])

    def test_a_broken_file_is_400_with_its_reason_and_creates_no_job(self):
        two_months = invoice_csv([MAY[0], ["20260601", *MAY[0][1:]]])
        no_names = invoice_csv([row[:5] + row[6:] for row in MAY], [column for column in COLUMNS if column != "消費明細_品名"])
        cases = [(two_months, "one month"), (no_names, "消費明細_品名"), (b"\xff\xfe\x00 not text", ""),
                 (invoice_csv([MAY[3]]), "No invoice records")]
        for data, reason in cases:
            with self.subTest(reason=reason):
                response = upload(self.client, self.headers, data)
                self.assertEqual((response.status_code, response.json()["detail"]), (400, "invalid_csv"))
                self.assertIn(reason, response.json()["message"])
        self.assertEqual(self.rows(Job), [])

    def test_a_file_over_two_megabytes_is_413(self):
        response = upload(self.client, self.headers, b"x" * (2 * 1024 * 1024 + 1))
        self.assertEqual((response.status_code, response.json()), (413, {"detail": "file_too_large"}))

    def test_the_uploaded_file_is_not_kept(self):
        made, original = [], invoices.tempfile.NamedTemporaryFile

        def recording(*args, **kwargs):
            handle = original(*args, **kwargs)
            made.append(handle.name)
            return handle
        with mock.patch.object(invoices.tempfile, "NamedTemporaryFile", side_effect=recording):
            upload(self.client, self.headers, invoice_csv(MAY))
            upload(self.client, self.headers, b"not a csv")
        self.assertEqual(len(made), 2)
        self.assertFalse(any(Path(name).exists() for name in made))

    def test_an_upload_needs_a_login(self):
        self.assertEqual(upload(self.client, {}, invoice_csv(MAY)).status_code, 401)


class JobAccessTests(unittest.TestCase):
    def test_a_job_is_only_its_uploaders_and_ids_are_checked(self):
        client = make_client()
        register(client)
        register(client, username="bob")
        upload(client, login(client), invoice_csv(MAY))
        bob = login(client, username="bob")
        for path, status in (("/api/jobs/1", 404), ("/api/jobs/99", 404), ("/api/jobs/0", 422),
                             (f"/api/jobs/{2**63}", 422), ("/api/jobs/abc", 422)):
            with self.subTest(path=path):
                self.assertEqual(client.get(path, headers=bob).status_code, status)
        self.assertEqual(client.get("/api/jobs/1", headers=bob).json(), {"detail": "not_found"})

    def test_demo_users_cannot_upload(self):
        client = make_client(demo_mode=True)
        seed_demo_users(client.app.state.engine, [{"name": "咖啡上班族 A", "type": "咖啡上班族"}])
        token = client.post("/api/auth/demo-login", json={"user_id": 1}).json()["access_token"]
        response = upload(client, {"Authorization": "Bearer " + token}, invoice_csv(MAY))
        self.assertEqual((response.status_code, response.json()), (403, {"detail": "demo_user_read_only"}))
        with Session(client.app.state.engine) as session:
            self.assertEqual(session.exec(select(Job)).all(), [])


if __name__ == "__main__":
    unittest.main()

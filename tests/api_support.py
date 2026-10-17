"""A test client on its own in-memory database (or a temporary file), with the fake models and no GPU, and fictional
invoice files."""
import csv
import io
import sqlite3
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.backends import Backends
from src.api.settings import Settings
from src.ml import fakes

SECRET = "test-secret-0123456789abcdef0123456789"


def fake_backends(**changes):
    values = {"category": "fake", "classify": fakes.classify, "attributes": "fake",
              "describe_items": fakes.describe_items, "gpu_probe": lambda: False}
    merged = {**values, **changes}
    # Unless a test names a version, the cache key is the setting name, as it was before versions existed.
    merged.setdefault("attributes_version", merged["attributes"])
    return Backends(**merged)


def make_client(demo_mode=False, **backend_changes):
    settings = Settings(jwt_secret=SECRET, demo_mode=demo_mode, database_url="sqlite://")
    return TestClient(create_app(settings, fake_backends(**backend_changes)))


def file_client(test, **backend_changes):
    """A test client on a SQLite file in a temporary folder, and the file's path, for a test that needs a connection
    of its own next to the app's, which the shared in-memory database cannot give. The test's cleanup removes it."""
    folder = tempfile.TemporaryDirectory()
    test.addCleanup(folder.cleanup)
    path = Path(folder.name) / "app.db"
    settings = Settings(jwt_secret=SECRET, database_url="sqlite:///" + path.as_posix())
    client = TestClient(create_app(settings, fake_backends(**backend_changes)))
    test.addCleanup(client.app.state.engine.dispose)  # first: Windows cannot delete a file that is still open
    return client, path


def commit_a_job(path, user_id, month):
    """Commit a queued upload job from a connection of its own, as another request's upload does: "locked" while
    someone else holds SQLite's write lock (waiting 0.1 seconds for it, not 5), else "written"."""
    connection = sqlite3.connect(path, timeout=0.1)
    try:
        connection.execute("INSERT INTO jobs (user_id, month, status, done, total, message, created_at)"
                           " VALUES (?, ?, 'queued', 0, 0, '排隊中', '2026-10-16 00:00:00')", (user_id, month))
        connection.commit()
        return "written"
    except sqlite3.OperationalError as error:
        if "locked" not in str(error):
            raise
        return "locked"
    finally:
        connection.close()


def register(client, username="amy", password="password123", **extra):
    return client.post("/api/auth/register", json={"username": username, "password": password, **extra})


def login(client, username="amy", password="password123"):
    """Bearer headers for a user that register() created."""
    response = client.post("/api/auth/login", data={"username": username, "password": password})
    return {"Authorization": "Bearer " + response.json()["access_token"]}


COLUMNS = ["發票日期", "發票狀態", "發票號碼", "賣方名稱", "賣方地址", "消費明細_品名", "消費明細_數量", "消費明細_金額"]
# A fictional May: a drink, a meal the fake model is unsure of, a pack of tissues, a voided invoice and a discount.
MAY = [
    ["20260502", "開立已確認", "TEST-INV-1", "測試飲料店", "臺北市大安區測試路1號", "鮮奶茶", 1, 60],
    ["20260502", "開立已確認", "TEST-INV-1", "測試飲料店", "臺北市大安區測試路1號", "滷肉飯", 1, 80],
    ["20260503", "開立已確認", "TEST-INV-2", "測試超市", "臺北市信義區測試路2號", "衛生紙", 2, 120],
    ["20260503", "作廢已確認", "TEST-INV-3", "測試超市", "臺北市信義區測試路2號", "鮮奶茶", 1, 60],
    ["20260504", "開立已確認", "TEST-INV-4", "測試超市", "臺北市信義區測試路2號", "測試折扣", 1, -20],
]


def invoice_csv(rows, columns=COLUMNS):
    """A fictional e-invoice export as UTF-8 bytes with a BOM and the export's footer line, like the real ones."""
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(columns)
    writer.writerows(rows)
    writer.writerow(["", "", "", "匯出摘要"])
    return (chr(0xFEFF) + stream.getvalue()).encode("utf-8")


def drain(client):
    """Wait until the app's worker has run every job queued so far."""
    client.app.state.worker.queue.join()


def upload(client, headers, data, wait=True):
    """POST a file to /api/invoices. The job runs on the app's worker thread, so unless wait is False this also
    waits for it, and the test reads the finished result."""
    response = client.post("/api/invoices", files={"file": ("month.csv", data, "text/csv")}, headers=headers)
    if wait:
        drain(client)
    return response

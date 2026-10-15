"""A test client on its own in-memory database, with the fake models and no GPU, and fictional invoice files."""
import csv
import io

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.backends import Backends
from src.api.settings import Settings
from src.ml import fakes

SECRET = "test-secret-0123456789abcdef0123456789"


def fake_backends(**changes):
    values = {"category": "fake", "classify": fakes.classify, "attributes": "fake",
              "describe_items": fakes.describe_items, "gpu_probe": lambda: False}
    return Backends(**{**values, **changes})


def make_client(demo_mode=False, **backend_changes):
    settings = Settings(jwt_secret=SECRET, demo_mode=demo_mode, database_url="sqlite://")
    return TestClient(create_app(settings, fake_backends(**backend_changes)))


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


def upload(client, headers, data):
    return client.post("/api/invoices", files={"file": ("month.csv", data, "text/csv")}, headers=headers)

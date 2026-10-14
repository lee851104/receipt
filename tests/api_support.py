"""A test client on its own in-memory database, with the fake models and no GPU."""
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

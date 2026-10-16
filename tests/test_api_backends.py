"""The server picks its models from the settings and probes the llama-server for GPU mode."""
import os
import socketserver
import tempfile
import threading
import unittest
import urllib.request
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.backends import llama_probe, load_backends, model_dir
from src.api.db import ROOT
from src.api.settings import Settings
from src.ml import fakes

SECRET = "s" * 32


class Answer(BaseHTTPRequestHandler):
    """A stand-in llama-server whose /health says ok."""
    status = 200

    def do_GET(self):
        self.send_response(self.status if self.path == "/health" else 404)
        self.end_headers()

    def log_message(self, *args):
        pass


class Loading(Answer):
    """A llama-server that is up but still loading its model."""
    status = 503


class Garbage(socketserver.BaseRequestHandler):
    """Something on the port that does not speak HTTP."""
    def handle(self):
        self.request.recv(1024)
        self.request.sendall(b"garbage\r\n\r\n")


@contextmanager
def serving(handler, server_class=HTTPServer):
    """The base URL of a stand-in server on a free local port, shut down afterwards."""
    server = server_class(("127.0.0.1", 0), handler)
    # A short poll interval lets shutdown() return at once instead of after the default half second.
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


class BackendTests(unittest.TestCase):
    def test_the_fakes_are_loaded_by_default(self):
        backends = load_backends(Settings(jwt_secret=SECRET))
        self.assertEqual((backends.category, backends.attributes), ("fake", "fake"))
        self.assertIs(backends.classify, fakes.classify)
        self.assertIs(backends.describe_items, fakes.describe_items)

    def test_the_fake_model_keeps_the_key_fake(self):
        self.assertEqual(load_backends(Settings(jwt_secret=SECRET)).attributes_version, "fake")

    def test_asking_for_a_real_model_before_it_exists_stops_the_server(self):
        for changes in ({"category_model": "tfidf"}, {"category_model": "embedding"}, {"attributes_model": "qwen"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                load_backends(Settings(jwt_secret=SECRET, **changes))

    def test_the_probe_asks_the_llama_server_named_in_the_settings(self):
        with serving(Answer) as url:
            self.assertTrue(load_backends(Settings(jwt_secret=SECRET, llama_server_url=url)).gpu_probe())

    def test_the_probe_is_false_unless_the_server_answers_ok(self):
        with serving(Loading) as url:
            self.assertFalse(llama_probe(url)())
        with serving(Garbage, socketserver.TCPServer) as url:
            self.assertFalse(llama_probe(url)())
        self.assertFalse(llama_probe(url)())  # nothing listens there any more
        self.assertFalse(llama_probe("not a url")())
        self.assertFalse(llama_probe("http://127.0.0.1:abc")())

    def test_the_probe_goes_straight_to_the_server_even_with_a_proxy_set(self):
        # urllib keeps one shared opener with the proxies it saw first. Drop it now so the proxy below would count,
        # and again afterwards even if this test fails, so no other test inherits the proxy.
        urllib.request.install_opener(None)
        self.addCleanup(urllib.request.install_opener, None)
        with serving(Answer) as url, mock.patch.dict(os.environ, {"HTTP_PROXY": "http://127.0.0.1:9"}):
            self.assertTrue(llama_probe(url)())

    def test_an_answer_is_remembered_for_a_while(self):
        with serving(Answer) as url:
            remembered, fresh = llama_probe(url, remember=60), llama_probe(url, remember=0)
            self.assertTrue(remembered())
            self.assertTrue(fresh())
        self.assertTrue(remembered())
        self.assertFalse(fresh())


class BertBackendTests(unittest.TestCase):
    def settings(self, folder):
        return Settings(jwt_secret=SECRET, category_model="bert", category_model_dir=str(folder))

    def test_without_a_model_the_category_model_is_unavailable_and_the_server_still_starts(self):
        folder = Path(tempfile.mkdtemp())
        with self.assertLogs("src.api.backends", level="WARNING"):
            backends = load_backends(self.settings(folder))
        self.assertEqual(backends.category, "unavailable")
        with self.assertRaises(RuntimeError):
            backends.classify(["鮮奶茶"])

    def test_the_health_check_says_unavailable_and_the_classify_box_is_503(self):
        folder = Path(tempfile.mkdtemp())
        with self.assertLogs("src.api.backends", level="WARNING"):
            client = TestClient(create_app(Settings(jwt_secret=SECRET, database_url="sqlite://", category_model="bert",
                                                    category_model_dir=str(folder))))
        self.assertEqual(client.get("/api/health").json()["models"]["category"], "unavailable")
        client.post("/api/auth/register", json={"username": "amy", "password": "password123"})
        token = client.post("/api/auth/login", data={"username": "amy", "password": "password123"}).json()["access_token"]
        response = client.post("/api/items/classify", json={"name": "鮮奶茶"}, headers={"Authorization": "Bearer " + token})
        self.assertEqual((response.status_code, response.json()), (503, {"detail": "model_unavailable"}))

    def test_a_relative_folder_starts_at_the_repository_root(self):
        self.assertEqual(model_dir(Settings(jwt_secret=SECRET)), ROOT / "models" / "category")


if __name__ == "__main__":
    unittest.main()

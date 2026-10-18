"""The server picks its models from the settings and probes the llama-server for GPU mode."""
import dataclasses
import json
import os
import socketserver
import sys
import tempfile
import threading
import types
import unittest
import urllib.request
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from src import ml as ml_package
from src.api.app import create_app
from src.api.backends import llama_probe, load_backends, model_dir
from src.api.db import ROOT
from src.api.settings import Settings
from src.ml import attributes, fakes
from tests.model_contract import check_describe

SECRET = "s" * 32
# What the llama-server answers for one name, nothing known about it: role 3's adapter turns it into a full answer.
ANSWER = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(
    {"items": [{"id": "i0", "yes": [], "unknown": [], "sugar": None, "fun": None, "species": None}]})}}]}


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
        for changes in ({"category_model": "tfidf"}, {"category_model": "embedding"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                load_backends(Settings(jwt_secret=SECRET, **changes))

    def test_an_attribute_model_it_does_not_know_stops_the_server(self):
        with self.assertRaisesRegex(ValueError, "ATTRIBUTES_MODEL=gpt does not work; use fake or qwen"):
            load_backends(Settings(jwt_secret=SECRET, attributes_model="gpt"))

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


class QwenBackendTests(unittest.TestCase):
    def stand_in(self):
        """A module shaped like role 3's src/ml/attributes.py, with nothing behind it: an AttributeDescriber that
        remembers the address it was built with and, like role 3's, refuses one that is not local."""
        module = types.ModuleType("src.ml.attributes")
        module.MODEL_VERSION = "qwen-test:v1"

        class AttributeDescriber:
            model_version = "qwen-test:v1"

            def __init__(self, server_url="http://127.0.0.1:8080"):
                if urlsplit(server_url).hostname not in ("localhost", "127.0.0.1", "::1", "host.docker.internal"):
                    raise ValueError("LLAMA_SERVER_URL must be a local HTTP server")
                self.server_url = server_url

            def describe_items(self, names, ask_model=True):
                return [None] * len(names)

        module.AttributeDescriber = AttributeDescriber
        return module

    def test_without_role_3s_module_qwen_stops_the_server_saying_to_merge_it(self):
        # The import_module call in src/api/backends.py asks for the module named src.ml.attributes; None in
        # sys.modules makes importing it fail, whether or not role 3's file is in the repository by then.
        with mock.patch.dict(sys.modules, {"src.ml.attributes": None}):
            with self.assertRaisesRegex(ValueError, "src/ml/attributes.py"):
                load_backends(Settings(jwt_secret=SECRET, attributes_model="qwen"))

    def test_a_module_the_package_still_holds_from_an_earlier_import_does_not_count_when_sys_modules_says_none(self):
        # Once role 3's file is merged, another test may import it and leave it on the src.ml package as an attribute.
        with mock.patch.object(ml_package, "attributes", self.stand_in(), create=True), \
                mock.patch.dict(sys.modules, {"src.ml.attributes": None}):
            with self.assertRaisesRegex(ValueError, "src/ml/attributes.py"):
                load_backends(Settings(jwt_secret=SECRET, attributes_model="qwen"))

    def test_a_module_that_is_there_but_cannot_import_something_shows_that_error_not_the_merge_message(self):
        # Role 3's file merged, but a package it needs (say a typo in its requirements) is not installed: saying
        # "merge role 3's branch first" would send whoever reads it the wrong way.
        settings = Settings(jwt_secret=SECRET, attributes_model="qwen")
        broken = ModuleNotFoundError("No module named 'some_dependency'", name="some_dependency")
        with mock.patch("src.api.backends.importlib.import_module", side_effect=broken):
            with self.assertRaises(ModuleNotFoundError) as caught:
                load_backends(settings)
        self.assertEqual(caught.exception.name, "some_dependency")

    def test_with_the_module_qwen_answers_through_it_and_keys_the_cache_by_its_version(self):
        module = self.stand_in()
        settings = Settings(jwt_secret=SECRET, attributes_model="qwen", llama_server_url="http://127.0.0.1:8123")
        with mock.patch.dict(sys.modules, {"src.ml.attributes": module}):
            backends = load_backends(settings)
        self.assertEqual((backends.attributes, backends.attributes_version), ("qwen", "qwen-test:v1"))
        # Settings is the only source of the address: the describer was built from it, and answers through itself.
        describer = backends.describe_items.__self__
        self.assertIsInstance(describer, module.AttributeDescriber)
        self.assertEqual(describer.server_url, settings.llama_server_url)
        check_describe(self, backends.describe_items)

    def test_qwen_with_an_address_that_is_not_local_stops_without_showing_it(self):
        # The real module decides which addresses are local; this checks what the backend does with its refusal.
        for url in ("http://example.com:8080", "http://user:secret@127.0.0.1:8080", "http://127.0.0.1:8080/v1"):
            with self.subTest(url=url):
                settings = Settings(jwt_secret=SECRET, attributes_model="qwen", llama_server_url=url)
                with self.assertRaisesRegex(ValueError, "ATTRIBUTES_MODEL=qwen needs LLAMA_SERVER_URL") as caught:
                    load_backends(settings)
                message = str(caught.exception)
                for shown in ("secret", "example.com", "/v1", "\n", "must be a local HTTP server"):
                    self.assertNotIn(shown, message)
                self.assertTrue(caught.exception.__suppress_context__, "role 3's own message must not be chained on")
        for url in ("http://localhost:8080", "http://[::1]:8080"):
            with self.subTest(url=url):
                backends = load_backends(Settings(jwt_secret=SECRET, attributes_model="qwen", llama_server_url=url))
                self.assertEqual(backends.attributes, "qwen")

    def test_the_real_module_keys_the_cache_the_way_the_seed_writes_it(self):
        backends = load_backends(Settings(jwt_secret=SECRET, attributes_model="qwen"))
        self.assertEqual(backends.attributes_version, attributes.MODEL_VERSION)
        # Only _request would reach a llama-server (one may be running on this PC), so it answers instead.
        with mock.patch.object(attributes.AttributeDescriber, "_request", return_value=ANSWER):
            answers = check_describe(self, backends.describe_items)
        self.assertEqual(len(answers), 3)
        self.assertTrue(all(answer is not None for answer in answers), answers)

    def test_the_health_check_says_cache_only_without_the_gpu_and_qwen_with_it(self):
        module = self.stand_in()
        for answering, shown in ((False, "cache_only"), (True, "qwen")):
            with self.subTest(gpu=answering), mock.patch.dict(sys.modules, {"src.ml.attributes": module}):
                backends = load_backends(Settings(jwt_secret=SECRET, attributes_model="qwen"))
                backends = dataclasses.replace(backends, gpu_probe=lambda: answering)
                client = TestClient(create_app(Settings(jwt_secret=SECRET, database_url="sqlite://"), backends))
                self.assertEqual(client.get("/api/health").json()["models"]["attributes"], shown)

    def test_the_fake_attribute_model_never_imports_role_3s_module(self):
        with mock.patch.dict(sys.modules, {"src.ml.attributes": None}):
            backends = load_backends(Settings(jwt_secret=SECRET))
        self.assertEqual((backends.attributes, backends.attributes_version), ("fake", "fake"))


if __name__ == "__main__":
    unittest.main()

"""The server picks its models from the settings and probes the llama-server for GPU mode."""
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from src.api.backends import llama_probe, load_backends
from src.api.settings import Settings
from src.ml import fakes

SECRET = "s" * 32


class Answer(BaseHTTPRequestHandler):
    """A stand-in llama-server whose /health says ok."""
    def do_GET(self):
        self.send_response(200 if self.path == "/health" else 404)
        self.end_headers()

    def log_message(self, *args):
        pass


class BackendTests(unittest.TestCase):
    def test_the_fakes_are_loaded_by_default(self):
        backends = load_backends(Settings(jwt_secret=SECRET))
        self.assertEqual((backends.category, backends.attributes), ("fake", "fake"))
        self.assertIs(backends.classify, fakes.classify)
        self.assertIs(backends.describe_items, fakes.describe_items)

    def test_asking_for_a_real_model_before_it_exists_stops_the_server(self):
        for changes in ({"category_model": "bert"}, {"attributes_model": "qwen"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                load_backends(Settings(jwt_secret=SECRET, **changes))

    def test_the_probe_is_true_while_the_llama_server_answers(self):
        server = HTTPServer(("127.0.0.1", 0), Answer)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            self.assertTrue(llama_probe(f"http://127.0.0.1:{server.server_port}")())
        finally:
            server.shutdown()
            server.server_close()

    def test_the_probe_is_false_when_nothing_listens_or_the_url_is_broken(self):
        server = HTTPServer(("127.0.0.1", 0), Answer)
        port = server.server_port
        server.server_close()  # the port was free a moment ago and nothing listens on it now
        self.assertFalse(llama_probe(f"http://127.0.0.1:{port}")())
        self.assertFalse(llama_probe("not a url")())


if __name__ == "__main__":
    unittest.main()

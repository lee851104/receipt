"""Offline adapter boundary tests; wire examples here are synthetic, not model evidence."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from model_contract import check_describe
from src.ml import attributes


def wire(ident="i0", **values):
    return {"id": ident, "yes": ["food", "drink"], "unknown": ["quick"],
            "sugar": 1, "fun": None, "species": None, **values}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.client = attributes.AttributeDescriber(model_version="test-v1", timeout=0.1)

    def answer(self, entries):
        return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"items": entries})}}]}

    def test_contract_order_duplicates_guards_and_defensive_cache(self):
        response = self.answer([wire("i1", yes=["daily"], fun="movie"), wire()])
        with patch.object(self.client, "_request", return_value=response) as request:
            result = self.client.describe_items(["示範奶茶", "示範家庭號電影組", "示範奶茶"])
            self.assertEqual(result[0]["sugar"], None)
            self.assertIsNone(result[0]["quick"])
            self.assertIs(result[0]["alcohol"], False)
            self.assertEqual(result[1]["fun"], "電影")
            self.assertIs(result[1]["bulk"], True)
            self.assertEqual(result[0], result[2])
            result[0]["drink"] = False
            self.assertIs(self.client.describe_items(["示範奶茶"], ask_model=False)[0]["drink"], True)
            check_describe(self, self.client.describe_items, ["示範奶茶", "示範家庭號電影組"])
            self.assertEqual(request.call_count, 1)

    def test_cache_only_misses_never_call_model(self):
        with patch.object(self.client, "_request", side_effect=AssertionError("must not infer")):
            self.assertEqual(self.client.describe_items(["示範新品"], ask_model=False), [None])
            self.assertEqual(self.client.describe_items([]), [])

    def test_timeout_does_not_poison_cache(self):
        with patch.object(self.client, "_request", side_effect=TimeoutError):
            self.assertEqual(self.client.describe_items(["示範無糖茶"]), [None])
        with patch.object(self.client, "_request", return_value=self.answer([wire(sugar=0)])):
            self.assertEqual(self.client.describe_items(["示範無糖茶"])[0]["sugar"], 0)

    def test_malformed_batch_is_not_cached(self):
        invalid = [self.answer([wire("wrong")]), self.answer([wire(), wire()]),
                   self.answer([wire(yes=["drink"], unknown=["drink"])]),
                   self.answer([wire(yes=["invented"])]), self.answer([wire(sugar=True)]),
                   self.answer([wire(fun="bad")]), self.answer([wire(species=[])]),
                   {"choices":[{"finish_reason":"length", "message":{"content":"{}"}}]},
                   {"choices":[]}, self.answer([wire(yes="food")])]
        for response in invalid:
            with self.subTest(response=response), patch.object(self.client, "_request", return_value=response):
                self.assertEqual(self.client.describe_items(["示範半糖茶"]), [None])
                self.assertEqual(self.client.describe_items(["示範半糖茶"], ask_model=False), [None])

    def test_model_versions_do_not_share_cache(self):
        cache = {}
        first = attributes.AttributeDescriber(model_version="v1", cache=cache)
        second = attributes.AttributeDescriber(model_version="v2", cache=cache)
        with patch.object(first, "_request", return_value=self.answer([wire()])):
            first.describe_items(["示範奶茶"])
        self.assertEqual(second.describe_items(["示範奶茶"], ask_model=False), [None])

    def test_cache_only_and_contending_inference_return_while_busy(self):
        entered, release = threading.Event(), threading.Event()
        def blocked(payload):
            entered.set()
            release.wait(3)
            return self.answer([wire()])
        with patch.object(self.client, "_request", side_effect=blocked):
            thread = threading.Thread(target=self.client.describe_items, args=(["示範奶茶"],))
            thread.start()
            try:
                self.assertTrue(entered.wait(1))
                self.assertEqual(self.client.describe_items(["示範奶茶"], ask_model=False), [None])
                self.assertEqual(self.client.describe_items(["示範奶茶"]), [None])
            finally:
                release.set()
                thread.join(3)
            self.assertFalse(thread.is_alive())

    def test_only_local_hosts_allowed(self):
        for url in ["https://example.com", "http://127.0.0.1.evil.test", "http://user@localhost", "http://localhost/?x=y"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                attributes.AttributeDescriber(server_url=url)

    def test_http_transport_posts_json_without_following_redirects(self):
        received = []
        response = self.answer([wire()])
        class Handler(BaseHTTPRequestHandler):
            def do_POST(handler):
                received.append((handler.path, json.loads(handler.rfile.read(int(handler.headers["Content-Length"])))))
                handler.send_response(200)
                handler.end_headers()
                handler.wfile.write(json.dumps(response).encode())
            def log_message(*args): pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            client = attributes.AttributeDescriber(server_url=f"http://127.0.0.1:{server.server_port}", timeout=2)
            self.assertIsNotNone(client.describe_items(["示範奶茶"])[0])
            self.assertEqual(received[0][0], "/v1/chat/completions")
            self.assertEqual(json.loads(received[0][1]["messages"][1]["content"])[0]["name"], "示範奶茶")
            self.assertEqual(received[0][1]["temperature"], 0)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_recorded_qwen_response_replays_without_gpu(self):
        from pathlib import Path
        recorded = json.loads((Path(__file__).parent / "fixtures/qwen-attributes-recorded.json").read_text(encoding="utf-8"))
        names = [item["name"] for item in json.loads(recorded["request"]["messages"][1]["content"])]
        with patch.object(self.client, "_request", return_value=recorded["response"]):
            answers = check_describe(self, self.client.describe_items, names)
        self.assertTrue(all(answer is not None for answer in answers))

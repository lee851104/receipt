"""UploadLimit judges a request by its headers alone, so it is tried on a tiny app of its own."""
import unittest

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.api.limits import UploadLimit

LIMIT = 10


async def answer(request):
    return PlainTextResponse("in")


def make_client(root_path=""):
    routes = [Route("/up", answer, methods=["GET", "POST"]), Route("/other", answer, methods=["POST"])]
    return TestClient(UploadLimit(Starlette(routes=routes), "/up", LIMIT), root_path=root_path)


class UploadLimitTests(unittest.TestCase):
    def test_a_length_up_to_the_limit_gets_through_and_one_over_is_413(self):
        with make_client() as client:
            self.assertEqual(client.post("/up", content=b"x" * LIMIT).status_code, 200)
            self.assertEqual(client.post("/up", content=b"x" * (LIMIT + 1)).status_code, 413)

    def test_only_a_post_to_the_upload_path_is_limited(self):
        with make_client() as client:  # entering it also sends the app its lifespan messages, which pass untouched
            big = b"x" * (LIMIT + 1)
            self.assertEqual(client.post("/other", content=big).status_code, 200)
            self.assertEqual(client.request("GET", "/up", content=big).status_code, 200)

    def test_behind_a_root_path_the_upload_path_is_still_limited(self):
        # uvicorn --root-path puts the prefix in front of the path it passes on, as this client does.
        with make_client(root_path="/receipt") as client:
            self.assertEqual(client.post("/receipt/up", content=b"x" * LIMIT).status_code, 200)
            self.assertEqual(client.post("/receipt/up", content=b"x" * (LIMIT + 1)).status_code, 413)
            self.assertEqual(client.post("/receipt/other", content=b"x" * (LIMIT + 1)).status_code, 200)

    def test_only_plain_digits_up_to_the_limit_are_acceptable(self):
        limit = UploadLimit(None, "/up", LIMIT)
        # A superscript two is what the byte 0xB2 reads as in latin-1: isdigit() accepts it, int() does not.
        cases = [("0", True), (str(LIMIT), True), (str(LIMIT + 1), False), ("-1", False), ("1.5", False),
                 ("", False), (" 5", False), ("\xb2", False), ("9" * 5000, False)]
        for length, accepted in cases:
            with self.subTest(length=length[:12]):
                self.assertEqual(limit.acceptable(length), accepted)


if __name__ == "__main__":
    unittest.main()

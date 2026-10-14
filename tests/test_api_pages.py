"""The same server hands out the web pages under /web/, so the pages call the API without CORS."""
import unittest

from tests.api_support import make_client


class PageTests(unittest.TestCase):
    def test_the_web_folder_is_served_next_to_the_api(self):
        client = make_client()
        page = client.get("/web/match.html")
        self.assertEqual(page.status_code, 200)
        self.assertIn("text/html", page.headers["content-type"])
        self.assertEqual(client.get("/web/trait-similarity.js").status_code, 200)

    def test_the_api_docs_and_unknown_paths_are_not_files(self):
        client = make_client()
        self.assertEqual(client.post("/api/nothing").status_code, 404)
        self.assertEqual(client.get("/api/health").json()["status"], "ok")
        self.assertEqual(client.get("/docs").status_code, 200)
        self.assertEqual(client.get("/openapi.json").json()["info"]["title"], "消費配對系統 API")


if __name__ == "__main__":
    unittest.main()

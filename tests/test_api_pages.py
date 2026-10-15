"""The same server hands out the v2 pages under /web/, so the pages call the API without CORS."""
import unittest

from tests.api_support import make_client


class PageTests(unittest.TestCase):
    def test_the_v2_folder_is_served_next_to_the_api(self):
        client = make_client()
        page = client.get("/web/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("text/html", page.headers["content-type"])
        self.assertIn("消費配對系統 v2", page.text)

    def test_the_v1_sources_are_not_served(self):
        client = make_client()
        for path in ("/web/match.html", "/web/trait-similarity.js", "/web/../web/match.html"):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 404)

    def test_the_api_docs_and_unknown_paths_are_not_files(self):
        client = make_client()
        self.assertEqual(client.post("/api/nothing").status_code, 404)
        self.assertEqual(client.get("/docs").status_code, 200)


if __name__ == "__main__":
    unittest.main()

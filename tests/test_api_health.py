"""GET /api/health answers without a login and says which models and modes are on."""
import unittest

from tests.api_support import make_client


class HealthTests(unittest.TestCase):
    def test_health_needs_no_login_and_reports_models_and_modes(self):
        response = make_client().get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "gpu_mode": False, "demo_mode": False,
                                           "models": {"category": "fake", "attributes": "fake"}})

    def test_gpu_mode_follows_the_llama_server_probe(self):
        self.assertTrue(make_client(gpu_probe=lambda: True).get("/api/health").json()["gpu_mode"])
        self.assertTrue(make_client(demo_mode=True).get("/api/health").json()["demo_mode"])

    def test_qwen_without_the_llama_server_reads_only_its_cache(self):
        down = make_client(attributes="qwen").get("/api/health").json()
        up = make_client(attributes="qwen", gpu_probe=lambda: True).get("/api/health").json()
        self.assertEqual((down["models"]["attributes"], up["models"]["attributes"]), ("cache_only", "qwen"))

    def test_unknown_api_paths_are_404(self):
        self.assertEqual(make_client().get("/api/nothing").status_code, 404)


if __name__ == "__main__":
    unittest.main()

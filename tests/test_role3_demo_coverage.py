"""All fictional accounts use the container seed and the public authenticated API."""
import unittest
from unittest.mock import Mock

from src.api import container
from src.ml.attributes import MODEL_VERSION
from tests.api_support import make_client


class DemoCoverageTests(unittest.TestCase):
    def test_all_300_accounts_have_ready_profiles_and_both_demo_only_lists(self):
        model = Mock(side_effect=AssertionError("Synthetic seed must not ask a model"))
        empty = {"similar": 0, "opposite": 0}
        with make_client(demo_mode=True, attributes="qwen", attributes_version=MODEL_VERSION,
                         describe_items=model) as client:
            summary = container.seed_demo(client.app.state.engine, True)
            self.assertEqual(summary["users"], 300)
            listed = client.get("/api/auth/demo-users").json()
            ids = {user["user_id"] for user in listed}
            self.assertEqual(len(ids), 300)
            for user in listed:
                response = client.post("/api/auth/demo-login", json={"user_id": user["user_id"]})
                self.assertEqual(response.status_code, 200)
                headers = {"Authorization": "Bearer " + response.json()["access_token"]}
                response = client.get("/api/me/profile", headers=headers)
                self.assertEqual(response.status_code, 200)
                profile = response.json()
                self.assertTrue(profile["ready"])
                self.assertEqual(profile["pending_attributes"], 0)
                for kind in empty:
                    response = client.get(f"/api/matches?kind={kind}", headers=headers)
                    self.assertEqual(response.status_code, 200)
                    body = response.json()
                    self.assertTrue(body["ready"])
                    people = body["people"]
                    empty[kind] += not people
                    self.assertLessEqual(len(people), 5)
                    self.assertTrue({person["user_id"] for person in people} <= ids - {user["user_id"]})
                    self.assertTrue(all(person["percent"] >= 30 if kind == "similar" else person["percent"] <= -10
                                        for person in people))
            model.assert_not_called()
        self.assertEqual(empty, {"similar": 0, "opposite": 0})

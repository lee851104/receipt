"""The expanded demo appends to the original population and can be seeded repeatedly."""
from collections import Counter
from pathlib import Path
import unittest
from api_support import make_client
from src.api.seed import seed_demo_users
from src.receipt.personas import build_personas
from src.receipt.traits import load_context
CONTEXT=load_context(Path(__file__).resolve().parents[1])

class PopulationTests(unittest.TestCase):
    def test_300_balanced_reproducible_people_preserve_original_40(self):
        original=build_personas(CONTEXT["calendar"])
        expanded=build_personas(CONTEXT["calendar"], total=300)
        self.assertEqual(expanded[:40], original)
        self.assertEqual(len(expanded),300)
        self.assertEqual(len({p["name"] for p in expanded}),300)
        counts=Counter(p["type"] for p in expanded)
        self.assertEqual(sorted(counts.values()),[37,37,37,37,38,38,38,38])
        self.assertEqual(expanded,build_personas(CONTEXT["calendar"],total=300))
        self.assertTrue(all(len(p["rows"])>=20 for p in expanded))
        self.assertTrue(all(r["name"].startswith("示範") and r["merchant"].startswith("示範") for p in expanded for r in p["rows"]))

    def test_existing_ids_survive_expansion_and_api_lists_300(self):
        with make_client(demo_mode=True) as client:
            engine=client.app.state.engine
            seed_demo_users(engine,build_personas(CONTEXT["calendar"]))
            before=client.get("/api/auth/demo-users").json()
            people=build_personas(CONTEXT["calendar"],total=300)
            self.assertEqual(seed_demo_users(engine,people),260)
            self.assertEqual(seed_demo_users(engine,people),0)
            after=client.get("/api/auth/demo-users").json()
            self.assertEqual(len(after),300)
            self.assertEqual(after[:40],before)

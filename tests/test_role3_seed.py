"""Only fictional receipts: seed the normal pipeline without GPU or private files."""
import copy
import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from sqlmodel import Session, select

from src.api import profiles, seed
from src.ml.attributes import MODEL_VERSION
from src.api.db import MEMORY, init_db, make_engine
from src.api.tables import Item, ItemCache, Job, Profile, User
from src.receipt.personas import build_personas
from src.receipt.traits import build_vector, load_context
from src.receipt.personas import PERIOD
from tests.api_support import fake_backends, login, make_client, register

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = load_context(ROOT)
CACHE_PATH = ROOT / "datasets/synthetic/attribute-cache.jsonl"
RECORDS = [json.loads(line) for line in CACHE_PATH.read_text(encoding="utf-8").splitlines()]


class SeedPopulationTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine(MEMORY)
        init_db(self.engine)
        self.people = build_personas(CONTEXT["calendar"])[:3]
        self.addCleanup(self.engine.dispose)

    def seed(self, people=None, **kwargs):
        self.assertTrue(callable(getattr(seed, "seed_demo_population", None)), "Seed must populate items and profiles")
        return seed.seed_demo_population(self.engine, self.people if people is None else people, CONTEXT, **kwargs)

    def snapshot(self):
        with Session(self.engine) as session:
            return {"users": [(u.id, u.username, u.display_name, u.token_key) for u in session.exec(select(User).order_by(User.id))],
                    "items": [(r.user_id, r.month, r.day, r.invoice, r.name, r.quantity, r.amount, r.category)
                              for r in session.exec(select(Item).order_by(Item.id))],
                    "profiles": [(p.user_id, p.vector, p.areas, p.item_count) for p in session.exec(select(Profile).order_by(Profile.user_id))],
                    "cache": [(c.name, c.model, c.fields) for c in session.exec(select(ItemCache).order_by(ItemCache.name))]}

    def test_all_300_have_items_ready_profiles_and_reproducible_no_gpu_results(self):
        people = build_personas(CONTEXT["calendar"], total=300)
        with patch("src.ml.attributes.describe_items", side_effect=AssertionError("No model calls during seed")):
            result = self.seed(people)
        self.assertEqual((result["users"], result["profiles"], result["cache_items"]), (300, 300, 107))
        with Session(self.engine) as session:
            users = session.exec(select(User).order_by(User.id)).all()
            self.assertEqual(len(users), 300)
            self.assertTrue(all(u.is_demo and u.password_hash is None for u in users))
            items = session.exec(select(Item)).all()
            self.assertEqual(len(items), sum(len(p["rows"]) for p in people))
            self.assertEqual({r.user_id for r in items}, {u.id for u in users})
            self.assertTrue(all(r.invoice.startswith(r.month + "-R") for r in items))
            expected = {r["name"]: r["category"] for p in people for r in p["rows"]}
            self.assertTrue(all(r.category == expected[r.name] for r in items))
            jobs = session.exec(select(Job)).all()
            self.assertEqual(len(jobs), 600)
            self.assertTrue(all(j.status == "done" and j.done == j.total for j in jobs))
            backend = fake_backends(attributes="qwen", attributes_version=MODEL_VERSION, describe_items=lambda *a, **kw: self.fail("Recompute asked a model"))
            reviewed = {r["name"]: r["attributes"] for r in RECORDS}
            for user, person in zip(users, people, strict=True):
                previous = session.get(Profile, user.id)
                self.assertIsNotNone(previous.vector)
                self.assertEqual(len(json.loads(previous.vector)), 18)
                self.assertEqual(json.loads(previous.vector), build_vector(person["rows"], PERIOD, CONTEXT, attributes=reviewed))
                self.assertGreaterEqual(previous.item_count, 20)
                before = (previous.vector, previous.areas, previous.item_count)
                profiles.recompute(session, backend, CONTEXT, user.id)
                session.expire_all()
                after = session.get(Profile, user.id)
                self.assertEqual((after.vector, after.areas, after.item_count), before)

    def test_rerun_backfills_legacy_accounts_without_duplicates_or_identity_changes(self):
        seed.seed_demo_users(self.engine, self.people[:2])
        legacy = self.snapshot()["users"]
        self.seed()
        before = self.snapshot()
        self.assertEqual(before["users"][:2], legacy)
        result = self.seed()
        self.assertEqual(result["added_users"], 0)
        self.assertEqual(self.snapshot(), before)
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(Job)).all()), 6)

    def test_appending_people_preserves_existing_accounts_and_non_demo_data(self):
        with Session(self.engine) as session:
            real = User(username="test_person", display_name="測試一般帳號")
            session.add(real)
            session.commit()
            real_id = real.id
            session.add(Profile(user_id=real_id, vector=None, item_count=0))
            session.add(Item(user_id=real_id, month="2026-05", day=1, invoice="TEST-ONLY", merchant="測試店",
                             name="測試一般品項", quantity=1, amount=50, category=0))
            session.commit()
        self.seed(self.people[:2])
        before = self.snapshot()
        self.seed()
        after = self.snapshot()
        self.assertEqual(after["users"][:3], before["users"])
        self.assertEqual(after["profiles"][0], before["profiles"][0])
        self.assertEqual([r for r in after["items"] if r[0] == real_id], [r for r in before["items"] if r[0] == real_id])

    def test_conflicting_demo_identity_stops_before_cache_or_items_are_written(self):
        seed.seed_demo_users(self.engine, self.people[:1])
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "demo_001"):
            self.seed(self.people[::-1])
        self.assertEqual(self.snapshot(), before)

    def test_invalid_or_incomplete_synthetic_cache_fails_before_database_changes(self):
        self.assertTrue(callable(getattr(seed, "seed_demo_population", None)), "Seed must populate items and profiles")
        for invalid in ("source", "review", "fields", "duplicate", "missing", "changed_values", "missing_confirmation", "old_model"):
            self.engine = make_engine(MEMORY)
            init_db(self.engine)
            self.addCleanup(self.engine.dispose)
            records = copy.deepcopy(RECORDS)
            if invalid == "old_model": records[0]["model_version"] = "old-synthetic-version"
            if invalid == "source": records[0]["source"] = "real"
            if invalid == "review": records[0]["human_confirmed"] = False
            if invalid == "fields": records[0]["attributes"].pop("food")
            if invalid == "duplicate": records.append(records[0])
            if invalid == "missing": records = []
            if invalid == "changed_values": records[0]["attributes"]["food"] = not records[0]["attributes"]["food"]
            if invalid == "missing_confirmation": records[0].pop("confirmation")
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "fictional-cache.jsonl"
                path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.seed(cache_path=path)
                self.assertEqual(self.snapshot(), {"users": [], "items": [], "profiles": [], "cache": []})

    def test_cache_uses_qwen_version_and_other_models_stay_untouched(self):
        with Session(self.engine) as session:
            session.add(ItemCache(name=RECORDS[0]["name"], model="unrelated-test-model", fields="{}"))
            session.commit()
        self.seed()
        with Session(self.engine) as session:
            cache = session.exec(select(ItemCache).where(ItemCache.model == MODEL_VERSION)).all()
            self.assertEqual(len(cache), 107)
            self.assertEqual(session.get(ItemCache, (RECORDS[0]["name"], "unrelated-test-model")).fields, "{}")
            self.assertTrue(all(p.vector is not None for p in session.exec(select(Profile))))

    def test_seeded_demo_matches_are_nonempty_and_never_include_general_accounts(self):
        self.assertTrue(callable(getattr(seed, "seed_demo_population", None)), "Seed must populate items and profiles")
        with make_client(demo_mode=True, attributes="qwen", attributes_version=MODEL_VERSION,
                         describe_items=lambda *a, **k: self.fail("No live model")) as client:
            engine = client.app.state.engine
            seed.seed_demo_population(engine, self.people, CONTEXT)
            register(client, username="test_general", display_name="測試一般帳號")
            with Session(engine) as session:
                demo = session.exec(select(User).where(User.username == "demo_001")).one()
                general = session.exec(select(User).where(User.username == "test_general")).one()
                original = session.get(Profile, demo.id)
                session.add(Profile(user_id=general.id, vector=original.vector, areas=original.areas, item_count=original.item_count))
                session.commit()
                demo_id, general_id = demo.id, general.id
                demo_ids = {u.id for u in session.exec(select(User).where(User.is_demo))}
            token = client.post("/api/auth/demo-login", json={"user_id": demo_id}).json()["access_token"]
            headers = {"Authorization": "Bearer " + token}
            profile = client.get("/api/me/profile", headers=headers).json()
            self.assertTrue(profile["ready"])
            self.assertEqual(profile["pending_attributes"], 0)
            response = client.get("/api/matches", headers=headers)
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertTrue(body["ready"])
            self.assertTrue(body["people"])
            self.assertTrue({p["user_id"] for p in body["people"]} <= demo_ids - {demo_id})
            self.assertEqual(body["eligible"], len(demo_ids) - 1)
            self.assertNotIn(general_id, {p["user_id"] for p in body["people"]})
            general_matches = client.get("/api/matches", headers=login(client, username="test_general")).json()
            self.assertTrue({p["user_id"] for p in general_matches["people"]} & demo_ids)

    def test_conflicting_cache_and_unfinished_jobs_are_not_overwritten(self):
        self.seed(self.people[:1])
        with Session(self.engine) as session:
            entry = session.get(ItemCache, (RECORDS[0]["name"], MODEL_VERSION))
            entry.fields = "{}"
            session.add(entry)
            session.commit()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "cache differs"):
            self.seed()
        self.assertEqual(self.snapshot(), before)
        with Session(self.engine) as session:
            entry = session.get(ItemCache, (RECORDS[0]["name"], MODEL_VERSION))
            entry.fields = json.dumps(RECORDS[0]["attributes"], ensure_ascii=False)
            session.add(entry)
            session.add(Job(user_id=before["users"][0][0], month="2026-05", status="running"))
            session.commit()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "unfinished demo jobs"):
            self.seed()
        self.assertEqual(self.snapshot(), before)

    def test_command_entrypoint_populates_profiles_without_reading_env_files(self):
        from src.api.settings import Settings
        from tests.api_support import SECRET
        settings = Settings(jwt_secret=SECRET, database_url=MEMORY, attributes_model="fake")
        with patch.object(seed, "load_dotenv"), \
             patch.object(seed.Settings, "from_env", return_value=settings), \
             patch.object(seed, "make_engine", return_value=self.engine), \
             patch.object(self.engine, "dispose"), \
             patch.object(seed, "build_personas", return_value=self.people) as generate, redirect_stdout(io.StringIO()):
            seed.main()
        generate.assert_called_once_with(CONTEXT["calendar"], total=300)
        self.assertEqual(len(self.snapshot()["profiles"]), len(self.people))
        self.assertEqual({r[1] for r in self.snapshot()["cache"]}, {MODEL_VERSION})

    def test_failed_seed_job_can_be_retried(self):
        from src.api.jobs import update

        def crash(session, job, *args):
            update(session, job, status="running")
            raise RuntimeError("synthetic test failure")

        with patch.object(seed, "process", side_effect=crash), self.assertRaisesRegex(RuntimeError, "synthetic test failure"):
            self.seed()
        with Session(self.engine) as session:
            self.assertEqual([j.status for j in session.exec(select(Job))], ["failed"])
        result = self.seed()
        self.assertEqual(result["profiles"], 3)
        with Session(self.engine) as session:
            self.assertTrue(all(j.status == "done" for j in session.exec(select(Job))))

    def test_complete_current_population_skips_jobs_and_database_writes(self):
        from sqlalchemy import event
        self.seed()
        statements = []
        def track(conn, cursor, statement, parameters, context, many):
            if statement.lstrip().split()[0].upper() in ("INSERT", "UPDATE", "DELETE"):
                statements.append(statement)
        event.listen(self.engine, "before_cursor_execute", track)
        try:
            with patch.object(seed, "process", side_effect=AssertionError("Complete seed must skip processing")):
                result = self.seed()
        finally:
            event.remove(self.engine, "before_cursor_execute", track)
        self.assertEqual(statements, [])
        self.assertEqual(result["skipped"], True)
        self.assertEqual(result["added_users"], 0)

    def test_incomplete_or_stale_population_is_repaired_instead_of_skipped(self):
        for fault in ("item", "item_value", "profile", "profile_value", "area", "cache", "old_version", "job"):
            with self.subTest(fault=fault):
                engine = make_engine(MEMORY)
                init_db(engine)
                try:
                    seed.seed_demo_population(engine, self.people[:1], CONTEXT)
                    with Session(engine) as session:
                        item = session.exec(select(Item)).first()
                        profile = session.exec(select(Profile)).first()
                        if fault == "item": session.delete(item)
                        if fault == "item_value":
                            item.amount += 1
                            session.add(item)
                        if fault == "profile": session.delete(profile)
                        if fault == "profile_value":
                            profile.vector = "[0]"
                            session.add(profile)
                        if fault == "area":
                            profile.areas = "[]"
                            session.add(profile)
                        if fault == "cache":
                            session.delete(session.get(ItemCache, (item.name, MODEL_VERSION)))
                        if fault == "old_version":
                            for entry in session.exec(select(ItemCache)).all():
                                entry.model = "old-synthetic-version"
                                session.add(entry)
                        if fault == "job":
                            session.delete(session.exec(select(Job)).first())
                        session.commit()
                    with patch.object(seed, "process", wraps=seed.process) as process:
                        result = seed.seed_demo_population(engine, self.people[:1], CONTEXT)
                    self.assertFalse(result["skipped"])
                    self.assertEqual(process.call_count, 2)
                    with patch.object(seed, "process", side_effect=AssertionError("Repair should be complete")):
                        self.assertTrue(seed.seed_demo_population(engine, self.people[:1], CONTEXT)["skipped"])
                finally:
                    engine.dispose()

    def test_complete_population_with_too_few_items_keeps_null_vector_and_skips(self):
        people = copy.deepcopy(self.people[:1])
        people[0]["rows"] = people[0]["rows"][:1]
        self.seed(people)
        with Session(self.engine) as session:
            self.assertIsNone(session.exec(select(Profile)).one().vector)
        with patch.object(seed, "process", side_effect=AssertionError("A valid null vector is complete")):
            self.assertTrue(self.seed(people)["skipped"])

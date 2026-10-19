"""Put fictional users, parsed receipts, reviewed attributes and computed profiles in the database. Run from the repository root:

    .venv/Scripts/python.exe -m src.api.seed

Stop the API server before seeding. No GPU or live model is used.
The list of fictional people may only grow at the end. Identity or cache conflicts stop the seed;
resolve the conflicting fixtures or use a separate demo database, never delete a database holding real accounts.
"""
import csv
import hashlib
import json
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session, col, delete, select

from ..ml.fields import FIELDS
from ..ml.attributes import MODEL_VERSION
from ..receipt.invoices import REQUIRED, build_month
from ..receipt import places, traits
from .profiles import months_of
from ..receipt.personas import build_personas
from ..receipt.traits import load_context
from .backends import Backends
from .db import ROOT, init_db, make_engine
from .jobs import UNFINISHED, mark_failed, process
from .settings import Settings
from .tables import Item, ItemCache, Job, Profile, User


def clash(username, user, person):
    """Why the database user at username is not the fictional person meant to be there, or None when it is."""
    if user.is_demo and user.display_name == person["name"]:
        return None
    holder = repr(user.display_name) + ("" if user.is_demo else " (a real account)")
    return f"{username} is {holder} in the database but {person['name']!r} in the list"


def seed_demo_users(engine, people):
    """One demo user per fictional person, demo_001 onwards by position, adding only the ones not there yet.
    A username held by anyone else stops the seed. The list may only grow at the end: a shorter list leaves the
    extra demo users in place."""
    wanted = {f"demo_{index:03}": person for index, person in enumerate(people, start=1)}
    with Session(engine) as session:
        existing = {user.username: user
                    for user in session.exec(select(User).where(col(User.username).in_(list(wanted)))).all()}
        wrong = [clash(username, existing[username], person) for username, person in wanted.items()
                 if username in existing]
        wrong = [message for message in wrong if message]
        if wrong:
            raise ValueError("; ".join(wrong) + ". Delete the database file and run the seed again.")
        for username, person in wanted.items():
            if username not in existing:
                session.add(User(username=username, display_name=person["name"], is_demo=True,
                                 persona=person["type"]))
        session.commit()
    return len(wanted) - len(existing)


def synthetic_cache(path):
    """Reviewed public fixtures only; their original model/version provenance remains in the JSONL."""
    records = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]
    cache = {}
    for record in records:
        fields = record.get("attributes")
        if (record.get("source") != "synthetic" or record.get("human_confirmed") is not True
                or record.get("review_status") not in ("human_confirmed", "human_corrected")
                or record.get("model_version") != MODEL_VERSION or not isinstance(fields, dict) or set(fields) != set(FIELDS)
                or not record.get("name", "").startswith("示範") or record["name"] in cache):
            raise ValueError("Seed requires unique, human-reviewed synthetic attribute records")
        boolean = set(FIELDS) - {"sugar", "fun", "species"}
        if (any(fields[key] is not None and type(fields[key]) is not bool for key in boolean)
                or fields["sugar"] is not None and (type(fields["sugar"]) not in (int, float) or fields["sugar"] not in (0, .2, .3, .5, .7, 1))
                or fields["fun"] not in (None, "電影", "唱歌", "展演", "遊樂")
                or fields["species"] not in (None, "cat", "dog")):
            raise ValueError("Invalid synthetic attribute fields")
        confirmation = record.get("confirmation")
        digest = hashlib.sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if (not isinstance(confirmation, dict) or confirmation.get("confirmed_by") != "user"
                or not confirmation.get("date") or not confirmation.get("source")
                or confirmation.get("attributes_sha256") != digest):
            raise ValueError("Synthetic attributes must match their human confirmation")
        cache[record["name"]] = fields
    return cache


def synthetic_months(person):
    """Serialize fictional invoice lines, then use the upload parser (including address and invoice coding)."""
    groups = defaultdict(list)
    for row in person["rows"]:
        groups[row["date"].strftime("%Y-%m")].append(row)
    months = {}
    with tempfile.TemporaryDirectory(prefix="receipt-synthetic-") as folder:
        path = Path(folder) / "fictional.csv"
        for month, rows in sorted(groups.items()):
            with path.open("w", encoding="utf-8-sig", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=[*REQUIRED, "賣方地址"])
                writer.writeheader()
                for row in rows:
                    writer.writerow({"發票日期": row["date"].strftime("%Y%m%d"), "發票狀態": "開立已確認",
                                     "發票號碼": row["invoice"], "賣方名稱": row["merchant"],
                                     "賣方地址": row["district"] + "示範路1號" if row["district"] else "",
                                     "消費明細_品名": row["name"], "消費明細_數量": row["quantity"],
                                     "消費明細_金額": row["amount"]})
            key, parsed = build_month(path, {}, for_upload=True)
            months[key] = parsed["rows"]
    return months


ITEM_FIELDS = ("month", "day", "invoice", "merchant", "district", "name", "quantity", "amount", "category")


def population_complete(session, usernames, people, months, categories, cache, context):
    """Read-only comparison with current fixtures and taste rules; never trust counts alone."""
    users = {u.username: u for u in session.exec(select(User).where(col(User.username).in_(usernames)))}
    if len(users) != len(usernames):
        return False
    if any(clash(name, users[name], person) for name, person in zip(usernames, people, strict=True)):
        return False  # seed_demo_users will report the identity conflict before writing
    ids = [user.id for user in users.values()]
    items, jobs = defaultdict(list), defaultdict(list)
    for item in session.exec(select(Item).where(col(Item.user_id).in_(ids)).order_by(Item.id)):
        items[item.user_id].append(item)
    for job in session.exec(select(Job).where(col(Job.user_id).in_(ids))):
        jobs[job.user_id].append(job)
    profiles = {p.user_id: p for p in session.exec(select(Profile).where(col(Profile.user_id).in_(ids)))}
    for username, person_months in zip(usernames, months, strict=True):
        user = users[username]
        expected = [(month, *(row[key] for key in ITEM_FIELDS[1:-1]), categories[row["name"]])
                    for month, rows in person_months.items() for row in rows]
        actual = [tuple(getattr(item, key) for key in ITEM_FIELDS) for item in items[user.id]]
        if actual != expected:
            return False
        counts = {month: len({row["name"] for row in rows}) for month, rows in person_months.items()}
        finished = jobs[user.id]
        if (len(finished) != len(counts) or {j.month for j in finished} != set(counts)
                or any(j.status != "done" or j.done != counts[j.month] or j.total != counts[j.month]
                       for j in finished)):
            return False
        profile = profiles.get(user.id)
        if profile is None or profile.item_count != len(expected):
            return False
        rows, period = traits.dated(months_of(items[user.id]))
        try:
            vector = None if profile.vector is None else json.loads(profile.vector)
            if (vector != traits.build_vector(rows, period, context, attributes=cache)
                    or json.loads(profile.areas) != places.areas_of(rows, context)):
                return False
        except (ValueError, TypeError):
            return False
    return True


def seed_demo_population(engine, people, context, *, cache_path=None):
    """Backfill demo purchases and profiles through the normal upload job, without querying any live model.

    Run with the server stopped. Account ids/tokens remain stable; each requested demo's receipts and finished
    jobs are replaced when incomplete or stale. A complete current population skips all writes and jobs;
    items, completed month jobs, versioned cache and profiles are compared first. Other accounts and other
    model caches are untouched.
    The cache always uses MODEL_VERSION, regardless of ATTRIBUTES_MODEL. These are human-reviewed Qwen
    fixtures (46 of 107 corrected), not untouched model output; the JSONL retains predictions and provenance.
    """
    cache = synthetic_cache(cache_path or ROOT / "datasets/synthetic/attribute-cache.jsonl")
    categories = {}
    for person in people:
        if not person.get("rows"):
            raise ValueError("A synthetic person needs invoice rows")
        for row in person["rows"]:
            name, category = row["name"], row["category"]
            if name not in cache or type(category) is not int or not 0 <= category < 10:
                raise ValueError("Every synthetic item needs reviewed attributes and a category")
            if name in categories and categories[name] != category:
                raise ValueError("Synthetic categories must agree per name")
            categories[name] = category
    months = [synthetic_months(person) for person in people]
    usernames = [f"demo_{i:03}" for i in range(1, len(people) + 1)]
    summary = {"users": len(people), "profiles": len(people), "cache_items": len(cache),
               "items": sum(len(rows) for person in months for rows in person.values())}
    with Session(engine) as session:
        # Refuse a conflicting cache rather than replace a value another account may already use.
        existing = session.exec(select(ItemCache).where(ItemCache.model == MODEL_VERSION,
                                                        col(ItemCache.name).in_(list(cache)))).all()
        if any(json.loads(entry.fields) != cache[entry.name] for entry in existing):
            raise ValueError("Synthetic cache differs from stored answers; review the cache model before seeding")
        ids = session.exec(select(User.id).where(col(User.username).in_(usernames))).all()
        if session.exec(select(Job).where(col(Job.user_id).in_(ids), col(Job.status).in_(UNFINISHED))).first():
            raise ValueError("Stop unfinished demo jobs before seeding")
        if len(existing) == len(cache) and population_complete(
                session, usernames, people, months, categories, cache, context):
            return {**summary, "added_users": 0, "skipped": True}
    added = seed_demo_users(engine, people)  # checks every account collision before adding any user

    def classify(names):
        return [{"category": categories[name], "probs": [float(i == categories[name]) for i in range(10)]}
                for name in names]

    def no_model(*args, **kwargs):
        raise AssertionError("Synthetic seed must be fully cached")

    backend = Backends(category="synthetic-recorded", classify=classify, attributes="qwen", attributes_version=MODEL_VERSION,
                       describe_items=no_model, gpu_probe=lambda: False)
    settings = SimpleNamespace(category_min_prob=0.5)
    with Session(engine) as session:
        if cache:
            session.exec(insert(ItemCache).values([{"name": name, "model": MODEL_VERSION,
                                                   "fields": json.dumps(fields, ensure_ascii=False)}
                                                  for name, fields in cache.items()]).on_conflict_do_nothing())
        session.commit()
        for username, person_months in zip(usernames, months, strict=True):
            user = session.exec(select(User).where(User.username == username)).one()
            session.exec(delete(Item).where(Item.user_id == user.id))
            session.exec(delete(Job).where(Job.user_id == user.id))
            session.commit()
            for month, rows in person_months.items():
                session.add_all([Item(user_id=user.id, month=month,
                                      **{key: row[key] for key in ("day", "invoice", "merchant", "district", "name", "quantity", "amount")})
                                 for row in rows])
                job = Job(user_id=user.id, month=month)
                session.add(job)
                session.commit()
                job_id = job.id
                try:
                    process(session, job, backend, settings, context)
                except Exception:
                    mark_failed(session, job_id)
                    raise
    return {**summary, "added_users": added, "skipped": False}


def main():
    load_dotenv(ROOT / ".env")
    engine = None
    try:
        settings = Settings.from_env(os.environ)
        engine = make_engine(settings.database_url)
        init_db(engine)
        context = load_context(ROOT)
        people = build_personas(context["calendar"], total=300)
        result = seed_demo_population(engine, people, context)
    except ValueError as error:  # a bad setting, or a database that no longer matches the list
        sys.exit(f"error: {error}")
    finally:
        if engine is not None:
            engine.dispose()
    print(json.dumps(result))


if __name__ == "__main__":
    main()

"""A user's taste profile: their stored items run through the taste pipeline, kept in the profiles table."""
import calendar
import json

from sqlalchemy.dialects.sqlite import insert
from sqlmodel import select

from ..receipt import places, traits
from ..receipt.signals import measure
from . import cache
from .tables import Item, Profile, now


def months_of(items):
    """Stored items as report months, shaped like invoices.build_month's: {"2026-05": {"year", "monthNumber",
    "month", "days", "rows"}}. Months and rows go by date; lines of one day keep the order they were given in."""
    months = {}
    for item in sorted(items, key=lambda item: (item.month, item.day)):
        if item.month not in months:
            year, number = map(int, item.month.split("-"))
            months[item.month] = {"year": year, "monthNumber": number, "month": f"{year} 年 {number} 月",
                                  "days": calendar.monthrange(year, number)[1], "rows": []}
        # Stored items are never provisional: a name the model was unsure of has category 10 instead.
        months[item.month]["rows"].append({
            "day": item.day, "invoice": item.invoice, "merchant": item.merchant, "district": item.district,
            "name": item.name, "quantity": item.quantity, "amount": item.amount, "category": item.category,
            "provisional": False})
    return months


def stored_vector(profile, size):
    """A profile's taste vector, or None without a profile or with too few items for one. A vector of another length
    was stored before configs/traits.json changed: fail (a 500) rather than read its values into the wrong traits."""
    if profile is None or profile.vector is None:
        return None
    vector = json.loads(profile.vector)
    if len(vector) != size:
        raise ValueError("a stored taste vector has the wrong length; work every profile out again")
    return vector


def attributes_of(session, backends, names):
    """{name: the 23 attribute fields, or None} from the cache of the current attribute model alone. It never asks
    the model and never writes: a name nobody has judged yet is None, which the pipeline treats as pending."""
    known = cache.cached(session, backends, names)
    return {name: known.get(name) for name in names}


def history(session, backends, user_id):
    """The user's stored items as dated rows and the (year, month) period they cover, with the cached attribute
    answers of their names ({} without a period). It only reads: the model is never asked."""
    items = session.exec(select(Item).where(Item.user_id == user_id).order_by(Item.id)).all()
    rows, period = traits.dated(months_of(items))
    return rows, period, attributes_of(session, backends, {row["name"] for row in rows}) if period else {}


def recompute(session, backends, context, user_id):
    """Work the user's profile out again from all their items and store it, replacing the old one in one statement,
    so a failure before it leaves the old profile as it was."""
    rows, period, attributes = history(session, backends, user_id)
    if period:
        item_count = measure(rows, period, context, attributes)["counts"]["items"]
        vector, areas = traits.build_vector(rows, period, context, attributes), places.areas_of(rows, context)
    else:
        # Nothing to measure, and measure divides by the number of months.
        item_count, vector, areas = 0, None, []
    values = {"vector": None if vector is None else json.dumps(vector, allow_nan=False),
              "areas": json.dumps(areas), "item_count": item_count, "updated_at": now()}
    statement = insert(Profile).values(user_id=user_id, **values)
    session.exec(statement.on_conflict_do_update(index_elements=["user_id"], set_=values))
    session.commit()

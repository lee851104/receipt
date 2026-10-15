"""A user's taste profile: their stored items run through the taste pipeline, kept in the profiles table."""
import calendar
import json

from sqlalchemy.dialects.sqlite import insert
from sqlmodel import col, select

from ..receipt import places, traits
from ..receipt.signals import measure
from .tables import Item, ItemCache, Profile, now


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


def attributes_of(session, backends, names):
    """{name: the 23 attribute fields, or None} from the cache of the current attribute model alone. It never asks
    the model and never writes: a name nobody has judged yet is None, which the pipeline treats as pending."""
    rows = session.exec(select(ItemCache).where(ItemCache.model == backends.attributes,
                                                col(ItemCache.name).in_(list(names)))).all()
    known = {row.name: json.loads(row.fields) for row in rows}
    return {name: known.get(name) for name in names}


def recompute(session, backends, context, user_id):
    """Work the user's profile out again from all their items and store it, replacing the old one in one statement,
    so a failure before it leaves the old profile as it was."""
    items = session.exec(select(Item).where(Item.user_id == user_id).order_by(Item.id)).all()
    rows, period = traits.dated(months_of(items))
    if period:
        attributes = attributes_of(session, backends, {row["name"] for row in rows})
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

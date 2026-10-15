"""Attributes through the item_cache table, so each product name is judged once per attribute model."""
import json

from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session, col, select

from .tables import ItemCache


def model_ready(backends):
    """Whether the attribute model can judge a name now: the fake always, Qwen only while its llama-server answers."""
    return backends.attributes == "fake" or backends.gpu_probe()


def describe(session, backends, names, ask_model):
    """Each name's 23 attribute fields, or None while it is not analysed yet. The cache answers first; for the rest
    the model is asked (only its own cache unless ask_model and the model is ready), and new answers are stored."""
    rows = session.exec(select(ItemCache).where(ItemCache.model == backends.attributes,
                                                col(ItemCache.name).in_(names))).all()
    known = {row.name: json.loads(row.fields) for row in rows}
    # End the read here: its open transaction would keep a connection checked out through the slow model call below.
    session.commit()
    missing = [name for name in dict.fromkeys(names) if name not in known]
    if missing:
        answers = backends.describe_items(missing, ask_model=ask_model and model_ready(backends))
        found = {name: fields for name, fields in zip(missing, answers, strict=True) if fields is not None}
        if found:
            rows = [{"name": name, "model": backends.attributes, "fields": json.dumps(fields)}
                    for name, fields in found.items()]
            # Another upload may store the same name at the same moment: the first answer stays and nothing fails.
            session.exec(insert(ItemCache).values(rows).on_conflict_do_nothing())
            session.commit()
        known.update(found)
    return [known.get(name) for name in names]


def describe_later(engine, backends, name):
    """Judge one name in the background, for the classify box: its answer is waiting in the cache next time."""
    with Session(engine) as session:
        describe(session, backends, [name], ask_model=True)

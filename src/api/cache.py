"""Attributes through the item_cache table, so each product name is judged once per attribute model."""
import json
import logging
import threading

from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session, col, select

from .tables import ItemCache

log = logging.getLogger(__name__)


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


class Judging:
    """The names the classify box has being judged in the background right now. The page asks about a pending name
    again every 2 seconds, up to 5 times, and each ask would otherwise send the same name to the model once more."""

    def __init__(self):
        self.names = set()
        self.lock = threading.Lock()  # requests run on many threads at once

    def take(self, name):
        """True when nobody is judging the name and the caller now is; False while it is judged already."""
        with self.lock:
            if name in self.names:
                return False
            self.names.add(name)
            return True

    def drop(self, name):
        with self.lock:
            self.names.discard(name)


def describe_later(engine, backends, name, judging):
    """Judge one name in the background, for the classify box: its answer is waiting in the cache next time. The
    name was taken in judging, and is dropped from it however this ends."""
    # The answer has gone out already, so a failure is only logged; the name stays pending and is asked again
    # next time. The log leaves the name out: it may be a real product name.
    try:
        with Session(engine) as session:
            describe(session, backends, [name], ask_model=True)
    except Exception:
        log.exception("judging a name in the background failed")
    finally:
        judging.drop(name)

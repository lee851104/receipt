"""The half of an upload that runs after the answer: categories, then attributes, then the job is done."""
import logging
import threading

from sqlmodel import Session, col, select

from . import cache
from .tables import Item, Job

PENDING = 10   # 待確認: the model was not sure enough, so the item stays out of the taste vector
BATCH = 20     # names judged between two progress updates
UNFINISHED = ("queued", "running")
# One job runs at a time: there is a single llama-server, SQLite has a single writer, and the next batch updates a
# profile at the end of a job. A waiting job holds no connection and honestly stays "queued".
WORK = threading.Lock()
log = logging.getLogger(__name__)


def update(session, job, **changes):
    for key, value in changes.items():
        setattr(job, key, value)
    session.add(job)
    session.commit()


def classify_items(session, job, backends, min_prob, names):
    """Store each name's category on the job's items: the model's first choice, or 10 below min_prob."""
    chosen = {}
    # strict: a model that answers for fewer names fails the job instead of leaving names pending unnoticed.
    for name, answer in zip(names, backends.classify(names), strict=True):
        category = answer["category"]
        chosen[name] = category if answer["probs"][category] >= min_prob else PENDING
    items = session.exec(select(Item).where(Item.user_id == job.user_id, Item.month == job.month)).all()
    for item in items:
        # Only these names: a newer upload of the same month may have replaced the items meanwhile; its own job
        # classifies those.
        if item.name in chosen:
            item.category = chosen[item.name]
            session.add(item)
    session.commit()


def process(session, job, backends, settings):
    names = sorted(set(session.exec(select(Item.name).where(Item.user_id == job.user_id,
                                                            Item.month == job.month)).all()))
    update(session, job, status="running", done=0, total=len(names), message="分類品名")
    if backends.category == "unavailable":
        update(session, job, status="failed", message="分類模型無法使用，請稍後重新上傳")
        return
    classify_items(session, job, backends, settings.category_min_prob, names)
    update(session, job, message="判斷品項屬性")
    for start in range(0, len(names), BATCH):
        batch = names[start:start + BATCH]
        # A name the model cannot judge now (no GPU) stays pending, yet counts as handled.
        cache.describe(session, backends, batch, ask_model=True)
        update(session, job, done=job.done + len(batch))
    update(session, job, status="done", message="完成")


def mark_failed(session, job_id):
    """Fail the job after a crash. It may be gone (its account was deleted meanwhile) and the database may be what
    crashed, so a write that does not work is logged instead of raised: nothing can be done about it here, and the
    next start-up fails the job anyway."""
    try:
        session.rollback()
        job = session.get(Job, job_id)
        if job is not None:
            update(session, job, status="failed", message="處理失敗，請重新上傳")
    except Exception:
        log.exception("could not mark upload job %s failed", job_id)


def run_job(engine, backends, settings, job_id):
    """Background task for one upload. Any crash marks the job failed instead of leaving it running. A job whose
    account was deleted meanwhile has nothing left to do."""
    with WORK, Session(engine) as session:
        try:
            job = session.get(Job, job_id)
            if job is None:
                return
            process(session, job, backends, settings)
        except Exception:
            log.exception("upload job %s failed", job_id)
            mark_failed(session, job_id)


def fail_unfinished(engine):
    """At start-up nothing is running any more: jobs left queued or running by a stop are failed, to be uploaded
    again."""
    with Session(engine) as session:
        for job in session.exec(select(Job).where(col(Job.status).in_(UNFINISHED))).all():
            job.status, job.message = "failed", "服務重新啟動，請重新上傳"
            session.add(job)
        session.commit()

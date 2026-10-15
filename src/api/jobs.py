"""The half of an upload that runs after the answer: categories, then attributes, then the job is done."""
import logging

from sqlmodel import Session, col, select

from . import cache
from .tables import Item, Job

PENDING = 10   # 待確認: the model was not sure enough, so the item stays out of the taste vector
BATCH = 20     # names judged between two progress updates
UNFINISHED = ("queued", "running")
log = logging.getLogger(__name__)


def update(session, job, **changes):
    for key, value in changes.items():
        setattr(job, key, value)
    session.add(job)
    session.commit()


def classify_items(session, job, backends, min_prob, names):
    """Store each name's category on the job's items: the model's first choice, or 10 below min_prob."""
    chosen = {}
    for name, answer in zip(names, backends.classify(names)):
        category = answer["category"]
        chosen[name] = category if answer["probs"][category] >= min_prob else PENDING
    items = session.exec(select(Item).where(Item.user_id == job.user_id, Item.month == job.month,
                                            col(Item.name).in_(list(chosen)))).all()
    # Only these names: a newer upload of the same month may have replaced the items meanwhile; its own job
    # classifies those.
    for item in items:
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


def run_job(engine, backends, settings, job_id):
    """Background task for one upload. Any crash marks the job failed instead of leaving it running."""
    with Session(engine) as session:
        job = session.get(Job, job_id)
        try:
            process(session, job, backends, settings)
        except Exception:
            log.exception("upload job %s failed", job_id)
            session.rollback()
            update(session, session.get(Job, job_id), status="failed", message="處理失敗，請重新上傳")


def fail_unfinished(engine):
    """At start-up nothing is running any more: jobs left queued or running by a stop are failed, to be uploaded
    again."""
    with Session(engine) as session:
        for job in session.exec(select(Job).where(col(Job.status).in_(UNFINISHED))).all():
            job.status, job.message = "failed", "服務重新啟動，請重新上傳"
            session.add(job)
        session.commit()

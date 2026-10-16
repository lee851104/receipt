"""The half of an upload that runs after the answer: categories, then attributes, then the taste profile, then the
job is done."""
import logging
import queue
import threading
from functools import partial

from sqlmodel import Session, col, select
from sqlmodel import update as update_rows

from . import cache, profiles
from .tables import Item, Job, User

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
    by_category = {}
    # strict: a model that answers for fewer names fails the job instead of leaving names pending unnoticed.
    for name, answer in zip(names, backends.classify(names), strict=True):
        category = answer["category"]
        by_category.setdefault(category if answer["probs"][category] >= min_prob else PENDING, []).append(name)
    # One UPDATE per category, matched by name, never by row: a newer upload of the same month may replace the items
    # at any moment, and its rows can take the old rows' ids. Its names that are not among these wait for its own
    # job; a name both uploads have gets the same category either way.
    for category, group in by_category.items():
        session.exec(update_rows(Item).values(category=category)
                     .where(Item.user_id == job.user_id, Item.month == job.month, col(Item.name).in_(group)))
    session.commit()


def process(session, job, backends, settings, context):
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
    update(session, job, message="重算品味向量")
    profiles.recompute(session, backends, context, job.user_id)
    # Last, because an upload deletes the finished jobs of its month: a job that says done has written everything.
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


def run_job(engine, backends, settings, context, job_id):
    """One upload's job, run by the Worker. Any crash marks the job failed instead of leaving it running. A job
    whose account was deleted meanwhile has nothing left to do."""
    with Session(engine) as session:
        try:
            job = session.get(Job, job_id)
            if job is None:
                return
            process(session, job, backends, settings, context)
        except Exception:
            log.exception("upload job %s failed", job_id)
            mark_failed(session, job_id)


def run_recompute(engine, backends, context, user_id):
    """Work a user's profile out again on the worker, as after a month of theirs was deleted. An account deleted while
    this waited has nothing left to recompute."""
    with Session(engine) as session:
        if session.get(User, user_id) is None:
            return
        profiles.recompute(session, backends, context, user_id)


class Worker:
    """The app's one thread for upload jobs, which runs them one at a time in the order they were queued: there is a
    single llama-server, SQLite has a single writer, and the next batch updates a profile at the end of a job. A
    waiting job is only an id in the queue, so it holds no connection or request thread and honestly stays "queued".
    A daemon thread, so stopping the server never waits for a running job; the next start-up fails it instead.
    Besides uploads, the profile recompute after a month is deleted is queued here too."""

    def __init__(self, run):
        self.run = run  # run(job_id) does one job
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self.loop, name="upload-jobs", daemon=True)
        self.thread.start()

    def add(self, job_id):
        """Queue an upload's job."""
        self.call(f"upload job {job_id}", partial(self.run, job_id))

    def call(self, label, task):
        """Queue other work that writes profiles, such as the recompute after a month is deleted. It waits behind the
        uploads queued before it, so two writes of one profile never overlap; label names it in the log."""
        self.queue.put((label, task))

    def loop(self):
        while True:
            label, task = self.queue.get()
            try:
                task()
            # run_job already fails a job that crashes; this keeps anything else from ending the loop, which would
            # leave every later job queued until a restart.
            except Exception:
                log.exception("%s failed", label)
            finally:
                self.queue.task_done()


def fail_unfinished(engine):
    """At start-up nothing is running any more: jobs left queued or running by a stop are failed, to be uploaded
    again."""
    with Session(engine) as session:
        for job in session.exec(select(Job).where(col(Job.status).in_(UNFINISHED))).all():
            job.status, job.message = "failed", "服務重新啟動，請重新上傳"
            session.add(job)
        session.commit()

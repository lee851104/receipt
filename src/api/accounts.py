"""What a user can delete: a month of their uploads or the whole account, and with it the attribute answers no stored
item needs any more. Nothing here commits; the route does, so each deletion is one transaction."""
from sqlmodel import col, delete, select

from .jobs import UNFINISHED
from .tables import Item, ItemCache, Job, Profile, User

# Names per statement when forgetting answers: SQLite takes at most 32,766 variables in one, and an account may have
# more names than that.
CHUNK = 10_000


def uploaded_months(session, user_id):
    """The months the user uploaded, oldest first: those with items, and those with a job even if no line was kept.
    (profiles.months_of is another thing: the stored items as report months.)"""
    with_items = session.exec(select(Item.month).where(Item.user_id == user_id).distinct()).all()
    with_jobs = session.exec(select(Job.month).where(Job.user_id == user_id).distinct()).all()
    return sorted(set(with_items) | set(with_jobs))


def busy(session, user_id, month=None):
    """Whether the user has an upload job queued or running, of that month when one is given."""
    query = select(Job.id).where(Job.user_id == user_id, col(Job.status).in_(UNFINISHED))
    if month is not None:
        query = query.where(Job.month == month)
    return session.exec(query.limit(1)).first() is not None


def forget_unused(session, names):
    """Delete every model's answers for those of names that no stored item has any more. A name only the classify box
    was asked about is nobody's, so it is never among the names a deletion passes here."""
    names = list(names)
    still_used = select(Item.name)  # no names bound here, so a chunk's names are its only variables
    for start in range(0, len(names), CHUNK):
        chunk = names[start:start + CHUNK]
        session.exec(delete(ItemCache).where(col(ItemCache.name).in_(chunk), col(ItemCache.name).not_in(still_used)))


def delete_month(session, user_id, month):
    """Delete one month's items and jobs, then the answers only they used. False instead, with only the items deleted
    for the caller to roll back, while an upload job of that month is queued or running. The items go before that
    check because their delete takes SQLite's write lock: an upload of the month cannot commit its job between the
    check and the deletes, and the jobs go after it because the check reads them."""
    names = list(set(session.exec(select(Item.name).where(Item.user_id == user_id, Item.month == month)).all()))
    session.exec(delete(Item).where(Item.user_id == user_id, Item.month == month))
    if busy(session, user_id, month):
        return False
    session.exec(delete(Job).where(Job.user_id == user_id, Job.month == month))
    forget_unused(session, names)
    return True


def delete_account(session, user_id):
    """Delete the user and everything they uploaded, in the order the foreign keys need (items, jobs, profile, then
    the user), then the answers only their items used."""
    names = list(set(session.exec(select(Item.name).where(Item.user_id == user_id)).all()))
    session.exec(delete(Item).where(Item.user_id == user_id))
    session.exec(delete(Job).where(Job.user_id == user_id))
    session.exec(delete(Profile).where(Profile.user_id == user_id))
    session.exec(delete(User).where(User.id == user_id))
    forget_unused(session, names)

"""What a user can delete: a month of their uploads or the whole account, and with it the attribute answers no stored
item needs any more. Nothing here commits; the route does, so each deletion is one transaction."""
from sqlmodel import col, delete, select

from .jobs import UNFINISHED
from .tables import Item, ItemCache, Job, Profile, User


def months_of(session, user_id):
    """The months the user uploaded, oldest first: those with items, and those with a job even if no line was kept."""
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
    if not names:
        return
    still_used = select(Item.name).where(col(Item.name).in_(names))
    session.exec(delete(ItemCache).where(col(ItemCache.name).in_(names), col(ItemCache.name).not_in(still_used)))


def delete_month(session, user_id, month):
    """Delete one month's items and jobs, then the answers only they used."""
    names = list(set(session.exec(select(Item.name).where(Item.user_id == user_id, Item.month == month)).all()))
    session.exec(delete(Item).where(Item.user_id == user_id, Item.month == month))
    session.exec(delete(Job).where(Job.user_id == user_id, Job.month == month))
    forget_unused(session, names)


def delete_account(session, user_id):
    """Delete the user and everything they uploaded, in the order the foreign keys need (items, jobs, profile, then
    the user), then the answers only their items used."""
    names = list(set(session.exec(select(Item.name).where(Item.user_id == user_id)).all()))
    session.exec(delete(Item).where(Item.user_id == user_id))
    session.exec(delete(Job).where(Job.user_id == user_id))
    session.exec(delete(Profile).where(Profile.user_id == user_id))
    session.exec(delete(User).where(User.id == user_id))
    forget_unused(session, names)

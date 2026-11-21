"""Dating profiles for the fictional demo users, made the first time anyone could see them: a name, age, gender, city,
bio and avatar from dating.demo_profile, the same on every run. The seed (src/api/seed.py) never knows about them."""
from sqlmodel import Session, col, select

from . import dating
from .tables import DatingProfile, Profile, User


def add_demo_profiles(session, config, regions):
    """Give every demo user without a dating profile one, and commit; the number added. Cheap when there is none to
    add: one query."""
    have = select(DatingProfile.user_id)
    users = session.exec(select(User).where(col(User.is_demo).is_(True), col(User.id).not_in(have))).all()
    for user in users:
        stored = session.get(Profile, user.id)
        session.add(DatingProfile(user_id=user.id, **dating.demo_profile(user, stored, config, regions)))
    if users:
        session.commit()
    return len(users)


def ensure_demo_profiles(engine, config, regions):
    with Session(engine) as session:
        return add_demo_profiles(session, config, regions)

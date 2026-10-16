"""GET /api/me/profile: the logged-in user's taste profile and uploaded months, for the profile and report pages."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlmodel import select

from ...receipt.build import trait_words
from .. import profiles
from ..db import SessionDep
from ..security import current_user
from ..tables import Item, Profile, User

router = APIRouter(prefix="/api/me")
UserDep = Annotated[User, Depends(current_user)]


# A plain def, not async: the reads block, so FastAPI runs this in a worker thread.
@router.get("/profile")
def my_profile(user: UserDep, request: Request, session: SessionDep):
    state = request.app.state
    settings = state.context["traits"]
    # The profile as the last upload job stored it: a request never works it out again, and never asks a model.
    profile = session.get(Profile, user.id)
    vector = None if profile is None or profile.vector is None else json.loads(profile.vector)
    words = trait_words(settings)
    # No vector, no values: every cell is null, but the 18 traits are always there for the page to draw.
    cells = [None] * len(words) if vector is None else vector
    items = session.exec(select(Item).where(Item.user_id == user.id).order_by(Item.id)).all()
    known = profiles.attributes_of(session, state.backends, {item.name for item in items})
    return {
        "user_id": user.id, "display_name": user.display_name, "is_demo": user.is_demo,
        "ready": vector is not None,
        "item_count": 0 if profile is None else profile.item_count,
        "min_items": settings["min_items"],
        # Names the current attribute model has not judged yet, so the page can say they are still being analysed.
        "pending_attributes": sum(fields is None for fields in known.values()),
        "areas": [] if profile is None else json.loads(profile.areas),
        "traits": [{**word, "value": value} for word, value in zip(words, cells, strict=True)],
        "categories": [{"name": category["name"], "color": category["color"]}
                       for category in state.context["report"]["categories"]],
        "months": profiles.months_of(items)}

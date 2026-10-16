"""GET /api/matches: the people whose taste is closest to mine, or most opposite, within a distance of me."""
import json
from typing import Literal

from fastapi import APIRouter, Request
from sqlmodel import col, select

from ...receipt.traits import similarity_model
from .. import matching, profiles
from ..db import SessionDep
from ..errors import ApiError
from ..security import UserDep
from ..tables import Profile, User

router = APIRouter(prefix="/api/matches")


# A plain def, not async: the reads block, so FastAPI runs this in a worker thread.
@router.get("")
def match_list(user: UserDep, request: Request, session: SessionDep,
               kind: Literal["similar", "opposite"] = "similar",
               scope: Literal["all", "district", "city", "region"] = "all"):
    state = request.app.state
    settings = state.context["traits"]
    size = len(settings["traits"])
    profile = session.get(Profile, user.id)
    vector = profiles.stored_vector(profile, size)
    my_areas = [] if profile is None else json.loads(profile.areas)
    head = {"kind": kind, "scope": scope, "ready": vector is not None, "my_areas": my_areas}
    # Too little data of my own comes first: whatever the scope, there is no list to narrow, so no error either.
    if vector is None:
        return {**head, "eligible": 0, "within": 0, "people": []}
    level = matching.SCOPES[scope]
    if level is not None and not my_areas:
        raise ApiError(400, "no_home_area")
    # Scores are worked out now from everyone's stored profile and never stored (design D3).
    others = session.exec(select(User, Profile).join(Profile, col(Profile.user_id) == col(User.id))
                          .where(col(User.id) != user.id, col(Profile.vector).is_not(None))).all()
    people = [{"user_id": other.id, "display_name": other.display_name,
               "vector": profiles.stored_vector(stored, size), "areas": json.loads(stored.areas)}
              for other, stored in others]
    entries = matching.entries(vector, my_areas, people, similarity_model(settings), state.regions)
    return {**head, **matching.pick(entries, kind, level, settings["match"])}

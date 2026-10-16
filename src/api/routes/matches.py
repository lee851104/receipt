"""GET /api/matches: the people whose taste is closest to mine, or most opposite, within a distance of me."""
import json
from typing import Literal

from fastapi import APIRouter, Request
from sqlmodel import col, select

from ...receipt.build import trait_words
from ...receipt.traits import explain as explain_taste, similarity_model
from .. import matching, profiles
from ..db import SessionDep
from ..errors import ApiError
from ..security import UserDep
from ..tables import Profile, User
from ..validation import PathId

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
    query = (select(User, Profile).join(Profile, col(Profile.user_id) == col(User.id))
             .where(col(User.id) != user.id, col(Profile.vector).is_not(None)))
    if user.is_demo:  # demo login needs no password, so a demo session must never reveal real people
        query = query.where(col(User.is_demo))
    others = session.exec(query).all()
    people = [{"user_id": other.id, "display_name": other.display_name,
               "vector": profiles.stored_vector(stored, size), "areas": json.loads(stored.areas)}
              for other, stored in others]
    entries = matching.entries(vector, my_areas, people, similarity_model(settings), state.regions)
    return {**head, **matching.pick(entries, kind, level, settings["match"])}


# A plain def, not async: the reads and the taste worked out for the graph block, so FastAPI runs this in a thread.
@router.get("/{user_id}/explain")
def explain_match(user_id: PathId, user: UserDep, request: Request, session: SessionDep):
    if user_id == user.id:
        raise ApiError(400, "self")
    other = session.get(User, user_id)
    # A demo session never learns about real people: one answers exactly like an id nobody has.
    if other is None or (user.is_demo and not other.is_demo):
        raise ApiError(404, "not_found")
    state = request.app.state
    settings = state.context["traits"]
    size = len(settings["traits"])
    vectors = {"mine": profiles.stored_vector(session.get(Profile, user.id), size),
               "theirs": profiles.stored_vector(session.get(Profile, other.id), size)}
    parts = matching.breakdown(vectors["mine"], vectors["theirs"], similarity_model(settings))
    cells = [{"id": cell["id"], "name": word["name"], **{key: value for key, value in cell.items() if key != "id"}}
             for cell, word in zip(parts.pop("cells"), trait_words(settings), strict=True)]
    # The graph's pushes, signals and purchases are worked out now from the stored items; its dots are the stored
    # vectors, the same values as the cells.
    sides = {}
    for side, person in (("mine", user.id), ("theirs", other.id)):
        explained = None
        if vectors[side] is not None:
            rows, period, attributes = profiles.history(session, state.backends, person)
            explained = explain_taste(rows, period, state.context, attributes)
        sides[side] = (vectors[side], explained)
    return {"user_id": other.id, "display_name": other.display_name, "comparable": parts.pop("comparable"),
            "reason": parts.pop("reason"), "cells": cells, **parts, "network": matching.network(settings, sides)}

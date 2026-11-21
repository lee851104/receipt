"""GET /api/matches: the people whose taste is closest to mine, or most opposite, within a distance of me; and
GET /api/matches/{user_id}/explain: how my score with one person is made up, with the network graph of the two of us."""
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
from ..tables import DatingProfile, Profile, User
from ..validation import PathId
from . import dating as dating_routes

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
    # Nobody who hid themselves on the dating app, and nobody blocked either way.
    hidden = select(DatingProfile.user_id).where(col(DatingProfile.discoverable).is_(False))
    query = query.where(col(User.id).not_in(hidden))
    blocked = dating_routes.blocked(session, user.id)
    others = [(other, stored) for other, stored in session.exec(query).all() if other.id not in blocked]
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
    # A demo session never learns about real people: one answers exactly like an id nobody has; nor does anyone learn
    # about someone they blocked or who blocked them.
    if other is None or (user.is_demo and not other.is_demo) or other.id in dating_routes.blocked(session, user.id):
        raise ApiError(404, "not_found")
    # Someone who paused being seen on the dating app is hidden here too, except from the people they matched.
    hidden = session.get(DatingProfile, other.id)
    if hidden is not None and not hidden.discoverable and dating_routes.match_between(session, user.id, other.id) is None:
        raise ApiError(404, "not_found")
    state = request.app.state
    settings = state.context["traits"]
    size = len(settings["traits"])
    vectors = {"mine": profiles.stored_vector(session.get(Profile, user.id), size),
               "theirs": profiles.stored_vector(session.get(Profile, other.id), size)}
    parts = matching.breakdown(vectors["mine"], vectors["theirs"], similarity_model(settings))
    cells = [{"id": cell["id"], "name": word["name"], **{key: value for key, value in cell.items() if key != "id"}}
             for cell, word in zip(parts.pop("cells"), trait_words(settings), strict=True)]
    # The graph's dots, pushes, signals and purchases are all worked out now from the stored items, so its pushes add
    # up to its dots; the cells keep the stored vectors, which are the same values once the recompute has run.
    sides = {}
    for side, person in (("mine", user.id), ("theirs", other.id)):
        explained = None
        if vectors[side] is not None:
            rows, period, attributes = profiles.history(session, state.backends, person)
            explained = explain_taste(rows, period, state.context, attributes)
        sides[side] = (vectors[side], explained)
    network = matching.network(settings, sides)
    # A real person on the dating app shows what they bought only to the people they matched with there; everyone
    # else still sees their traits and how each signal pushed them, with no purchase listed.
    private = (not other.is_demo and session.get(DatingProfile, other.id) is not None
               and dating_routes.match_between(session, user.id, other.id) is None)
    if private and network["theirs"]["items"] is not None:
        network["theirs"]["items"] = [None if listed is None else [] for listed in network["theirs"]["items"]]
    return {"user_id": other.id, "display_name": other.display_name, "comparable": parts.pop("comparable"),
            "reason": parts.pop("reason"), "cells": cells, **parts, "purchases_hidden": private, "network": network}

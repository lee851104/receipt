"""The dating app under /api/dating (docs/dating-app.md): a dating profile with a photo and the taste quiz, cards to
swipe, likes, matches and their chats, blocking and reporting. src/api/dating.py holds the rules; this module reads and
writes the tables.

Who sees whom: a demo session (demo login needs no password) only ever sees demo people, a real person sees demo
people only while DEMO_MODE is on, and nobody sees someone they blocked or who blocked them."""
import json
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Request, Response, UploadFile
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, delete, select

from ...receipt.traits import similarity_model
from .. import dating, sample
from ..dating_demo import add_demo_profiles
from ..db import SessionDep
from ..errors import ApiError
from ..security import UserDep
from ..tables import Block, DatingProfile, Match, Message, Photo, Profile, Report, Swipe, User, now
from ..validation import DisplayName, PathId, RowId, visible

router = APIRouter(prefix="/api/dating")
public = APIRouter(prefix="/api/dating")  # no login: the app's word lists, and photos by their random key
PHOTO_PATH = "/api/dating/me/photo"
PHOTO_KEY = r"^[0-9a-f]{32}$"
HISTORY = 200  # messages one request returns at most


def written(text, field):
    """visible(), but a line break is allowed, as in a bio or a chat message."""
    # The zero-width joiner is invisible on its own but builds emoji such as 👨‍👩‍👧, so it is let through here.
    for line in text.split("\n"):
        visible(line.replace("‍", ""), field)
    return text


Bio = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300), AfterValidator(lambda text: written(text, "bio"))]
Body = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
                 AfterValidator(lambda text: written(text, "body"))]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500), AfterValidator(lambda text: written(text, "note"))]
Year = Annotated[int, Field(strict=True, ge=1900, le=2100)]
Age = Annotated[int, Field(strict=True, ge=18, le=99)]


class ProfileChange(BaseModel):
    """What PATCH /api/dating/me may change; fields left out stay as they are, and null clears an optional one."""
    model_config = ConfigDict(extra="forbid")
    display_name: DisplayName | None = None
    birth_year: Year | None = None
    gender: str | None = None
    interested_in: list[str] | None = Field(default=None, max_length=3)
    age_min: Age | None = None
    age_max: Age | None = None
    city: str | None = None
    bio: Bio | None = None
    intent: str | None = None
    emoji: str | None = None
    discoverable: bool | None = None


class QuizAnswers(BaseModel):
    answers: list[float | None] = Field(max_length=64)


class SwipeBody(BaseModel):
    user_id: RowId
    action: Literal["like", "pass"]


class MessageBody(BaseModel):
    body: Body


class Target(BaseModel):
    user_id: RowId


class ReportBody(BaseModel):
    user_id: RowId
    reason: str
    note: Note = ""


@dataclass
class Person:
    user: User
    profile: DatingProfile | None
    stored: Profile | None
    vector: list | None
    source: str | None
    age: int | None

    @property
    def id(self):
        return self.user.id

    @property
    def ready(self):
        """Whether they can see cards and be seen: a whole profile and a taste."""
        return not dating.missing(self.profile) and self.vector is not None


def config(request):
    return request.app.state.dating


def settings_of(request):
    return request.app.state.context["traits"]


def person_of(session, request, user):
    profile, stored = session.get(DatingProfile, user.id), session.get(Profile, user.id)
    vector, source = dating.taste(stored, profile, len(settings_of(request)["traits"]))
    return Person(user, profile, stored, vector, source, dating.age_of(profile and profile.birth_year))


def everyone(session, request, viewer):
    """Everyone else with a dating profile whom the viewer may ever see, blocks aside."""
    size = len(settings_of(request)["traits"])
    state = request.app.state
    if viewer.is_demo or state.settings.demo_mode:  # demo users the seed added after start-up get theirs now
        add_demo_profiles(session, state.dating, state.regions)
    query = (select(User, DatingProfile, Profile).join(DatingProfile, col(DatingProfile.user_id) == col(User.id))
             .join(Profile, col(Profile.user_id) == col(User.id), isouter=True).where(col(User.id) != viewer.id))
    if viewer.is_demo:
        query = query.where(col(User.is_demo).is_(True))
    elif not request.app.state.settings.demo_mode:
        query = query.where(col(User.is_demo).is_(False))
    found = []
    for user, profile, stored in session.exec(query).all():
        vector, source = dating.taste(stored, profile, size)
        found.append(Person(user, profile, stored, vector, source, dating.age_of(profile.birth_year)))
    return found


def may_see(request, viewer, other):
    if other.is_demo:
        return viewer.is_demo or request.app.state.settings.demo_mode
    return not viewer.is_demo


def blocked(session, user_id):
    """The ids of everyone user_id blocked or was blocked by."""
    rows = session.exec(select(Block.user_id, Block.target_id)
                        .where(or_(col(Block.user_id) == user_id, col(Block.target_id) == user_id))).all()
    return {target if owner == user_id else owner for owner, target in rows}


def ordered(a, b):
    return (a, b) if a < b else (b, a)


def match_between(session, a, b):
    low, high = ordered(a, b)
    return session.exec(select(Match).where(Match.low_id == low, Match.high_id == high)).first()


def other_side(match, user_id):
    return match.high_id if match.low_id == user_id else match.low_id


def photo_url(profile):
    return None if profile is None or profile.photo_key is None else f"/api/dating/photos/{profile.photo_key}"


def card(request, me, other, liked_me=False, detail=False):
    """Someone as a card for me: who they are, our score and what we share and where we differ. detail adds every
    trait's two values, each trait's share of the score and openers for a chat."""
    settings, cfg = settings_of(request), config(request)
    result, percent = dating.score(me.vector, other.vector, similarity_model(settings))
    parts = result["parts"] if result["comparable"] else None
    found = dating.highlights(me.vector, other.vector, settings, parts)
    profile = other.profile
    answer = {"user_id": other.id, "name": profile.nickname or other.user.display_name, "age": other.age,
              "gender": profile.gender, "city": profile.city, "bio": profile.bio, "intent": profile.intent,
              "emoji": profile.emoji, "photo": photo_url(profile), "is_demo": other.user.is_demo,
              "persona": other.user.persona if other.user.is_demo else None, "source": other.source,
              "percent": percent, "band": dating.band(percent, cfg), "keywords": dating.keywords(other.vector, settings),
              "alike": found["alike"][:3], "contrast": found["contrast"][:2], "liked_me": liked_me}
    if detail:
        mine = me.vector or [None] * len(settings["traits"])
        theirs = other.vector or [None] * len(settings["traits"])
        answer.update(alike=found["alike"], contrast=found["contrast"],
                      traits=[{"id": trait["id"], "mine": mine[index], "theirs": theirs[index]}
                              for index, trait in enumerate(settings["traits"])],
                      contributions=dating.contributions(parts, settings), icebreakers=dating.icebreakers(found, cfg))
    return answer


def me_answer(request, session, me):
    settings, profile, stored = settings_of(request), me.profile, me.stored
    details = None
    if profile is not None:
        details = {"nickname": profile.nickname, "birth_year": profile.birth_year, "age": me.age,
                   "gender": profile.gender, "interested_in": dating.interested(profile), "age_min": profile.age_min,
                   "age_max": profile.age_max, "city": profile.city, "bio": profile.bio, "intent": profile.intent,
                   "emoji": profile.emoji, "photo": photo_url(profile), "discoverable": profile.discoverable}
    return {"user_id": me.id, "username": me.user.username, "name": (profile and profile.nickname) or me.user.display_name,
            "display_name": me.user.display_name, "is_demo": me.user.is_demo, "has_profile": profile is not None,
            "missing": dating.missing(profile), "ready": me.ready, "profile": details,
            "taste": {"source": me.source, "vector": me.vector, "keywords": dating.keywords(me.vector, settings, 5),
                      "quiz": dating.quiz_vector(profile, len(settings["traits"])),
                      "invoice_ready": stored is not None and stored.vector is not None,
                      "item_count": 0 if stored is None else stored.item_count, "min_items": settings["min_items"],
                      "recomputing": request.app.state.worker.recomputing(me.id)}}


def writable(user):
    if user.is_demo:
        raise ApiError(403, "demo_user_read_only")


def ready_or_409(me):
    if dating.missing(me.profile):
        raise ApiError(409, "profile_incomplete")
    if me.vector is None:
        raise ApiError(409, "no_taste")


def visible_person(session, request, me, user_id, answering=False):
    """Someone I may look at: on the dating app with a whole profile, not blocked either way, and either discoverable,
    matched with me, or someone who liked me. Anyone else answers exactly like an id nobody has."""
    if user_id == me.id:
        raise ApiError(400, "self")
    user = session.get(User, user_id)
    if user is None or not may_see(request, me.user, user) or user_id in blocked(session, me.id):
        raise ApiError(404, "not_found")
    other = person_of(session, request, user)
    if other.profile is None or dating.missing(other.profile):
        raise ApiError(404, "not_found")
    if not other.profile.discoverable and match_between(session, me.id, user_id) is None:
        liked = session.get(Swipe, (user_id, me.id))
        if liked is None or liked.action != "like":
            raise ApiError(404, "not_found")
    # Answering a card needs both sides to want each other, as on discover, so a like never reaches someone who would
    # not want it (or whose wishes changed since); a match already made stays answerable.
    if (answering and match_between(session, me.id, user_id) is None
            and not dating.mutual(me.profile, me.age, other.profile, other.age)):
        raise ApiError(404, "not_found")
    return other


def owned_match(session, request, me, match_id):
    match = session.get(Match, match_id)
    if match is None or me.id not in (match.low_id, match.high_id):
        raise ApiError(404, "not_found")
    other_user = session.get(User, other_side(match, me.id))
    if other_user is None or not may_see(request, me.user, other_user) or other_user.id in blocked(session, me.id):
        raise ApiError(404, "not_found")
    return match, other_user


def unmatch(session, match):
    session.exec(delete(Message).where(Message.match_id == match.id))
    session.exec(delete(Match).where(Match.id == match.id))


def stamp(moment):
    """A time as ISO text with its UTC offset: SQLite hands back times without one, and a browser would read those
    as its own local time."""
    return (moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)).isoformat()


def message_answer(message, me_id):
    return {"id": message.id, "from_me": message.sender_id == me_id, "body": message.body,
            "created_at": stamp(message.created_at)}


def maybe_admirers(request, session, me):
    """In DEMO_MODE, a real person who just became ready gets a few likes from fitting demo people (the two most alike
    and the most opposite), so the likes tab and a first match can be tried at once. Once only: never again after
    any demo person has answered their card."""
    if not request.app.state.settings.demo_mode or me.user.is_demo or not me.ready:
        return
    demo_ids = select(User.id).where(col(User.is_demo).is_(True))
    if session.exec(select(Swipe).where(Swipe.target_id == me.id, col(Swipe.user_id).in_(demo_ids)).limit(1)).first():
        return
    mine = {row for row in session.exec(select(Swipe.target_id).where(Swipe.user_id == me.id)).all()}
    model = similarity_model(settings_of(request))
    scored = []
    for other in everyone(session, request, me.user):
        if (not other.user.is_demo or other.id in mine or not other.ready or not other.profile.discoverable
                or not dating.mutual(me.profile, me.age, other.profile, other.age)):
            continue
        _, percent = dating.score(me.vector, other.vector, model)
        if percent is not None:
            scored.append((percent, other.id))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    chosen = [user_id for percent, user_id in scored[:2] if percent >= 10]
    chosen += [user_id for percent, user_id in scored[::-1][:1] if percent <= -10]
    for user_id in chosen:
        session.add(Swipe(user_id=user_id, target_id=me.id, action="like"))
    if chosen:
        try:
            session.commit()
        except IntegrityError:  # another request for this person wrote the same likes a moment earlier
            session.rollback()


class Throttle:
    """At most `limit` messages a minute per sender, kept in memory (the server is one process)."""

    def __init__(self, limit, window=60.0):
        self.limit, self.window, self.sent, self.lock = limit, window, defaultdict(deque), threading.Lock()

    def allow(self, user_id, clock=time.monotonic):
        moment = clock()
        with self.lock:
            sent = self.sent[user_id]
            while sent and moment - sent[0] > self.window:
                sent.popleft()
            if len(sent) >= self.limit:
                return False
            sent.append(moment)
            return True


# ---- public --------------------------------------------------------------------------------------------------------

@public.get("/meta")
def meta(request: Request):
    """The app's word lists: genders, intents, avatar emojis, report reasons, the quiz, the traits and the cities."""
    cfg, settings, state = config(request), settings_of(request), request.app.state
    traits = []
    for trait in settings["traits"]:
        entry = {"id": trait["id"], "kind": trait["kind"], "name": trait["name"],
                 "emoji": cfg["trait_emoji"].get(trait["id"], "•")}
        entry.update({"ends": trait["ends"], "short": trait["short"]} if trait["kind"] == "two_sided"
                     else {"habit": trait["habit"]})
        traits.append(entry)
    keys = ("app_name", "min_age", "max_age", "bio_max", "message_max", "photo_max_bytes", "genders", "intents",
            "emojis", "report_reasons", "bands", "quiz")
    return {**{key: cfg[key] for key in keys}, "traits": traits, "regions": state.region_list,
            "min_items": settings["min_items"], "min_shared": settings["similarity"]["min_shared_two_sided"],
            "demo_mode": state.settings.demo_mode}


@public.get("/sample-invoices")
def sample_invoices(request: Request, variant: Annotated[int, Query(ge=0, le=99)] = 0):
    """A fictional invoice CSV to try an upload with; DEMO_MODE only, so a real service never invites fake taste."""
    if not request.app.state.settings.demo_mode:
        raise ApiError(404, "not_found")
    return Response(content=sample.demo_csv("2026-06", variant), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="sample-invoices-{variant}.csv"'})


@public.get("/photos/{key}")
def photo(key: Annotated[str, Path(pattern=PHOTO_KEY)], session: SessionDep):
    stored = session.get(Photo, key)
    if stored is None:
        raise ApiError(404, "not_found")
    return Response(content=stored.data, media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff",
                             "Content-Security-Policy": "default-src 'none'"})


# ---- my profile ----------------------------------------------------------------------------------------------------

@router.get("/me")
def my_profile(user: UserDep, request: Request, session: SessionDep):
    return me_answer(request, session, person_of(session, request, user))


def checked(change, cfg, regions):
    """The fields of a ProfileChange that were sent, checked against configs/dating.json; a 422 names a bad one."""
    values = {name: getattr(change, name) for name in change.model_fields_set}

    def refuse(field, message):
        raise ApiError(422, "invalid_profile", f"{field}: {message}")

    for field in ("birth_year", "gender", "interested_in", "display_name", "bio", "age_min", "age_max", "discoverable"):
        if field in values and values[field] is None:
            refuse(field, "may not be empty")
    if "birth_year" in values:
        age = dating.age_of(values["birth_year"])
        if not cfg["min_age"] <= age <= cfg["max_age"]:
            refuse("birth_year", f"you must be {cfg['min_age']} or older")
    genders = dating.ids(cfg, "genders")
    if "gender" in values and values["gender"] not in genders:
        refuse("gender", "unknown gender")
    if "interested_in" in values:
        wanted = values["interested_in"]
        if not wanted or any(item not in genders for item in wanted) or len(set(wanted)) != len(wanted):
            refuse("interested_in", "pick one or more genders")
        values["interested_in"] = json.dumps([gender for gender in genders if gender in wanted])
    if values.get("city") is not None and values["city"] not in regions:
        refuse("city", "unknown city or county")
    if values.get("intent") is not None and values["intent"] not in dating.ids(cfg, "intents"):
        refuse("intent", "unknown intent")
    if values.get("emoji") is not None and values["emoji"] not in cfg["emojis"]:
        refuse("emoji", "unknown emoji")
    return values


@router.patch("/me")
def change_profile(change: ProfileChange, user: UserDep, request: Request, session: SessionDep):
    writable(user)
    values = checked(change, config(request), request.app.state.regions)
    profile = session.get(DatingProfile, user.id) or DatingProfile(user_id=user.id)
    name = values.pop("display_name", None)
    if name is not None:
        user.display_name = name
        session.add(user)
    for field, value in values.items():
        setattr(profile, field, value)
    if profile.age_min > profile.age_max:
        raise ApiError(422, "invalid_profile", "age_min: must not be above age_max")
    profile.updated_at = now()
    session.add(profile)
    session.commit()
    session.refresh(user)
    me = person_of(session, request, user)
    maybe_admirers(request, session, me)
    return me_answer(request, session, me)


@router.put("/me/quiz")
def answer_quiz(body: QuizAnswers, user: UserDep, request: Request, session: SessionDep):
    writable(user)
    try:
        answers = dating.quiz_answers(body.answers, settings_of(request), config(request))
    except ValueError as error:
        raise ApiError(422, "invalid_quiz", str(error)) from None
    profile = session.get(DatingProfile, user.id) or DatingProfile(user_id=user.id)
    profile.quiz, profile.updated_at = json.dumps(answers), now()
    session.add(profile)
    session.commit()
    session.refresh(user)
    me = person_of(session, request, user)
    maybe_admirers(request, session, me)
    return me_answer(request, session, me)


@router.post(PHOTO_PATH.removeprefix("/api/dating"))
def upload_photo(file: UploadFile, user: UserDep, request: Request, session: SessionDep):
    writable(user)
    cfg = config(request)
    data = file.file.read(cfg["photo_max_bytes"] + 1)
    if len(data) > cfg["photo_max_bytes"]:
        raise ApiError(413, "file_too_large")
    try:
        cleaned, _ = dating.clean_jpeg(data, cfg["photo_max_side"])
    except ValueError as error:
        raise ApiError(400, "invalid_photo", str(error)) from None
    profile = session.get(DatingProfile, user.id) or DatingProfile(user_id=user.id)
    session.exec(delete(Photo).where(Photo.user_id == user.id))
    key = secrets.token_hex(16)
    session.add(Photo(key=key, user_id=user.id, data=cleaned))
    profile.photo_key, profile.updated_at = key, now()
    session.add(profile)
    session.commit()
    session.refresh(user)
    return me_answer(request, session, person_of(session, request, user))


@router.delete("/me/photo")
def remove_photo(user: UserDep, request: Request, session: SessionDep):
    writable(user)
    profile = session.get(DatingProfile, user.id)
    session.exec(delete(Photo).where(Photo.user_id == user.id))
    if profile is not None:
        profile.photo_key, profile.updated_at = None, now()
        session.add(profile)
    session.commit()
    session.refresh(user)
    return me_answer(request, session, person_of(session, request, user))


# ---- cards and swipes ----------------------------------------------------------------------------------------------

@router.get("/discover")
def discover(user: UserDep, request: Request, session: SessionDep,
             mode: Literal["similar", "opposite"] = "similar", scope: Literal["all", "city", "region"] = "all"):
    """The next cards: people who fit what I am looking for (and want someone like me), whom I have not answered,
    most alike first, or most opposite first."""
    me = person_of(session, request, user)
    ready_or_409(me)
    if scope != "all" and not me.profile.city:
        raise ApiError(400, "no_city")
    regions = request.app.state.regions
    hidden = blocked(session, me.id) | set(session.exec(select(Swipe.target_id).where(Swipe.user_id == me.id)).all())
    liked_me = set(session.exec(select(Swipe.user_id).where(Swipe.target_id == me.id, Swipe.action == "like")).all())
    model = similarity_model(settings_of(request))
    scored = []
    for other in everyone(session, request, user):
        if (other.id in hidden or not other.ready or not other.profile.discoverable
                or not dating.mutual(me.profile, me.age, other.profile, other.age)):
            continue
        if scope == "city" and other.profile.city != me.profile.city:
            continue
        if scope == "region" and (other.profile.city is None
                                  or regions.get(other.profile.city) != regions.get(me.profile.city)):
            continue
        result, percent = dating.score(me.vector, other.vector, model)
        if percent is not None:
            scored.append((result["score"], other))
    scored.sort(key=lambda pair: (pair[0] if mode == "opposite" else -pair[0], pair[1].id))
    batch = scored[:config(request)["discover_batch"]]
    return {"mode": mode, "scope": scope, "remaining": len(scored),
            "cards": [card(request, me, other, liked_me=other.id in liked_me) for _, other in batch]}


def match_answer(request, session, me, match, other):
    my_read = match.low_read if match.low_id == me.id else match.high_read
    opened = match.low_opened if match.low_id == me.id else match.high_opened
    last = session.exec(select(Message).where(Message.match_id == match.id).order_by(col(Message.id).desc()).limit(1)).first()
    unread = session.exec(select(func.count()).select_from(Message).where(
        Message.match_id == match.id, Message.sender_id != me.id, Message.id > my_read)).one()
    return {"match_id": match.id, "created_at": stamp(match.created_at), "last_at": stamp(match.last_at),
            "opened": opened, "unread": unread, "last_message": None if last is None else message_answer(last, me.id),
            "person": card(request, me, other)}


@router.post("/swipes")
def swipe(body: SwipeBody, user: UserDep, request: Request, session: SessionDep):
    me = person_of(session, request, user)
    ready_or_409(me)
    other = visible_person(session, request, me, body.user_id, answering=True)
    answer = session.get(Swipe, (me.id, other.id)) or Swipe(user_id=me.id, target_id=other.id, action=body.action)
    answer.action, answer.created_at = body.action, now()
    session.add(answer)
    match = None
    if body.action == "like":
        match = match_between(session, me.id, other.id)
        if match is None:
            theirs = session.get(Swipe, (other.id, me.id))
            likes_back = theirs is not None and theirs.action == "like"
            if not likes_back and other.user.is_demo:
                _, percent = dating.score(me.vector, other.vector, similarity_model(settings_of(request)))
                if dating.demo_likes_back(other.id, me.id, percent):
                    session.add(Swipe(user_id=other.id, target_id=me.id, action="like"))
                    likes_back = True
            if likes_back:
                low, high = ordered(me.id, other.id)
                match = Match(low_id=low, high_id=high)
                session.add(match)
    try:
        session.commit()
    except IntegrityError:
        # The other side's like (or this same answer sent twice) wrote first: keep my answer, use the match there is.
        session.rollback()
        answer = session.get(Swipe, (me.id, other.id)) or Swipe(user_id=me.id, target_id=other.id, action=body.action)
        answer.action, answer.created_at = body.action, now()
        session.add(answer)
        session.commit()
        match = match_between(session, me.id, other.id) if body.action == "like" else None
    if body.action == "like" and match is None:
        # Both likes may have committed at the same moment, each before seeing the other: look once more, now that
        # mine is written, so the second of the two still makes the match.
        theirs = session.get(Swipe, (other.id, me.id))
        if theirs is not None and theirs.action == "like":
            low, high = ordered(me.id, other.id)
            session.add(Match(low_id=low, high_id=high))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
            match = match_between(session, me.id, other.id)
    if match is not None:
        session.refresh(match)
    return {"action": body.action,
            "match": None if match is None else match_answer(request, session, me, match, other)}


@router.post("/swipes/reset")
def reset_passes(user: UserDep, session: SessionDep):
    """Forget my passes, so the people I skipped come round again."""
    passes = session.exec(select(func.count()).select_from(Swipe).where(Swipe.user_id == user.id, Swipe.action == "pass")).one()
    session.exec(delete(Swipe).where(Swipe.user_id == user.id, Swipe.action == "pass"))
    session.commit()
    return {"reset": passes}


@router.get("/likes")
def likes(user: UserDep, request: Request, session: SessionDep):
    """The people who liked me and whom I have not answered yet, newest first."""
    me = person_of(session, request, user)
    maybe_admirers(request, session, me)
    hidden = blocked(session, me.id) | set(session.exec(select(Swipe.target_id).where(Swipe.user_id == me.id)).all())
    incoming = session.exec(select(Swipe).where(Swipe.target_id == me.id, Swipe.action == "like")
                            .order_by(col(Swipe.created_at).desc())).all()
    by_id = {other.id: other for other in everyone(session, request, user)}
    people = [by_id[swipe.user_id] for swipe in incoming
              if swipe.user_id in by_id and swipe.user_id not in hidden and by_id[swipe.user_id].ready
              and by_id[swipe.user_id].profile.discoverable
              and dating.mutual(me.profile, me.age, by_id[swipe.user_id].profile, by_id[swipe.user_id].age)]
    return {"ready": me.ready, "people": [card(request, me, other, liked_me=True) for other in people]}


@router.get("/people/{user_id}")
def person(user_id: PathId, user: UserDep, request: Request, session: SessionDep):
    me = person_of(session, request, user)
    other = visible_person(session, request, me, user_id)
    match = match_between(session, me.id, other.id)
    liked = session.get(Swipe, (other.id, me.id))
    mine = session.get(Swipe, (me.id, other.id))
    return {**card(request, me, other, liked_me=liked is not None and liked.action == "like", detail=True),
            "match_id": None if match is None else match.id, "my_answer": None if mine is None else mine.action}


# ---- matches and chat ----------------------------------------------------------------------------------------------

@router.get("/matches")
def matches(user: UserDep, request: Request, session: SessionDep):
    me = person_of(session, request, user)
    hidden = blocked(session, me.id)
    rows = session.exec(select(Match).where(or_(Match.low_id == me.id, Match.high_id == me.id))
                        .order_by(col(Match.last_at).desc(), col(Match.id).desc())).all()
    answers = []
    for match in rows:
        other_user = session.get(User, other_side(match, me.id))
        if other_user is None or other_user.id in hidden or not may_see(request, user, other_user):
            continue
        other = person_of(session, request, other_user)
        if other.profile is None:
            continue
        answers.append(match_answer(request, session, me, match, other))
    return {"matches": answers}


@router.get("/matches/{match_id}")
def match_detail(match_id: PathId, user: UserDep, request: Request, session: SessionDep):
    me = person_of(session, request, user)
    match, other_user = owned_match(session, request, me, match_id)
    if match.low_id == me.id:
        match.low_opened = True
    else:
        match.high_opened = True
    session.add(match)
    session.commit()
    session.refresh(match)
    other = person_of(session, request, other_user)
    return {**match_answer(request, session, me, match, other), "person": card(request, me, other, detail=True)}


@router.delete("/matches/{match_id}", status_code=204)
def leave_match(match_id: PathId, user: UserDep, request: Request, session: SessionDep):
    me = person_of(session, request, user)
    match, _ = owned_match(session, request, me, match_id)
    unmatch(session, match)
    session.commit()
    return Response(status_code=204)


@router.get("/matches/{match_id}/messages")
def read_messages(match_id: PathId, user: UserDep, request: Request, session: SessionDep,
                  after: Annotated[int, Query(ge=0, le=2**63 - 1)] = 0):
    """The chat after message id `after` (the latest ones when 0), oldest first; reading marks them read."""
    me = person_of(session, request, user)
    match, _ = owned_match(session, request, me, match_id)
    query = select(Message).where(Message.match_id == match.id)
    if after:
        rows = session.exec(query.where(Message.id > after).order_by(col(Message.id)).limit(HISTORY)).all()
    else:
        rows = list(reversed(session.exec(query.order_by(col(Message.id).desc()).limit(HISTORY)).all()))
    latest = session.exec(select(func.max(Message.id)).where(Message.match_id == match.id)).one() or 0
    if match.low_id == me.id:
        match.low_read, match.low_opened = max(match.low_read, latest), True
        theirs = match.high_read
    else:
        match.high_read, match.high_opened = max(match.high_read, latest), True
        theirs = match.low_read
    session.add(match)
    session.commit()
    return {"messages": [message_answer(message, me.id) for message in rows], "their_read": theirs}


@router.post("/matches/{match_id}/messages", status_code=201)
def send_message(match_id: PathId, body: MessageBody, user: UserDep, request: Request, session: SessionDep):
    me = person_of(session, request, user)
    match, other_user = owned_match(session, request, me, match_id)
    if not request.app.state.throttle.allow(me.id):
        raise ApiError(429, "slow_down")
    sent_before = session.exec(select(func.count()).select_from(Message).where(
        Message.match_id == match.id, Message.sender_id == me.id)).one()
    message = Message(match_id=match.id, sender_id=me.id, body=body.body)
    session.add(message)
    session.flush()
    moment = now()
    match.last_at = moment
    if match.low_id == me.id:
        match.low_read, match.low_opened = message.id, True
    else:
        match.high_read, match.high_opened = message.id, True
    replies = []
    if other_user.is_demo:
        other = person_of(session, request, other_user)
        settings = settings_of(request)
        result, percent = dating.score(me.vector, other.vector, similarity_model(settings))
        found = dating.highlights(me.vector, other.vector, settings, result["parts"] if result["comparable"] else None)
        name = (me.profile and me.profile.nickname) or me.user.display_name
        text = dating.demo_reply(config(request), body.body, sent_before, found, name, percent, match.id)
        reply = Message(match_id=match.id, sender_id=other_user.id, body=text, created_at=moment)
        session.add(reply)
        session.flush()
        replies.append(reply)
        # A demo person answers at once, so they have read everything up to their answer.
        if match.low_id == other_user.id:
            match.low_read, match.low_opened = reply.id, True
        else:
            match.high_read, match.high_opened = reply.id, True
    session.add(match)
    session.commit()
    session.refresh(message)
    for reply in replies:
        session.refresh(reply)
    return {"message": message_answer(message, me.id), "replies": [message_answer(reply, me.id) for reply in replies]}


# ---- safety --------------------------------------------------------------------------------------------------------

def block_pair(session, me_id, other_id):
    if session.get(Block, (me_id, other_id)) is None:
        session.add(Block(user_id=me_id, target_id=other_id))
    match = match_between(session, me_id, other_id)
    if match is not None:
        unmatch(session, match)


def target_of(session, request, user, user_id):
    if user_id == user.id:
        raise ApiError(400, "self")
    other = session.get(User, user_id)
    if other is None or not may_see(request, user, other):
        raise ApiError(404, "not_found")
    return other


@router.post("/blocks", status_code=204)
def block(body: Target, user: UserDep, request: Request, session: SessionDep):
    other = target_of(session, request, user, body.user_id)
    block_pair(session, user.id, other.id)
    session.commit()
    return Response(status_code=204)


@router.post("/reports", status_code=204)
def report(body: ReportBody, user: UserDep, request: Request, session: SessionDep):
    if body.reason not in dating.ids(config(request), "report_reasons"):
        raise ApiError(422, "invalid_report", "reason: unknown reason")
    other = target_of(session, request, user, body.user_id)
    session.add(Report(reporter_id=user.id, target_id=other.id, reason=body.reason, note=body.note))
    block_pair(session, user.id, other.id)
    session.commit()
    return Response(status_code=204)


@router.get("/summary")
def summary(user: UserDep, request: Request, session: SessionDep):
    """The tab bar's badges: people waiting in my likes, matches I have not opened and unread messages."""
    me = person_of(session, request, user)
    maybe_admirers(request, session, me)
    waiting = likes(user, request, session)["people"]
    chats = matches(user, request, session)["matches"]
    return {"ready": me.ready, "missing": dating.missing(me.profile), "likes": len(waiting),
            "new_matches": sum(1 for chat in chats if not chat["opened"]),
            "unread": sum(chat["unread"] for chat in chats)}

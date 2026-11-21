"""Database tables: accounts, upload jobs, the purchases they hold, the attribute cache and taste profiles."""
import secrets
from datetime import datetime, timezone

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


def now():
    return datetime.now(timezone.utc)


def new_token_key():
    """A fresh random key for an account's tokens."""
    return secrets.token_hex(8)


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str | None = None  # demo users have none, so only demo-login lets them in
    display_name: str
    is_demo: bool = False
    persona: str | None = None        # the fictional type, such as 咖啡上班族; None for real people
    # Goes into every token next to the id. SQLite reuses the id of a deleted user, and a fresh database starts
    # the ids again, but a new account gets a new key, so an old token never works for it.
    token_key: str = Field(default_factory=new_token_key)


class Job(SQLModel, table=True):
    """One upload: queued, then running, then done or failed; done and total count distinct product names."""
    __tablename__ = "jobs"
    # Never reuse the id of a deleted job: a page still polling the old id must not see a different upload.
    __table_args__ = {"sqlite_autoincrement": True}
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    month: str                        # YYYY-MM
    status: str = "queued"
    done: int = 0
    total: int = 0
    message: str = "排隊中"
    created_at: datetime = Field(default_factory=now)


class Item(SQLModel, table=True):
    """One purchase line kept from an upload. Only what the analysis needs: no address, no invoice number."""
    __tablename__ = "items"
    # Every look-up is one user's items, often of one month: one index serves both.
    __table_args__ = (Index("ix_items_user_month", "user_id", "month"),)
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    month: str                        # YYYY-MM
    day: int
    invoice: str                      # the coded YYYY-MM-Rnn, never the real invoice number
    merchant: str
    district: str | None = None       # city or county plus district only
    name: str
    quantity: int
    amount: int
    category: int = 10                # 0-9, or 10 (待確認) until classified or when the model is unsure


class ItemCache(SQLModel, table=True):
    """What an attribute model answered for a product name, so the name is judged once per model version
    (Backends.attributes_version)."""
    __tablename__ = "item_cache"
    name: str = Field(primary_key=True)
    model: str = Field(primary_key=True)  # the attribute model's version: "fake", or role 3's MODEL_VERSION
    fields: str                           # the 23 fields as JSON; null means unknown, never false


class Profile(SQLModel, table=True):
    """A user's taste, worked out again after every finished upload."""
    __tablename__ = "profiles"
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    vector: str | None = None         # 18 values as JSON, or None when there are too few valid items
    areas: str = "[]"                 # home districts as JSON, at most two
    item_count: int = 0               # valid items, the number ready is judged by
    updated_at: datetime = Field(default_factory=now)


# The dating app (configs/dating.json, src/api/dating.py). A person is on it once they have a dating profile; their
# taste comes from their invoices (the profiles table) when there are enough, else from the taste quiz.

class DatingProfile(SQLModel, table=True):
    """What others see of someone on the dating app, and who they want to meet."""
    __tablename__ = "dating_profiles"
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    nickname: str | None = None       # demo users only; a real person's name is users.display_name
    birth_year: int | None = None
    gender: str | None = None         # an id from configs/dating.json genders
    interested_in: str = "[]"         # gender ids as JSON
    age_min: int = 18
    age_max: int = 99
    city: str | None = None           # a city or county from configs/regions.json
    bio: str = ""
    intent: str | None = None         # an id from configs/dating.json intents
    emoji: str | None = None          # the avatar when there is no photo
    photo_key: str | None = None      # photos.key of the current photo
    discoverable: bool = True
    quiz: str | None = None           # 18 values or nulls as JSON, from the taste quiz
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class Photo(SQLModel, table=True):
    """A profile photo as a cleaned JPEG (no EXIF, so no GPS). The key is random and changes with every upload, so a
    photo's address tells nothing about its owner and an old address stops working."""
    __tablename__ = "photos"
    key: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    data: bytes
    created_at: datetime = Field(default_factory=now)


class Swipe(SQLModel, table=True):
    """One person's answer to another's card: like or pass."""
    __tablename__ = "swipes"
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    target_id: int = Field(foreign_key="users.id", primary_key=True, index=True)
    action: str                       # like | pass
    created_at: datetime = Field(default_factory=now)


class Match(SQLModel, table=True):
    """Two people who liked each other; low is the smaller user id. Unmatching deletes the row and its messages."""
    __tablename__ = "matches"
    __table_args__ = (Index("ix_matches_pair", "low_id", "high_id", unique=True), {"sqlite_autoincrement": True})
    id: int | None = Field(default=None, primary_key=True)
    low_id: int = Field(foreign_key="users.id", index=True)
    high_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=now)
    last_at: datetime = Field(default_factory=now)  # the last message, or the match itself; the chat list's order
    low_read: int = 0                 # the last message id each side has seen
    high_read: int = 0
    low_opened: bool = False          # whether each side has opened the match once ("new match" until then)
    high_opened: bool = False


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    __table_args__ = {"sqlite_autoincrement": True}
    id: int | None = Field(default=None, primary_key=True)
    match_id: int = Field(foreign_key="matches.id", index=True)
    sender_id: int = Field(foreign_key="users.id")
    body: str
    created_at: datetime = Field(default_factory=now)


class Block(SQLModel, table=True):
    """user_id never sees target_id again, and target_id never sees user_id."""
    __tablename__ = "blocks"
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    target_id: int = Field(foreign_key="users.id", primary_key=True, index=True)
    created_at: datetime = Field(default_factory=now)


class Report(SQLModel, table=True):
    """A report for whoever looks after the service; reporting also blocks."""
    __tablename__ = "reports"
    id: int | None = Field(default=None, primary_key=True)
    reporter_id: int = Field(foreign_key="users.id", index=True)
    target_id: int = Field(foreign_key="users.id", index=True)
    reason: str                       # an id from configs/dating.json report_reasons
    note: str = ""
    created_at: datetime = Field(default_factory=now)

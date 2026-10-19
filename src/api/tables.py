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

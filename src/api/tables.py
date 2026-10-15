"""Database tables. Week 1 needs only users; jobs, items, item_cache and profiles come with the uploads."""
import secrets

from sqlmodel import Field, SQLModel


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
    token_key: str = Field(default_factory=lambda: secrets.token_hex(8))

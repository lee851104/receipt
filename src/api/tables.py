"""Database tables. Week 1 needs only users; jobs, items, item_cache and profiles come with the uploads."""
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str | None = None  # demo users have none, so only demo-login lets them in
    display_name: str
    is_demo: bool = False
    persona: str | None = None        # the fictional type, such as 咖啡上班族; None for real people

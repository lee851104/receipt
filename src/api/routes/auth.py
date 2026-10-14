"""Accounts: register and log in, and the demo quick switch that exists only when DEMO_MODE=1."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, StringConstraints, field_validator
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..db import get_session
from ..errors import ApiError
from ..security import MAX_PASSWORD, hash_password, token_response, verify_password
from ..tables import User
from ..validation import visible

router = APIRouter(prefix="/api/auth")
SessionDep = Annotated[Session, Depends(get_session)]


class Registration(BaseModel):
    # Stored in lowercase, so Amy, amy and AMY are one account however a phone capitalises it.
    username: Annotated[str, StringConstraints(to_lower=True, pattern=r"^[A-Za-z0-9_]{3,32}$")]
    password: str = Field(min_length=8, max_length=MAX_PASSWORD)
    display_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)] | None = None

    @field_validator("display_name")
    @classmethod
    def visible_name(cls, name):
        return None if name is None else visible(name, "display_name")


@router.post("/register", status_code=201)
def register(body: Registration, session: SessionDep):
    user = User(username=body.username, password_hash=hash_password(body.password),
                display_name=body.display_name or body.username)
    session.add(user)
    try:
        session.commit()
    except IntegrityError:  # the username is unique in the table, so a taken one fails here
        raise ApiError(409, "username_taken") from None
    session.refresh(user)
    return {"user_id": user.id, "username": user.username, "display_name": user.display_name}


@router.post("/login")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], request: Request, session: SessionDep):
    user = session.exec(select(User).where(User.username == form.username.lower())).first()
    # One answer for an unknown username and a wrong password, so neither tells which accounts exist.
    if not verify_password(form.password, None if user is None else user.password_hash):
        raise ApiError(401, "bad_credentials", headers={"WWW-Authenticate": "Bearer"})
    return token_response(user, request.app.state.settings)

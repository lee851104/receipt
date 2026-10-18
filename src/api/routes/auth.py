"""Accounts: register, log in and log out, and the demo quick switch that exists only when DEMO_MODE=1."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, StringConstraints, field_validator
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select

from ..db import SessionDep
from ..errors import ApiError
from ..security import Password, UserDep, end_sessions, hash_password, token_response, verify_password
from ..tables import User
from ..validation import DisplayName, RowId

router = APIRouter(prefix="/api/auth")
demo_router = APIRouter(prefix="/api/auth")


class Registration(BaseModel):
    # Stored in lowercase, so Amy, amy and AMY are one account however a phone capitalises it.
    username: Annotated[str, StringConstraints(to_lower=True, pattern=r"^[A-Za-z0-9_]{3,32}$")]
    password: Password
    display_name: DisplayName | None = None

    @field_validator("username")
    @classmethod
    def not_a_demo_name(cls, username):
        """demo_ names belong to the fictional users the seed adds, so a real account can never take one."""
        if username.startswith("demo_"):
            raise ValueError("usernames starting with demo_ are kept for the fictional users")
        return username


class DemoLogin(BaseModel):
    user_id: RowId


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


@router.post("/logout", status_code=204)
def logout(user: UserDep, session: SessionDep):
    # A demo persona is shared by everyone who switches to it, so its key stays: the browser that logs out drops its
    # token, and the persona's other visitors stay logged in.
    if not user.is_demo:
        end_sessions(user)
        session.add(user)
        session.commit()
    return Response(status_code=204)


@demo_router.get("/demo-users")
def demo_users(session: SessionDep):
    users = session.exec(select(User).where(col(User.is_demo).is_(True)).order_by(col(User.id))).all()
    return [{"user_id": user.id, "display_name": user.display_name, "persona": user.persona} for user in users]


@demo_router.post("/demo-login")
def demo_login(body: DemoLogin, request: Request, session: SessionDep):
    user = session.get(User, body.user_id)
    if user is None:
        raise ApiError(404, "not_found")
    # Real accounts always need their password, even with DEMO_MODE on.
    if not user.is_demo:
        raise ApiError(403, "not_demo_user")
    return token_response(user, request.app.state.settings)

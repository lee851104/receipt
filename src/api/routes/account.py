"""Account management (overview 5.11): see and rename the account, change its password, delete it. Logout is in
routes/auth.py; deleting a month is below too."""
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from .. import accounts
from ..db import SessionDep
from ..errors import ApiError
from ..security import Password, UserDep, end_sessions, hash_password, token_response, verify_password
from ..validation import DisplayName

router = APIRouter(prefix="/api/me")


class Rename(BaseModel):
    display_name: DisplayName


class PasswordChange(BaseModel):
    current_password: str
    new_password: Password


class Confirmation(BaseModel):
    password: str


def writable(user):
    """Demo users are shared by everyone, so nobody may change or delete one; checked before any password."""
    if user.is_demo:
        raise ApiError(403, "demo_user_read_only")


def confirm(user, password):
    if not verify_password(password, user.password_hash):
        raise ApiError(403, "wrong_password")


def account(session, user):
    return {"user_id": user.id, "username": user.username, "display_name": user.display_name,
            "is_demo": user.is_demo, "months": accounts.months_of(session, user.id)}


@router.get("")
def my_account(user: UserDep, session: SessionDep):
    return account(session, user)


@router.patch("")
def rename(body: Rename, user: UserDep, session: SessionDep):
    writable(user)
    user.display_name = body.display_name
    session.add(user)
    session.commit()
    return account(session, user)


@router.post("/password")
def change_password(body: PasswordChange, user: UserDep, request: Request, session: SessionDep):
    writable(user)
    confirm(user, body.current_password)
    user.password_hash = hash_password(body.new_password)
    end_sessions(user)  # the answer's token carries the new key, so this device stays logged in
    session.add(user)
    session.commit()
    return token_response(user, request.app.state.settings)


@router.delete("", status_code=204)
def delete_account(body: Confirmation, user: UserDep, session: SessionDep):
    writable(user)
    confirm(user, body.password)
    # A job still to run would write the user's names into the cache again after they are gone.
    if accounts.busy(session, user.id):
        raise ApiError(409, "job_in_progress")
    accounts.delete_account(session, user.id)
    session.commit()
    return Response(status_code=204)

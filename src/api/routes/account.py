"""Account management (overview 5.11): see and rename the account, change its password, delete one month of it or all
of it. Logout is in routes/auth.py."""
from functools import partial
from typing import Annotated

from fastapi import APIRouter, Path, Request, Response
from pydantic import BaseModel

from .. import accounts, jobs
from ..db import SessionDep
from ..errors import ApiError
from ..security import Password, UserDep, end_sessions, hash_password, token_response, verify_password
from ..validation import DisplayName

router = APIRouter(prefix="/api/me")
Month = Annotated[str, Path(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]  # YYYY-MM


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
            "is_demo": user.is_demo, "months": accounts.uploaded_months(session, user.id)}


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
    user_id = user.id
    # The new key's UPDATE takes SQLite's write lock before the check, so no upload can commit a job between the check
    # and the deletes; a refused delete rolls it back and keeps the old key.
    end_sessions(user)
    session.add(user)
    session.flush()
    # A job still to run would write the user's names into the cache again after they are gone.
    if accounts.busy(session, user_id):
        session.rollback()
        raise ApiError(409, "job_in_progress")
    accounts.delete_account(session, user_id)
    session.commit()
    return Response(status_code=204)


@router.delete("/months/{month}", status_code=204)
def delete_month(month: Month, user: UserDep, request: Request, session: SessionDep):
    writable(user)
    # The id before the commit: the commit expires the user, so reading user.id after it costs a query whose connection
    # stays checked out until the route returns, next to the worker's (the in-memory test database has only one
    # connection for both, and closing this session would roll the recompute's write back).
    user_id = user.id
    if month not in accounts.uploaded_months(session, user_id):
        raise ApiError(404, "month_not_found")
    # It checks for an upload job of the month only once it holds SQLite's write lock (see accounts.delete_month).
    if not accounts.delete_month(session, user_id, month):
        session.rollback()
        raise ApiError(409, "job_in_progress")
    session.commit()
    state = request.app.state
    # Not here on the request's thread: an upload job of this user may be writing the profile right now. Queued behind
    # it on the worker, the recompute reads the items as they are when it runs. Until it has, /api/me/profile says
    # recomputing.
    state.worker.call(f"recompute for user {user_id}",
                      partial(jobs.run_recompute, state.engine, state.backends, state.context, user_id),
                      user_id=user_id)
    return Response(status_code=204)

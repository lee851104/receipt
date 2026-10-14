"""Password hashes, access tokens, and the logged-in user behind a request."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlmodel import Session

from .db import get_session
from .errors import ApiError
from .tables import User

HASHER = PasswordHash.recommended()  # argon2
# Checked when there is no password to check, so a wrong username takes as long as a wrong password.
DUMMY_HASH = HASHER.hash("no account has this password")
ALGORITHM = "HS256"
# auto_error=False: a missing token reaches current_user, which answers in the API's own error format.
bearer = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password):
    return HASHER.hash(password)


def verify_password(password, hashed):
    """Whether password matches hashed; always False without a hash (no such user, or a demo user)."""
    if hashed is None:
        HASHER.verify(password, DUMMY_HASH)
        return False
    return HASHER.verify(password, hashed)


def create_token(user_id, settings, now=None):
    now = now or datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "exp": now + timedelta(minutes=settings.jwt_expire_minutes)}
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)


def read_token(token, settings):
    """The user id a token was issued for, or None when it is forged, broken or expired."""
    try:
        return int(jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


def token_response(user, settings):
    """What login and demo-login send back."""
    return {"access_token": create_token(user.id, settings), "token_type": "bearer",
            "expires_in": settings.jwt_expire_minutes * 60}


def current_user(request: Request, token: Annotated[str | None, Depends(bearer)],
                 session: Annotated[Session, Depends(get_session)]):
    """The user the bearer token names; 401 not_authenticated when there is no valid token."""
    user_id = None if token is None else read_token(token, request.app.state.settings)
    user = None if user_id is None else session.get(User, user_id)
    if user is None:
        raise ApiError(401, "not_authenticated", headers={"WWW-Authenticate": "Bearer"})
    return user
